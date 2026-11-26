"""Live mandi-rate endpoint tests.

All provider calls are mocked so the tests verify normalisation, source
labelling, provider selection and fallback behaviour without network access.
"""

from __future__ import annotations

import httpx
import pytest

from app.core.config import settings
from app.services import live_market

OFFICIAL_PAYLOAD = {
    "updated_date": "2026-11-25T09:00:56Z",
    "records": [
        {
            "state": "Maharashtra",
            "district": "Nashik",
            "market": "Lasalgaon",
            "commodity": "Onion",
            "variety": "Red",
            "grade": "FAQ",
            "arrival_date": "25/11/2026",
            "min_price": 1800,
            "max_price": 3200,
            "modal_price": 2500,
        },
        {
            "state": "Maharashtra",
            "district": "Pune",
            "market": "Junnar",
            "commodity": "Onion",
            "variety": "Local",
            "grade": "FAQ",
            "arrival_date": "24/11/2026",
            "min_price": 1500,
            "max_price": 3000,
            "modal_price": 2200,
        },
    ],
}

KERALA_PAYLOAD = {
    "updated_date": "2026-11-25T09:00:56Z",
    "records": [
        {
            "state": "Keralam",
            "district": "Palakad",
            "market": "Palakkad Market",
            "commodity": "Onion",
            "variety": "Small",
            "grade": "FAQ",
            "arrival_date": "25/11/2026",
            "min_price": 17000,
            "max_price": 18000,
            "modal_price": 17600,
        },
    ],
}

VARIETY_PAYLOAD = {
    "status": "ok",
    "updated_date": "2026-11-25T09:00:56Z",
    "records": [
        {
            "Arrival_Date": "25/11/2026",
            "Commodity": "Onion",
            "Commodity_Code": "21",
            "District": "Nashik",
            "Grade": "FAQ",
            "Market": "Lasalgaon",
            "Max_Price": "3200",
            "Min_Price": "1800",
            "Modal_Price": "2500",
            "State": "Maharashtra",
            "Variety": "Red",
        },
        {
            "Arrival_Date": "25/11/2026",
            "Commodity": "Onion",
            "Commodity_Code": "21",
            "District": "Nashik",
            "Grade": "FAQ",
            "Market": "Pimpalgaon Baswant",
            "Max_Price": "3300",
            "Min_Price": "1800",
            "Modal_Price": "2600",
            "State": "Maharashtra",
            "Variety": "Red",
        },
        {
            "Arrival_Date": "23/11/2026",
            "Commodity": "Onion",
            "Commodity_Code": "21",
            "District": "Nashik",
            "Grade": "FAQ",
            "Market": "Lasalgaon",
            "Max_Price": "2800",
            "Min_Price": "1500",
            "Modal_Price": "2300",
            "State": "Maharashtra",
            "Variety": "Local",
        },
    ],
}

KEYLESS_PAYLOAD = {
    "success": True,
    "data": [
        {
            "state": "Maharashtra",
            "district": "Nashik",
            "market": "Lasalgaon",
            "commodity": "Onion",
            "variety": "Red",
            "grade": "FAQ",
            "arrival_date": "2026-10-16",
            "min_price": 1500,
            "max_price": 3000,
            "modal_price": 2400,
            "fetched_at": "2026-10-16T18:31:18+00:00",
        }
    ],
}


class FakeResponse:
    def __init__(self, payload: dict, status_code: int = 200) -> None:
        self.payload = payload
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise httpx.HTTPStatusError(
                "upstream error",
                request=httpx.Request("GET", "https://example.invalid"),
                response=httpx.Response(self.status_code),
            )

    def json(self) -> dict:
        return self.payload


class FakeClient:
    def __init__(self, handler) -> None:
        self.handler = handler

    def __enter__(self) -> "FakeClient":
        return self

    def __exit__(self, *_args) -> bool:
        return False

    def get(self, url: str, params: dict | None = None) -> FakeResponse:
        return self.handler(url, params or {})


@pytest.fixture(autouse=True)
def _isolated_live_state(monkeypatch):
    live_market._CACHE.clear()
    monkeypatch.setattr(settings, "LIVE_MARKET_PROVIDER", "auto")
    monkeypatch.setattr(settings, "DATA_GOV_API_KEY", "test-key")
    yield
    live_market._CACHE.clear()


def _patch_client(monkeypatch, handler) -> list[str]:
    calls: list[str] = []

    def tracked(url: str, params: dict) -> FakeResponse:
        calls.append(url)
        return handler(url, params)

    monkeypatch.setattr(
        live_market.httpx,
        "Client",
        lambda *_args, **_kwargs: FakeClient(tracked),
    )
    return calls


def test_live_rates_official_source(client, api_prefix, user_headers, monkeypatch):
    calls = _patch_client(
        monkeypatch, lambda _url, _params: FakeResponse(OFFICIAL_PAYLOAD)
    )
    response = client.get(
        f"{api_prefix}/market/live-rates?crop=Onion&state=Maharashtra",
        headers=user_headers,
    )
    assert response.status_code == 200, response.text
    body = response.json()

    assert body["provider"] == "data_gov"
    assert body["is_official"] is True
    assert body["is_demo"] is False
    assert body["source_name"] == "Agmarknet / data.gov.in"
    assert body["latest_observation_date"] == "2026-11-25"
    assert body["records"][0]["market"] == "Lasalgaon"
    assert body["records"][0]["modal_price"] == 2500
    assert body["records"][1]["date"] == "2026-11-24"
    assert body["disclaimer"]
    assert calls and "api.data.gov.in" in calls[0]


@pytest.mark.parametrize("state", ["Telangana", "Andhra Pradesh"])
def test_live_rates_official_supports_priority_south_states(
    client, api_prefix, user_headers, monkeypatch, state
):
    payload = {
        "updated_date": OFFICIAL_PAYLOAD["updated_date"],
        "records": [
            {
                **OFFICIAL_PAYLOAD["records"][0],
                "state": state,
                "district": "Test district",
                "market": f"{state} APMC",
            }
        ],
    }

    def handler(url: str, _params: dict) -> FakeResponse:
        if settings.DATA_GOV_VARIETY_RESOURCE_ID in url:
            return FakeResponse({"records": []})
        return FakeResponse(payload)

    _patch_client(monkeypatch, handler)
    response = client.get(
        f"{api_prefix}/market/live-rates?crop=Onion&state={state.replace(' ', '%20')}",
        headers=user_headers,
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["state"] == state
    assert body["is_official"] is True
    assert body["records"][0]["state"] == state
    assert body["records"][0]["market"] == f"{state} APMC"


def test_live_rates_can_filter_to_farm_district(
    client, api_prefix, user_headers, monkeypatch
):
    def handler(url: str, _params: dict) -> FakeResponse:
        if settings.DATA_GOV_VARIETY_RESOURCE_ID in url:
            return FakeResponse({"records": []})
        return FakeResponse(OFFICIAL_PAYLOAD)

    _patch_client(monkeypatch, handler)
    response = client.get(
        f"{api_prefix}/market/live-rates?crop=Onion&state=Maharashtra&district=Pune",
        headers=user_headers,
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["district"] == "Pune"
    assert [row["district"] for row in body["records"]] == ["Pune"]
    assert body["records"][0]["market"] == "Junnar"
    assert "Filtered to Pune district" in body["coverage_note"]


def test_api_state_filter_maps_agmarknet_spellings():
    assert live_market.api_state_filter("Kerala") == "Keralam"
    assert live_market.api_state_filter("Keralam") == "Keralam"
    assert live_market.api_state_filter("Puducherry") == "Pondicherry"
    assert live_market.api_state_filter("Pondicherry") == "Pondicherry"
    assert live_market.api_state_filter("Chhattisgarh") == "Chattisgarh"
    assert live_market.api_state_filter("Chhattisgarh") == "Chattisgarh"
    assert live_market.api_state_filter("Maharashtra") == "Maharashtra"


def test_live_rates_official_uses_agmarknet_state_name(
    client, api_prefix, user_headers, monkeypatch
):
    captured: dict = {}

    def handler(_url: str, params: dict) -> FakeResponse:
        captured.update(params)
        return FakeResponse(KERALA_PAYLOAD)

    _patch_client(monkeypatch, handler)
    response = client.get(
        f"{api_prefix}/market/live-rates?crop=Onion&state=Kerala",
        headers=user_headers,
    )
    assert response.status_code == 200, response.text
    assert captured["filters[state]"] == "Keralam"
    body = response.json()
    assert body["records"][0]["state"] == "Kerala"
    assert body["records"][0]["market"] == "Palakkad Market"


def test_live_rates_falls_back_to_keyless(client, api_prefix, user_headers, monkeypatch):
    def handler(url: str, _params: dict) -> FakeResponse:
        if "api.data.gov.in" in url:
            return FakeResponse({}, status_code=502)
        return FakeResponse(KEYLESS_PAYLOAD)

    calls = _patch_client(monkeypatch, handler)
    response = client.get(
        f"{api_prefix}/market/live-rates?crop=Onion&state=Maharashtra&refresh=true",
        headers=user_headers,
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["provider"] == "mandi_api"
    assert body["is_official"] is False
    assert body["is_demo"] is False
    assert body["latest_observation_date"] == "2026-10-16"
    assert "Maharashtra" in body["coverage_note"]
    assert len(calls) == 2


def test_live_rates_mandi_api_provider_skips_official(
    client, api_prefix, user_headers, monkeypatch
):
    monkeypatch.setattr(settings, "LIVE_MARKET_PROVIDER", "mandi_api")
    calls = _patch_client(
        monkeypatch, lambda _url, _params: FakeResponse(KEYLESS_PAYLOAD)
    )
    response = client.get(
        f"{api_prefix}/market/live-rates?crop=Onion&state=Maharashtra",
        headers=user_headers,
    )
    assert response.status_code == 200, response.text
    assert response.json()["provider"] == "mandi_api"
    assert len(calls) == 1
    assert "mandi-api.onrender.com" in calls[0]


def test_live_rates_rejects_unsupported_crop(client, api_prefix, user_headers, monkeypatch):
    _patch_client(monkeypatch, lambda _url, _params: FakeResponse(OFFICIAL_PAYLOAD))
    response = client.get(
        f"{api_prefix}/market/live-rates?crop=Dragonfruit", headers=user_headers
    )
    assert response.status_code == 422


def test_keyless_mirror_rejects_unsupported_state(
    client, api_prefix, user_headers, monkeypatch
):
    monkeypatch.setattr(settings, "LIVE_MARKET_PROVIDER", "mandi_api")
    _patch_client(monkeypatch, lambda _url, _params: FakeResponse(KEYLESS_PAYLOAD))
    response = client.get(
        f"{api_prefix}/market/live-rates?crop=Onion&state=Kerala",
        headers=user_headers,
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "unsupported_state"


def test_official_failure_outside_keyless_mirror_reports_retry(
    client, api_prefix, user_headers, monkeypatch
):
    def handler(url: str, _params: dict) -> FakeResponse:
        assert "api.data.gov.in" in url
        return FakeResponse({}, status_code=502)

    calls = _patch_client(monkeypatch, handler)
    response = client.get(
        f"{api_prefix}/market/live-rates?crop=Onion&state=Telangana&refresh=true",
        headers=user_headers,
    )
    assert response.status_code == 503
    body = response.json()["error"]
    assert body["code"] == "official_feed_unavailable"
    assert "Telangana" in body["message"]
    assert "retry" in body["message"].lower()
    assert body["details"]["state"] == "Telangana"
    assert len(calls) == 1  # no misleading keyless fallback for Telangana


def test_live_rates_disabled_provider_returns_503(
    client, api_prefix, user_headers, monkeypatch
):
    monkeypatch.setattr(settings, "LIVE_MARKET_PROVIDER", "disabled")
    response = client.get(
        f"{api_prefix}/market/live-rates?crop=Onion", headers=user_headers
    )
    assert response.status_code == 503


def _is_variety_url(url: str) -> bool:
    return settings.DATA_GOV_VARIETY_RESOURCE_ID in url


def test_live_rates_combines_both_official_resources(
    client, api_prefix, user_headers, monkeypatch
):
    def handler(url: str, _params: dict) -> FakeResponse:
        return FakeResponse(VARIETY_PAYLOAD if _is_variety_url(url) else OFFICIAL_PAYLOAD)

    calls = _patch_client(monkeypatch, handler)
    response = client.get(
        f"{api_prefix}/market/live-rates?crop=Onion&state=Maharashtra&limit=10",
        headers=user_headers,
    )
    assert response.status_code == 200, response.text
    body = response.json()

    assert body["provider"] == "data_gov"
    assert body["source_name"] == "Agmarknet / data.gov.in (daily + variety-wise)"
    assert [source["record_count"] for source in body["sources"]] == [2, 2]
    assert len(body["records"]) == 4
    assert len(calls) == 2

    duplicate_rows = [
        row
        for row in body["records"]
        if row["market"] == "Lasalgaon" and row["date"] == "2026-11-25"
    ]
    assert len(duplicate_rows) == 1
    assert duplicate_rows[0]["source_resource_id"] == settings.DATA_GOV_RESOURCE_ID

    variety_row = next(
        row for row in body["records"] if row["market"] == "Pimpalgaon Baswant"
    )
    assert variety_row["commodity_code"] == "21"
    assert variety_row["source_resource_id"] == settings.DATA_GOV_VARIETY_RESOURCE_ID


def test_variety_source_failure_keeps_primary(
    client, api_prefix, user_headers, monkeypatch
):
    def handler(url: str, _params: dict) -> FakeResponse:
        if _is_variety_url(url):
            return FakeResponse({}, status_code=502)
        return FakeResponse(OFFICIAL_PAYLOAD)

    calls = _patch_client(monkeypatch, handler)
    response = client.get(
        f"{api_prefix}/market/live-rates?crop=Onion&state=Maharashtra&refresh=true",
        headers=user_headers,
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["provider"] == "data_gov"
    assert body["source_name"] == "Agmarknet / data.gov.in"
    assert [source["record_count"] for source in body["sources"]] == [2, 0]
    assert len(calls) == 2
    assert all("mandi-api.onrender.com" not in url for url in calls)


def test_variety_source_uses_latest_sort_and_api_state_name(
    client, api_prefix, user_headers, monkeypatch
):
    captured: dict = {}

    def handler(url: str, params: dict) -> FakeResponse:
        if _is_variety_url(url):
            captured.update(params)
            return FakeResponse(VARIETY_PAYLOAD)
        return FakeResponse(KERALA_PAYLOAD)

    _patch_client(monkeypatch, handler)
    response = client.get(
        f"{api_prefix}/market/live-rates?crop=Onion&state=Kerala",
        headers=user_headers,
    )
    assert response.status_code == 200, response.text
    assert captured["sort[Arrival_Date]"] == "desc"
    assert captured["filters[State]"] == "Keralam"
    assert captured["filters[Commodity]"] == "Onion"


def test_merge_reserves_room_for_unique_variety_rows():
    def row(day: str, price: int, source: str, index: int) -> dict:
        return {
            "date": day,
            "state": "Maharashtra",
            "district": "Nashik",
            "market": f"Market {index}",
            "commodity": "Onion",
            "variety": "Local",
            "grade": "FAQ",
            "modal_price": price,
            "source_resource_id": source,
        }

    primary = [row("2026-11-25", 100 - i, "primary", i) for i in range(4)]
    secondary = [row("2026-11-24", 500 - i, "variety", i) for i in range(2)]

    merged = live_market._merge_official_records(primary, secondary, 4)

    assert len(merged) == 4
    assert sum(item["source_resource_id"] == "variety" for item in merged) == 2
    assert sum(item["source_resource_id"] == "primary" for item in merged) == 2
    assert merged[0]["date"] == "2026-11-25"


def test_variety_source_can_be_disabled(
    client, api_prefix, user_headers, monkeypatch
):
    monkeypatch.setattr(settings, "LIVE_MARKET_USE_VARIETY_SOURCE", False)
    calls = _patch_client(
        monkeypatch, lambda _url, _params: FakeResponse(OFFICIAL_PAYLOAD)
    )
    response = client.get(
        f"{api_prefix}/market/live-rates?crop=Onion&state=Maharashtra",
        headers=user_headers,
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert len(calls) == 1
    assert len(body["sources"]) == 1
    assert body["source_name"] == "Agmarknet / data.gov.in"
