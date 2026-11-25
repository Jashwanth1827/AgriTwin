from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class YieldPredictRequest(BaseModel):
    farm_id: int
    crop_id: int
    growth_stage_override: str | None = None


class YieldPredictionOut(ORMModel):
    id: int
    farm_id: int
    crop_id: int
    model_version: str
    model_name: str
    predicted_yield_per_hectare: float
    predicted_total_quintals: float | None
    lower_yield_per_hectare: float | None
    upper_yield_per_hectare: float | None
    lower_total_quintals: float | None
    upper_total_quintals: float | None
    interval_method: str
    interval_coverage: float | None
    confidence: float
    input_completeness: float
    is_experimental: bool
    inputs: dict
    notes: str | None
    predicted_at: datetime


class HarvestReadinessOut(BaseModel):
    crop: str
    sowing_date: date
    expected_harvest_date: date | None
    estimated_days_remaining: int | None
    harvest_window_start: date | None
    harvest_window_end: date | None
    readiness_status: str
    confidence: float
    notes: str
    weather_considerations: list[str] = Field(default_factory=list)
    calendar_source: str


class YieldModelInfo(BaseModel):
    available: bool
    model_version: str | None = None
    model_name: str | None = None
    metrics: dict | None = None
    dataset_provenance: str | None = None
    features: list[str] = Field(default_factory=list)
    interval_method: str | None = None
    message: str | None = None


class YieldPredictionDetail(BaseModel):
    prediction: YieldPredictionOut
    harvest_readiness: HarvestReadinessOut
    model: YieldModelInfo
