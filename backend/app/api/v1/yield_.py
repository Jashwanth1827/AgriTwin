"""Yield prediction and harvest-readiness routes."""

from __future__ import annotations

from fastapi import APIRouter, Query, status

from app.api.deps import CurrentUser, DbSession, get_crop, get_farm
from app.schemas.yield_ import (
    HarvestReadinessOut,
    YieldModelInfo,
    YieldPredictRequest,
    YieldPredictionDetail,
    YieldPredictionOut,
)
from app.services import yield_service

router = APIRouter(prefix="/yield", tags=["yield"])


@router.get("/model", response_model=YieldModelInfo)
def model_info() -> YieldModelInfo:
    return YieldModelInfo(**yield_service.model_info())


@router.post(
    "/predict", response_model=YieldPredictionDetail, status_code=status.HTTP_201_CREATED
)
def predict(payload: YieldPredictRequest, user: CurrentUser, db: DbSession) -> YieldPredictionDetail:
    farm = get_farm(db, user, payload.farm_id)
    crop = get_crop(db, user, payload.crop_id)
    if crop.farm_id != farm.id:
        from app.core.errors import AppError

        raise AppError("The selected crop does not belong to this farm", status_code=422)
    prediction = yield_service.predict(
        db, user, farm, crop, growth_stage_override=payload.growth_stage_override
    )
    readiness = yield_service.readiness_for_crop(crop)
    return YieldPredictionDetail(
        prediction=YieldPredictionOut.model_validate(prediction),
        harvest_readiness=HarvestReadinessOut(**readiness),
        model=YieldModelInfo(**yield_service.model_info()),
    )


@router.get("/predictions", response_model=list[YieldPredictionOut])
def list_predictions(
    user: CurrentUser,
    db: DbSession,
    farm_id: int | None = Query(default=None),
    crop_id: int | None = Query(default=None),
) -> list[YieldPredictionOut]:
    return [
        YieldPredictionOut.model_validate(row)
        for row in yield_service.list_predictions(db, user, farm_id=farm_id, crop_id=crop_id)
    ]


@router.get("/predictions/{prediction_id}", response_model=YieldPredictionOut)
def get_prediction(prediction_id: int, user: CurrentUser, db: DbSession) -> YieldPredictionOut:
    return YieldPredictionOut.model_validate(
        yield_service.get_prediction(db, user, prediction_id)
    )


@router.get("/readiness/{crop_id}", response_model=HarvestReadinessOut)
def readiness(crop_id: int, user: CurrentUser, db: DbSession) -> HarvestReadinessOut:
    crop = get_crop(db, user, crop_id)
    return HarvestReadinessOut(**yield_service.readiness_for_crop(crop))


@router.get("/history")
def history(
    _user: CurrentUser,
    db: DbSession,
    crop: str = Query(...),
    state: str | None = Query(default=None),
    limit_years: int = Query(default=12, ge=1, le=30),
) -> dict:
    return {
        "crop": crop,
        "state": state,
        "years": yield_service.history(db, crop, state, limit_years),
        "unit": "quintal/hectare",
    }
