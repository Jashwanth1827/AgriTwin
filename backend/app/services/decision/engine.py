"""Deterministic, explainable decision engine.

Given a yield prediction, a market-price forecast, an optional crop-health
scan, and a list of buyer offers, the engine answers one question:

    "Should this farmer sell now, wait, or inspect the crop first?"

The answer is produced by ordered, documented rules (see
``docs/DECISION_ENGINE.md``), never by a language model.  Money is calculated
with :class:`decimal.Decimal` and rounded half-up to paise.
"""

from __future__ import annotations

from dataclasses import asdict
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from app.services.decision import fusion
from app.services.decision.models import (
    BuyerEvaluation,
    BuyerInput,
    DecisionFactor,
    DecisionInput,
    DecisionOutcome,
)
from app.services.decision.policy import DecisionPolicy, get_policy
from app.services.decision.risk import clamp, compute_risk, risk_adjusted_net

PAISE = Decimal("0.01")


def money(value: float | Decimal | None) -> Decimal | None:
    if value is None:
        return None
    return Decimal(str(value)).quantize(PAISE, rounding=ROUND_HALF_UP)


def _f(value: Decimal | None) -> float | None:
    return float(value) if value is not None else None


def _ratio(numerator: float | None, denominator: float | None) -> float | None:
    if numerator is None or denominator is None or denominator == 0:
        return None
    return float(numerator) / float(denominator)


def _offer_risk(evaluation: BuyerEvaluation, today: date) -> float:
    """Standalone offer risk used for ranking (mirrors the risk component)."""
    freshness = clamp(evaluation.offer_freshness_days / 14.0)
    days_to_expiry = max(0, (evaluation.offer_expiry - today).days)
    expiry = clamp(1.0 - days_to_expiry / 3.0)
    demo = 0.75 if evaluation.buyer_is_demo else 0.0
    approximate = 0.55 if evaluation.transport_cost is None else 0.0
    parts = [freshness, expiry]
    if demo:
        parts.append(demo)
    if approximate:
        parts.append(approximate)
    return clamp(sum(parts) / len(parts))


def evaluate_buyers(
    inputs: DecisionInput, policy: DecisionPolicy
) -> list[BuyerEvaluation]:
    """Evaluate every offer for eligibility and net realisation."""
    evaluations: list[BuyerEvaluation] = []
    finance = policy.finance
    quantity = Decimal(str(inputs.quantity_quintals))
    crop_key = inputs.crop_name.strip().lower()

    for buyer in inputs.buyers:
        reasons: list[str] = []
        if not buyer.is_active:
            reasons.append("Offer is inactive")
        if buyer.crop.strip().lower() != crop_key:
            reasons.append(f"Offer is for {buyer.crop}, not {inputs.crop_name}")
        if buyer.offer_date > inputs.today:
            reasons.append("Offer starts in the future")
        if buyer.expiry_date < inputs.today:
            reasons.append("Offer has expired")
        if buyer.offered_price_per_quintal <= 0:
            reasons.append("Offer price is not positive")
        if quantity < Decimal(str(buyer.min_quantity_quintals)):
            reasons.append(
                f"Minimum quantity is {buyer.min_quantity_quintals:g} quintals"
            )

        partial = False
        sold = quantity
        if (
            buyer.max_quantity_quintals is not None
            and quantity > Decimal(str(buyer.max_quantity_quintals))
        ):
            sold = Decimal(str(buyer.max_quantity_quintals))
            partial = True

        eligible = not reasons
        price = Decimal(str(buyer.offered_price_per_quintal))
        gross = price * sold
        commission = gross * Decimal(str(finance.commission_pct))
        other = sold * Decimal(str(finance.other_selling_cost_per_quintal))
        transport: Decimal | None = None
        if buyer.transport_cost is not None:
            transport = Decimal(str(buyer.transport_cost))
            if partial and quantity > 0:
                # Approximate proportional allocation; documented as an
                # assumption because a partial load may still require a trip.
                transport = transport * sold / quantity
        net = gross - commission - other - (transport or Decimal("0"))
        net_per_quintal = net / sold if sold > 0 else None

        evaluation = BuyerEvaluation(
            buyer_id=buyer.buyer_id,
            buyer_name=buyer.buyer_name,
            buyer_is_demo=buyer.is_demo,
            offer_id=buyer.offer_id,
            offered_price_per_quintal=float(price),
            offer_expiry=buyer.expiry_date,
            offer_freshness_days=max(0, (inputs.today - buyer.offer_date).days),
            quantity_quintals=float(sold),
            eligible=eligible,
            ineligibility_reasons=reasons,
            distance_km=buyer.distance_km,
            distance_method=buyer.distance_method,
            transport_cost=_f(transport),
            trips=buyer.trips,
            gross_revenue=_f(gross),
            commission=_f(commission),
            other_selling_costs=_f(other),
            net_realization=_f(net),
            net_realization_per_quintal=_f(net_per_quintal),
            risk_score=0.0,
        )
        evaluation.risk_score = _offer_risk(evaluation, inputs.today)
        evaluation.risk_adjusted_net = risk_adjusted_net(
            evaluation.net_realization, evaluation.gross_revenue, evaluation.risk_score, policy
        )
        evaluations.append(evaluation)

    eligible = [item for item in evaluations if item.eligible]
    eligible.sort(
        key=lambda item: (
            _ratio(item.risk_adjusted_net, item.quantity_quintals) or float("-inf")
        ),
        reverse=True,
    )
    for rank, item in enumerate(eligible, start=1):
        item.rank = rank
    return evaluations


def _market_scenario(inputs: DecisionInput, policy: DecisionPolicy) -> dict:
    info = inputs.price_info
    if not info.available or info.expected is None:
        return {}
    quantity = Decimal(str(inputs.quantity_quintals))
    price = Decimal(str(info.expected))
    gross = price * quantity
    commission = gross * Decimal(str(policy.finance.commission_pct))
    other = quantity * Decimal(str(policy.finance.other_selling_cost_per_quintal))
    net = gross - commission - other
    return {
        "channel": "mandi",
        "market": info.market,
        "price_per_quintal": float(price),
        "quantity_quintals": float(quantity),
        "gross_revenue": _f(gross),
        "commission": _f(commission),
        "other_selling_costs": _f(other),
        "transport_cost": None,
        "net_realization": _f(net),
        "net_realization_per_quintal": _f(net / quantity if quantity else None),
    }


def _wait_scenario(
    inputs: DecisionInput,
    policy: DecisionPolicy,
    *,
    immediate_net: float | None,
    immediate_price: float | None,
    best_buyer: BuyerEvaluation | None,
) -> dict:
    wait_policy = policy.policy.wait
    points = sorted(
        [point for point in inputs.price_info.points if point.date > inputs.today],
        key=lambda point: point.date,
    )
    harvest_days = inputs.harvest_info.days_to_harvest
    if not inputs.harvest_info.ready and harvest_days and harvest_days > 0:
        wait_days = min(harvest_days, wait_policy.max_recommended_wait_days)
        reason = f"Crop is not ready; harvest is estimated in {harvest_days} day(s)."
    elif points:
        candidate = min(
            points,
            key=lambda point: abs((point.date - inputs.today).days),
        )
        wait_days = max(1, min((candidate.date - inputs.today).days, wait_policy.max_recommended_wait_days))
        reason = "Price forecast indicates a possible improvement."
    else:
        return {
            "recommended": False,
            "reason": "No future price forecast or harvest delay is available.",
        }

    target = None
    for point in points:
        if (point.date - inputs.today).days <= wait_days:
            target = point
    # Value the wait on the same price basis as the immediate channel.  When a
    # buyer offer is the immediate channel, apply the forecast's relative move to
    # that offer instead of comparing a farm-gate offer with a mandi price.
    if target is not None and inputs.price_info.expected and immediate_price is not None:
        price = immediate_price * (target.expected / inputs.price_info.expected)
    elif target is not None:
        price = target.expected
    else:
        price = immediate_price if immediate_price is not None else inputs.price_info.expected
    if price is None:
        return {
            "recommended": False,
            "wait_days": wait_days,
            "reason": reason + " No price forecast is available to value the wait.",
        }

    quantity = Decimal(str(inputs.quantity_quintals))
    deterioration = Decimal(str(wait_policy.crop_deterioration_per_day)) * wait_days
    adjusted_quantity = quantity * max(Decimal("0"), Decimal("1") - deterioration)
    holding = quantity * Decimal(str(wait_policy.holding_cost_per_quintal_per_day)) * wait_days
    price_d = Decimal(str(price))
    gross = price_d * adjusted_quantity
    commission = gross * Decimal(str(policy.finance.commission_pct))
    other = adjusted_quantity * Decimal(str(policy.finance.other_selling_cost_per_quintal))
    transport = Decimal(str(best_buyer.transport_cost)) if best_buyer and best_buyer.transport_cost else Decimal("0")
    net = gross - commission - other - transport - holding
    uplift = (
        (float(net) - immediate_net) / immediate_net
        if immediate_net not in (None, 0)
        else None
    )
    margin = wait_policy.risk_margin * abs(immediate_net or 0)
    recommended = bool(
        wait_days <= wait_policy.max_recommended_wait_days
        and (
            not inputs.harvest_info.ready
            or (
                uplift is not None
                and uplift >= wait_policy.min_expected_wait_uplift_pct
                and float(net) > (immediate_net or 0) + margin
            )
        )
    )
    if not inputs.harvest_info.ready:
        reason = (
            f"Crop is not ready; harvest is estimated in {harvest_days} day(s). "
            "Waiting is required before a sale can be executed."
        )
    elif recommended:
        reason = (
            f"Waiting {wait_days} day(s) is expected to improve net realisation by "
            f"{uplift:.1%} after holding and deterioration costs."
        )
    else:
        reason = (
            f"Waiting {wait_days} day(s) does not clear the "
            f"{wait_policy.min_expected_wait_uplift_pct:.0%} uplift threshold after costs."
        )
    return {
        "recommended": recommended,
        "wait_days": wait_days,
        "expected_price_per_quintal": float(price_d),
        "adjusted_quantity_quintals": float(adjusted_quantity),
        "holding_cost": _f(holding),
        "gross_revenue": _f(gross),
        "net_realization": _f(net),
        "uplift_pct": round(uplift, 4) if uplift is not None else None,
        "reason": reason,
    }


def _factor_direction(value: float) -> str:
    if value <= 0.33:
        return "positive"
    if value <= 0.66:
        return "neutral"
    return "negative"


def decide(inputs: DecisionInput, policy: DecisionPolicy | None = None) -> DecisionOutcome:
    """Run the ordered decision rules and return a fully explained outcome."""
    policy = policy or get_policy()
    completeness = fusion.completeness(inputs)
    evaluations = evaluate_buyers(inputs, policy)
    eligible = [item for item in evaluations if item.eligible]
    best_buyer = eligible[0] if eligible else None
    market = _market_scenario(inputs, policy)

    # Immediate scenario: choose the better of the best eligible buyer offer and
    # the mandi channel.  Comparing both prevents a low buyer offer from
    # overriding a clearly better local market price.
    market_net = market.get("net_realization") if market else None
    buyer_net = best_buyer.net_realization if best_buyer is not None else None
    use_buyer = best_buyer is not None and (
        market_net is None or (buyer_net is not None and buyer_net >= market_net)
    )
    if use_buyer:
        immediate_net = best_buyer.net_realization
        immediate_per_quintal = best_buyer.net_realization_per_quintal
        immediate_gross = best_buyer.gross_revenue
        immediate_transport = best_buyer.transport_cost
        immediate_other = (best_buyer.commission or 0.0) + (best_buyer.other_selling_costs or 0.0)
        immediate_price = best_buyer.offered_price_per_quintal
        channel = f"buyer:{best_buyer.buyer_name}"
        selected_channel_buyer = best_buyer
    elif market:
        immediate_net = market["net_realization"]
        immediate_per_quintal = market["net_realization_per_quintal"]
        immediate_gross = market["gross_revenue"]
        immediate_transport = None
        immediate_other = (market.get("commission") or 0.0) + (market.get("other_selling_costs") or 0.0)
        immediate_price = market["price_per_quintal"]
        channel = "mandi"
        selected_channel_buyer = None
    else:
        immediate_net = immediate_per_quintal = immediate_gross = None
        immediate_transport = immediate_other = immediate_price = None
        channel = "none"
        selected_channel_buyer = None

    risk = compute_risk(
        inputs,
        policy,
        selected_buyer=selected_channel_buyer,
        data_completeness=completeness.score,
        weather_available=inputs.weather_available,
    )
    wait = _wait_scenario(
        inputs,
        policy,
        immediate_net=immediate_net,
        immediate_price=immediate_price,
        best_buyer=selected_channel_buyer,
    )
    conf = fusion.confidence(inputs, completeness.score)

    inspect_policy = policy.policy.inspect
    yield_interval = fusion.yield_relative_interval(inputs)
    preference_cap = policy.risk.risk_preference_max_scores.get(inputs.risk_preference, 0.72)

    action = "INSPECT"
    primary_reason = ""
    health = inputs.health_info
    severe_health = bool(
        health.available
        and health.is_healthy is False
        and (
            health.severity >= inspect_policy.max_health_severity
            or health.confidence < inspect_policy.min_health_confidence
        )
    )

    if severe_health:
        action = "INSPECT"
        primary_reason = (
            f"The latest scan indicates {health.label or 'a crop-health problem'} "
            f"(severity {health.severity:.0%}, confidence {health.confidence:.0%}). "
            "Confirm the diagnosis in the field before committing the harvest."
        )
    elif not inputs.harvest_info.ready and (inputs.harvest_info.days_to_harvest or 0) > 0:
        action = "WAIT"
        primary_reason = (
            f"The crop is not ready for harvest yet "
            f"({inputs.harvest_info.days_to_harvest} day(s) remaining)."
        )
    elif completeness.score < inspect_policy.min_data_completeness:
        action = "INSPECT"
        primary_reason = (
            f"Only {completeness.score:.0%} of the expected decision inputs are "
            "available; refresh the missing data before selling."
        )
    elif (
        yield_interval is not None
        and yield_interval > inspect_policy.max_yield_relative_interval
    ):
        action = "INSPECT"
        primary_reason = (
            f"The yield interval is ±{yield_interval:.0%} of the estimate, wider "
            "than the configured limit; verify the standing crop."
        )
    elif (
        inputs.price_info.age_days is not None
        and inputs.price_info.age_days > inspect_policy.max_price_age_days
    ):
        action = "INSPECT"
        primary_reason = (
            f"Market prices are {inputs.price_info.age_days} days old "
            f"(limit {inspect_policy.max_price_age_days}); refresh the price feed."
        )
    elif risk.score > preference_cap:
        action = "INSPECT"
        primary_reason = (
            f"Composite risk is {risk.score:.2f}, above the "
            f"{inputs.risk_preference} preference limit of {preference_cap:.2f}. "
            "Reduce uncertainty before selling."
        )
    elif wait.get("recommended"):
        action = "WAIT"
        primary_reason = wait.get("reason", "Waiting is expected to improve the outcome.")
    elif immediate_per_quintal is not None and immediate_per_quintal >= policy.policy.sell.min_net_realization_per_quintal:
        action = "SELL"
        primary_reason = (
            f"Net realisation of ₹{immediate_per_quintal:,.2f} per quintal clears the "
            "configured floor and no material wait advantage was found."
        )
    else:
        action = "INSPECT"
        primary_reason = (
            "No eligible buyer offer or usable price forecast produced a positive "
            "net realisation; inspect the crop and refresh market data."
        )

    selected = selected_channel_buyer if action == "SELL" else None
    selected_name = (
        selected.buyer_name
        if selected
        else (inputs.price_info.market if action == "SELL" else None)
    )

    factors = [
        DecisionFactor(
            factor=component.name,
            direction=_factor_direction(component.value),
            weight=round(component.weight, 4),
            value=round(component.value, 4),
            description=component.description,
        )
        for component in risk.components
    ]
    if best_buyer is not None and inputs.price_info.expected:
        premium = best_buyer.offered_price_per_quintal / inputs.price_info.expected - 1.0
        factors.append(
            DecisionFactor(
                factor="buyer_price_premium",
                direction="positive" if premium > 0.01 else ("negative" if premium < -0.01 else "neutral"),
                weight=None,
                value=round(premium, 4),
                description=(
                    f"Best eligible offer is {premium:+.1%} versus the expected "
                    f"mandi price of ₹{inputs.price_info.expected:,.0f}/quintal."
                ),
            )
        )
    if wait.get("uplift_pct") is not None:
        factors.append(
            DecisionFactor(
                factor="wait_uplift",
                direction="positive" if wait["uplift_pct"] > 0 else "negative",
                weight=None,
                value=round(wait["uplift_pct"], 4),
                description=wait.get("reason", "Estimated effect of waiting."),
            )
        )

    missing_inputs = sorted(
        {
            f"No {name.replace('_', ' ')} signal"
            for name in completeness.missing
        }
        | {
            f"No {name.replace('_', ' ')} signal"
            for name in risk.missing
            if name not in {"data_completeness"}
        }
    )
    assumptions = [
        f"Commission of {policy.finance.commission_pct:.1%} and "
        f"₹{policy.finance.other_selling_cost_per_quintal:,.0f}/quintal other selling "
        "costs are applied.",
        "Transport costs come from the routing service; when absent they are excluded "
        "and flagged as an assumption.",
        "Price and yield forecasts are experimental statistical estimates, not guarantees.",
    ]
    if best_buyer is not None and best_buyer.buyer_is_demo:
        assumptions.append(
            f"Buyer '{best_buyer.buyer_name}' is a clearly-labelled DEMO record."
        )
    if best_buyer is not None and best_buyer.quantity_quintals < inputs.quantity_quintals:
        assumptions.append(
            f"Buyer '{best_buyer.buyer_name}' can absorb only "
            f"{best_buyer.quantity_quintals:g} of {inputs.quantity_quintals:g} quintals; "
            "the remainder requires another buyer."
        )
    if immediate_transport is None:
        assumptions.append(
            "Transport cost was not available for the selected channel and is treated as zero."
        )
    if not inputs.price_info.available:
        assumptions.append("No market forecast was available; buyer offers were the price basis.")
    if not inputs.health_info.available:
        assumptions.append("No crop-health scan was provided for this decision.")
    assumptions.extend(inputs.notes)

    top_factors = sorted(
        [component for component in risk.components if component.contribution > 0],
        key=lambda component: component.contribution,
        reverse=True,
    )[:3]
    top_text = ", ".join(
        f"{component.label.lower()} ({component.value:.0%})" for component in top_factors
    )
    if action == "SELL":
        explanation = (
            f"Sell {inputs.quantity_quintals:g} quintals of {inputs.crop_name} via "
            f"{selected_name or 'the mandi'}. {primary_reason} Estimated net realisation "
            f"is ₹{immediate_net:,.2f}"
            + (
                f" (₹{immediate_per_quintal:,.2f}/quintal)."
                if immediate_per_quintal is not None
                else "."
            )
            + f" Composite risk is {risk.score:.2f} ({risk.category}); the largest "
            f"contributors are {top_text}."
        )
    elif action == "WAIT":
        explanation = (
            f"Wait before selling {inputs.crop_name}. {primary_reason} "
            + (
                f"Waiting {wait.get('wait_days')} day(s) is modelled at "
                f"₹{wait.get('net_realization'):,.2f} net versus "
                f"₹{immediate_net:,.2f} now. "
                if wait.get("net_realization") is not None and immediate_net is not None
                else ""
            )
            + f"Composite risk is {risk.score:.2f} ({risk.category})."
        )
    else:
        explanation = (
            f"Inspect the {inputs.crop_name} crop before selling. {primary_reason} "
            f"Composite risk is {risk.score:.2f} ({risk.category}); the largest "
            f"contributors are {top_text}."
        )

    data_freshness = fusion.freshness(inputs, policy)
    low_revenue, high_revenue = fusion.revenue_bounds(inputs)
    price_low = price_high = None
    if immediate_price is not None:
        market_expected = inputs.price_info.expected
        if (
            market_expected
            and inputs.price_info.lower is not None
            and inputs.price_info.upper is not None
        ):
            price_low = round(immediate_price * inputs.price_info.lower / market_expected, 2)
            price_high = round(immediate_price * inputs.price_info.upper / market_expected, 2)
        else:
            price_low = price_high = immediate_price

    outputs = {
        "policy_version": policy.version,
        "channel": channel,
        "risk": {
            "score": round(risk.score, 4),
            "category": risk.category,
            "components": risk.to_dict(),
        },
        "completeness": {
            "score": completeness.score,
            "present": completeness.present,
        },
        "scenarios": {
            "immediate": {
                "channel": channel,
                "gross_revenue": immediate_gross,
                "transport_cost": immediate_transport,
                "other_costs": immediate_other,
                "net_realization": immediate_net,
                "net_realization_per_quintal": immediate_per_quintal,
            },
            "market": market,
            "wait": wait,
        },
        "revenue_interval": {
            "low": low_revenue,
            "high": high_revenue,
            "method": "yield 80% interval × price interval (independence assumption)",
        },
        "selected_offer": (
            {
                "offer_id": selected.offer_id,
                "buyer_id": selected.buyer_id,
                "price_per_quintal": selected.offered_price_per_quintal,
                "quantity_quintals": selected.quantity_quintals,
                "expiry_date": selected.offer_expiry.isoformat(),
            }
            if selected
            else None
        ),
        "risk_preference": inputs.risk_preference,
        "risk_preference_cap": preference_cap,
    }

    return DecisionOutcome(
        action=action,
        selected_buyer_id=selected.buyer_id if selected else None,
        selected_offer_id=selected.offer_id if selected else None,
        selected_buyer_name=selected_name,
        expected_yield_quintals=float(
            inputs.yield_info.mean_total_quintals or inputs.quantity_quintals
        ),
        yield_low_quintals=inputs.yield_info.low_total_quintals,
        yield_high_quintals=inputs.yield_info.high_total_quintals,
        expected_price_per_quintal=immediate_price,
        price_low_per_quintal=price_low,
        price_high_per_quintal=price_high,
        gross_revenue=immediate_gross,
        transport_cost=immediate_transport,
        other_costs=immediate_other,
        net_realization=immediate_net,
        net_realization_per_quintal=immediate_per_quintal,
        wait_expected_net=wait.get("net_realization"),
        risk_score=round(risk.score, 4),
        risk_category=risk.category,
        data_completeness=completeness.score,
        confidence=conf,
        factors=factors,
        buyer_evaluations=evaluations,
        missing_inputs=missing_inputs,
        assumptions=assumptions,
        explanation=explanation,
        data_freshness=data_freshness,
        outputs=outputs,
        wait_scenario=wait,
    )
