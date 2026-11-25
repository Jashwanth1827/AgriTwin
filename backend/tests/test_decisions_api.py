"""Decision API tests: policy exposure, creation, lifecycle and ownership."""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _offline_weather(monkeypatch):
    """Keep decision tests deterministic and network-free."""

    def fake_weather(_farm, days: int = 3) -> dict:
        return {"risk_score": 0.25, "days": days, "source": "pytest-stub"}

    monkeypatch.setattr("app.services.decision_service.fetch_weather", fake_weather)


def _create(client, api_prefix, headers, farm_id, crop_id, **overrides):
    payload = {
        "farm_id": farm_id,
        "crop_id": crop_id,
        "quantity_quintals": 10.0,
        "auto_compute": False,
        "risk_preference": "medium",
    }
    payload.update(overrides)
    return client.post(f"{api_prefix}/decisions", headers=headers, json=payload)


def test_decision_policy_is_exposed(client, api_prefix, demo_headers):
    response = client.get(f"{api_prefix}/decisions/policy", headers=demo_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["version"] == "1.0.1"
    assert body["finance"]["commission_pct"] == 0.01
    assert body["policy"]["inspect"]["max_price_age_days"] == 90
    assert sum(body["risk"]["weights"].values()) == pytest.approx(1.0)


def test_create_decision_returns_explained_output(
    client, api_prefix, demo_headers, demo_farm_crop
):
    farm_id, crop_id = demo_farm_crop
    response = _create(client, api_prefix, demo_headers, farm_id, crop_id)
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["action"] in {"SELL", "WAIT", "INSPECT"}
    assert body["farm_id"] == farm_id
    assert body["crop_id"] == crop_id
    assert body["expected_yield_quintals"] > 0
    assert body["risk_score"] >= 0.0
    assert body["risk_category"] in {"low", "medium", "high"}
    assert 0.0 <= body["data_completeness"] <= 1.0
    assert 0.0 <= body["confidence"] <= 1.0
    assert body["policy_version"] == "1.0.1"
    assert body["explanation"]
    assert body["factors"]
    assert body["outputs"]["channel"] in {"mandi"} or body["outputs"]["channel"].startswith(
        "buyer:"
    )
    assert body["outputs"]["risk"]["components"]
    assert "scenarios" in body["outputs"]
    assert "harvest_readiness" in body["outputs"]
    assert isinstance(body["buyer_evaluations"], list)
    assert isinstance(body["missing_inputs"], list)
    assert isinstance(body["assumptions"], list)
    assert body["data_freshness"]


def test_create_decision_with_auto_compute(
    client, api_prefix, demo_headers, demo_farm_crop
):
    farm_id, crop_id = demo_farm_crop
    response = _create(
        client,
        api_prefix,
        demo_headers,
        farm_id,
        crop_id,
        quantity_quintals=None,
        auto_compute=True,
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["expected_yield_quintals"] > 0
    assert body["action"] in {"SELL", "WAIT", "INSPECT"}


def test_decision_lifecycle(client, api_prefix, demo_headers, demo_farm_crop):
    farm_id, crop_id = demo_farm_crop
    created = _create(client, api_prefix, demo_headers, farm_id, crop_id)
    assert created.status_code == 201
    decision_id = created.json()["id"]

    listed = client.get(
        f"{api_prefix}/decisions?farm_id={farm_id}&crop_id={crop_id}", headers=demo_headers
    )
    assert listed.status_code == 200
    assert any(row["id"] == decision_id for row in listed.json())

    filtered = client.get(
        f"{api_prefix}/decisions?action={created.json()['action']}", headers=demo_headers
    )
    assert filtered.status_code == 200
    assert any(row["id"] == decision_id for row in filtered.json())

    detail = client.get(f"{api_prefix}/decisions/{decision_id}", headers=demo_headers)
    assert detail.status_code == 200
    assert detail.json()["id"] == decision_id
    assert detail.json()["buyer_evaluations"] is not None

    assert client.delete(f"{api_prefix}/decisions/{decision_id}", headers=demo_headers).status_code == 200
    assert client.get(f"{api_prefix}/decisions/{decision_id}", headers=demo_headers).status_code == 404


def test_decision_validation(client, api_prefix, demo_headers, demo_farm_crop):
    farm_id, crop_id = demo_farm_crop

    zero_quantity = _create(
        client, api_prefix, demo_headers, farm_id, crop_id, quantity_quintals=0
    )
    assert zero_quantity.status_code == 422

    bad_preference = _create(
        client, api_prefix, demo_headers, farm_id, crop_id, risk_preference="reckless"
    )
    assert bad_preference.status_code == 422

    missing_crop = _create(client, api_prefix, demo_headers, farm_id, 99_999_999)
    assert missing_crop.status_code == 404


def test_decision_ownership_isolation(
    client, api_prefix, demo_headers, other_user_headers, demo_farm_crop
):
    farm_id, crop_id = demo_farm_crop
    created = _create(client, api_prefix, demo_headers, farm_id, crop_id)
    assert created.status_code == 201
    decision_id = created.json()["id"]

    assert (
        client.get(f"{api_prefix}/decisions/{decision_id}", headers=other_user_headers).status_code
        == 404
    )
    assert (
        client.delete(
            f"{api_prefix}/decisions/{decision_id}", headers=other_user_headers
        ).status_code
        == 404
    )
    assert client.delete(
        f"{api_prefix}/decisions/{decision_id}", headers=demo_headers
    ).status_code == 200
    assert (
        _create(client, api_prefix, other_user_headers, farm_id, crop_id).status_code == 404
    )
