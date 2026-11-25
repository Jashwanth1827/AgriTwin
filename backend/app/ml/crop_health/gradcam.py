"""Grad-CAM explainability for supported CNN architectures."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import torch
from PIL import Image
from torch import nn


def jet_colormap(values: np.ndarray) -> np.ndarray:
    """OpenCV-compatible JET colour map for a float array in ``[0, 1]``.

    Implemented with NumPy so the runtime image does not need OpenCV.
    Returns an ``H x W x 3`` RGB array in ``[0, 1]``.
    """
    x = np.clip(np.asarray(values, dtype=np.float32), 0.0, 1.0)
    red = np.clip(1.5 - np.abs(4.0 * x - 3.0), 0.0, 1.0)
    green = np.clip(1.5 - np.abs(4.0 * x - 2.0), 0.0, 1.0)
    blue = np.clip(1.5 - np.abs(4.0 * x - 1.0), 0.0, 1.0)
    return np.stack([red, green, blue], axis=-1)


def resolve_target_layer(model: nn.Module, architecture: str) -> nn.Module:
    if architecture.startswith("efficientnet"):
        return model.features[-1]
    if architecture.startswith("resnet"):
        return model.layer4[-1]
    if architecture.startswith("mobilenet"):
        return model.features[-1]
    if architecture.startswith("convnext"):
        # torchvision ConvNeXt features: [0]=stem, [1..4]=stages; [-1][-1] is the
        # final ConvNeXt block, whose 4-D output is suitable for Grad-CAM.
        return model.features[-1][-1]
    if architecture.startswith("efficientnet_v2"):
        return model.features[-1]
    raise ValueError(f"Grad-CAM is not configured for architecture '{architecture}'")


class GradCAM:
    def __init__(self, model: nn.Module, target_layer: nn.Module) -> None:
        self.model = model
        self.activations: torch.Tensor | None = None
        self.gradients: torch.Tensor | None = None
        self._handles = [
            target_layer.register_forward_hook(self._forward_hook),
            target_layer.register_full_backward_hook(self._backward_hook),
        ]

    def _forward_hook(self, _module, _inputs, output) -> None:
        self.activations = output

    def _backward_hook(self, _module, _grad_input, grad_output) -> None:
        self.gradients = grad_output[0]

    def generate(self, input_tensor: torch.Tensor, class_index: int) -> np.ndarray:
        # Callers often run inference under torch.no_grad(); backpropagation for the
        # CAM needs gradients enabled regardless of that outer context.
        with torch.enable_grad():
            self.model.zero_grad(set_to_none=True)
            output = self.model(input_tensor)
            score = output[0, class_index]
            score.backward()
        if self.activations is None or self.gradients is None:
            raise RuntimeError("Grad-CAM hooks did not capture activations")
        weights = self.gradients.mean(dim=(2, 3), keepdim=True)
        cam = torch.relu((weights * self.activations).sum(dim=1))[0]
        cam = cam.detach().cpu().numpy()
        cam -= cam.min()
        maximum = cam.max()
        if maximum > 0:
            cam /= maximum
        return cam

    def close(self) -> None:
        for handle in self._handles:
            handle.remove()


def save_gradcam_visuals(
    cam: np.ndarray,
    image: Image.Image,
    output_dir: Path,
    stem: str,
    input_size: int,
) -> tuple[Path, Path]:
    """Save a heatmap and an overlay at the model input resolution."""
    output_dir.mkdir(parents=True, exist_ok=True)
    base = image.convert("RGB").resize((input_size, input_size))
    cam_image = Image.fromarray(np.asarray(cam, dtype=np.float32), mode="F")
    cam_resized = np.asarray(
        cam_image.resize((input_size, input_size), Image.BILINEAR), dtype=np.float32
    )
    cam_resized = np.clip(cam_resized, 0.0, 1.0)
    heatmap = np.uint8(255 * jet_colormap(cam_resized))
    base_array = np.asarray(base).astype(np.float32)
    overlay = np.clip(0.55 * base_array + 0.45 * heatmap.astype(np.float32), 0, 255).astype(np.uint8)

    heatmap_path = output_dir / f"{stem}_heatmap.png"
    overlay_path = output_dir / f"{stem}_overlay.png"
    Image.fromarray(heatmap).save(heatmap_path)
    Image.fromarray(overlay).save(overlay_path)
    return heatmap_path, overlay_path
