"""Bridge between database entities and the pure decision engine."""

from __future__ import annotations

import math
from dataclasses import asdict, is_dataclass
from datetime import date, datetime, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import AppError, NotFoundError
from app.models.decision import DecisionFactor, DecisionResult
from app.models.farm import Crop, Farm
from app.models.market import MarketForecast
from app.models.user import User
from app.models.yield_ import HistoricalYieldRecord
from app.schemas.decision import DecisionOut, DecisionRequest
from app.services import buyers as buyer_service
from app.services import crop_health as health_service
from app.services import market as market_service
from app.services import yield_service
from app.services.crop_calendar import harvest_readiness
from app.services.decision.engine import decide
from app.services.decision.models import (
    BuyerInput,
    DecisionInput,
    HealthInfo,
    HarvestInfo,
    PriceInfo,
    PricePoint,
    YieldInfo,
)
from app.services.decision.policy import get_policy
from app.services.transport import route_distance, vehicle_config
from app.services.weather import WeatherUnavailable, fetch_weather


def _jsonable(value: Any) -> Any:
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if is_dataclass(value):
        return _jsonable(asdict(value))
    if isinstance(value, dict):
        return {key: _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if isinstance(value, float):
        return round(value, 4)
    return value


def _quote_transport(
    farm: Farm,
    buyer,
    quantity: float,
    *,
    vehicle_type: str,
    cost_per_km: float | None,
) -> dict | None:
    if farm.latitude is None or farm.longitude is None:
        return None
    if buyer.latitude is None or buyer.longitude is None:
        return None
    config = vehicle_config(vehicle_type)
    capacity = float(config.get("capacity_quintals", 100))
    distance, method, _provider, approximate = route_distance(
        (farm.latitude, farm.longitude),
        (buyer.latitude, buyer.longitude),
        use_routing=False,
    )
    trips = max(1, math.ceil(quantity / capacity))
    rate = float(cost_per_km if cost_per_km is not None else config.get("cost_per_km_inr", 18))
    total = trips * (
        distance * rate
        + float(config.get("fixed_cost_inr", 350))
        + float(config.get("loading_cost_inr", 150))
        + float(config.get("unloading_cost_inr", 150))
    )
    return {
        "distance_km": distance,
        "distance_method": method,
        "transport_cost": round(total, 2),
        "trips": trips,
        "is_approximate": approximate,
        "has_coordinates": True,
    }


def _yield_info(
    db: Session, user: User, farm: Farm, crop: Crop, auto_compute: bool
) -> tuple[YieldInfo, list[str], list[str]]:
    assumptions: list[str] = []
    prediction = yield_service.latest_for_crop(db, user, crop.id)
    if prediction is None and auto_compute:
        try:
            prediction = yield_service.predict(db, user, farm, crop)
        except AppError:
            prediction = None
    if prediction is not None:
        age = (date.today() - prediction.predicted_at.date()).days
        return (
            YieldInfo(
                available=True,
                mean_total_quintals=prediction.predicted_total_quintals,
                low_total_quintals=prediction.lower_total_quintals,
                high_total_quintals=prediction.upper_total_quintals,
                per_hectare=prediction.predicted_yield_per_hectare,
                low_per_hectare=prediction.lower_yield_per_hectare,
                high_per_hectare=prediction.upper_yield_per_hectare,
                confidence=prediction.confidence,
                completeness=prediction.input_completeness,
                is_demo=False,
                model_version=prediction.model_version,
                age_days=age,
            ),
            assumptions,
            [],
        )

    # Transparent fallback: district/state historical average, not the ML model.
    average = db.scalar(
        select(func.avg(HistoricalYieldRecord.yield_per_hectare)).where(
            HistoricalYieldRecord.crop == crop.crop_name,
            HistoricalYieldRecord.state == farm.state,
        )
    )
    scope = f"{crop.crop_name} in {farm.state}"
    if average is None:
        average = db.scalar(
            select(func.avg(HistoricalYieldRecord.yield_per_hectare)).where(
                HistoricalYieldRecord.crop == crop.crop_name
            )
        )
        scope = crop.crop_name
    if average is None:
        return YieldInfo(available=False), assumptions, ["yield"]
    mean_total = float(average) * float(crop.area_hectares)
    assumptions.append(
        f"No ML yield prediction was available; quantity was estimated from the "
        f"historical average yield for {scope}."
    )
    return (
        YieldInfo(
            available=True,
            mean_total_quintals=round(mean_total, 3),
            low_total_quintals=round(mean_total * 0.7, 3),
            high_total_quintals=round(mean_total * 1.3, 3),
            per_hectare=float(average),
            low_per_hectare=round(float(average) * 0.7, 3),
            high_per_hectare=round(float(average) * 1.3, 3),
            confidence=0.35,
            completeness=0.5,
            is_demo=False,
            model_version="historical_average",
        ),
        assumptions,
        [],
    )


def _health_info(db: Session, user: User, crop: Crop) -> HealthInfo:
    prediction = health_service.latest_for_crop(db, user, crop.id)
    if prediction is None:
        return HealthInfo(available=False)
    return HealthInfo(
        available=True,
        is_healthy=prediction.is_healthy,
        severity=prediction.severity,
        confidence=prediction.confidence,
        label=prediction.predicted_label,
        is_demo=prediction.is_demo,
        age_days=(date.today() - prediction.predicted_at.date()).days,
    )


def _price_info(
    db: Session,
    *,
    crop_name: str,
    market_name: str | None,
    forecast_id: int | None,
    auto_compute: bool,
    preferred_state: str | None = None,
) -> PriceInfo:
    forecast: MarketForecast | None = None
    if forecast_id is not None:
        forecast = db.get(MarketForecast, forecast_id)
        if forecast is None or forecast.crop != crop_name:
            raise NotFoundError("Price forecast not found for this crop")
    else:
        forecast = market_service.latest_forecast(db, crop_name, market_name)
    if forecast is None and auto_compute:
        try:
            forecast = market_service.create_forecast(
                db,
                crop=crop_name,
                market=market_name,
                horizon_days=14,
                preferred_state=preferred_state,
            )
        except AppError:
            forecast = None
    if forecast is not None:
        points = [
            PricePoint(
                date=date.fromisoformat(point["date"]),
                expected=float(point["expected_price"]),
                lower=point.get("lower_bound"),
                upper=point.get("upper_bound"),
            )
            for point in (forecast.points or [])
        ]
        return PriceInfo(
            available=True,
            expected=forecast.expected_price,
            lower=forecast.lower_bound,
            upper=forecast.upper_bound,
            horizon_days=forecast.horizon_days,
            age_days=forecast.data_freshness_days,
            model_name=forecast.model_name,
            is_demo=forecast.is_demo,
            points=points,
            market=forecast.market,
        )

    snapshot = market_service.latest_market_snapshot(
        db, crop_name, market_name, preferred_state
    )
    if snapshot is not None:
        return PriceInfo(
            available=True,
            expected=snapshot["latest_price"],
            lower=None,
            upper=None,
            horizon_days=0,
            age_days=snapshot["data_freshness_days"],
            model_name="latest_observation",
            is_demo=False,
            points=[],
            market=snapshot["market"],
        )
    return PriceInfo(available=False)


def _buyer_inputs(
    db: Session,
    user: User,
    farm: Farm,
    crop: Crop,
    quantity: float,
    *,
    vehicle_type: str,
    cost_per_km: float | None,
    buyer_ids: list[int] | None,
) -> list[BuyerInput]:
    offers = buyer_service.active_offers_for_crop(db, user, crop.crop_name)
    inputs: list[BuyerInput] = []
    for buyer, offer in offers:
        if buyer_ids and buyer.id not in buyer_ids:
            continue
        quote = _quote_transport(
            farm, buyer, quantity, vehicle_type=vehicle_type, cost_per_km=cost_per_km
        )
        inputs.append(
            BuyerInput(
                buyer_id=buyer.id,
                buyer_name=buyer.name,
                offer_id=offer.id,
                offered_price_per_quintal=offer.offered_price_per_quintal,
                min_quantity_quintals=offer.min_quantity_quintals,
                max_quantity_quintals=offer.max_quantity_quintals,
                offer_date=offer.offer_date,
                expiry_date=offer.expiry_date,
                crop=offer.crop,
                distance_km=quote["distance_km"] if quote else None,
                distance_method=quote["distance_method"] if quote else None,
                transport_cost=quote["transport_cost"] if quote else None,
                trips=quote["trips"] if quote else None,
                transport_is_approximate=bool(quote["is_approximate"]) if quote else True,
                is_demo=buyer.is_demo or offer.is_demo,
                has_coordinates=bool(quote),
                is_active=offer.is_active,
            )
        )
    return inputs


def run(
    db: Session, user: User, request: DecisionRequest
) -> tuple[DecisionResult, DecisionOut]:
    farm = db.get(Farm, request.farm_id)
    if farm is None or farm.user_id != user.id:
        raise NotFoundError("Farm not found")
    crop = db.get(Crop, request.crop_id)
    if crop is None or crop.farm_id != farm.id:
        raise NotFoundError("Crop not found")

    assumptions: list[str] = []
    missing: list[str] = []
    yield_info, yield_assumptions, yield_missing = _yield_info(
        db, user, farm, crop, request.auto_compute
    )
    assumptions.extend(yield_assumptions)
    missing.extend(yield_missing)

    quantity = float(request.quantity_quintals or yield_info.mean_total_quintals or 0.0)
    if quantity <= 0:
        raise AppError(
            "A positive quantity is required. Provide quantity_quintals or create a yield prediction.",
            status_code=422,
        )
    health_info = _health_info(db, user, crop)
    price_info = _price_info(
        db,
        crop_name=crop.crop_name,
        market_name=request.market_name,
        forecast_id=request.price_forecast_id,
        auto_compute=request.auto_compute,
        preferred_state=farm.state,
    )
    buyer_inputs = _buyer_inputs(
        db,
        user,
        farm,
        crop,
        quantity,
        vehicle_type=request.vehicle_type,
        cost_per_km=request.cost_per_km,
        buyer_ids=request.buyer_ids,
    )
    if not buyer_inputs:
        assumptions.append(
            "No active buyer offer matched this crop; the decision uses mandi prices."
        )

    readiness = harvest_readiness(
        crop=crop.crop_name,
        season=crop.season,
        sowing_date=crop.sowing_date,
        expected_harvest_date=crop.expected_harvest_date,
        today=date.today(),
    )
    ready = readiness["readiness_status"] in {"ready", "overdue"}
    days_to_harvest = max(0, int(readiness["estimated_days_remaining"]))
    harvest_info = HarvestInfo(
        ready=ready,
        days_to_harvest=0 if ready else days_to_harvest,
        status=readiness["readiness_status"],
        confidence=readiness["confidence"],
    )

    weather_risk = 0.3
    weather_available = False
    weather_note = None
    if farm.latitude is not None and farm.longitude is not None:
        try:
            weather = fetch_weather(farm, days=3)
            weather_risk = float(weather["risk_score"])
            weather_available = True
        except WeatherUnavailable as exc:
            weather_note = str(exc)
    else:
        weather_note = "Farm coordinates are missing; weather risk uses a neutral default."
    if not weather_available:
        assumptions.append(weather_note or "Live weather was unavailable.")

    inputs = DecisionInput(
        today=date.today(),
        farm_id=farm.id,
        crop_id=crop.id,
        crop_name=crop.crop_name,
        quantity_quintals=quantity,
        yield_info=yield_info,
        health_info=health_info,
        price_info=price_info,
        buyers=buyer_inputs,
        harvest_info=harvest_info,
        risk_preference=request.risk_preference,
        weather_risk=weather_risk,
        weather_available=weather_available,
        transport_available=any(b.has_coordinates for b in buyer_inputs),
    )
    policy = get_policy()
    outcome = decide(inputs, policy)

    outputs = {
        **_jsonable(outcome.outputs),
        "buyer_evaluations": _jsonable(outcome.buyer_evaluations),
        "missing_inputs": outcome.missing_inputs,
        "assumptions": outcome.assumptions + assumptions,
        "data_freshness": outcome.data_freshness,
        "wait_scenario": _jsonable(outcome.wait_scenario),
        "explanation": outcome.explanation,
        "data_mode": "real",
        "harvest_readiness": _jsonable(readiness),
    }
    inputs_snapshot = {
        "farm": {
            "id": farm.id,
            "name": farm.name,
            "state": farm.state,
            "district": farm.district,
            "latitude": farm.latitude,
            "longitude": farm.longitude,
        },
        "crop": {
            "id": crop.id,
            "crop_name": crop.crop_name,
            "season": crop.season,
            "area_hectares": crop.area_hectares,
            "sowing_date": crop.sowing_date.isoformat(),
            "expected_harvest_date": crop.expected_harvest_date.isoformat()
            if crop.expected_harvest_date
            else None,
        },
        "quantity_quintals": quantity,
        "yield": _jsonable(yield_info),
        "health": _jsonable(health_info),
        "price": _jsonable(price_info),
        "buyers": _jsonable(buyer_inputs),
        "harvest": _jsonable(harvest_info),
        "weather": {"risk": weather_risk, "available": weather_available},
        "risk_preference": request.risk_preference,
    }

    generated_at = datetime.now(timezone.utc)
    result = DecisionResult(
        user_id=user.id,
        farm_id=farm.id,
        crop_id=crop.id,
        action=outcome.action,
        selected_buyer_id=outcome.selected_buyer_id,
        selected_offer_id=outcome.selected_offer_id,
        selected_buyer_name=outcome.selected_buyer_name,
        expected_yield_quintals=outcome.expected_yield_quintals,
        yield_low_quintals=outcome.yield_low_quintals,
        yield_high_quintals=outcome.yield_high_quintals,
        expected_price_per_quintal=outcome.expected_price_per_quintal,
        price_low_per_quintal=outcome.price_low_per_quintal,
        price_high_per_quintal=outcome.price_high_per_quintal,
        gross_revenue=outcome.gross_revenue,
        transport_cost=outcome.transport_cost,
        other_costs=outcome.other_costs,
        net_realization=outcome.net_realization,
        net_realization_per_quintal=outcome.net_realization_per_quintal,
        wait_expected_net=outcome.wait_expected_net,
        risk_score=outcome.risk_score,
        risk_category=outcome.risk_category,
        data_completeness=outcome.data_completeness,
        confidence=outcome.confidence,
        policy_version=policy.version,
        explanation=outcome.explanation,
        inputs_snapshot=inputs_snapshot,
        outputs=outputs,
        generated_at=generated_at,
    )
    result.factors = [
        DecisionFactor(
            factor=factor.factor,
            direction=factor.direction,
            weight=factor.weight,
            value=factor.value,
            description=factor.description,
        )
        for factor in outcome.factors
    ]
    db.add(result)
    db.commit()
    db.refresh(result)
    return result, to_schema(result)


def to_schema(result: DecisionResult) -> DecisionOut:
    outputs = result.outputs or {}
    return DecisionOut(
        id=result.id,
        farm_id=result.farm_id,
        crop_id=result.crop_id,
        action=result.action,
        selected_buyer_id=result.selected_buyer_id,
        selected_offer_id=result.selected_offer_id,
        selected_buyer_name=result.selected_buyer_name,
        expected_yield_quintals=result.expected_yield_quintals,
        yield_low_quintals=result.yield_low_quintals,
        yield_high_quintals=result.yield_high_quintals,
        expected_price_per_quintal=result.expected_price_per_quintal,
        price_low_per_quintal=result.price_low_per_quintal,
        price_high_per_quintal=result.price_high_per_quintal,
        gross_revenue=result.gross_revenue,
        transport_cost=result.transport_cost,
        other_costs=result.other_costs,
        net_realization=result.net_realization,
        net_realization_per_quintal=result.net_realization_per_quintal,
        wait_expected_net=result.wait_expected_net,
        risk_score=result.risk_score,
        risk_category=result.risk_category,
        data_completeness=result.data_completeness,
        confidence=result.confidence,
        policy_version=result.policy_version,
        explanation=result.explanation,
        inputs_snapshot=result.inputs_snapshot,
        outputs=result.outputs,
        generated_at=result.generated_at,
        factors=[factor for factor in result.factors],
        buyer_evaluations=outputs.get("buyer_evaluations", []),
        missing_inputs=outputs.get("missing_inputs", []),
        assumptions=outputs.get("assumptions", []),
        data_freshness=outputs.get("data_freshness", {}),
    )


def list_decisions(
    db: Session,
    user: User,
    *,
    farm_id: int | None = None,
    crop_id: int | None = None,
    action: str | None = None,
) -> list[DecisionResult]:
    query = select(DecisionResult).where(DecisionResult.user_id == user.id)
    if farm_id is not None:
        query = query.where(DecisionResult.farm_id == farm_id)
    if crop_id is not None:
        query = query.where(DecisionResult.crop_id == crop_id)
    if action:
        query = query.where(DecisionResult.action == action)
    return list(db.scalars(query.order_by(DecisionResult.generated_at.desc())))


def get_decision(db: Session, user: User, decision_id: int) -> DecisionResult:
    row = db.get(DecisionResult, decision_id)
    if row is None or row.user_id != user.id:
        raise NotFoundError("Decision not found")
    return row


def delete_decision(db: Session, row: DecisionResult) -> None:
    db.delete(row)
    db.commit()
