"""System metadata, options, notifications and report API tests."""

from __future__ import annotations


def test_health_endpoint(client, api_prefix):
    response = client.get(f"{api_prefix}/system/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["database"] == "ok"
    assert body["app"] == "AgriTwin"
    assert body["demo_mode"] is True


def test_system_status_reports_models_and_providers(client, api_prefix):
    response = client.get(f"{api_prefix}/system/status")
    assert response.status_code == 200
    body = response.json()
    assert body["data_mode"] == "real"
    assert body["database_backend"] == "sqlite"
    models = {model["name"]: model for model in body["models"]}
    assert {"crop_health", "yield_prediction", "market_forecasting"} <= set(models)
    assert models["yield_prediction"]["available"] is True
    assert models["market_forecasting"]["available"] is True
    assert body["providers"]["weather"]["requires_key"] is False
    assert body["providers"]["routing"]["configured"] is True
    assert body["server_time"]


def test_options_expose_domain_constants(client, api_prefix):
    response = client.get(f"{api_prefix}/system/options")
    assert response.status_code == 200
    body = response.json()
    assert "Onion" in body["crops"]
    assert "Maharashtra" in body["states"]
    assert "Kharif" in body["seasons"]
    assert "truck" in body["vehicle_types"]
    assert body["demo_mode"] is True


def test_notifications_list_and_mark_read(client, api_prefix, demo_headers):
    response = client.get(f"{api_prefix}/system/notifications", headers=demo_headers)
    assert response.status_code == 200
    rows = response.json()
    assert rows
    unread = next((row for row in rows if not row["is_read"]), rows[0])

    marked = client.post(
        f"{api_prefix}/system/notifications/{unread['id']}/read", headers=demo_headers
    )
    assert marked.status_code == 200
    assert marked.json()["is_read"] is True

    all_read = client.post(f"{api_prefix}/system/notifications/read-all", headers=demo_headers)
    assert all_read.status_code == 200
    assert "marked as read" in all_read.json()["message"]


def test_report_generation_lifecycle(client, api_prefix, demo_headers, demo_farm_crop):
    farm_id, crop_id = demo_farm_crop
    created = client.post(
        f"{api_prefix}/system/reports",
        headers=demo_headers,
        json={"farm_id": farm_id, "crop_id": crop_id},
    )
    assert created.status_code == 201, created.text
    report = created.json()
    report_id = report["id"]
    assert report["report_type"] == "farm_advisory"
    assert report["payload"]["crops"]
    assert report["payload"]["disclaimer"]

    listed = client.get(f"{api_prefix}/system/reports", headers=demo_headers)
    assert listed.status_code == 200
    assert any(row["id"] == report_id for row in listed.json())

    detail = client.get(f"{api_prefix}/system/reports/{report_id}", headers=demo_headers)
    assert detail.status_code == 200
    assert detail.json()["id"] == report_id

    assert client.delete(f"{api_prefix}/system/reports/{report_id}", headers=demo_headers).status_code == 200
    assert client.get(f"{api_prefix}/system/reports/{report_id}", headers=demo_headers).status_code == 404


def test_report_ownership_isolation(
    client, api_prefix, demo_headers, other_user_headers, demo_farm_crop
):
    farm_id, crop_id = demo_farm_crop
    created = client.post(
        f"{api_prefix}/system/reports",
        headers=demo_headers,
        json={"farm_id": farm_id, "crop_id": crop_id},
    )
    assert created.status_code == 201
    report_id = created.json()["id"]

    assert (
        client.get(f"{api_prefix}/system/reports/{report_id}", headers=other_user_headers).status_code
        == 404
    )
    assert (
        client.post(
            f"{api_prefix}/system/reports",
            headers=other_user_headers,
            json={"farm_id": farm_id},
        ).status_code
        == 404
    )
    client.delete(f"{api_prefix}/system/reports/{report_id}", headers=demo_headers)
