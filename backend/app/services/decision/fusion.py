"""Fusion helpers: completeness, confidence, freshness and revenue bounds.

These functions turn heterogeneous signals (yield interval, price forecast,
health scan, buyer offers, weather) into the scalar summaries that the decision
engine exposes to the API and the UI.  Keeping them separate makes the
weighting explicit and testable.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.services.decision.models import DecisionInput
from app.services.decision.policy import DecisionPolicy
from app.services.decision.risk import clamp, relative_half_width

# Weights sum to 1.0.  A signal that is present but of poor quality still counts
# as present; quality is handled by the risk score.
COMPLETENESS_WEIGHTS = {
    "yield": 0.25,
    "price": 0.20,
    "health": 0.15,
    "buyers": 0.15,
    "harvest": 0.10,
    "location": 0.10,
    "transport": 0.05,
}


@dataclass
class CompletenessBreakdown:
    score: float
    present: dict[str, bool]
    missing: list[str]


def completeness(inputs: DecisionInput) -> CompletenessBreakdown:
    present = {
        "yield": bool(inputs.yield_info.available and inputs.yield_info.mean_total_quintals),
        "price": bool(inputs.price_info.available and inputs.price_info.expected is not None),
        "health": bool(inputs.health_info.available),
        "buyers": bool(inputs.buyers),
        "harvest": inputs.harvest_info.status != "unknown",
        "location": bool(inputs.buyers and any(b.has_coordinates for b in inputs.buyers))
        or bool(inputs.transport_available),
        "transport": bool(inputs.transport_available),
    }
    score = sum(
        COMPLETENESS_WEIGHTS[name] for name, available in present.items() if available
    )
    missing = [name for name, available in present.items() if not available]
    return CompletenessBreakdown(score=round(clamp(score), 4), present=present, missing=missing)


def confidence(inputs: DecisionInput, completeness_score: float) -> float:
    """Blend source confidence with overall data completeness."""
    yield_conf = float(inputs.yield_info.confidence) if inputs.yield_info.available else 0.0
    health_conf = float(inputs.health_info.confidence) if inputs.health_info.available else 0.0
    price_quality = 0.0
    if inputs.price_info.available and inputs.price_info.expected:
        half_width = relative_half_width(
            inputs.price_info.lower,
            inputs.price_info.upper,
            inputs.price_info.expected,
        )
        price_quality = 1.0 - clamp((half_width or 0.25) / 0.5)
    harvest_conf = float(inputs.harvest_info.confidence)
    value = (
        0.50 * completeness_score
        + 0.20 * yield_conf
        + 0.15 * health_conf
        + 0.10 * price_quality
        + 0.05 * harvest_conf
    )
    return round(clamp(value, 0.0, 0.95), 4)


def revenue_bounds(inputs: DecisionInput) -> tuple[float | None, float | None]:
    """Conservative revenue interval (yield interval × price interval)."""
    yield_info = inputs.yield_info
    price_info = inputs.price_info
    if not yield_info.available or yield_info.mean_total_quintals is None:
        return None, None
    low_yield = yield_info.low_total_quintals or yield_info.mean_total_quintals
    high_yield = yield_info.high_total_quintals or yield_info.mean_total_quintals
    if price_info.available and price_info.expected is not None:
        low_price = price_info.lower if price_info.lower is not None else price_info.expected
        high_price = price_info.upper if price_info.upper is not None else price_info.expected
    else:
        low_price = high_price = None
    if low_price is None or high_price is None:
        return None, None
    return round(low_yield * low_price, 2), round(high_yield * high_price, 2)


def freshness(inputs: DecisionInput, policy: DecisionPolicy) -> dict:
    price_age = inputs.price_info.age_days
    health_age = inputs.health_info.age_days
    yield_age = inputs.yield_info.age_days
    warnings: list[str] = []
    if price_age is not None and price_age > policy.freshness.price_max_age_days:
        warnings.append(
            f"Market prices are {price_age} days old (limit "
            f"{policy.freshness.price_max_age_days})."
        )
    if health_age is not None and health_age > policy.freshness.prediction_max_age_days:
        warnings.append(f"The latest crop-health scan is {health_age} days old.")
    if yield_age is not None and yield_age > policy.freshness.prediction_max_age_days:
        warnings.append(f"The latest yield prediction is {yield_age} days old.")
    return {
        "price_age_days": price_age,
        "health_age_days": health_age,
        "yield_age_days": yield_age,
        "price_max_age_days": policy.freshness.price_max_age_days,
        "prediction_max_age_days": policy.freshness.prediction_max_age_days,
        "stale": bool(warnings),
        "warnings": warnings,
    }


def yield_relative_interval(inputs: DecisionInput) -> float | None:
    info = inputs.yield_info
    return relative_half_width(info.low_total_quintals, info.high_total_quintals, info.mean_total_quintals)
