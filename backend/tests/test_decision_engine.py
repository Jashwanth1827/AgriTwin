"""Unit tests for the deterministic decision engine.

The engine is deliberately free of FastAPI/SQLAlchemy dependencies, so these
tests construct dataclass inputs directly and assert the ordered policy rules,
money arithmetic and explanation fields.
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest

from app.services.decision.engine import decide, evaluate_buyers, money
from app.services.decision.models import (
    BuyerInput,
    DecisionInput,
    HarvestInfo,
    HealthInfo,
    PriceInfo,
    PricePoint,
    YieldInfo,
)
from app.services.decision.policy import get_policy

TODAY = date(2026, 11, 4)


def _buyer(**overrides) -> BuyerInput:
    base = {
        "buyer_id": 1,
        "buyer_name": "Test Buyer",
        "offer_id": 11,
        "offered_price_per_quintal": 2200.0,
        "min_quantity_quintals": 1.0,
        "max_quantity_quintals": None,
        "offer_date": TODAY - timedelta(days=1),
        "expiry_date": TODAY + timedelta(days=10),
        "crop": "Onion",
        "distance_km": 50.0,
        "distance_method": "osrm",
        "transport_cost": 500.0,
        "trips": 1,
        "transport_is_approximate": False,
        "is_demo": False,
        "has_coordinates": True,
        "is_active": True,
    }
    base.update(overrides)
    return BuyerInput(**base)


def _inputs(**overrides) -> DecisionInput:
    base = {
        "today": TODAY,
        "farm_id": 1,
        "crop_id": 1,
        "crop_name": "Onion",
        "quantity_quintals": 100.0,
        "yield_info": YieldInfo(
            available=True,
            mean_total_quintals=100.0,
            low_total_quintals=90.0,
            high_total_quintals=110.0,
            per_hectare=50.0,
            low_per_hectare=45.0,
            high_per_hectare=55.0,
            confidence=0.8,
            completeness=0.9,
            age_days=2,
        ),
        "health_info": HealthInfo(
            available=True,
            is_healthy=True,
            severity=0.0,
            confidence=0.9,
            label="Onion___healthy",
            age_days=1,
        ),
        "price_info": PriceInfo(
            available=True,
            expected=2000.0,
            lower=1900.0,
            upper=2100.0,
            horizon_days=14,
            age_days=1,
            model_name="test-model",
            market="Test Mandi",
            points=[],
        ),
        "buyers": [_buyer()],
        "harvest_info": HarvestInfo(
            ready=True, days_to_harvest=0, status="ready", confidence=0.9
        ),
        "risk_preference": "medium",
        "weather_risk": 0.2,
        "weather_available": True,
        "transport_available": True,
    }
    base.update(overrides)
    return DecisionInput(**base)


def test_policy_weights_sum_to_one():
    policy = get_policy()
    assert policy.risk.weights.total() == pytest.approx(1.0)
    assert policy.version == "1.0.1"


def test_money_rounds_half_up_to_paise():
    assert money(1234.565) == Decimal("1234.57")
    assert money(0.004) == Decimal("0.00")
    assert money(None) is None


def test_sell_selects_better_buyer_offer():
    outcome = decide(_inputs())
    assert outcome.action == "SELL"
    assert outcome.selected_buyer_id == 1
    assert outcome.selected_offer_id == 11
    assert outcome.outputs["channel"] == "buyer:Test Buyer"
    # 2200*100 - 1% commission - 5/q other cost - 500 transport
    assert outcome.gross_revenue == pytest.approx(220_000.0)
    assert outcome.net_realization == pytest.approx(216_800.0)
    assert outcome.net_realization_per_quintal == pytest.approx(2168.0)
    assert outcome.risk_category in {"low", "medium", "high"}
    assert outcome.factors
    assert "Sell 100 quintals of Onion" in outcome.explanation


def test_sell_selects_mandi_when_offer_is_worse():
    cheap_buyer = _buyer(offered_price_per_quintal=1500.0)
    outcome = decide(_inputs(buyers=[cheap_buyer]))
    assert outcome.action == "SELL"
    assert outcome.selected_buyer_id is None
    assert outcome.selected_buyer_name == "Test Mandi"
    assert outcome.outputs["channel"] == "mandi"
    # Mandi: 2000*100 - 1% commission - 5/q other cost.
    assert outcome.net_realization == pytest.approx(197_500.0)
    assert outcome.net_realization_per_quintal == pytest.approx(1975.0)


def test_wait_when_crop_is_not_ready():
    outcome = decide(
        _inputs(
            harvest_info=HarvestInfo(
                ready=False, days_to_harvest=20, status="growing", confidence=0.8
            )
        )
    )
    assert outcome.action == "WAIT"
    assert "not ready" in outcome.explanation.lower()
    assert outcome.wait_scenario is not None
    assert outcome.wait_scenario["wait_days"] == 20


def test_inspect_on_severe_health_signal():
    outcome = decide(
        _inputs(
            health_info=HealthInfo(
                available=True,
                is_healthy=False,
                severity=0.9,
                confidence=0.9,
                label="Onion___Purple_blotch",
                age_days=1,
            )
        )
    )
    assert outcome.action == "INSPECT"
    assert "scan" in outcome.explanation.lower()
    assert outcome.outputs["risk"]["components"]["crop_health"] > 0.5


def test_inspect_on_low_data_completeness():
    outcome = decide(
        _inputs(
            yield_info=YieldInfo(available=False),
            health_info=HealthInfo(available=False),
            price_info=PriceInfo(available=False),
            buyers=[],
            transport_available=False,
            weather_available=False,
            harvest_info=HarvestInfo(
                ready=True, days_to_harvest=0, status="ready", confidence=0.5
            ),
        )
    )
    assert outcome.action == "INSPECT"
    assert outcome.data_completeness < 0.6
    assert "expected decision inputs" in outcome.explanation


def test_inspect_on_stale_market_price():
    outcome = decide(_inputs(price_info=PriceInfo(
        available=True,
        expected=2000.0,
        lower=1900.0,
        upper=2100.0,
        horizon_days=14,
        age_days=120,
        model_name="test-model",
        market="Test Mandi",
        points=[],
    )))
    assert outcome.action == "INSPECT"
    assert "days old" in outcome.explanation


def test_inspect_on_wide_yield_interval():
    outcome = decide(
        _inputs(
            yield_info=YieldInfo(
                available=True,
                mean_total_quintals=100.0,
                low_total_quintals=20.0,
                high_total_quintals=180.0,
                confidence=0.6,
                age_days=1,
            )
        )
    )
    assert outcome.action == "INSPECT"
    assert "yield interval" in outcome.explanation.lower()


def test_inspect_when_risk_exceeds_low_preference_cap():
    outcome = decide(
        _inputs(
            risk_preference="low",
            yield_info=YieldInfo(
                available=True,
                mean_total_quintals=100.0,
                low_total_quintals=60.0,
                high_total_quintals=140.0,
                confidence=0.6,
                age_days=1,
            ),
            price_info=PriceInfo(
                available=True,
                expected=2000.0,
                lower=1600.0,
                upper=2400.0,
                horizon_days=14,
                age_days=60,
                model_name="test-model",
                market="Test Mandi",
                points=[],
            ),
            buyers=[_buyer(is_demo=True, distance_method="geodesic_detour")],
            weather_risk=0.9,
            weather_available=True,
        )
    )
    assert outcome.action == "INSPECT"
    assert outcome.risk_score > 0.45
    assert outcome.outputs["risk_preference_cap"] == pytest.approx(0.45)


def test_ineligible_offers_are_explained_and_excluded():
    buyers = [
        _buyer(buyer_id=1, offer_id=1, is_active=False),
        _buyer(buyer_id=2, offer_id=2, expiry_date=TODAY - timedelta(days=1)),
        _buyer(buyer_id=3, offer_id=3, crop="Wheat"),
        _buyer(buyer_id=4, offer_id=4, min_quantity_quintals=500.0),
        _buyer(buyer_id=5, offer_id=5, offer_date=TODAY + timedelta(days=2)),
    ]
    outcome = decide(_inputs(buyers=buyers))
    assert all(not item.eligible for item in outcome.buyer_evaluations)
    assert all(item.ineligibility_reasons for item in outcome.buyer_evaluations)
    # With no eligible offer the engine falls back to the mandi channel.
    assert outcome.action == "SELL"
    assert outcome.outputs["channel"] == "mandi"


def test_partial_quantity_is_allocated_and_disclosed():
    outcome = decide(_inputs(buyers=[_buyer(max_quantity_quintals=40.0)]))
    evaluation = outcome.buyer_evaluations[0]
    assert evaluation.eligible is True
    assert evaluation.quantity_quintals == pytest.approx(40.0)
    # Transport is allocated proportionally to the absorbed quantity.
    assert evaluation.transport_cost == pytest.approx(200.0)
    assert any("can absorb only" in note for note in outcome.assumptions)


def test_wait_scenario_uses_forecast_relative_move():
    future = [
        PricePoint(date=TODAY + timedelta(days=10), expected=2400.0, lower=2300.0, upper=2500.0)
    ]
    outcome = decide(
        _inputs(
            buyers=[],
            price_info=PriceInfo(
                available=True,
                expected=2000.0,
                lower=1900.0,
                upper=2100.0,
                horizon_days=14,
                age_days=1,
                model_name="test-model",
                market="Test Mandi",
                points=future,
            ),
        )
    )
    assert outcome.action == "WAIT"
    wait = outcome.outputs["scenarios"]["wait"]
    assert wait["wait_days"] == 10
    assert wait["uplift_pct"] >= 0.04
    assert outcome.wait_expected_net > outcome.net_realization
    assert any(factor.factor == "wait_uplift" for factor in outcome.factors)


def test_demo_buyer_and_missing_transport_are_disclosed():
    outcome = decide(
        _inputs(
            buyers=[
                _buyer(is_demo=True, transport_cost=None, distance_method="approximate")
            ]
        )
    )
    assert any("DEMO record" in note for note in outcome.assumptions)
    assert any("Transport cost was not available" in note for note in outcome.assumptions)


def test_revenue_bounds_and_freshness_are_reported():
    outcome = decide(_inputs())
    interval = outcome.outputs["revenue_interval"]
    assert interval["low"] == pytest.approx(90.0 * 1900.0)
    assert interval["high"] == pytest.approx(110.0 * 2100.0)
    assert outcome.data_freshness["stale"] is False
    assert outcome.data_freshness["price_age_days"] == 1


def test_engine_is_deterministic():
    first = decide(_inputs())
    second = decide(_inputs())
    assert first.action == second.action
    assert first.net_realization == second.net_realization
    assert first.risk_score == second.risk_score
    assert first.explanation == second.explanation


def test_buyer_ranking_prefers_risk_adjusted_value():
    strong = _buyer(
        buyer_id=1,
        offer_id=1,
        buyer_name="Strong",
        offered_price_per_quintal=2300.0,
        transport_cost=300.0,
    )
    weak = _buyer(
        buyer_id=2,
        offer_id=2,
        buyer_name="Weak",
        offered_price_per_quintal=2250.0,
        transport_cost=900.0,
        is_demo=True,
    )
    evaluations = evaluate_buyers(_inputs(buyers=[strong, weak]), get_policy())
    ranked = [item for item in evaluations if item.eligible]
    assert [item.buyer_name for item in ranked] == ["Strong", "Weak"]
    assert ranked[0].rank == 1
    assert ranked[1].rank == 2
