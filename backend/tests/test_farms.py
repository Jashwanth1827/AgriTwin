"""Farm and crop CRUD, validation and ownership-isolation tests."""

from __future__ import annotations

from datetime import date, timedelta


def _farm_payload(name: str = "Test Farm", area: float = 4.0) -> dict:
    return {
        "name": name,
        "village": "Test Village",
        "district": "Nashik",
        "state": "Maharashtra",
        "latitude": 20.0,
        "longitude": 73.8,
        "total_area_hectares": area,
        "soil_type": "Black (Regur)",
        "soil_ph": 7.2,
        "nitrogen_kg_per_ha": 120,
        "phosphorus_kg_per_ha": 40,
        "potassium_kg_per_ha": 110,
        "soil_moisture_pct": 38,
    }


def test_demo_farms_are_clearly_labelled(client, api_prefix, demo_headers):
    response = client.get(f"{api_prefix}/farms", headers=demo_headers)
    assert response.status_code == 200
    farms = response.json()
    assert len(farms) >= 3
    assert all(farm["is_demo"] is True for farm in farms)
    assert {farm["state"] for farm in farms} >= {"Maharashtra", "Tamil Nadu"}


def test_farm_crud_and_crop_lifecycle(client, api_prefix, user_headers):
    created = client.post(
        f"{api_prefix}/farms", headers=user_headers, json=_farm_payload("Lifecycle Farm")
    )
    assert created.status_code == 201, created.text
    farm = created.json()
    farm_id = farm["id"]
    assert farm["is_demo"] is False

    detail = client.get(f"{api_prefix}/farms/{farm_id}", headers=user_headers)
    assert detail.status_code == 200
    assert detail.json()["crops"] == []

    patched = client.patch(
        f"{api_prefix}/farms/{farm_id}",
        headers=user_headers,
        json={"name": "Renamed Farm", "soil_ph": 6.5},
    )
    assert patched.status_code == 200
    assert patched.json()["name"] == "Renamed Farm"
    assert patched.json()["soil_ph"] == 6.5

    crop_response = client.post(
        f"{api_prefix}/crops",
        headers=user_headers,
        json={
            "farm_id": farm_id,
            "crop_name": "Maize",
            "variety": "DHM-117",
            "season": "Kharif",
            "sowing_date": date.today().isoformat(),
            "growth_stage": "Vegetative",
            "area_hectares": 1.5,
        },
    )
    assert crop_response.status_code == 201, crop_response.text
    crop = crop_response.json()
    crop_id = crop["id"]
    assert crop["farm_id"] == farm_id
    assert crop["expected_harvest_date"] is not None  # estimated from the calendar
    assert crop["is_demo"] is False

    listed = client.get(f"{api_prefix}/farms/{farm_id}/crops", headers=user_headers)
    assert listed.status_code == 200
    assert [row["id"] for row in listed.json()] == [crop_id]

    crop_detail = client.get(f"{api_prefix}/crops/{crop_id}", headers=user_headers)
    assert crop_detail.status_code == 200

    crop_patch = client.patch(
        f"{api_prefix}/crops/{crop_id}",
        headers=user_headers,
        json={"growth_stage": "Flowering", "notes": "Updated by test"},
    )
    assert crop_patch.status_code == 200
    assert crop_patch.json()["growth_stage"] == "Flowering"

    assert client.delete(f"{api_prefix}/crops/{crop_id}", headers=user_headers).status_code == 200
    assert client.get(f"{api_prefix}/crops/{crop_id}", headers=user_headers).status_code == 404
    assert client.delete(f"{api_prefix}/farms/{farm_id}", headers=user_headers).status_code == 200
    assert client.get(f"{api_prefix}/farms/{farm_id}", headers=user_headers).status_code == 404


def test_active_crop_area_cannot_exceed_farm(client, api_prefix, user_headers):
    farm = client.post(
        f"{api_prefix}/farms", headers=user_headers, json=_farm_payload("Small Farm", area=1.0)
    ).json()
    response = client.post(
        f"{api_prefix}/crops",
        headers=user_headers,
        json={
            "farm_id": farm["id"],
            "crop_name": "Onion",
            "season": "Kharif",
            "sowing_date": date.today().isoformat(),
            "area_hectares": 2.0,
        },
    )
    assert response.status_code == 409
    assert "exceeds the farm size" in response.json()["error"]["message"]
    client.delete(f"{api_prefix}/farms/{farm['id']}", headers=user_headers)


def test_farm_and_crop_validation(client, api_prefix, user_headers):
    lone_coordinate = client.post(
        f"{api_prefix}/farms",
        headers=user_headers,
        json={**_farm_payload("Bad Coords"), "longitude": None},
    )
    assert lone_coordinate.status_code == 422

    negative_area = client.post(
        f"{api_prefix}/farms",
        headers=user_headers,
        json={**_farm_payload("Bad Area"), "total_area_hectares": -1},
    )
    assert negative_area.status_code == 422

    bad_state = client.post(
        f"{api_prefix}/farms",
        headers=user_headers,
        json={**_farm_payload("Bad State"), "state": "Narnia"},
    )
    assert bad_state.status_code == 422

    farm = client.post(
        f"{api_prefix}/farms", headers=user_headers, json=_farm_payload("Validation Farm")
    ).json()
    bad_crop = client.post(
        f"{api_prefix}/crops",
        headers=user_headers,
        json={
            "farm_id": farm["id"],
            "crop_name": "Dragonfruit",
            "season": "Kharif",
            "sowing_date": date.today().isoformat(),
            "area_hectares": 1.0,
        },
    )
    assert bad_crop.status_code == 422

    harvest_before_sowing = client.post(
        f"{api_prefix}/crops",
        headers=user_headers,
        json={
            "farm_id": farm["id"],
            "crop_name": "Onion",
            "season": "Kharif",
            "sowing_date": date.today().isoformat(),
            "expected_harvest_date": (date.today() - timedelta(days=1)).isoformat(),
            "area_hectares": 1.0,
        },
    )
    assert harvest_before_sowing.status_code == 422
    client.delete(f"{api_prefix}/farms/{farm['id']}", headers=user_headers)


def test_farm_ownership_isolation(client, api_prefix, user_headers, other_user_headers):
    farm = client.post(
        f"{api_prefix}/farms", headers=user_headers, json=_farm_payload("Private Farm")
    ).json()
    farm_id = farm["id"]

    # Farm-level dependency checks return 403; service-level crop creation
    # returns 404 so that the farm's existence is not disclosed.
    assert client.get(f"{api_prefix}/farms/{farm_id}", headers=other_user_headers).status_code == 403
    assert (
        client.patch(
            f"{api_prefix}/farms/{farm_id}",
            headers=other_user_headers,
            json={"name": "Hijacked"},
        ).status_code
        == 403
    )
    assert (
        client.delete(f"{api_prefix}/farms/{farm_id}", headers=other_user_headers).status_code
        == 403
    )
    assert (
        client.get(f"{api_prefix}/farms/{farm_id}/crops", headers=other_user_headers).status_code
        == 403
    )
    assert (
        client.post(
            f"{api_prefix}/crops",
            headers=other_user_headers,
            json={
                "farm_id": farm_id,
                "crop_name": "Onion",
                "season": "Kharif",
                "sowing_date": date.today().isoformat(),
                "area_hectares": 1.0,
            },
        ).status_code
        == 404
    )

    # The owner can still read the farm.
    assert client.get(f"{api_prefix}/farms/{farm_id}", headers=user_headers).status_code == 200
    client.delete(f"{api_prefix}/farms/{farm_id}", headers=user_headers)
