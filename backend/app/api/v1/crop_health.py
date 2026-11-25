"""Crop-health routes: model info, image upload, inference and history."""

from __future__ import annotations

from fastapi import APIRouter, File, Form, Query, UploadFile, status

from app.api.deps import CurrentUser, DbSession, get_crop, get_farm
from app.core.config import settings
from app.core.constants import DEMO_DATA_NOTICE
from app.schemas.common import Message
from app.schemas.crop_health import (
    CropHealthModelInfo,
    CropHealthPredictResponse,
    CropHealthPredictionOut,
    DiseaseClassOut,
    RecommendationOut,
)
from app.services import crop_health as health_service

router = APIRouter(prefix="/crop-health", tags=["crop-health"])


def _prediction_out(prediction) -> CropHealthPredictionOut:
    payload = CropHealthPredictionOut.model_validate(prediction)
    payload.recommendations = [
        RecommendationOut.model_validate(item) for item in prediction.recommendations
    ]
    if prediction.file_id is not None and prediction.file is not None:
        payload.image_url = f"/uploads/{prediction.file.stored_path}"
    if prediction.gradcam_path:
        payload.gradcam_url = f"/uploads/{prediction.gradcam_path}"
    return payload


@router.get("/model", response_model=CropHealthModelInfo)
def model_info() -> CropHealthModelInfo:
    return CropHealthModelInfo(**health_service.model_info())


@router.get("/classes", response_model=list[DiseaseClassOut])
def classes(db: DbSession, _user: CurrentUser) -> list[DiseaseClassOut]:
    return [DiseaseClassOut.model_validate(row) for row in health_service.disease_classes(db)]


@router.post(
    "/predict",
    response_model=CropHealthPredictResponse,
    status_code=status.HTTP_201_CREATED,
)
def predict(
    user: CurrentUser,
    db: DbSession,
    farm_id: int = Form(...),
    crop_id: int = Form(...),
    file: UploadFile = File(...),
) -> CropHealthPredictResponse:
    farm = get_farm(db, user, farm_id)
    crop = get_crop(db, user, crop_id)
    if crop.farm_id != farm.id:
        from app.core.errors import AppError

        raise AppError("The selected crop does not belong to this farm", status_code=422)
    content = file.file.read()
    upload = health_service.store_upload(
        db,
        user,
        farm=farm,
        crop=crop,
        filename=file.filename or "upload.jpg",
        content_type=file.content_type,
        content=content,
    )
    prediction = health_service.predict(db, user, farm=farm, crop=crop, upload=upload)
    return CropHealthPredictResponse(
        prediction=_prediction_out(prediction),
        model=CropHealthModelInfo(**health_service.model_info()),
        disclaimer=(
            "This is an AI-assisted screening result, not a laboratory diagnosis. "
            "Confirm findings with a local extension officer before applying any treatment."
            + (f" {DEMO_DATA_NOTICE}" if prediction.is_demo else "")
        ),
    )


@router.get("/predictions", response_model=list[CropHealthPredictionOut])
def list_predictions(
    user: CurrentUser,
    db: DbSession,
    farm_id: int | None = Query(default=None),
    crop_id: int | None = Query(default=None),
) -> list[CropHealthPredictionOut]:
    rows = health_service.list_predictions(db, user, farm_id=farm_id, crop_id=crop_id)
    return [_prediction_out(row) for row in rows]


@router.get("/predictions/{prediction_id}", response_model=CropHealthPredictionOut)
def get_prediction(
    prediction_id: int, user: CurrentUser, db: DbSession
) -> CropHealthPredictionOut:
    return _prediction_out(health_service.get_prediction(db, user, prediction_id))


@router.delete("/predictions/{prediction_id}", response_model=Message)
def delete_prediction(
    prediction_id: int, user: CurrentUser, db: DbSession
) -> Message:
    prediction = health_service.get_prediction(db, user, prediction_id)
    health_service.delete_prediction(db, prediction)
    return Message(message="Prediction deleted")
