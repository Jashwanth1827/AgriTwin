"""Dashboard aggregation queries."""

from __future__ import annotations

from datetime import date, datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.constants import CROPS
from app.models.decision import DecisionResult
from app.models.farm import Crop, Farm
from app.models.user import User
from app.services import crop_health as health_service
from app.services import market as market_service
from app.services import yield_service


def _latest_decision(db: Session, user: User) -> DecisionResult | None:
    return db.scalar(
        select(DecisionResult)
        .where(DecisionResult.user_id == user.id)
        .order_by(DecisionResult.generated_at.desc())
        .limit(1)
    )


def _pick_crop(db: Session, user: User) -> Crop | None:
    return db.scalar(
        select(Crop)
        .join(Farm, Crop.farm_id == Farm.id)
        .where(Farm.user_id == user.id, Crop.status == "active")
        .order_by(Crop.created_at.desc())
        .limit(1)
    )


def overview(db: Session, user: User) -> dict:
    farms = list(
        db.scalars(select(Farm).where(Farm.user_id == user.id).order_by(Farm.created_at))
    )
    farm_ids = [farm.id for farm in farms]
    active_crops = 0
    if farm_ids:
        active_crops = int(
            db.scalar(
                select(func.count(Crop.id)).where(
                    Crop.farm_id.in_(farm_ids), Crop.status == "active"
                )
            )
            or 0
        )
    crop = _pick_crop(db, user)
    health = health_service.latest_for_crop(db, user, crop.id) if crop else None
    yield_row = yield_service.latest_for_crop(db, user, crop.id) if crop else None
    decision = _latest_decision(db, user)

    market: dict = {"available": False}
    if crop:
        snapshot = market_service.latest_market_snapshot(db, crop.crop_name)
        if snapshot:
            forecast = market_service.latest_forecast(db, crop.crop_name, snapshot["market"])
            market = {
                "available": True,
                "crop": crop.crop_name,
                "market": snapshot["market"],
                "latest_price": snapshot["latest_price"],
                "forecast_price": forecast.expected_price if forecast else None,
                "lower_bound": forecast.lower_bound if forecast else None,
                "upper_bound": forecast.upper_bound if forecast else None,
                "latest_observation_date": snapshot["latest_observation_date"],
                "data_freshness_days": snapshot["data_freshness_days"],
                "is_demo": False,
            }

    notices: list[str] = []
    if health is not None and health.is_demo:
        notices.append("The latest crop-health result is a labelled demo heuristic, not a trained-model diagnosis.")
    if market.get("data_freshness_days") is not None and market["data_freshness_days"] > 90:
        notices.append(
            f"Market prices are {market['data_freshness_days']} days old. Forecasts and "
            "decisions are marked with elevated data-freshness risk."
        )

    return {
        "total_farms": len(farms),
        "total_area_hectares": round(sum(farm.total_area_hectares for farm in farms), 2),
        "active_crops": active_crops,
        "crop_health": {
            "available": health is not None,
            "prediction_id": health.id if health else None,
            "predicted_label": health.predicted_label if health else None,
            "crop": crop.crop_name if crop else None,
            "confidence": health.confidence if health else None,
            "severity": health.severity if health else None,
            "is_healthy": health.is_healthy if health else None,
            "predicted_at": health.predicted_at if health else None,
            "is_demo": bool(health.is_demo) if health else False,
        },
        "yield_prediction": {
            "available": yield_row is not None,
            "prediction_id": yield_row.id if yield_row else None,
            "crop": crop.crop_name if crop else None,
            "yield_per_hectare": yield_row.predicted_yield_per_hectare if yield_row else None,
            "total_quintals": yield_row.predicted_total_quintals if yield_row else None,
            "lower_total_quintals": yield_row.lower_total_quintals if yield_row else None,
            "upper_total_quintals": yield_row.upper_total_quintals if yield_row else None,
            "input_completeness": yield_row.input_completeness if yield_row else None,
            "predicted_at": yield_row.predicted_at if yield_row else None,
        },
        "market": market,
        "decision": {
            "available": decision is not None,
            "decision_id": decision.id if decision else None,
            "action": decision.action if decision else None,
            "selected_buyer_name": decision.selected_buyer_name if decision else None,
            "net_realization": decision.net_realization if decision else None,
            "net_realization_per_quintal": decision.net_realization_per_quintal if decision else None,
            "risk_score": decision.risk_score if decision else None,
            "risk_category": decision.risk_category if decision else None,
            "generated_at": decision.generated_at if decision else None,
        },
        "farms": [
            {
                "id": farm.id,
                "name": farm.name,
                "district": farm.district,
                "state": farm.state,
                "total_area_hectares": farm.total_area_hectares,
                "active_crops": sum(1 for item in farm.crops if item.status == "active"),
                "is_demo": farm.is_demo,
            }
            for farm in farms
        ],
        "data_mode": "real",
        "is_demo": any(farm.is_demo for farm in farms),
        "generated_at": datetime.now(timezone.utc),
        "notices": notices,
    }


def crop_health_summary(db: Session, user: User) -> dict:
    from app.models.crop_health import CropHealthPrediction

    rows = list(
        db.scalars(
            select(CropHealthPrediction)
            .where(CropHealthPrediction.user_id == user.id)
            .order_by(CropHealthPrediction.predicted_at.desc())
        )
    )
    healthy = sum(1 for row in rows if row.is_healthy)
    by_label: dict[str, int] = {}
    for row in rows:
        by_label[row.predicted_label] = by_label.get(row.predicted_label, 0) + 1
    recent = [
        {
            "id": row.id,
            "label": row.predicted_label,
            "crop": row.predicted_crop,
            "is_healthy": row.is_healthy,
            "confidence": row.confidence,
            "severity": row.severity,
            "is_demo": row.is_demo,
            "predicted_at": row.predicted_at,
        }
        for row in rows[:10]
    ]
    return {
        "total_predictions": len(rows),
        "healthy_count": healthy,
        "diseased_count": len(rows) - healthy,
        "average_confidence": round(sum(row.confidence for row in rows) / len(rows), 4) if rows else None,
        "recent": recent,
        "by_label": [
            {"label": label, "count": count}
            for label, count in sorted(by_label.items(), key=lambda item: item[1], reverse=True)
        ],
        "data_mode": "real",
    }


def market_summary(db: Session, user: User, crop: str | None = None) -> dict:
    available = {row["crop"] for row in market_service.available_crops(db)}
    if crop is None:
        selected = _pick_crop(db, user)
        crop = selected.crop_name if selected and selected.crop_name in available else None
        if crop is None and available:
            crop = sorted(available)[0]
    if crop is None:
        return {
            "crop": None,
            "points": [],
            "forecast": None,
            "markets": [],
            "data_freshness_days": None,
            "data_mode": "real",
        }
    series = market_service.series_payload(db, crop, None, days=180)
    forecast = market_service.latest_forecast(db, crop, series["market"])
    return {
        "crop": crop,
        "points": series["points"],
        "forecast": {
            "id": forecast.id,
            "market": forecast.market,
            "expected_price": forecast.expected_price,
            "lower_bound": forecast.lower_bound,
            "upper_bound": forecast.upper_bound,
            "model_name": forecast.model_name,
            "points": forecast.points,
            "generated_at": forecast.generated_at,
            "is_experimental": forecast.is_experimental,
        }
        if forecast
        else None,
        "markets": market_service.available_markets(db, crop),
        "data_freshness_days": series["data_freshness_days"],
        "data_mode": "real",
    }


def decisions_summary(db: Session, user: User) -> dict:
    rows = list(
        db.scalars(
            select(DecisionResult)
            .where(DecisionResult.user_id == user.id)
            .order_by(DecisionResult.generated_at.desc())
        )
    )
    by_action: dict[str, int] = {}
    for row in rows:
        by_action[row.action] = by_action.get(row.action, 0) + 1
    return {
        "total": len(rows),
        "by_action": by_action,
        "recent": [
            {
                "id": row.id,
                "action": row.action,
                "crop_id": row.crop_id,
                "selected_buyer_name": row.selected_buyer_name,
                "net_realization": row.net_realization,
                "risk_score": row.risk_score,
                "risk_category": row.risk_category,
                "generated_at": row.generated_at,
            }
            for row in rows[:10]
        ],
        "data_mode": "real",
    }
