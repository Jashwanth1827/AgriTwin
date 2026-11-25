"""Farm and crop routes with ownership isolation."""

from __future__ import annotations

from fastapi import APIRouter, Query, status

from app.api.deps import CurrentUser, DbSession, get_crop, get_farm
from app.schemas.common import Message
from app.schemas.farm import (
    CropCreate,
    CropOut,
    CropUpdate,
    FarmCreate,
    FarmDetail,
    FarmOut,
    FarmUpdate,
)
from app.services import farms as farm_service

router = APIRouter(tags=["farms"])


@router.get("/farms", response_model=list[FarmOut])
def list_farms(user: CurrentUser, db: DbSession) -> list[FarmOut]:
    return [FarmOut.model_validate(farm) for farm in farm_service.list_farms(db, user)]


@router.post("/farms", response_model=FarmOut, status_code=status.HTTP_201_CREATED)
def create_farm(payload: FarmCreate, user: CurrentUser, db: DbSession) -> FarmOut:
    return FarmOut.model_validate(farm_service.create_farm(db, user, payload))


@router.get("/farms/{farm_id}", response_model=FarmDetail)
def get_farm_detail(farm_id: int, user: CurrentUser, db: DbSession) -> FarmDetail:
    farm = get_farm(db, user, farm_id)
    detail = FarmDetail.model_validate(farm)
    detail.crops = [CropOut.model_validate(crop) for crop in farm.crops]
    return detail


@router.patch("/farms/{farm_id}", response_model=FarmOut)
def update_farm(
    farm_id: int, payload: FarmUpdate, user: CurrentUser, db: DbSession
) -> FarmOut:
    farm = get_farm(db, user, farm_id)
    return FarmOut.model_validate(farm_service.update_farm(db, farm, payload))


@router.delete("/farms/{farm_id}", response_model=Message)
def delete_farm(farm_id: int, user: CurrentUser, db: DbSession) -> Message:
    farm = get_farm(db, user, farm_id)
    farm_service.delete_farm(db, farm)
    return Message(message="Farm deleted")


@router.get("/farms/{farm_id}/crops", response_model=list[CropOut])
def list_farm_crops(farm_id: int, user: CurrentUser, db: DbSession) -> list[CropOut]:
    get_farm(db, user, farm_id)
    return [CropOut.model_validate(crop) for crop in farm_service.list_crops(db, user, farm_id)]


@router.get("/crops", response_model=list[CropOut])
def list_crops(
    user: CurrentUser,
    db: DbSession,
    farm_id: int | None = Query(default=None),
) -> list[CropOut]:
    if farm_id is not None:
        get_farm(db, user, farm_id)
    return [CropOut.model_validate(crop) for crop in farm_service.list_crops(db, user, farm_id)]


@router.post("/crops", response_model=CropOut, status_code=status.HTTP_201_CREATED)
def create_crop(payload: CropCreate, user: CurrentUser, db: DbSession) -> CropOut:
    return CropOut.model_validate(farm_service.create_crop(db, user, payload))


@router.get("/crops/{crop_id}", response_model=CropOut)
def get_crop_detail(crop_id: int, user: CurrentUser, db: DbSession) -> CropOut:
    return CropOut.model_validate(get_crop(db, user, crop_id))


@router.patch("/crops/{crop_id}", response_model=CropOut)
def update_crop(
    crop_id: int, payload: CropUpdate, user: CurrentUser, db: DbSession
) -> CropOut:
    crop = get_crop(db, user, crop_id)
    return CropOut.model_validate(farm_service.update_crop(db, crop, payload))


@router.delete("/crops/{crop_id}", response_model=Message)
def delete_crop(crop_id: int, user: CurrentUser, db: DbSession) -> Message:
    crop = get_crop(db, user, crop_id)
    farm_service.delete_crop(db, crop)
    return Message(message="Crop deleted")
