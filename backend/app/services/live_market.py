"""Live mandi rate retrieval from public government data providers.

Two official Agmarknet/data.gov.in resources are combined: the current daily
mandi-price feed and the variety-wise daily market-price archive, sorted to its
latest observations. When no API key is configured, the keyless Mandi Price API
mirror is used for its five supported states. Every response records the real
provider, contributing resources, source URLs and observation dates so live data
is never confused with bundled demo data.
"""

from __future__ import annotations

import logging
import threading
import time
from datetime import date, datetime, timezone
from typing import Any

import httpx

from app.core.config import settings
from app.core.constants import CROPS
from app.core.errors import AppError

logger = logging.getLogger(__name__)

KELESS_STATES = {
    "Maharashtra",
    "Uttar Pradesh",
    "Punjab",
    "Madhya Pradesh",
    "Karnataka",
}

# Agmarknet uses historical commodity labels that do not always match the
# display names in AgriTwin. The first alias with records wins.
COMMODITY_ALIASES: dict[str, tuple[str, ...]] = {
    "Rice": ("Paddy(Rice)", "Rice", "Paddy"),
    "Wheat": ("Wheat",),
    "Maize": ("Maize", "Corn"),
    "Cotton": ("Cotton",),
    "Soyabean": ("Soyabean", "Soybean"),
    "Groundnut": ("Groundnut",),
    "Onion": ("Onion",),
    "Tomato": ("Tomato",),
    "Potato": ("Potato",),
    "Sugarcane": ("Sugarcane",),
    "Chickpea": (
        "Bengal Gram(Gram)(Whole)",
        "Kabuli Chana(Chickpeas-White)",
        "Gram",
        "Chickpea",
        "Chana",
    ),
    "Mustard": ("Mustard", "Rapeseed &Mustard", "Rapeseed & Mustard"),
    "Chilli": ("Chilli", "Chillies", "Dry chillies", "Green Chilli"),
    "Banana": ("Banana",),
}

STATE_ALIASES: dict[str, str] = {
    "keralam": "Kerala",
    "chatttisgarh": "Chhattisgarh",
    "chattisgarh": "Chhattisgarh",
    "pondicherry": "Puducherry",
}

# The Agmarknet API uses a few older spellings that differ from the display
# names above. Convert display names back before sending state filters.
API_STATE_NAMES: dict[str, str] = {
    "kerala": "Keralam",
    "chhattisgarh": "Chattisgarh",
    "puducherry": "Pondicherry",
}

OFFICIAL_SOURCE_NAME = "Agmarknet / data.gov.in"
OFFICIAL_SOURCE_URL = (
    "https://data.gov.in/catalog/current-daily-price-various-commodities-various-markets-mandi"
)
OFFICIAL_LICENSE = "Government of India Open Government Data (data.gov.in)"
KEYLESS_SOURCE_NAME = "Mandi Price API (Agmarknet/data.gov.in mirror)"
KEYLESS_LICENSE = "CC BY-NC-SA 4.0 (Mandi Price API); source data: Agmarknet/data.gov.in"
VARIETY_SOURCE_NAME = "Agmarknet / data.gov.in - Variety-wise Daily Market Prices"

# The variety-wise resource uses title-cased, underscored field names.
VARIETY_FIELD_MAP: dict[str, str] = {
    "Arrival_Date": "arrival_date",
    "Commodity": "commodity",
    "Commodity_Code": "commodity_code",
    "District": "district",
    "Grade": "grade",
    "Market": "market",
    "Max_Price": "max_price",
    "Min_Price": "min_price",
    "Modal_Price": "modal_price",
    "State": "state",
    "Variety": "variety",
}

# data.gov.in's gateway stalls requests that use library default user agents.
LIVE_MARKET_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/131.0 Safari/537.36"
    ),
    "Accept": "application/json",
}

_CACHE: dict[tuple[Any, ...], tuple[float, dict[str, Any]]] = {}
_CACHE_LOCK = threading.Lock()


def normalise_state(state: str | None) -> str | None:
    if state is None:
        return None
    cleaned = state.strip()
    if not cleaned:
        return None
    return STATE_ALIASES.get(cleaned.lower(), cleaned)


def api_state_filter(state: str | None) -> str | None:
    """Return the state spelling expected by the official Agmarknet API."""
    display_state = normalise_state(state)
    if display_state is None:
        return None
    return API_STATE_NAMES.get(display_state.casefold(), display_state)


def _parse_date(value: Any) -> date | None:
    text = str(value or "").strip()
    if not text:
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d/%m/%y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        return None


def _parse_datetime(value: Any) -> datetime:
    text = str(value or "").strip().replace("Z", "+00:00")
    if text:
        try:
            parsed = datetime.fromisoformat(text)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed.astimezone(timezone.utc)
        except ValueError:
            pass
    return datetime.now(timezone.utc)


def _as_float(value: Any) -> float | None:
    try:
        result = float(str(value).strip())
    except (TypeError, ValueError):
        return None
    return result if result > 0 else None


def _normalise_rows(
    rows: list[dict[str, Any]],
    *,
    crop: str,
    state: str | None,
    market: str | None,
    aliases: tuple[str, ...],
    source_name: str,
    source_url: str,
    license_name: str,
    fetched_at: datetime,
    record_fetched_at: bool,
    limit: int,
    source_resource_id: str | None = None,
) -> list[dict[str, Any]]:
    allowed_commodities = {alias.casefold() for alias in aliases}
    wanted_state = state.casefold() if state else None
    wanted_market = market.casefold() if market else None
    seen: set[tuple[Any, ...]] = set()
    result: list[dict[str, Any]] = []

    for row in rows:
        commodity = str(row.get("commodity") or "").strip()
        if commodity.casefold() not in allowed_commodities:
            continue
        row_state = normalise_state(str(row.get("state") or "").strip()) or ""
        if wanted_state and row_state.casefold() != wanted_state:
            continue
        row_market = str(row.get("market") or "").strip()
        if wanted_market and wanted_market not in row_market.casefold():
            continue

        observed = _parse_date(row.get("arrival_date") or row.get("date"))
        low = _as_float(row.get("min_price"))
        high = _as_float(row.get("max_price"))
        modal = _as_float(row.get("modal_price"))
        if observed is None or low is None or high is None or modal is None:
            continue
        if low > high or not (low <= modal <= high):
            continue

        variety = str(row.get("variety") or "").strip() or "Other"
        grade = str(row.get("grade") or "").strip() or "FAQ"
        district = str(row.get("district") or "").strip()
        commodity_code = str(row.get("commodity_code") or "").strip() or None
        dedupe_key = (observed, row_state, district, row_market, commodity, variety, grade)
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)

        result.append(
            {
                "crop": crop,
                "date": observed,
                "state": row_state,
                "district": district,
                "market": row_market,
                "commodity": commodity,
                "commodity_code": commodity_code,
                "variety": variety,
                "grade": grade,
                "min_price": round(low, 2),
                "max_price": round(high, 2),
                "modal_price": round(modal, 2),
                "unit": "INR/quintal",
                "source": source_name,
                "source_resource_id": source_resource_id,
                "source_url": source_url,
                "license": license_name,
                "fetched_at": _parse_datetime(row.get("fetched_at")) if record_fetched_at else fetched_at,
            }
        )

    result.sort(key=lambda item: (item["date"], item["modal_price"]), reverse=True)
    return result[:limit]


def _canonical_variety_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Map the variety-wise resource's field names to the common row shape."""
    canonical: list[dict[str, Any]] = []
    for row in rows:
        mapped: dict[str, Any] = {}
        for source_key, target_key in VARIETY_FIELD_MAP.items():
            if source_key in row:
                mapped[target_key] = row[source_key]
            elif target_key in row:
                mapped[target_key] = row[target_key]
        if mapped:
            canonical.append(mapped)
    return canonical


def _record_key(row: dict[str, Any]) -> tuple[Any, ...]:
    return (
        row["date"],
        row["state"],
        row["district"],
        str(row["market"]).casefold(),
        str(row["commodity"]).casefold(),
        str(row["variety"]).casefold(),
        str(row["grade"]).casefold(),
    )


def _merge_official_records(
    primary: list[dict[str, Any]],
    secondary: list[dict[str, Any]],
    limit: int,
) -> list[dict[str, Any]]:
    """Deduplicate both feeds while reserving room for unique variety rows."""
    seen = {_record_key(row) for row in primary}
    unique_secondary: list[dict[str, Any]] = []
    for row in secondary:
        key = _record_key(row)
        if key in seen:
            continue
        seen.add(key)
        unique_secondary.append(row)

    sort_key = lambda item: (item["date"], item["modal_price"])
    primary_sorted = sorted(primary, key=sort_key, reverse=True)
    secondary_sorted = sorted(unique_secondary, key=sort_key, reverse=True)

    quota = min(len(secondary_sorted), limit // 2)
    if secondary_sorted and limit >= 2 and quota == 0:
        quota = 1
    primary_slots = limit - quota
    merged = primary_sorted[:primary_slots] + secondary_sorted[:quota]

    remaining = limit - len(merged)
    if remaining > 0:
        for row in primary_sorted[primary_slots:]:
            if remaining <= 0:
                break
            merged.append(row)
            remaining -= 1
        for row in secondary_sorted[quota:]:
            if remaining <= 0:
                break
            merged.append(row)
            remaining -= 1

    merged.sort(key=sort_key, reverse=True)
    return merged[:limit]


def _source_info(
    *,
    resource_id: str,
    name: str,
    url: str,
    rows: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "resource_id": resource_id,
        "name": name,
        "url": url,
        "record_count": len(rows),
        "observation_date": rows[0]["date"] if rows else None,
    }


def _fetch_variety_rows(
    client: httpx.Client,
    *,
    aliases: tuple[str, ...],
    state: str | None,
) -> tuple[list[dict[str, Any]], str | None, datetime]:
    """Fetch the latest variety-wise rows; failures degrade to the primary feed."""
    resource_id = settings.DATA_GOV_VARIETY_RESOURCE_ID
    url = f"{settings.DATA_GOV_BASE_URL.rstrip('/')}/{resource_id}"
    base_params: dict[str, Any] = {
        "api-key": settings.DATA_GOV_API_KEY,
        "format": "json",
        "limit": max(1, settings.DATA_GOV_PAGE_SIZE),
        "sort[Arrival_Date]": "desc",
    }
    if state:
        base_params["filters[State]"] = api_state_filter(state) or state

    fetched_at = datetime.now(timezone.utc)
    for alias in aliases:
        params = {**base_params, "filters[Commodity]": alias}
        try:
            response = client.get(url, params=params)
            response.raise_for_status()
            payload = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            logger.warning("Variety-wise live-rate source unavailable: %s", exc)
            return [], None, fetched_at
        if payload.get("status") not in (None, "ok"):
            logger.warning(
                "Variety-wise live-rate source returned status=%s", payload.get("status")
            )
            return [], None, fetched_at
        rows = payload.get("records") or []
        if rows:
            return rows, alias, _parse_datetime(payload.get("updated_date"))
    return [], None, fetched_at


def _provider() -> str:
    configured = settings.LIVE_MARKET_PROVIDER
    if configured == "disabled":
        raise AppError(
            "Live market provider is disabled",
            status_code=503,
            code="service_unavailable",
        )
    if configured == "data_gov" and not settings.DATA_GOV_API_KEY:
        raise AppError(
            "DATA_GOV_API_KEY is not configured",
            status_code=503,
            code="service_unavailable",
        )
    if configured == "mandi_api":
        return "mandi_api"
    if configured == "data_gov":
        return "data_gov"
    return "data_gov" if settings.DATA_GOV_API_KEY else "mandi_api"


def _fetch_official(
    client: httpx.Client,
    *,
    crop: str,
    state: str | None,
    market: str | None,
    limit: int,
) -> dict[str, Any]:
    aliases = COMMODITY_ALIASES[crop]
    url = f"{settings.DATA_GOV_BASE_URL.rstrip('/')}/{settings.DATA_GOV_RESOURCE_ID}"
    base_params: dict[str, Any] = {
        "api-key": settings.DATA_GOV_API_KEY,
        "format": "json",
        "limit": max(1, settings.DATA_GOV_PAGE_SIZE),
    }
    if state:
        base_params["filters[state]"] = api_state_filter(state) or state

    records: list[dict[str, Any]] = []
    matched_alias: str | None = None
    fetched_at = datetime.now(timezone.utc)
    for alias in aliases:
        params = {**base_params, "filters[commodity]": alias}
        try:
            response = client.get(url, params=params)
            response.raise_for_status()
            payload = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise AppError(
                "Official Agmarknet price service is unavailable",
                status_code=503,
                code="service_unavailable",
                details={"provider": "data_gov"},
            ) from exc
        rows = payload.get("records") or []
        if rows:
            records = rows
            matched_alias = alias
            fetched_at = _parse_datetime(payload.get("updated_date"))
            break

    primary = _normalise_rows(
        records,
        crop=crop,
        state=state,
        market=market,
        aliases=aliases,
        source_name=OFFICIAL_SOURCE_NAME,
        source_url=OFFICIAL_SOURCE_URL,
        license_name=OFFICIAL_LICENSE,
        fetched_at=fetched_at,
        record_fetched_at=False,
        limit=limit,
        source_resource_id=settings.DATA_GOV_RESOURCE_ID,
    )

    variety_rows: list[dict[str, Any]] = []
    variety_alias: str | None = None
    variety_fetched_at = fetched_at
    variety_url = (
        f"https://data.gov.in/resource/{settings.DATA_GOV_VARIETY_RESOURCE_ID}"
    )
    if settings.LIVE_MARKET_USE_VARIETY_SOURCE:
        raw_variety, variety_alias, variety_fetched_at = _fetch_variety_rows(
            client, aliases=aliases, state=state
        )
        variety_rows = _normalise_rows(
            _canonical_variety_rows(raw_variety),
            crop=crop,
            state=state,
            market=market,
            aliases=aliases,
            source_name=VARIETY_SOURCE_NAME,
            source_url=variety_url,
            license_name=OFFICIAL_LICENSE,
            fetched_at=variety_fetched_at,
            record_fetched_at=False,
            limit=max(limit, settings.DATA_GOV_PAGE_SIZE),
            source_resource_id=settings.DATA_GOV_VARIETY_RESOURCE_ID,
        )

    merged = _merge_official_records(primary, variety_rows, limit)
    primary_contributed = [
        row
        for row in merged
        if row["source_resource_id"] == settings.DATA_GOV_RESOURCE_ID
    ]
    variety_contributed = [
        row
        for row in merged
        if row["source_resource_id"] == settings.DATA_GOV_VARIETY_RESOURCE_ID
    ]
    sources = [
        _source_info(
            resource_id=settings.DATA_GOV_RESOURCE_ID,
            name=OFFICIAL_SOURCE_NAME,
            url=OFFICIAL_SOURCE_URL,
            rows=primary_contributed,
        )
    ]
    if settings.LIVE_MARKET_USE_VARIETY_SOURCE:
        sources.append(
            _source_info(
                resource_id=settings.DATA_GOV_VARIETY_RESOURCE_ID,
                name=VARIETY_SOURCE_NAME,
                url=variety_url,
                rows=variety_contributed,
            )
        )

    if primary_contributed and variety_contributed:
        display_source_name = "Agmarknet / data.gov.in (daily + variety-wise)"
    elif variety_contributed and not primary_contributed:
        display_source_name = VARIETY_SOURCE_NAME
    else:
        display_source_name = OFFICIAL_SOURCE_NAME

    return {
        "provider": "data_gov",
        "source_name": display_source_name,
        "source_url": OFFICIAL_SOURCE_URL,
        "license": OFFICIAL_LICENSE,
        "commodity_query": matched_alias or variety_alias or aliases[0],
        "records": merged,
        "fetched_at": max(fetched_at, variety_fetched_at),
        "sources": sources,
    }


def _fetch_keyless(
    client: httpx.Client,
    *,
    crop: str,
    state: str | None,
    market: str | None,
    limit: int,
) -> dict[str, Any]:
    if state and normalise_state(state) not in KELESS_STATES and state not in KELESS_STATES:
        raise AppError(
            "The keyless live-rate mirror covers only Maharashtra, Uttar Pradesh, "
            "Punjab, Madhya Pradesh and Karnataka. Configure DATA_GOV_API_KEY for "
            "nationwide live rates.",
            status_code=422,
            code="unsupported_state",
            details={"supported_states": sorted(KELESS_STATES)},
        )

    aliases = COMMODITY_ALIASES[crop]
    url = f"{settings.MANDI_API_BASE_URL.rstrip('/')}/prices"
    records: list[dict[str, Any]] = []
    matched_alias: str | None = None
    for alias in aliases:
        params: dict[str, Any] = {"commodity": alias}
        if state:
            params["state"] = normalise_state(state) or state
        try:
            response = client.get(url, params=params)
            response.raise_for_status()
            payload = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise AppError(
                "Keyless live market mirror is unavailable",
                status_code=503,
                code="service_unavailable",
                details={"provider": "mandi_api"},
            ) from exc
        rows = payload.get("data") or []
        if rows:
            records = rows
            matched_alias = alias
            break

    fetched_at = _parse_datetime(max((row.get("fetched_at") for row in records), default=None))
    normalised = _normalise_rows(
        records,
        crop=crop,
        state=state,
        market=market,
        aliases=aliases,
        source_name=KEYLESS_SOURCE_NAME,
        source_url=settings.MANDI_API_BASE_URL,
        license_name=KEYLESS_LICENSE,
        fetched_at=fetched_at,
        record_fetched_at=True,
        limit=limit,
    )
    return {
        "provider": "mandi_api",
        "source_name": KEYLESS_SOURCE_NAME,
        "source_url": settings.MANDI_API_BASE_URL,
        "license": KEYLESS_LICENSE,
        "commodity_query": matched_alias or aliases[0],
        "records": normalised,
        "fetched_at": fetched_at,
    }


def _cache_get(key: tuple[Any, ...]) -> dict[str, Any] | None:
    now = time.monotonic()
    with _CACHE_LOCK:
        item = _CACHE.get(key)
        if item is None:
            return None
        expires, value = item
        if expires < now:
            _CACHE.pop(key, None)
            return None
        return dict(value)


def _cache_set(key: tuple[Any, ...], value: dict[str, Any]) -> None:
    expires = time.monotonic() + max(0, settings.EXTERNAL_CACHE_TTL_SECONDS)
    with _CACHE_LOCK:
        _CACHE[key] = (expires, dict(value))


def fetch_live_rates(
    *,
    crop: str,
    state: str | None = None,
    market: str | None = None,
    limit: int = 20,
    force_refresh: bool = False,
) -> dict[str, Any]:
    """Return current mandi rates from the configured live provider."""
    if crop not in CROPS:
        raise AppError(
            f"Unsupported crop '{crop}'",
            status_code=422,
            code="validation_error",
            details={"supported_crops": CROPS},
        )
    crop = next(name for name in CROPS if name.casefold() == crop.casefold())
    state = normalise_state(state)
    market = market.strip() if market and market.strip() else None
    limit = max(1, min(limit, 100))
    provider = _provider()
    cache_key = (provider, crop, state, market, limit)
    if not force_refresh:
        cached = _cache_get(cache_key)
        if cached is not None:
            return cached

    with httpx.Client(
        timeout=settings.LIVE_MARKET_TIMEOUT_SECONDS,
        headers=LIVE_MARKET_HEADERS,
        follow_redirects=True,
    ) as client:
        if provider == "mandi_api":
            payload = _fetch_keyless(
                client, crop=crop, state=state, market=market, limit=limit
            )
        else:
            try:
                payload = _fetch_official(
                    client, crop=crop, state=state, market=market, limit=limit
                )
            except AppError as exc:
                if settings.LIVE_MARKET_PROVIDER != "auto":
                    raise
                logger.warning(
                    "Official live rates failed, using keyless mirror: %s", exc.message
                )
                payload = _fetch_keyless(
                    client, crop=crop, state=state, market=market, limit=limit
                )

    if not payload["records"]:
        raise AppError(
            f"No live {crop} rates were returned for the selected filters",
            status_code=404,
            code="no_live_data",
            details={
                "provider": payload["provider"],
                "commodity_query": payload["commodity_query"],
                "state": state,
            },
        )

    records = payload["records"]
    latest_date = records[0]["date"]
    payload.update(
        {
            "crop": crop,
            "state": state,
            "market": market,
            "unit": "INR/quintal",
            "latest_observation_date": latest_date,
            "data_freshness_days": max(0, (date.today() - latest_date).days),
            "is_demo": False,
            "is_official": payload["provider"] == "data_gov",
            "disclaimer": (
                "Live wholesale mandi rates from a public government data feed. "
                "Rates are indicative, vary by market and variety, and are not a "
                "guaranteed transaction price."
            ),
            "coverage_note": (
                "Nationwide Agmarknet coverage from the daily mandi feed plus "
                "the variety-wise feed; duplicates prefer the primary feed."
                if payload["provider"] == "data_gov"
                else "Keyless mirror covers Maharashtra, Uttar Pradesh, Punjab, "
                "Madhya Pradesh and Karnataka only."
            ),
        }
    )
    _cache_set(cache_key, payload)
    return payload
