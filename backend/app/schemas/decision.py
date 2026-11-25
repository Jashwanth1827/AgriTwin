from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, Field, field_validator

from app.core.constants import RISK_PREFERENCES, VEHICLE_TYPES
from app.schemas.common import ORMModel


class DecisionRequest(BaseModel):
    farm_id: int
    crop_id: int
    risk_preference: str = "medium"
    quantity_quintals: float | None = Field(default=None, gt=0, le=100000)
    buyer_ids: list[int] | None = None
    market_name: str | None = None
    yield_prediction_id: int | None = None
    health_prediction_id: int | None = None
    price_forecast_id: int | None = None
    vehicle_type: str = "truck"
    cost_per_km: float | None = Field(default=None, gt=0, le=1000)
    auto_compute: bool = True

    @field_validator("risk_preference")
    @classmethod
    def valid_risk(cls, value: str) -> str:
        if value not in RISK_PREFERENCES:
            raise ValueError("Risk preference must be low, medium or high")
        return value

    @field_validator("vehicle_type")
    @classmethod
    def valid_vehicle(cls, value: str) -> str:
        if value not in VEHICLE_TYPES:
            raise ValueError("Unknown vehicle type")
        return value


class BuyerEvaluation(BaseModel):
    buyer_id: int
    buyer_name: str
    buyer_is_demo: bool
    offer_id: int
    offered_price_per_quintal: float
    offer_expiry: date
    offer_freshness_days: int
    quantity_quintals: float
    eligible: bool
    ineligibility_reasons: list[str] = Field(default_factory=list)
    distance_km: float | None
    distance_method: str | None
    transport_cost: float | None
    trips: int | None
    gross_revenue: float | None
    commission: float | None
    other_selling_costs: float | None
    net_realization: float | None
    net_realization_per_quintal: float | None
    risk_score: float
    risk_adjusted_net: float | None
    rank: int | None = None


class DecisionFactorOut(ORMModel):
    factor: str
    direction: str
    weight: float | None
    value: float | None
    description: str


class DecisionOut(ORMModel):
    id: int
    farm_id: int
    crop_id: int
    action: str
    selected_buyer_id: int | None
    selected_offer_id: int | None
    selected_buyer_name: str | None
    expected_yield_quintals: float
    yield_low_quintals: float | None
    yield_high_quintals: float | None
    expected_price_per_quintal: float | None
    price_low_per_quintal: float | None
    price_high_per_quintal: float | None
    gross_revenue: float | None
    transport_cost: float | None
    other_costs: float | None
    net_realization: float | None
    net_realization_per_quintal: float | None
    wait_expected_net: float | None
    risk_score: float
    risk_category: str
    data_completeness: float
    confidence: float
    policy_version: str
    explanation: str
    inputs_snapshot: dict
    outputs: dict
    generated_at: datetime
    factors: list[DecisionFactorOut] = Field(default_factory=list)
    buyer_evaluations: list[BuyerEvaluation] = Field(default_factory=list)
    missing_inputs: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    data_freshness: dict = Field(default_factory=dict)


class DecisionListItem(BaseModel):
    id: int
    action: str
    farm_id: int
    crop_id: int
    selected_buyer_name: str | None
    net_realization: float | None
    risk_score: float
    risk_category: str
    generated_at: datetime
