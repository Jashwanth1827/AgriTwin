from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, Field, field_validator, model_validator

from app.core.constants import BUYER_TYPES, CROPS, INDIAN_STATES
from app.schemas.common import ORMModel


class BuyerBase(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    buyer_type: str
    contact_name: str | None = Field(default=None, max_length=120)
    contact_phone: str | None = Field(default=None, max_length=30)
    market_name: str | None = Field(default=None, max_length=160)
    district: str = Field(min_length=2, max_length=120)
    state: str
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    notes: str | None = Field(default=None, max_length=2000)

    @field_validator("buyer_type")
    @classmethod
    def valid_type(cls, value: str) -> str:
        if value not in BUYER_TYPES:
            raise ValueError(f"Buyer type must be one of: {', '.join(BUYER_TYPES)}")
        return value

    @field_validator("state")
    @classmethod
    def valid_state(cls, value: str) -> str:
        if value not in INDIAN_STATES:
            raise ValueError("Unknown Indian state or union territory")
        return value

    @model_validator(mode="after")
    def coordinates_pair(self):
        if (self.latitude is None) != (self.longitude is None):
            raise ValueError("Latitude and longitude must be provided together")
        return self


class BuyerCreate(BuyerBase):
    pass


class BuyerUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=160)
    buyer_type: str | None = None
    contact_name: str | None = Field(default=None, max_length=120)
    contact_phone: str | None = Field(default=None, max_length=30)
    market_name: str | None = Field(default=None, max_length=160)
    district: str | None = Field(default=None, min_length=2, max_length=120)
    state: str | None = None
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    notes: str | None = Field(default=None, max_length=2000)


class OfferCreate(BaseModel):
    crop: str
    variety: str | None = Field(default=None, max_length=120)
    offered_price_per_quintal: float = Field(gt=0, le=1000000)
    min_quantity_quintals: float = Field(default=1, gt=0, le=1000000)
    max_quantity_quintals: float | None = Field(default=None, gt=0, le=1000000)
    offer_date: date
    expiry_date: date
    conditions: str | None = Field(default=None, max_length=2000)
    is_active: bool = True

    @field_validator("crop")
    @classmethod
    def valid_crop(cls, value: str) -> str:
        if value not in CROPS:
            raise ValueError("Unsupported crop")
        return value

    @model_validator(mode="after")
    def validate_offer(self):
        if self.expiry_date < self.offer_date:
            raise ValueError("Expiry date cannot be before offer date")
        if self.max_quantity_quintals is not None and self.max_quantity_quintals < self.min_quantity_quintals:
            raise ValueError("Maximum quantity cannot be less than minimum quantity")
        return self


class OfferUpdate(BaseModel):
    crop: str | None = None
    variety: str | None = None
    offered_price_per_quintal: float | None = Field(default=None, gt=0, le=1000000)
    min_quantity_quintals: float | None = Field(default=None, gt=0)
    max_quantity_quintals: float | None = Field(default=None, gt=0)
    offer_date: date | None = None
    expiry_date: date | None = None
    conditions: str | None = None
    is_active: bool | None = None


class OfferOut(ORMModel):
    id: int
    buyer_id: int
    crop: str
    variety: str | None
    offered_price_per_quintal: float
    min_quantity_quintals: float
    max_quantity_quintals: float | None
    offer_date: date
    expiry_date: date
    conditions: str | None
    is_active: bool
    is_demo: bool
    created_at: datetime


class BuyerOut(ORMModel):
    id: int
    name: str
    buyer_type: str
    contact_name: str | None
    contact_phone: str | None
    market_name: str | None
    district: str
    state: str
    latitude: float | None
    longitude: float | None
    notes: str | None
    is_demo: bool
    created_at: datetime
    updated_at: datetime


class BuyerDetail(BuyerOut):
    offers: list[OfferOut] = []


class BuyerWithOffers(BuyerOut):
    active_offers: list[OfferOut] = []
    best_offer_price: float | None = None
