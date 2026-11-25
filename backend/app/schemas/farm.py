from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, Field, field_validator, model_validator

from app.core.constants import CROPS, GROWTH_STAGES, INDIAN_STATES, SEASONS, SOIL_TYPES
from app.schemas.common import ORMModel


class FarmBase(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    village: str | None = Field(default=None, max_length=160)
    district: str = Field(min_length=2, max_length=120)
    state: str
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    total_area_hectares: float = Field(gt=0, le=100000)
    soil_type: str | None = None
    soil_ph: float | None = Field(default=None, ge=0, le=14)
    nitrogen_kg_per_ha: float | None = Field(default=None, ge=0, le=1000)
    phosphorus_kg_per_ha: float | None = Field(default=None, ge=0, le=1000)
    potassium_kg_per_ha: float | None = Field(default=None, ge=0, le=1000)
    soil_moisture_pct: float | None = Field(default=None, ge=0, le=100)
    notes: str | None = Field(default=None, max_length=2000)

    @field_validator("state")
    @classmethod
    def valid_state(cls, value: str) -> str:
        if value not in INDIAN_STATES:
            raise ValueError("Unknown Indian state or union territory")
        return value

    @field_validator("soil_type")
    @classmethod
    def valid_soil(cls, value: str | None) -> str | None:
        if value and value not in SOIL_TYPES:
            raise ValueError("Unknown soil type")
        return value

    @model_validator(mode="after")
    def coordinates_pair(self):
        if (self.latitude is None) != (self.longitude is None):
            raise ValueError("Latitude and longitude must be provided together")
        return self


class FarmCreate(FarmBase):
    pass


class FarmUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=160)
    village: str | None = Field(default=None, max_length=160)
    district: str | None = Field(default=None, min_length=2, max_length=120)
    state: str | None = None
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    total_area_hectares: float | None = Field(default=None, gt=0, le=100000)
    soil_type: str | None = None
    soil_ph: float | None = Field(default=None, ge=0, le=14)
    nitrogen_kg_per_ha: float | None = Field(default=None, ge=0, le=1000)
    phosphorus_kg_per_ha: float | None = Field(default=None, ge=0, le=1000)
    potassium_kg_per_ha: float | None = Field(default=None, ge=0, le=1000)
    soil_moisture_pct: float | None = Field(default=None, ge=0, le=100)
    notes: str | None = Field(default=None, max_length=2000)

    @field_validator("state")
    @classmethod
    def valid_state(cls, value: str | None) -> str | None:
        if value and value not in INDIAN_STATES:
            raise ValueError("Unknown Indian state or union territory")
        return value


class FarmOut(ORMModel):
    id: int
    user_id: int
    name: str
    village: str | None
    district: str
    state: str
    latitude: float | None
    longitude: float | None
    total_area_hectares: float
    soil_type: str | None
    soil_ph: float | None
    nitrogen_kg_per_ha: float | None
    phosphorus_kg_per_ha: float | None
    potassium_kg_per_ha: float | None
    soil_moisture_pct: float | None
    notes: str | None
    is_demo: bool
    created_at: datetime
    updated_at: datetime


class CropBase(BaseModel):
    crop_name: str
    variety: str | None = Field(default=None, max_length=120)
    season: str
    sowing_date: date
    expected_harvest_date: date | None = None
    growth_stage: str | None = None
    area_hectares: float = Field(gt=0, le=100000)
    status: str = "active"
    notes: str | None = Field(default=None, max_length=2000)

    @field_validator("crop_name")
    @classmethod
    def valid_crop(cls, value: str) -> str:
        if value not in CROPS:
            raise ValueError(f"Unsupported crop. Choose one of: {', '.join(CROPS)}")
        return value

    @field_validator("season")
    @classmethod
    def valid_season(cls, value: str) -> str:
        if value not in SEASONS:
            raise ValueError(f"Season must be one of: {', '.join(SEASONS)}")
        return value

    @field_validator("growth_stage")
    @classmethod
    def valid_stage(cls, value: str | None) -> str | None:
        if value and value not in GROWTH_STAGES:
            raise ValueError(f"Growth stage must be one of: {', '.join(GROWTH_STAGES)}")
        return value

    @model_validator(mode="after")
    def harvest_after_sowing(self):
        if self.expected_harvest_date and self.expected_harvest_date < self.sowing_date:
            raise ValueError("Expected harvest date cannot be before sowing date")
        return self


class CropCreate(CropBase):
    farm_id: int


class CropUpdate(BaseModel):
    crop_name: str | None = None
    variety: str | None = Field(default=None, max_length=120)
    season: str | None = None
    sowing_date: date | None = None
    expected_harvest_date: date | None = None
    growth_stage: str | None = None
    area_hectares: float | None = Field(default=None, gt=0, le=100000)
    status: str | None = None
    notes: str | None = Field(default=None, max_length=2000)


class CropOut(ORMModel):
    id: int
    farm_id: int
    crop_name: str
    variety: str | None
    season: str
    sowing_date: date
    expected_harvest_date: date | None
    growth_stage: str | None
    area_hectares: float
    status: str
    notes: str | None
    is_demo: bool
    created_at: datetime
    updated_at: datetime


class FarmDetail(FarmOut):
    crops: list[CropOut] = []
