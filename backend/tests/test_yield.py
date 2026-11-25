"""Yield prediction, model metadata, readiness and history API tests."""

from __future__ import annotations


def test_yield_model_metadata(client, api_prefix):
    response = client.get(f"{api_prefix}/yield/model")
    assert response.status_code == 200
    body = response.json()
    assert body["available"] is True
    assert body["model_version"]
    assert body["model_name"]
    assert body["features"]
    assert body["interval_method"]
    assert body["metrics"]
    assert body["dataset_provenance"]


def test_yield_prediction_for_demo_onion(client, api_prefix, demo_headers, demo_farm_crop):
    farm_id, crop_id = demo_farm_crop
    response = client.post(
        f"{api_prefix}/yield/predict",
        headers=demo_headers,
        json={"farm_id": farm_id, "crop_id": crop_id},
    )
    assert response.status_code == 201, response.text
    body = response.json()
    prediction = body["prediction"]
    assert prediction["farm_id"] == farm_id
    assert prediction["crop_id"] == crop_id
    assert prediction["predicted_yield_per_hectare"] > 0
    assert prediction["predicted_total_quintals"] > 0
    assert (
        prediction["lower_yield_per_hectare"]
        <= prediction["predicted_yield_per_hectare"]
        <= prediction["upper_yield_per_hectare"]
    )
    assert (
        prediction["lower_total_quintals"]
        <= prediction["predicted_total_quintals"]
        <= prediction["upper_total_quintals"]
    )
    assert 0.0 <= prediction["confidence"] <= 1.0
    assert prediction["interval_method"]
    assert prediction["inputs"]
    assert body["model"]["available"] is True
    readiness = body["harvest_readiness"]
    assert readiness["crop"] == "Onion"
    assert readiness["readiness_status"] in {"ready", "overdue", "approaching", "not_ready"}
    assert readiness["calendar_source"]


def test_prediction_listing_and_detail(client, api_prefix, demo_headers, demo_farm_crop):
    farm_id, crop_id = demo_farm_crop
    created = client.post(
        f"{api_prefix}/yield/predict",
        headers=demo_headers,
        json={"farm_id": farm_id, "crop_id": crop_id},
    )
    assert created.status_code == 201
    prediction_id = created.json()["prediction"]["id"]

    listed = client.get(
        f"{api_prefix}/yield/predictions?farm_id={farm_id}&crop_id={crop_id}",
        headers=demo_headers,
    )
    assert listed.status_code == 200
    assert any(row["id"] == prediction_id for row in listed.json())

    detail = client.get(f"{api_prefix}/yield/predictions/{prediction_id}", headers=demo_headers)
    assert detail.status_code == 200
    assert detail.json()["id"] == prediction_id

    missing = client.get(f"{api_prefix}/yield/predictions/99999999", headers=demo_headers)
    assert missing.status_code == 404


def test_harvest_readiness_and_history(client, api_prefix, demo_headers, demo_farm_crop):
    _farm_id, crop_id = demo_farm_crop
    readiness = client.get(f"{api_prefix}/yield/readiness/{crop_id}", headers=demo_headers)
    assert readiness.status_code == 200
    body = readiness.json()
    assert body["crop"] == "Onion"
    assert body["estimated_days_remaining"] is not None
    assert body["harvest_window_start"] is not None
    assert body["harvest_window_end"] is not None

    history = client.get(
        f"{api_prefix}/yield/history?crop=Onion", headers=demo_headers
    )
    assert history.status_code == 200
    payload = history.json()
    assert payload["unit"] == "quintal/hectare"
    assert payload["years"]
    assert all(row["average_yield_per_hectare"] > 0 for row in payload["years"])


def test_prediction_requires_matching_farm_and_crop(
    client, api_prefix, demo_headers, demo_farm_crop
):
    farm_id, crop_id = demo_farm_crop
    farms = client.get(f"{api_prefix}/farms", headers=demo_headers).json()
    other_farm = next(farm for farm in farms if farm["id"] != farm_id)
    response = client.post(
        f"{api_prefix}/yield/predict",
        headers=demo_headers,
        json={"farm_id": other_farm["id"], "crop_id": crop_id},
    )
    assert response.status_code == 422
    assert "does not belong" in response.json()["error"]["message"]


def test_prediction_ownership_isolation(
    client, api_prefix, demo_headers, other_user_headers, demo_farm_crop
):
    farm_id, crop_id = demo_farm_crop
    created = client.post(
        f"{api_prefix}/yield/predict",
        headers=demo_headers,
        json={"farm_id": farm_id, "crop_id": crop_id},
    )
    prediction_id = created.json()["prediction"]["id"]

    assert (
        client.get(
            f"{api_prefix}/yield/predictions/{prediction_id}", headers=other_user_headers
        ).status_code
        == 404
    )
    assert (
        client.post(
            f"{api_prefix}/yield/predict",
            headers=other_user_headers,
            json={"farm_id": farm_id, "crop_id": crop_id},
        ).status_code
        == 403
    )
