from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, model_validator

from app.core.constants import TRANSPORT_MODES, VEHICLE_TYPES
from app.schemas.common import ORMModel


class TransportEstimateRequest(BaseModel):
    farm_id: int
    buyer_id: int | None = None
    crop_id: int | None = None
    quantity_quintals: float = Field(gt=0, le=100000)
    vehicle_type: str = "truck"
    transport_mode: str = "road"
    destination_name: str | None = None
    destination_latitude: float | None = Field(default=None, ge=-90, le=90)
    destination_longitude: float | None = Field(default=None, ge=-180, le=180)
    cost_per_km: float | None = Field(default=None, gt=0, le=1000)
    fixed_cost: float | None = Field(default=None, ge=0, le=1000000)
    loading_cost: float | None = Field(default=None, ge=0, le=1000000)
    unloading_cost: float | None = Field(default=None, ge=0, le=1000000)
    vehicle_capacity_quintals: float | None = Field(default=None, gt=0, le=10000)
    use_routing: bool = True

    @model_validator(mode="after")
    def validate_destination(self):
        if self.vehicle_type not in VEHICLE_TYPES:
            raise ValueError(f"Vehicle type must be one of: {', '.join(VEHICLE_TYPES)}")
        if self.transport_mode not in TRANSPORT_MODES:
            raise ValueError(f"Transport mode must be one of: {', '.join(TRANSPORT_MODES)}")
        has_coords = self.destination_latitude is not None and self.destination_longitude is not None
        if (self.destination_latitude is None) != (self.destination_longitude is None):
            raise ValueError("Destination latitude and longitude must be provided together")
        if not self.buyer_id and not has_coords:
            raise ValueError("Provide a buyer_id or destination coordinates")
        return self


class TransportEstimateOut(ORMModel):
    id: int
    farm_id: int
    buyer_id: int | None
    crop_id: int | None
    quantity_quintals: float
    transport_mode: str
    vehicle_type: str
    vehicle_capacity_quintals: float
    trips: int
    distance_km: float
    distance_method: str
    cost_per_km: float
    fixed_cost: float
    loading_cost: float
    unloading_cost: float
    total_cost: float
    cost_per_quintal: float
    cost_per_kg: float
    is_approximate: bool
    provider: str
    notes: str | None
    created_at: datetime
