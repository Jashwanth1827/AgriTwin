from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class RecommendationOut(ORMModel):
    id: int
    title: str
    body: str
    category: str
    source: str


class CropHealthPredictionOut(ORMModel):
    id: int
    farm_id: int
    crop_id: int
    file_id: int | None
    predicted_label: str
    predicted_crop: str
    is_healthy: bool
    confidence: float
    severity: float
    probabilities: dict[str, float]
    inference_ms: float
    model_version: str
    model_mode: str
    is_demo: bool
    notes: str | None
    predicted_at: datetime
    image_url: str | None = None
    gradcam_url: str | None = None
    recommendations: list[RecommendationOut] = Field(default_factory=list)


class CropHealthPredictResponse(BaseModel):
    prediction: CropHealthPredictionOut
    model: "CropHealthModelInfo"
    disclaimer: str


class CropHealthModelInfo(BaseModel):
    available: bool
    model_version: str | None = None
    architecture: str | None = None
    tta_views: int = 1
    crop_prior_alpha: float = 0.0
    mode: str
    classes: list[str] = Field(default_factory=list)
    metrics: dict | None = None
    dataset_provenance: str | None = None
    message: str | None = None


class DiseaseClassOut(ORMModel):
    id: int
    crop: str
    name: str
    display_name: str
    is_healthy: bool
    description: str | None
    severity: str | None
    inspection_steps: list | None
    preventive_practices: list | None
    expert_advice: str | None
