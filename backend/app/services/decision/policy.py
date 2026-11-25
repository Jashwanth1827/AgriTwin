"""Typed access to the decision policy JSON."""

from __future__ import annotations

import json
from functools import lru_cache

from pydantic import BaseModel, Field

from app.core.config import settings


class FinanceConfig(BaseModel):
    commission_pct: float = Field(ge=0, le=0.2)
    other_selling_cost_per_quintal: float = Field(ge=0)


class RiskWeights(BaseModel):
    yield_uncertainty: float
    price_uncertainty: float
    crop_health: float
    weather: float
    buyer_offer: float
    transport: float
    data_completeness: float
    market_freshness: float

    def total(self) -> float:
        return sum(self.model_dump().values())


class RiskConfig(BaseModel):
    weights: RiskWeights
    yield_relative_half_width_reference: float = 0.5
    price_relative_half_width_reference: float = 0.3
    market_freshness_reference_days: float = 30
    low_max: float = 0.33
    medium_max: float = 0.66
    risk_premium_lambda: float = 0.5
    risk_preference_max_scores: dict[str, float]


class InspectPolicy(BaseModel):
    min_health_confidence: float
    max_health_severity: float
    min_data_completeness: float
    max_yield_relative_interval: float
    max_price_age_days: int


class WaitPolicy(BaseModel):
    min_days_to_harvest: int
    min_expected_wait_uplift_pct: float
    holding_cost_per_quintal_per_day: float
    crop_deterioration_per_day: float
    max_recommended_wait_days: int
    risk_margin: float = 0.05


class SellPolicy(BaseModel):
    min_net_realization_per_quintal: float


class PolicySections(BaseModel):
    inspect: InspectPolicy
    wait: WaitPolicy
    sell: SellPolicy


class FreshnessConfig(BaseModel):
    price_max_age_days: int
    weather_max_age_days: int
    prediction_max_age_days: int


class DecisionPolicy(BaseModel):
    version: str
    finance: FinanceConfig
    risk: RiskConfig
    policy: PolicySections
    freshness: FreshnessConfig


@lru_cache
def get_policy() -> DecisionPolicy:
    path = settings.DECISION_POLICY_PATH
    if not path.exists():
        raise FileNotFoundError(f"Decision policy not found: {path}")
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    policy = DecisionPolicy.model_validate(payload)
    total = policy.risk.weights.total()
    if abs(total - 1.0) > 1e-6:
        raise ValueError(f"Risk weights must sum to 1.0 (found {total})")
    return policy
