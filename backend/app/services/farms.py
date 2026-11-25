"""Farm and crop CRUD with strict ownership isolation."""

from __future__ import annotations

from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import ConflictError, NotFoundError
from app.models.farm import Crop, Farm
from app.models.user import User
from app.schemas.farm import CropCreate, CropUpdate, FarmCreate, FarmUpdate
from app.schemas.common import validate_patch
from app.services.crop_calendar import estimate_harvest_date


def list_farms(db: Session, user: User) -> list[Farm]:
    return list(
        db.scalars(select(Farm).where(Farm.user_id == user.id).order_by(Farm.created_at.desc()))
    )


def create_farm(db: Session, user: User, payload: FarmCreate) -> Farm:
    farm = Farm(
        user_id=user.id,
        **payload.model_dump(),
        is_demo=False,
    )
    db.add(farm)
    db.commit()
    db.refresh(farm)
    return farm


def update_farm(db: Session, farm: Farm, payload: FarmUpdate) -> Farm:
    updates = payload.model_dump(exclude_unset=True)
    validate_patch(FarmCreate, farm, updates)
    for key, value in updates.items():
        setattr(farm, key, value)
    db.commit()
    db.refresh(farm)
    return farm


def delete_farm(db: Session, farm: Farm) -> None:
    db.delete(farm)
    db.commit()


def list_crops(db: Session, user: User, farm_id: int | None = None) -> list[Crop]:
    query = select(Crop).join(Farm, Crop.farm_id == Farm.id).where(Farm.user_id == user.id)
    if farm_id is not None:
        query = query.where(Crop.farm_id == farm_id)
    return list(db.scalars(query.order_by(Crop.created_at.desc())))


def create_crop(db: Session, user: User, payload: CropCreate) -> Crop:
    farm = db.get(Farm, payload.farm_id)
    if farm is None:
        raise NotFoundError("Farm not found")
    if farm.user_id != user.id:
        raise NotFoundError("Farm not found")

    active_area = db.scalar(
        select(func.coalesce(func.sum(Crop.area_hectares), 0.0)).where(
            Crop.farm_id == farm.id, Crop.status == "active"
        )
    ) or 0.0
    if float(active_area) + payload.area_hectares > farm.total_area_hectares * 1.001:
        raise ConflictError(
            f"Active crop area ({float(active_area):g} ha) plus this crop "
            f"({payload.area_hectares:g} ha) exceeds the farm size "
            f"({farm.total_area_hectares:g} ha)."
        )

    data = payload.model_dump()
    data.pop("farm_id")
    if data.get("expected_harvest_date") is None:
        data["expected_harvest_date"] = estimate_harvest_date(
            data["crop_name"], data["season"], data["sowing_date"]
        )
    crop = Crop(farm_id=farm.id, **data, is_demo=False)
    db.add(crop)
    db.commit()
    db.refresh(crop)
    return crop


def update_crop(db: Session, crop: Crop, payload: CropUpdate) -> Crop:
    updates = payload.model_dump(exclude_unset=True)
    validate_patch(CropCreate, crop, updates)
    for key, value in updates.items():
        setattr(crop, key, value)
    if updates.get("expected_harvest_date") is None and (
        "sowing_date" in updates or "crop_name" in updates or "season" in updates
    ):
        crop.expected_harvest_date = estimate_harvest_date(
            crop.crop_name, crop.season, crop.sowing_date
        )
    db.commit()
    db.refresh(crop)
    return crop


def delete_crop(db: Session, crop: Crop) -> None:
    db.delete(crop)
    db.commit()


def crop_age_days(crop: Crop, today: date | None = None) -> int:
    today = today or date.today()
    return max(0, (today - crop.sowing_date).days)
