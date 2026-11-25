from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, Field


class DashboardHealthSummary(BaseModel):
    available: bool
    prediction_id: int | None = None
    predicted_label: str | None = None
    crop: str | None = None
    confidence: float | None = None
    severity: float | None = None
    is_healthy: bool | None = None
    predicted_at: datetime | None = None
    is_demo: bool = False


class DashboardYieldSummary(BaseModel):
    available: bool
    prediction_id: int | None = None
    crop: str | None = None
    yield_per_hectare: float | None = None
    total_quintals: float | None = None
    lower_total_quintals: float | None = None
    upper_total_quintals: float | None = None
    input_completeness: float | None = None
    predicted_at: datetime | None = None


class DashboardMarketSummary(BaseModel):
    available: bool
    crop: str | None = None
    market: str | None = None
    latest_price: float | None = None
    forecast_price: float | None = None
    lower_bound: float | None = None
    upper_bound: float | None = None
    latest_observation_date: date | None = None
    data_freshness_days: int | None = None
    is_demo: bool = False


class DashboardDecisionSummary(BaseModel):
    available: bool
    decision_id: int | None = None
    action: str | None = None
    selected_buyer_name: str | None = None
    net_realization: float | None = None
    net_realization_per_quintal: float | None = None
    risk_score: float | None = None
    risk_category: str | None = None
    generated_at: datetime | None = None


class FarmSummary(BaseModel):
    id: int
    name: str
    district: str
    state: str
    total_area_hectares: float
    active_crops: int
    is_demo: bool


class DashboardOverview(BaseModel):
    total_farms: int
    total_area_hectares: float
    active_crops: int
    crop_health: DashboardHealthSummary
    yield_prediction: DashboardYieldSummary
    market: DashboardMarketSummary
    decision: DashboardDecisionSummary
    farms: list[FarmSummary]
    data_mode: str
    is_demo: bool
    generated_at: datetime
    notices: list[str] = Field(default_factory=list)


class DashboardCropHealth(BaseModel):
    total_predictions: int
    healthy_count: int
    diseased_count: int
    average_confidence: float | None
    recent: list[dict]
    by_label: list[dict]
    data_mode: str


class DashboardMarket(BaseModel):
    crop: str | None
    points: list[dict]
    forecast: dict | None
    markets: list[dict]
    data_freshness_days: int | None
    data_mode: str


class DashboardDecisions(BaseModel):
    total: int
    by_action: dict[str, int]
    recent: list[dict]
    data_mode: str
