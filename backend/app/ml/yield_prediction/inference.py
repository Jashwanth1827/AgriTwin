"""Yield model inference service (CPU friendly)."""

from __future__ import annotations

import json
import logging
import threading
from pathlib import Path
from typing import Any

import joblib
import numpy as np

from app.core.config import settings

logger = logging.getLogger(__name__)


class YieldModelUnavailable(RuntimeError):
    pass


class YieldModelService:
    _instance: "YieldModelService | None" = None
    _lock = threading.Lock()

    def __init__(self, artifact_dir: Path | None = None) -> None:
        self.artifact_dir = Path(artifact_dir or settings.YIELD_ARTIFACT_DIR)
        self._bundle: dict[str, Any] | None = None
        self._load_error: str | None = None
        self._loaded = False

    @classmethod
    def instance(cls) -> "YieldModelService":
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
            model_path = self.artifact_dir / "model.joblib"
            if not model_path.exists():
                self._load_error = (
                    "Yield model artifact not found. Run "
                    "`python ml/yield_prediction/training/train.py` to train it."
                )
                self._loaded = True
                return
            try:
                self._bundle = joblib.load(model_path)
                self._loaded = True
                logger.info("Loaded yield model %s", self._bundle.get("metadata", {}).get("version"))
            except Exception as exc:  # pragma: no cover - corrupt artifact path
                self._load_error = f"Failed to load yield model: {exc}"
                self._loaded = True
                logger.exception("Yield model load failed")

    @property
    def available(self) -> bool:
        self._ensure_loaded()
        return self._bundle is not None

    def info(self) -> dict[str, Any]:
        self._ensure_loaded()
        if not self._bundle:
            return {
                "available": False,
                "message": self._load_error,
                "features": [],
            }
        metadata = self._bundle.get("metadata", {})
        return {
            "available": True,
            "model_version": metadata.get("version"),
            "model_name": metadata.get("model_name"),
            "metrics": metadata.get("metrics"),
            "dataset_provenance": metadata.get("dataset_provenance"),
            "features": metadata.get("features", []),
            "interval_method": metadata.get("interval_method"),
            "message": None,
        }

    def predict(
        self,
        *,
        state: str,
        district: str,
        crop: str,
        season: str,
        area_ha: float,
    ) -> dict[str, Any]:
        self._ensure_loaded()
        if not self._bundle:
            raise YieldModelUnavailable(self._load_error or "Yield model unavailable")

        bundle = self._bundle
        builder = bundle["builder"]
        model = bundle["model"]
        metadata = bundle["metadata"]
        half_width = float(bundle.get("conformal_half_width") or 0.0)

        frame = builder.build_inference_frame(
            state=state, district=district, crop=crop, season=season, area_ha=area_ha
        )
        features = builder.transform(frame)
        prediction = float(model.predict(features)[0])
        prediction = max(prediction, 0.0)
        lower = max(prediction - half_width, 0.0)
        upper = max(prediction + half_width, prediction)

        coverage = metadata.get("metrics", {}).get("interval_coverage")
        confidence = 0.55
        if coverage is not None:
            confidence = float(np.clip(0.35 + 0.55 * float(coverage), 0.35, 0.9))

        return {
            "yield_per_hectare": round(prediction, 3),
            "lower_yield_per_hectare": round(lower, 3),
            "upper_yield_per_hectare": round(upper, 3),
            "model_version": metadata.get("version"),
            "model_name": metadata.get("model_name"),
            "interval_method": metadata.get("interval_method"),
            "interval_coverage": coverage,
            "confidence": round(confidence, 3),
            "is_experimental": bool(metadata.get("is_experimental", True)),
            "notes": metadata.get("notes"),
        }

    def reload(self) -> None:
        with self._lock:
            self._loaded = False
            self._bundle = None
            self._load_error = None
        self._ensure_loaded()

    def load_metadata_file(self) -> dict[str, Any] | None:
        path = self.artifact_dir / "metadata.json"
        if not path.exists():
            return None
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
