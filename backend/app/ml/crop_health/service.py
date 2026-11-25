"""Crop-health inference service with optional demo fallback.

Real mode uses the trained EfficientNet/ConvNeXt/ResNet/MobileNet artifact and
Grad-CAM. Artifact metadata may request 4-view test-time augmentation (TTA),
which is applied identically by serving and ``tta_eval.py``. If the artifact is
absent, demo mode produces a clearly-labelled heuristic result so that the
product workflow can still be demonstrated. Demo results are never presented
as a trained-model diagnosis.
"""

from __future__ import annotations

import json
import logging
import threading
import time
import uuid
from pathlib import Path
from typing import Any

import numpy as np
import torch
from PIL import Image
from torch import nn
from torchvision import transforms

from app.core.config import settings
from app.ml.crop_health.exg import ExGBackgroundSuppression
from app.ml.crop_health.gradcam import GradCAM, resolve_target_layer, save_gradcam_visuals
from app.ml.crop_health.labels import (
    class_crop,
    class_display,
    is_healthy,
    normalise_crop,
    recommendation_bundle,
    severity_for,
)

logger = logging.getLogger(__name__)

IMAGENET_MEAN = [0.485, 0.456, 0.406]
IMAGENET_STD = [0.229, 0.224, 0.225]
DEFAULT_CROP_PRIOR_ALPHA = 0.0


class CropHealthModelUnavailable(RuntimeError):
    pass


def build_architecture(architecture: str, num_classes: int) -> nn.Module:
    from torchvision import models

    if architecture == "efficientnet_b0":
        model = models.efficientnet_b0(weights=None)
        model.classifier[1] = nn.Linear(model.classifier[1].in_features, num_classes)
        return model
    if architecture == "efficientnet_b3":
        model = models.efficientnet_b3(weights=None)
        model.classifier[1] = nn.Linear(model.classifier[1].in_features, num_classes)
        return model
    if architecture == "resnet50":
        model = models.resnet50(weights=None)
        model.fc = nn.Linear(model.fc.in_features, num_classes)
        return model
    if architecture == "mobilenet_v3_large":
        model = models.mobilenet_v3_large(weights=None)
        model.classifier[3] = nn.Linear(model.classifier[3].in_features, num_classes)
        return model
    if architecture == "convnext_tiny":
        model = models.convnext_tiny(weights=None)
        model.classifier[2] = nn.Linear(model.classifier[2].in_features, num_classes)
        return model
    if architecture == "convnext_small":
        model = models.convnext_small(weights=None)
        model.classifier[2] = nn.Linear(model.classifier[2].in_features, num_classes)
        return model
    if architecture == "efficientnet_v2_s":
        model = models.efficientnet_v2_s(weights=None)
        model.classifier[1] = nn.Linear(model.classifier[1].in_features, num_classes)
        return model
    raise ValueError(f"Unsupported crop-health architecture: {architecture}")


def _tail_steps(model_meta: dict[str, Any]) -> list:
    """Preprocessing after resize/crop, shared by single-view and TTA paths."""
    steps: list = []
    if model_meta.get("exg_suppression"):
        steps.append(
            ExGBackgroundSuppression(
                strength=float(model_meta.get("exg_strength", 0.8))
            )
        )
    steps += [
        transforms.ToTensor(),
        transforms.Normalize(IMAGENET_MEAN, IMAGENET_STD),
    ]
    return steps


def tta_view_probabilities(
    model: nn.Module,
    model_meta: dict[str, Any],
    image: Image.Image,
    views: int = 1,
    device: torch.device | None = None,
) -> tuple[list[torch.Tensor], torch.Tensor]:
    """Return per-view probabilities and the first (unflipped) input tensor.

    The view grid is identical to ``ml/crop_health/evaluation/tta_eval.py``:
    1 = original, 2 = original + horizontal flip, 4 = flip × scale 1.0/0.9.
    The returned tensor is the original view and is used for Grad-CAM so the
    explanation always corresponds to a real input view.
    """
    crop = int(model_meta.get("input_size", 224))
    resize = int(model_meta.get("resize_size", int(crop * 1.14)))
    if views <= 1:
        configs = ((1.0, False),)
    elif views == 2:
        configs = ((1.0, False), (1.0, True))
    else:
        configs = ((1.0, False), (1.0, True), (0.9, False), (0.9, True))

    probabilities: list[torch.Tensor] = []
    base_tensor: torch.Tensor | None = None
    for scale, flip in configs:
        working = image.transpose(Image.Transpose.FLIP_LEFT_RIGHT) if flip else image
        target = max(crop, int(resize * scale))
        tensor = transforms.Compose(
            [transforms.Resize(target), transforms.CenterCrop(crop), *_tail_steps(model_meta)]
        )(working)
        if base_tensor is None:
            base_tensor = tensor
        model_input = tensor.to(device) if device is not None else tensor
        with torch.no_grad():
            probabilities.append(torch.softmax(model(model_input.unsqueeze(0)), dim=1)[0])
    assert base_tensor is not None
    return probabilities, base_tensor


def tta_probabilities(
    model: nn.Module,
    model_meta: dict[str, Any],
    image: Image.Image,
    views: int = 1,
    device: torch.device | None = None,
) -> tuple[torch.Tensor, torch.Tensor]:
    """Average the configured views and return the base view for Grad-CAM."""
    probabilities, base_tensor = tta_view_probabilities(
        model, model_meta, image, views, device
    )
    return torch.stack(probabilities).mean(dim=0), base_tensor


def apply_crop_prior(
    probabilities: torch.Tensor,
    classes: list[str],
    crop_hint: str | None,
    alpha: float = DEFAULT_CROP_PRIOR_ALPHA,
) -> tuple[torch.Tensor, str | None, float]:
    """Softly reweight probabilities toward classes of the selected crop.

    ``alpha=0`` is a no-op; ``alpha=1`` is a hard mask.  The deployed artifact
    sets 0.95, which keeps a route back to the unconstrained prediction if the
    crop selection is wrong.  Unsupported crop names are ignored so the endpoint
    never invents classes that the model was not trained on.
    """
    group = normalise_crop(crop_hint)
    if group is None or not 0.0 < alpha <= 1.0:
        return probabilities, None, 0.0
    indices = [i for i, label in enumerate(classes) if class_crop(label) == group]
    if not indices:
        return probabilities, None, 0.0
    mask = torch.zeros_like(probabilities)
    mask[indices] = 1.0
    adjusted = probabilities * (1.0 - alpha + alpha * mask)
    adjusted = adjusted / adjusted.sum()
    return adjusted, group, float(alpha)


class CropHealthService:
    _instance: "CropHealthService | None" = None
    _lock = threading.Lock()

    def __init__(self, artifact_dir: Path | None = None) -> None:
        self.artifact_dir = Path(artifact_dir or settings.CROP_HEALTH_ARTIFACT_DIR)
        self._model: nn.Module | None = None
        self._metadata: dict[str, Any] | None = None
        self._loaded = False
        self._load_error: str | None = None
        self._tta_views = 1

    @classmethod
    def instance(cls) -> "CropHealthService":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def _ensure_loaded(self) -> None:
        if self._loaded:
            return
        with self._lock:
            if self._loaded:
                return
            metadata_path = self.artifact_dir / "metadata.json"
            weights_path = self.artifact_dir / "model.pt"
            if not metadata_path.exists() or not weights_path.exists():
                self._load_error = (
                    "Crop-health model weights were not found. Run "
                    "`python ml/crop_health/training/train.py` to train the model, or use demo mode."
                )
                self._loaded = True
                return
            try:
                with metadata_path.open("r", encoding="utf-8") as handle:
                    self._metadata = json.load(handle)
                architecture = self._metadata["architecture"]
                classes = self._metadata["classes"]
                model = build_architecture(architecture, len(classes))
                state = torch.load(weights_path, map_location="cpu", weights_only=True)
                model.load_state_dict(state)
                model.eval()
                self._model = model
                self._tta_views = max(1, int(self._metadata.get("tta_views", 1)))
                self._loaded = True
                logger.info("Loaded crop-health model %s", self._metadata.get("version"))
            except Exception as exc:  # pragma: no cover - corrupt artifact path
                self._load_error = f"Failed to load crop-health model: {exc}"
                self._loaded = True
                logger.exception("Crop-health model load failed")

    @property
    def available(self) -> bool:
        self._ensure_loaded()
        return self._model is not None

    def info(self) -> dict[str, Any]:
        self._ensure_loaded()
        if not self._model or not self._metadata:
            return {
                "available": False,
                "mode": "demo" if settings.DEMO_MODE else "unavailable",
                "classes": [],
                "message": self._load_error,
            }
        return {
            "available": True,
            "model_version": self._metadata.get("version"),
            "architecture": self._metadata.get("architecture"),
            "tta_views": self._tta_views,
            "crop_prior_alpha": float(
                self._metadata.get("crop_prior_alpha", DEFAULT_CROP_PRIOR_ALPHA)
            ),
            "mode": "real",
            "classes": self._metadata.get("classes", []),
            "metrics": self._metadata.get("metrics"),
            "dataset_provenance": self._metadata.get("dataset_provenance"),
            "message": None,
        }

    def predict(
        self,
        image_path: Path,
        *,
        output_dir: Path,
        explanation_stem: str | None = None,
        crop_hint: str | None = None,
    ) -> dict[str, Any]:
        self._ensure_loaded()
        if not self._model or not self._metadata:
            if not settings.DEMO_MODE:
                raise CropHealthModelUnavailable(self._load_error or "Model unavailable")
            return self._demo_predict(image_path, output_dir)

        started = time.perf_counter()
        image = Image.open(image_path).convert("RGB")
        probabilities, base_tensor = tta_probabilities(
            self._model, self._metadata, image, self._tta_views
        )
        classes = self._metadata["classes"]
        alpha = float(
            self._metadata.get("crop_prior_alpha", DEFAULT_CROP_PRIOR_ALPHA)
        )
        probabilities, prior_group, applied_alpha = apply_crop_prior(
            probabilities, classes, crop_hint, alpha
        )
        top_probabilities, top_indices = torch.topk(probabilities, k=min(5, len(probabilities)))
        top = [
            {"label": classes[int(idx)], "display": class_display(classes[int(idx)]), "probability": round(float(prob), 6)}
            for prob, idx in zip(top_probabilities, top_indices)
        ]
        best_index = int(top_indices[0])
        label = classes[best_index]
        confidence = float(top_probabilities[0])

        gradcam_path: Path | None = None
        gradcam_error: str | None = None
        try:
            target = resolve_target_layer(self._model, self._metadata["architecture"])
            cam = GradCAM(self._model, target)
            try:
                input_size = int(self._metadata.get("input_size", 224))
                cam_array = cam.generate(base_tensor.unsqueeze(0), best_index)
                stem = explanation_stem or f"prediction_{uuid.uuid4().hex[:10]}"
                _, overlay_path = save_gradcam_visuals(
                    cam_array, image, output_dir, stem, input_size
                )
                gradcam_path = overlay_path
            finally:
                cam.close()
        except Exception as exc:  # pragma: no cover - architecture-specific
            gradcam_error = str(exc)
            logger.warning("Grad-CAM generation failed: %s", exc)

        inference_ms = round((time.perf_counter() - started) * 1000, 2)
        note_parts: list[str] = []
        if self._tta_views > 1:
            note_parts.append(
                f"{self._tta_views}-view test-time augmentation averaged before prediction"
            )
        if prior_group:
            note_parts.append(
                f"crop prior alpha {applied_alpha:g} applied to {prior_group} classes"
            )
        if gradcam_error:
            note_parts.append(f"Grad-CAM could not be generated: {gradcam_error}")
        notes = "; ".join(note_parts) or None

        return {
            "label": label,
            "display_label": class_display(label),
            "crop": class_crop(label),
            "is_healthy": is_healthy(label),
            "confidence": round(confidence, 6),
            "severity": severity_for(label),
            "probabilities": {item["label"]: item["probability"] for item in top},
            "top_predictions": top,
            "model_version": self._metadata.get("version", "unknown"),
            "model_mode": "real",
            "is_demo": False,
            "inference_views": self._tta_views,
            "crop_prior_applied": prior_group is not None,
            "crop_prior_group": prior_group,
            "crop_prior_alpha": applied_alpha,
            "gradcam_path": str(gradcam_path) if gradcam_path else None,
            "inference_ms": inference_ms,
            "recommendations": recommendation_bundle(label, confidence),
            "notes": notes,
            "metrics": self._metadata.get("metrics"),
            "dataset_provenance": self._metadata.get("dataset_provenance"),
        }

    def _demo_predict(self, image_path: Path, output_dir: Path) -> dict[str, Any]:
        """Heuristic demo classifier — explicitly labelled and not a diagnosis."""
        started = time.perf_counter()
        image = Image.open(image_path).convert("RGB").resize((224, 224))
        array = np.asarray(image).astype(np.float32) / 255.0
        red, green, blue = array[..., 0], array[..., 1], array[..., 2]
        green_mask = (green > red * 1.08) & (green > blue * 1.08) & (green > 0.2)
        yellow_mask = (red > 0.35) & (green > 0.3) & (blue < 0.35) & (red > blue * 1.25)
        dark_mask = (red + green + blue) / 3 < 0.18
        green_ratio = float(green_mask.mean())
        yellow_ratio = float(yellow_mask.mean())
        dark_ratio = float(dark_mask.mean())

        if green_ratio >= 0.35 and yellow_ratio < 0.15 and dark_ratio < 0.10:
            label = "Tomato___healthy"
            confidence = min(0.60, 0.42 + green_ratio * 0.25)
        elif yellow_ratio >= 0.20:
            label = "Tomato___Early_blight"
            confidence = min(0.58, 0.38 + yellow_ratio * 0.35)
        else:
            label = "Tomato___Septoria_leaf_spot"
            confidence = 0.40

        inference_ms = round((time.perf_counter() - started) * 1000, 2)
        note = (
            "DEMO MODE: no trained crop-health weights are installed. This result comes from a "
            "transparent colour-heuristic placeholder, is not a model diagnosis, and must not be "
            "used for treatment decisions. Train the CNN to enable real inference and Grad-CAM."
        )
        return {
            "label": label,
            "display_label": class_display(label) + " (demo)",
            "crop": class_crop(label),
            "is_healthy": is_healthy(label),
            "confidence": round(confidence, 4),
            "severity": severity_for(label),
            "probabilities": {label: round(confidence, 4)},
            "top_predictions": [{"label": label, "display": class_display(label), "probability": round(confidence, 4)}],
            "model_version": "demo-heuristic-v1",
            "model_mode": "demo",
            "is_demo": True,
            "gradcam_path": None,
            "inference_ms": inference_ms,
            "recommendations": recommendation_bundle(label, confidence),
            "notes": note,
            "metrics": None,
            "dataset_provenance": "Not applicable — demo heuristic, no trained model.",
        }

    def reload(self) -> None:
        with self._lock:
            self._loaded = False
            self._model = None
            self._metadata = None
            self._load_error = None
        self._ensure_loaded()
