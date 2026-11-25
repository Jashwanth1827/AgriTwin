"""Weather and geocoding routes."""

from __future__ import annotations

from fastapi import APIRouter, Query

from app.api.deps import CurrentUser, DbSession, get_farm
from app.core.errors import ServiceUnavailableError
from app.services import weather as weather_service

router = APIRouter(prefix="/weather", tags=["weather"])


@router.get("/geocode/search")
def geocode(
    _user: CurrentUser,
    district: str = Query(..., min_length=2),
    state: str = Query(..., min_length=2),
) -> dict:
    coordinates = weather_service.geocode(district, state)
    if coordinates is None:
        return {"found": False, "latitude": None, "longitude": None}
    return {
        "found": True,
        "latitude": coordinates[0],
        "longitude": coordinates[1],
        "source": "open-meteo-geocoding",
    }


@router.get("/{farm_id}")
def farm_weather(
    farm_id: int,
    user: CurrentUser,
    db: DbSession,
    days: int = Query(default=7, ge=1, le=16),
    store: bool = Query(default=True),
) -> dict:
    farm = get_farm(db, user, farm_id)
    try:
        payload = weather_service.fetch_weather(farm, days=days)
    except weather_service.WeatherUnavailable as exc:
        raise ServiceUnavailableError(str(exc)) from exc
    if store:
        weather_service.store_weather(db, user, farm, payload, days)
    payload["farm_id"] = farm.id
    return payload
