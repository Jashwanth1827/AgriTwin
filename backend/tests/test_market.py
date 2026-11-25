"""Market prices, comparison, forecasting and CSV-import API tests."""

from __future__ import annotations

import uuid

CSV_HEADER = (
    "crop,market,state,district,variety,grade,price_date,min_price,max_price,modal_price,unit"
)


def test_available_crops_include_real_dataset(client, api_prefix, user_headers):
    response = client.get(f"{api_prefix}/market/crops", headers=user_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["unit"] == "INR/quintal"
    crops = {row["crop"]: row for row in body["crops"]}
    assert "Onion" in crops
    assert crops["Onion"]["observations"] > 0
    assert crops["Onion"]["markets"] > 0
    assert len(crops) >= 10


def test_price_series_and_markets(client, api_prefix, user_headers):
    response = client.get(f"{api_prefix}/market/prices?crop=Onion", headers=user_headers)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["crop"] == "Onion"
    assert body["market"]
    assert body["points"]
    assert body["available_markets"]
    assert body["unit"] == "INR/quintal"
    assert body["is_demo"] is False
    point = body["points"][0]
    assert point["min_price"] <= point["modal_price"] <= point["max_price"]
    assert body["latest_observation_date"] is not None

    markets = client.get(f"{api_prefix}/market/markets?crop=Onion", headers=user_headers)
    assert markets.status_code == 200
    assert markets.json()["markets"]


def test_price_series_for_unknown_market(client, api_prefix, user_headers):
    response = client.get(
        f"{api_prefix}/market/prices?crop=Onion&market=NoSuchMandi", headers=user_headers
    )
    assert response.status_code == 404


def test_market_trends(client, api_prefix, user_headers):
    response = client.get(f"{api_prefix}/market/trends?crop=Onion", headers=user_headers)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["crop"] == "Onion"
    assert body["rows"]
    assert body["best_market"]
    assert body["average_modal_price"] > 0
    prices = [row["modal_price"] for row in body["rows"]]
    assert prices == sorted(prices, reverse=True)


def test_forecast_onion(client, api_prefix, user_headers):
    response = client.post(
        f"{api_prefix}/market/forecast",
        headers=user_headers,
        json={"crop": "Onion", "horizon_days": 14},
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["crop"] == "Onion"
    assert body["market"]
    assert body["model_name"]
    assert body["expected_price"] > 0
    assert body["lower_bound"] <= body["expected_price"] <= body["upper_bound"]
    assert len(body["points"]) == 14
    assert body["interval_method"]
    assert body["is_experimental"] is True
    assert body["is_demo"] is False
    assert body["disclaimer"]
    assert body["model_comparison"]


def test_forecast_rejects_insufficient_history(client, api_prefix, user_headers):
    response = client.post(
        f"{api_prefix}/market/forecast",
        headers=user_headers,
        json={"crop": "Sugarcane", "horizon_days": 14},
    )
    assert response.status_code == 422, response.text
    assert response.json()["error"]["code"] == "insufficient_data"


def test_forecast_request_validation(client, api_prefix, user_headers):
    bad_crop = client.post(
        f"{api_prefix}/market/forecast",
        headers=user_headers,
        json={"crop": "Dragonfruit"},
    )
    assert bad_crop.status_code == 422

    bad_horizon = client.post(
        f"{api_prefix}/market/forecast",
        headers=user_headers,
        json={"crop": "Onion", "horizon_days": 500},
    )
    assert bad_horizon.status_code == 422


def test_forecast_list_and_get(client, api_prefix, user_headers):
    created = client.post(
        f"{api_prefix}/market/forecast",
        headers=user_headers,
        json={"crop": "Wheat", "horizon_days": 7},
    )
    assert created.status_code == 201, created.text
    forecast_id = created.json()["id"]

    listed = client.get(f"{api_prefix}/market/forecasts?crop=Wheat", headers=user_headers)
    assert listed.status_code == 200
    assert any(row["id"] == forecast_id for row in listed.json())

    fetched = client.get(f"{api_prefix}/market/forecasts/{forecast_id}", headers=user_headers)
    assert fetched.status_code == 200
    assert fetched.json()["id"] == forecast_id

    assert (
        client.get(f"{api_prefix}/market/forecasts/99999999", headers=user_headers).status_code
        == 404
    )


def test_csv_import_and_deduplication(client, api_prefix, user_headers):
    source = f"pytest-{uuid.uuid4().hex[:8]}"
    market = f"Test Import Mandi {uuid.uuid4().hex[:6]}"
    csv = "\n".join(
        [
            CSV_HEADER,
            f"Banana,{market},Kerala,Thiruvananthapuram,Robusta,FAQ,2020-01-02,1000,1200,1100,INR/quintal",
            f"Banana,{market},Kerala,Thiruvananthapuram,Robusta,FAQ,2020-01-03,1050,1250,1150,INR/quintal",
            f"Dragonfruit,{market},Kerala,Thiruvananthapuram,Other,FAQ,2020-01-04,900,1100,1000,INR/quintal",
        ]
    )
    first = client.post(
        f"{api_prefix}/market/import",
        headers=user_headers,
        json={"csv_content": csv, "source": source},
    )
    assert first.status_code == 200, first.text
    body = first.json()
    assert body["inserted"] == 2
    assert body["skipped"] == 1
    assert any("unsupported crop" in error for error in body["errors"])

    second = client.post(
        f"{api_prefix}/market/import",
        headers=user_headers,
        json={"csv_content": csv, "source": source},
    )
    assert second.status_code == 200
    assert second.json()["inserted"] == 0
    assert second.json()["skipped"] == 3


def test_csv_import_rejects_missing_columns(client, api_prefix, user_headers):
    response = client.post(
        f"{api_prefix}/market/import",
        headers=user_headers,
        json={"csv_content": "crop,market\nOnion,Test", "source": "pytest-bad"},
    )
    assert response.status_code == 422
    assert "missing required columns" in response.json()["error"]["message"].lower()


def test_csv_import_rejects_inconsistent_prices(client, api_prefix, user_headers):
    source = f"pytest-bad-{uuid.uuid4().hex[:8]}"
    csv = "\n".join(
        [
            CSV_HEADER,
            "Onion,Test Bad Mandi,Maharashtra,Nashik,Other,FAQ,2020-01-02,1200,1000,1100,INR/quintal",
        ]
    )
    response = client.post(
        f"{api_prefix}/market/import",
        headers=user_headers,
        json={"csv_content": csv, "source": source},
    )
    assert response.status_code == 200
    assert response.json()["inserted"] == 0
    assert response.json()["skipped"] == 1
