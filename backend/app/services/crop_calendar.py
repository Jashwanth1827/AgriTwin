"""Crop calendar and harvest-readiness helpers (config-driven)."""

from __future__ import annotations

import json
from datetime import date, timedelta
from functools import lru_cache

from app.core.config import settings


@lru_cache
def _calendar() -> dict:
    with settings.CROP_CALENDAR_PATH.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def crop_calendar(crop: str, season: str) -> dict:
    payload = _calendar()
    entry = payload.get("crops", {}).get(crop)
    if entry is None:
        entry = payload["default"]
        configured = False
    else:
        configured = True
    duration = entry.get("seasons", {}).get(season)
    if duration is None:
        duration = entry.get("seasons", {}).get("Whole Year", 120)
    return {
        "duration_days": int(duration),
        "harvest_window_days": int(entry.get("harvest_window_days", 14)),
        "notes": entry.get("notes", ""),
        "source": payload.get("source", "ICAR package of practices"),
        "configured": configured,
        "version": payload.get("version"),
    }


def estimate_harvest_date(crop: str, season: str, sowing_date: date) -> date:
    return sowing_date + timedelta(days=crop_calendar(crop, season)["duration_days"])


def harvest_readiness(
    *,
    crop: str,
    season: str,
    sowing_date: date,
    expected_harvest_date: date | None,
    today: date,
) -> dict:
    calendar = crop_calendar(crop, season)
    expected = expected_harvest_date or estimate_harvest_date(crop, season, sowing_date)
    window = calendar["harvest_window_days"]
    window_start = expected - timedelta(days=max(1, window // 2))
    window_end = expected + timedelta(days=max(1, window // 2))
    days_remaining = (expected - today).days

    if today < sowing_date:
        status = "not_started"
    elif days_remaining > 21:
        status = "growing"
    elif days_remaining > 0:
        status = "approaching"
    elif days_remaining >= -window:
        status = "ready"
    else:
        status = "overdue"

    confidence = 0.78 if calendar["configured"] else 0.45
    notes = calendar["notes"]
    if status == "overdue":
        notes += (
            " The crop is past its typical harvest window; check for lodging,"
            " shattering or deterioration before further delay."
        )
    if expected_harvest_date is None:
        notes += " Harvest date was estimated from the configured crop calendar."
    return {
        "crop": crop,
        "sowing_date": sowing_date,
        "expected_harvest_date": expected,
        "estimated_days_remaining": days_remaining,
        "harvest_window_start": window_start,
        "harvest_window_end": window_end,
        "readiness_status": status,
        "confidence": confidence,
        "notes": notes,
        "weather_considerations": [
            "Avoid harvesting immediately after rain; check produce moisture before storage.",
            "Ensure adequate drying and clean storage to reduce post-harvest losses.",
        ],
        "calendar_source": calendar["source"],
    }
