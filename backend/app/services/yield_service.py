"""Yield prediction and harvest-readiness service."""

from __future__ import annotations

from datetime import date, datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import AppError, NotFoundError
from app.ml.yield_prediction.inference import YieldModelService, YieldModelUnavailable
from app.models.farm import Crop, Farm
from app.models.user import User
from app.models.yield_ import HistoricalYieldRecord, YieldPrediction
from app.services.crop_calendar import harvest_readiness


def _model() -> YieldModelService:
    return YieldModelService.instance()


def model_info() -> dict:
    return _model().info()


def predict(
    db: Session,
    user: User,
    farm: Farm,
    crop: Crop,
    *,
    growth_stage_override: str | None = None,
) -> YieldPrediction:
    service = _model()
    if not service.available:
        raise AppError(
            "Yield model is not available. Train it with "
            "`python ml/yield_prediction/training/train.py`.",
            status_code=503,
            code="model_unavailable",
            details=service.info(),
        )
    try:
        result = service.predict(
            state=farm.state,
            district=farm.district,
            crop=crop.crop_name,
            season=crop.season,
            area_ha=crop.area_hectares,
        )
    except YieldModelUnavailable as exc:
        raise AppError(str(exc), status_code=503, code="model_unavailable") from exc

    per_hectare = float(result["yield_per_hectare"])
    lower = float(result["lower_yield_per_hectare"])
    upper = float(result["upper_yield_per_hectare"])
    area = float(crop.area_hectares)
    inputs = {
        "state": farm.state,
        "district": farm.district,
        "crop": crop.crop_name,
        "season": crop.season,
        "area_hectares": area,
        "growth_stage": growth_stage_override or crop.growth_stage,
        "sowing_date": crop.sowing_date.isoformat(),
    }
    # The model consumes state, district, crop, season and area. Soil and weather
    # are deliberately not claimed as model inputs because the historical
    # dataset has no paired observations for them.
    completeness = 1.0
    notes = (
        "The yield model uses state, district, crop, season and area only. "
        "Soil and weather observations are displayed elsewhere but are not model inputs. "
        "The interval is an 80% split-conformal interval calibrated on 2013-2014."
    )
    prediction = YieldPrediction(
        user_id=user.id,
        farm_id=farm.id,
        crop_id=crop.id,
        model_version=str(result["model_version"]),
        model_name=str(result["model_name"]),
        predicted_yield_per_hectare=round(per_hectare, 3),
        predicted_total_quintals=round(per_hectare * area, 3),
        lower_yield_per_hectare=round(lower, 3),
        upper_yield_per_hectare=round(upper, 3),
        lower_total_quintals=round(lower * area, 3),
        upper_total_quintals=round(upper * area, 3),
        interval_method=str(result["interval_method"]),
        interval_coverage=result.get("interval_coverage"),
        confidence=float(result["confidence"]),
        input_completeness=completeness,
        is_experimental=bool(result.get("is_experimental", True)),
        inputs=inputs,
        notes=notes,
        predicted_at=datetime.now(timezone.utc),
    )
    db.add(prediction)
    db.commit()
    db.refresh(prediction)
    return prediction


def list_predictions(
    db: Session, user: User, *, farm_id: int | None = None, crop_id: int | None = None
) -> list[YieldPrediction]:
    query = select(YieldPrediction).where(YieldPrediction.user_id == user.id)
    if farm_id is not None:
        query = query.where(YieldPrediction.farm_id == farm_id)
    if crop_id is not None:
        query = query.where(YieldPrediction.crop_id == crop_id)
    return list(db.scalars(query.order_by(YieldPrediction.predicted_at.desc())))


def latest_for_crop(db: Session, user: User, crop_id: int) -> YieldPrediction | None:
    return db.scalar(
        select(YieldPrediction)
        .where(YieldPrediction.user_id == user.id, YieldPrediction.crop_id == crop_id)
        .order_by(YieldPrediction.predicted_at.desc())
        .limit(1)
    )


def get_prediction(db: Session, user: User, prediction_id: int) -> YieldPrediction:
    prediction = db.get(YieldPrediction, prediction_id)
    if prediction is None or prediction.user_id != user.id:
        raise NotFoundError("Yield prediction not found")
    return prediction


def readiness_for_crop(crop: Crop, today: date | None = None) -> dict:
    return harvest_readiness(
        crop=crop.crop_name,
        season=crop.season,
        sowing_date=crop.sowing_date,
        expected_harvest_date=crop.expected_harvest_date,
        today=today or date.today(),
    )


def history(
    db: Session, crop: str, state: str | None = None, limit_years: int = 12
) -> list[dict]:
    query = (
        select(
            HistoricalYieldRecord.year,
            func.avg(HistoricalYieldRecord.yield_per_hectare).label("average_yield"),
            func.count(HistoricalYieldRecord.id).label("records"),
        )
        .where(HistoricalYieldRecord.crop == crop)
        .group_by(HistoricalYieldRecord.year)
        .order_by(HistoricalYieldRecord.year.desc())
        .limit(limit_years)
    )
    if state:
        query = query.where(HistoricalYieldRecord.state == state)
    rows = list(db.execute(query).all())
    rows.reverse()
    return [
        {
            "year": int(year),
            "average_yield_per_hectare": round(float(average), 2),
            "records": int(records),
        }
        for year, average, records in rows
    ]
