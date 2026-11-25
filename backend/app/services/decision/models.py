"""Structured inputs and outputs of the decision engine.

These dataclasses are intentionally independent of FastAPI and SQLAlchemy so
that the engine can be unit-tested as pure business logic.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date


@dataclass
class YieldInfo:
    available: bool = False
    mean_total_quintals: float | None = None
    low_total_quintals: float | None = None
    high_total_quintals: float | None = None
    per_hectare: float | None = None
    low_per_hectare: float | None = None
    high_per_hectare: float | None = None
    confidence: float = 0.0
    completeness: float = 0.0
    is_demo: bool = False
    model_version: str | None = None
    age_days: int | None = None


@dataclass
class HealthInfo:
    available: bool = False
    is_healthy: bool | None = None
    severity: float = 0.0
    confidence: float = 0.0
    label: str | None = None
    is_demo: bool = False
    age_days: int | None = None


@dataclass
class PricePoint:
    date: date
    expected: float
    lower: float | None = None
    upper: float | None = None


@dataclass
class PriceInfo:
    available: bool = False
    expected: float | None = None
    lower: float | None = None
    upper: float | None = None
    horizon_days: int = 0
    age_days: int | None = None
    model_name: str | None = None
    is_demo: bool = False
    points: list[PricePoint] = field(default_factory=list)
    market: str | None = None


@dataclass
class BuyerInput:
    buyer_id: int
    buyer_name: str
    offer_id: int
    offered_price_per_quintal: float
    min_quantity_quintals: float
    max_quantity_quintals: float | None
    offer_date: date
    expiry_date: date
    crop: str
    distance_km: float | None = None
    distance_method: str | None = None
    transport_cost: float | None = None
    trips: int | None = None
    transport_is_approximate: bool = False
    is_demo: bool = False
    has_coordinates: bool = True
    is_active: bool = True


@dataclass
class HarvestInfo:
    ready: bool = False
    days_to_harvest: int | None = None
    status: str = "unknown"
    confidence: float = 0.5


@dataclass
class DecisionInput:
    today: date
    farm_id: int
    crop_id: int
    crop_name: str
    quantity_quintals: float
    yield_info: YieldInfo
    health_info: HealthInfo
    price_info: PriceInfo
    buyers: list[BuyerInput]
    harvest_info: HarvestInfo
    risk_preference: str = "medium"
    weather_risk: float = 0.3
    weather_available: bool = False
    transport_available: bool = True
    notes: list[str] = field(default_factory=list)


@dataclass
class BuyerEvaluation:
    buyer_id: int
    buyer_name: str
    buyer_is_demo: bool
    offer_id: int
    offered_price_per_quintal: float
    offer_expiry: date
    offer_freshness_days: int
    quantity_quintals: float
    eligible: bool
    ineligibility_reasons: list[str] = field(default_factory=list)
    distance_km: float | None = None
    distance_method: str | None = None
    transport_cost: float | None = None
    trips: int | None = None
    gross_revenue: float | None = None
    commission: float | None = None
    other_selling_costs: float | None = None
    net_realization: float | None = None
    net_realization_per_quintal: float | None = None
    risk_score: float = 0.0
    risk_adjusted_net: float | None = None
    rank: int | None = None


@dataclass
class DecisionFactor:
    factor: str
    direction: str
    weight: float | None
    value: float | None
    description: str


@dataclass
class DecisionOutcome:
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
    factors: list[DecisionFactor]
    buyer_evaluations: list[BuyerEvaluation]
    missing_inputs: list[str]
    assumptions: list[str]
    explanation: str
    data_freshness: dict
    outputs: dict
    wait_scenario: dict | None = None
