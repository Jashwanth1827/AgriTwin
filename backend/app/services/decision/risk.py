"""Risk scoring for the decision engine.

The score is a weighted sum of eight normalised components.  Weights live in
``config/decision_policy.json`` and are validated to sum to 1.0.  Every
component is in ``[0, 1]`` where 1 means the highest risk.  The module is pure
Python and has no database or framework dependencies so it can be unit-tested
directly.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.services.decision.models import (
    BuyerEvaluation,
    DecisionInput,
    HealthInfo,
    PriceInfo,
    YieldInfo,
)
from app.services.decision.policy import DecisionPolicy


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def relative_half_width(low: float | None, high: float | None, centre: float | None) -> float | None:
    """Half the interval width relative to the centre (dimensionless)."""
    if low is None or high is None or centre is None or centre <= 0:
        return None
    return max(0.0, (float(high) - float(low)) / 2.0 / float(centre))


@dataclass
class RiskComponent:
    name: str
    label: str
    value: float
    weight: float
    contribution: float
    description: str
    available: bool = True


@dataclass
class RiskAssessment:
    score: float
    category: str
    components: list[RiskComponent] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)

    @property
    def by_name(self) -> dict[str, RiskComponent]:
        return {component.name: component for component in self.components}

    def to_dict(self) -> dict[str, float]:
        return {component.name: round(component.value, 4) for component in self.components}


def _yield_component(info: YieldInfo, policy: DecisionPolicy) -> RiskComponent:
    if not info.available or info.mean_total_quintals is None:
        return RiskComponent(
            "yield_uncertainty",
            "Yield uncertainty",
            0.55,
            policy.risk.weights.yield_uncertainty,
            0.0,
            "No yield prediction was available; a moderate uncertainty penalty is applied.",
            available=False,
        )
    half_width = relative_half_width(
        info.low_total_quintals, info.high_total_quintals, info.mean_total_quintals
    )
    if half_width is None:
        value = 0.45
        description = "Yield prediction has no interval; using a conservative uncertainty penalty."
    else:
        reference = max(policy.risk.yield_relative_half_width_reference, 1e-6)
        value = clamp(half_width / reference)
        description = (
            f"80% yield interval is ±{half_width:.0%} of the point estimate "
            f"(reference ±{reference:.0%})."
        )
    return RiskComponent(
        "yield_uncertainty",
        "Yield uncertainty",
        value,
        policy.risk.weights.yield_uncertainty,
        0.0,
        description,
    )


def _price_component(info: PriceInfo, policy: DecisionPolicy) -> RiskComponent:
    if not info.available or info.expected is None:
        return RiskComponent(
            "price_uncertainty",
            "Price uncertainty",
            0.60,
            policy.risk.weights.price_uncertainty,
            0.0,
            "No market price forecast was available; price risk is treated as high.",
            available=False,
        )
    half_width = relative_half_width(info.lower, info.upper, info.expected)
    if half_width is None:
        value = 0.40
        description = "Price forecast has no interval; using a conservative uncertainty penalty."
    else:
        reference = max(policy.risk.price_relative_half_width_reference, 1e-6)
        value = clamp(half_width / reference)
        description = (
            f"Price interval is ±{half_width:.0%} of the expected price "
            f"(reference ±{reference:.0%})."
        )
    return RiskComponent(
        "price_uncertainty",
        "Price uncertainty",
        value,
        policy.risk.weights.price_uncertainty,
        0.0,
        description,
    )


def _health_component(info: HealthInfo, policy: DecisionPolicy) -> RiskComponent:
    if not info.available or info.is_healthy is None:
        return RiskComponent(
            "crop_health",
            "Crop health",
            0.45,
            policy.risk.weights.crop_health,
            0.0,
            "No crop-health scan was available; a moderate risk penalty is applied.",
            available=False,
        )
    if info.is_healthy:
        value = 0.05
        description = "Latest crop-health scan classified the crop as healthy."
    else:
        # Severity drives the score; low-confidence detections are less certain
        # but still warrant caution.
        value = clamp(0.35 + 0.65 * float(info.severity))
        description = (
            f"Latest scan detected {info.label or 'a disease'} "
            f"(severity {info.severity:.0%}, confidence {info.confidence:.0%})."
        )
    return RiskComponent(
        "crop_health",
        "Crop health",
        value,
        policy.risk.weights.crop_health,
        0.0,
        description,
    )


def _weather_component(inputs: DecisionInput) -> RiskComponent:
    value = clamp(float(inputs.weather_risk))
    if value >= 0.66:
        label = "elevated"
    elif value >= 0.33:
        label = "moderate"
    else:
        label = "low"
    return RiskComponent(
        "weather",
        "Weather",
        value,
        0.0,
        label,
        f"Weather risk is {label} ({value:.0%}) for the farm location.",
    )


def _buyer_component(
    evaluation: BuyerEvaluation | None, inputs: DecisionInput, policy: DecisionPolicy
) -> RiskComponent:
    if evaluation is None:
        return RiskComponent(
            "buyer_offer",
            "Buyer offer",
            0.55,
            policy.risk.weights.buyer_offer,
            0.0,
            "No buyer offer is available; sale would rely on the mandi price forecast.",
            available=False,
        )
    parts: list[float] = []
    notes: list[str] = []
    # Offer freshness: a two-week-old offer is treated as fully stale.
    freshness = clamp(evaluation.offer_freshness_days / 14.0)
    parts.append(freshness)
    notes.append(f"offer age {evaluation.offer_freshness_days}d")
    # Expiry proximity: expiring within 3 days is high risk.
    days_to_expiry = max(0, (evaluation.offer_expiry - inputs.today).days)
    parts.append(clamp(1.0 - days_to_expiry / 3.0))
    notes.append(f"expires in {days_to_expiry}d")
    if evaluation.buyer_is_demo:
        parts.append(0.75)
        notes.append("demo buyer")
    if evaluation.distance_method == "approximate" or evaluation.transport_cost is None:
        parts.append(0.55)
        notes.append("approximate transport")
    value = clamp(sum(parts) / len(parts))
    return RiskComponent(
        "buyer_offer",
        "Buyer offer",
        value,
        policy.risk.weights.buyer_offer,
        0.0,
        "Buyer-offer risk based on " + ", ".join(notes) + ".",
    )


def _transport_component(
    evaluation: BuyerEvaluation | None, inputs: DecisionInput, policy: DecisionPolicy
) -> RiskComponent:
    if not inputs.transport_available:
        return RiskComponent(
            "transport",
            "Transport",
            0.80,
            policy.risk.weights.transport,
            0.0,
            "No routing provider was available; transport cost is uncertain.",
            available=False,
        )
    if evaluation is None or evaluation.distance_km is None:
        return RiskComponent(
            "transport",
            "Transport",
            0.50,
            policy.risk.weights.transport,
            0.0,
            "No distance estimate is available for the selected buyer.",
            available=False,
        )
    distance_risk = clamp(evaluation.distance_km / 500.0)
    approximate = 0.25 if evaluation.distance_method != "osrm" else 0.0
    value = clamp(0.15 + 0.6 * distance_risk + approximate)
    return RiskComponent(
        "transport",
        "Transport",
        value,
        policy.risk.weights.transport,
        0.0,
        (
            f"{evaluation.distance_km:.0f} km by "
            f"{evaluation.distance_method or 'unknown'} route"
            + (" (approximate geodesic distance)" if approximate else "")
            + "."
        ),
    )


def _freshness_component(info: PriceInfo, policy: DecisionPolicy) -> RiskComponent:
    reference = max(policy.risk.market_freshness_reference_days, 1.0)
    if info.age_days is None:
        value = 0.50
        description = "Market data age is unknown."
    else:
        value = clamp(float(info.age_days) / reference)
        description = (
            f"Latest market observation is {info.age_days} day(s) old "
            f"(reference {reference:.0f} days)."
        )
    return RiskComponent(
        "market_freshness",
        "Market data freshness",
        value,
        policy.risk.weights.market_freshness,
        0.0,
        description,
    )


def compute_risk(
    inputs: DecisionInput,
    policy: DecisionPolicy,
    *,
    selected_buyer: BuyerEvaluation | None,
    data_completeness: float,
    weather_available: bool = False,
) -> RiskAssessment:
    """Return the weighted risk score and its explainable components."""
    weights = policy.risk.weights
    components = [
        _yield_component(inputs.yield_info, policy),
        _price_component(inputs.price_info, policy),
        _health_component(inputs.health_info, policy),
        _weather_component(inputs),
        _buyer_component(selected_buyer, inputs, policy),
        _transport_component(selected_buyer, inputs, policy),
    ]
    components[3].weight = weights.weather
    if not weather_available:
        components[3].value = max(components[3].value, 0.40)
        components[3].description += " No live weather feed was used; a floor is applied."
        components[3].available = False

    completeness_component = RiskComponent(
        "data_completeness",
        "Data completeness",
        clamp(1.0 - data_completeness),
        weights.data_completeness,
        0.0,
        f"{data_completeness:.0%} of expected decision inputs were available.",
    )
    components.append(completeness_component)
    components.append(_freshness_component(inputs.price_info, policy))

    score = 0.0
    for component in components:
        component.contribution = component.value * component.weight
        score += component.contribution
    score = clamp(score)

    if score <= policy.risk.low_max:
        category = "low"
    elif score <= policy.risk.medium_max:
        category = "medium"
    else:
        category = "high"

    missing = [component.name for component in components if not component.available]
    return RiskAssessment(score=score, category=category, components=components, missing=missing)


def risk_adjusted_net(net: float | None, gross: float | None, risk: float, policy: DecisionPolicy) -> float | None:
    """Apply a simple risk premium to a net-realisation estimate."""
    if net is None:
        return None
    if gross is None or gross <= 0:
        return net
    premium = policy.risk.risk_premium_lambda * clamp(risk) * gross
    return net - premium
