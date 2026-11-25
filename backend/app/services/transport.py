"""Road-transport cost estimation using OSRM with a geodesic fallback."""

from __future__ import annotations

import json
import math
from functools import lru_cache

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import NotFoundError, ServiceUnavailableError
from app.models.buyer import Buyer
from app.models.farm import Farm
from app.models.transport import TransportationEstimate
from app.models.user import User
from app.schemas.transport import TransportEstimateRequest


@lru_cache
def _defaults() -> dict:
    with settings.TRANSPORT_DEFAULTS_PATH.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def vehicle_options() -> list[dict]:
    payload = _defaults()
    return [
        {"type": key, **value}
        for key, value in payload.get("vehicles", {}).items()
    ]


def vehicle_config(vehicle_type: str) -> dict:
    payload = _defaults()
    entry = payload.get("vehicles", {}).get(vehicle_type)
    if entry is None:
        raise ServiceUnavailableError(f"Unknown vehicle type: {vehicle_type}")
    return entry


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius = 6371.0088
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)
    a = (
        math.sin(d_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    )
    return 2 * radius * math.asin(math.sqrt(a))


def route_distance(
    origin: tuple[float, float],
    destination: tuple[float, float],
    *,
    use_routing: bool = True,
) -> tuple[float, str, str, bool]:
    """Return (distance_km, method, provider, is_approximate)."""
    direct = haversine_km(origin[0], origin[1], destination[0], destination[1])
    if use_routing and settings.ROUTING_PROVIDER == "osrm":
        url = (
            f"{settings.OSRM_BASE_URL}/route/v1/driving/"
            f"{origin[1]},{origin[0]};{destination[1]},{destination[0]}"
        )
        try:
            with httpx.Client(timeout=settings.HTTP_TIMEOUT_SECONDS) as client:
                response = client.get(url, params={"overview": "false"})
                response.raise_for_status()
                payload = response.json()
                if payload.get("code") == "Ok" and payload.get("routes"):
                    return (
                        round(float(payload["routes"][0]["distance"]) / 1000.0, 2),
                        "osrm",
                        "osrm",
                        False,
                    )
        except Exception:
            pass
    distance = round(direct * settings.GEODESIC_DETOUR_FACTOR, 2)
    return distance, "geodesic_detour", "geodesic", True


def estimate(
    db: Session, user: User, payload: TransportEstimateRequest
) -> TransportationEstimate:
    farm = db.get(Farm, payload.farm_id)
    if farm is None or farm.user_id != user.id:
        raise NotFoundError("Farm not found")

    buyer: Buyer | None = None
    destination_name = payload.destination_name
    if payload.buyer_id is not None:
        buyer = db.get(Buyer, payload.buyer_id)
        if buyer is None or buyer.user_id != user.id:
            raise NotFoundError("Buyer not found")
        destination_name = destination_name or buyer.name
        dest_lat, dest_lon = buyer.latitude, buyer.longitude
    else:
        dest_lat, dest_lon = payload.destination_latitude, payload.destination_longitude

    if farm.latitude is None or farm.longitude is None:
        raise ServiceUnavailableError(
            "The farm has no coordinates. Add latitude and longitude to estimate transport."
        )
    if dest_lat is None or dest_lon is None:
        raise ServiceUnavailableError(
            "The destination has no coordinates. Add coordinates to the buyer or request."
        )

    config = vehicle_config(payload.vehicle_type)
    capacity = float(
        payload.vehicle_capacity_quintals
        or config.get("capacity_quintals")
        or settings.DEFAULT_VEHICLE_CAPACITY_QUINTALS
    )
    cost_per_km = float(
        payload.cost_per_km
        if payload.cost_per_km is not None
        else config.get("cost_per_km_inr", settings.DEFAULT_COST_PER_KM_INR)
    )
    fixed = float(
        payload.fixed_cost
        if payload.fixed_cost is not None
        else config.get("fixed_cost_inr", settings.DEFAULT_FIXED_COST_INR)
    )
    loading = float(
        payload.loading_cost
        if payload.loading_cost is not None
        else config.get("loading_cost_inr", settings.DEFAULT_LOADING_COST_INR)
    )
    unloading = float(
        payload.unloading_cost
        if payload.unloading_cost is not None
        else config.get("unloading_cost_inr", settings.DEFAULT_UNLOADING_COST_INR)
    )

    distance, method, provider, approximate = route_distance(
        (farm.latitude, farm.longitude),
        (dest_lat, dest_lon),
        use_routing=payload.use_routing,
    )
    trips = max(1, math.ceil(payload.quantity_quintals / capacity))
    total = trips * (distance * cost_per_km + fixed + loading + unloading)
    cost_per_quintal = total / payload.quantity_quintals
    notes = (
        "Distance is a geodesic estimate adjusted by a detour factor because the "
        "routing provider was unavailable."
        if approximate
        else "Road distance from OSRM. Freight rates are configurable planning defaults, not quotes."
    )

    estimate_row = TransportationEstimate(
        user_id=user.id,
        farm_id=farm.id,
        buyer_id=buyer.id if buyer else None,
        crop_id=payload.crop_id,
        quantity_quintals=payload.quantity_quintals,
        transport_mode=payload.transport_mode,
        vehicle_type=payload.vehicle_type,
        vehicle_capacity_quintals=capacity,
        trips=trips,
        distance_km=distance,
        distance_method=method,
        cost_per_km=cost_per_km,
        fixed_cost=fixed,
        loading_cost=loading,
        unloading_cost=unloading,
        total_cost=round(total, 2),
        cost_per_quintal=round(cost_per_quintal, 2),
        cost_per_kg=round(cost_per_quintal / 100.0, 4),
        is_approximate=approximate,
        provider=provider,
        notes=notes,
    )
    db.add(estimate_row)
    db.commit()
    db.refresh(estimate_row)
    return estimate_row


def list_estimates(db: Session, user: User, farm_id: int | None = None) -> list[TransportationEstimate]:
    query = select(TransportationEstimate).where(TransportationEstimate.user_id == user.id)
    if farm_id is not None:
        query = query.where(TransportationEstimate.farm_id == farm_id)
    return list(db.scalars(query.order_by(TransportationEstimate.created_at.desc())))
