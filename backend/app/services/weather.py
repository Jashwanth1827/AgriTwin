"""Weather and geocoding integration (Open-Meteo, no API key required)."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

import httpx
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.farm import Farm
from app.models.user import User
from app.models.yield_ import WeatherRecord
from app.services.transport import haversine_km

logger = logging.getLogger(__name__)


class WeatherUnavailable(RuntimeError):
    pass


def geocode(district: str, state: str) -> tuple[float, float] | None:
    if settings.GEOCODING_PROVIDER == "disabled":
        return None
    query = f"{district}, {state}, India"
    try:
        with httpx.Client(timeout=settings.HTTP_TIMEOUT_SECONDS) as client:
            response = client.get(
                f"{settings.GEOCODING_BASE_URL}/search",
                params={"name": query, "count": 1, "language": "en", "format": "json"},
            )
            response.raise_for_status()
            results = response.json().get("results") or []
            if not results:
                # Retry with the state alone; district names are often ambiguous.
                response = client.get(
                    f"{settings.GEOCODING_BASE_URL}/search",
                    params={"name": f"{state}, India", "count": 1, "language": "en", "format": "json"},
                )
                response.raise_for_status()
                results = response.json().get("results") or []
            if results:
                return float(results[0]["latitude"]), float(results[0]["longitude"])
    except Exception as exc:
        logger.warning("Geocoding failed for %s: %s", query, exc)
    return None


def resolve_coordinates(farm: Farm) -> tuple[float, float, str, bool]:
    if farm.latitude is not None and farm.longitude is not None:
        return farm.latitude, farm.longitude, "farm", False
    coordinates = geocode(farm.district, farm.state)
    if coordinates is None:
        raise WeatherUnavailable(
            "No coordinates are available for this farm and geocoding failed. "
            "Add latitude and longitude to the farm."
        )
    return coordinates[0], coordinates[1], "geocoded_district", True


def fetch_weather(farm: Farm, days: int = 7) -> dict:
    if settings.WEATHER_PROVIDER == "disabled":
        raise WeatherUnavailable("Weather provider is disabled in configuration")
    latitude, longitude, source, approximate = resolve_coordinates(farm)
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "current": "temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m",
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,wind_speed_10m_max",
        "forecast_days": max(1, min(days, 16)),
        "timezone": "Asia/Kolkata",
    }
    try:
        with httpx.Client(timeout=settings.HTTP_TIMEOUT_SECONDS) as client:
            response = client.get(f"{settings.OPEN_METEO_BASE_URL}/forecast", params=params)
            response.raise_for_status()
            payload = response.json()
    except Exception as exc:
        raise WeatherUnavailable(f"Open-Meteo request failed: {exc}") from exc

    current = payload.get("current") or {}
    daily = payload.get("daily") or {}
    dates = daily.get("time") or []
    daily_rows = [
        {
            "date": dates[index],
            "temperature_max_c": (daily.get("temperature_2m_max") or [None] * len(dates))[index],
            "temperature_min_c": (daily.get("temperature_2m_min") or [None] * len(dates))[index],
            "rainfall_mm": (daily.get("precipitation_sum") or [None] * len(dates))[index],
            "wind_max_kmh": (daily.get("wind_speed_10m_max") or [None] * len(dates))[index],
        }
        for index in range(len(dates))
    ]
    risk = weather_risk(daily_rows)
    return {
        "available": True,
        "source": "open-meteo",
        "latitude": latitude,
        "longitude": longitude,
        "location_source": source,
        "coordinates_approximate": approximate,
        "current": {
            "temperature_c": current.get("temperature_2m"),
            "humidity_pct": current.get("relative_humidity_2m"),
            "rainfall_mm": current.get("precipitation"),
            "wind_speed_kmh": current.get("wind_speed_10m"),
            "observed_at": current.get("time"),
        },
        "daily": daily_rows,
        "risk_score": risk,
        "risk_label": "high" if risk >= 0.66 else ("moderate" if risk >= 0.33 else "low"),
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }


def weather_risk(daily_rows: list[dict]) -> float:
    """Heuristic 0-1 weather risk for harvesting and field operations."""
    if not daily_rows:
        return 0.3
    next_three = daily_rows[:3]
    rain = sum(float(row.get("rainfall_mm") or 0) for row in next_three)
    max_temp = max(float(row.get("temperature_max_c") or 30) for row in next_three)
    wind = max(float(row.get("wind_max_kmh") or 0) for row in next_three)
    rain_risk = min(1.0, rain / 60.0)
    heat_risk = min(1.0, max(0.0, (max_temp - 34.0) / 12.0))
    wind_risk = min(1.0, max(0.0, (wind - 30.0) / 40.0))
    return round(max(0.0, min(1.0, 0.55 * rain_risk + 0.30 * heat_risk + 0.15 * wind_risk)), 4)


def store_weather(
    db: Session, user: User, farm: Farm, payload: dict, days: int
) -> WeatherRecord:
    current = payload.get("current", {})
    observed_raw = current.get("observed_at")
    try:
        observed_at = datetime.fromisoformat(observed_raw) if observed_raw else datetime.now(timezone.utc)
        if observed_at.tzinfo is None:
            observed_at = observed_at.replace(tzinfo=timezone.utc)
    except ValueError:
        observed_at = datetime.now(timezone.utc)
    record = WeatherRecord(
        farm_id=farm.id,
        observed_at=observed_at,
        temperature_c=current.get("temperature_c"),
        humidity_pct=current.get("humidity_pct"),
        rainfall_mm=current.get("rainfall_mm"),
        wind_speed_kmh=current.get("wind_speed_kmh"),
        forecast_days=days,
        source=payload.get("source", "open-meteo"),
        is_demo=False,
        raw=payload,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def distance_between(a: tuple[float, float], b: tuple[float, float]) -> float:
    return haversine_km(a[0], a[1], b[0], b[1])
