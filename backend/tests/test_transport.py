"""Transport estimate tests using the deterministic geodesic fallback."""

from __future__ import annotations


def _demo_buyer_with_coordinates(client, api_prefix, headers):
    buyers = client.get(f"{api_prefix}/buyers", headers=headers).json()
    return next(
        buyer
        for buyer in buyers
        if buyer["latitude"] is not None and buyer["longitude"] is not None
    )


def test_vehicle_options(client, api_prefix):
    response = client.get(f"{api_prefix}/transport/vehicles")
    assert response.status_code == 200
    body = response.json()
    types = {row["type"] for row in body["vehicles"]}
    assert {"tempo", "truck", "large_truck"} <= types
    assert "not freight quotes" in body["notes"]


def test_estimate_to_buyer_uses_geodesic_fallback(
    client, api_prefix, demo_headers, demo_farm_crop
):
    farm_id, crop_id = demo_farm_crop
    buyer = _demo_buyer_with_coordinates(client, api_prefix, demo_headers)
    response = client.post(
        f"{api_prefix}/transport/estimate",
        headers=demo_headers,
        json={
            "farm_id": farm_id,
            "buyer_id": buyer["id"],
            "crop_id": crop_id,
            "quantity_quintals": 40,
            "vehicle_type": "truck",
            "use_routing": False,
        },
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["buyer_id"] == buyer["id"]
    assert body["farm_id"] == farm_id
    assert body["distance_km"] > 0
    assert body["distance_method"] == "geodesic_detour"
    assert body["is_approximate"] is True
    assert body["provider"] == "geodesic"
    assert body["trips"] >= 1
    assert body["total_cost"] > 0
    assert body["cost_per_quintal"] > 0
    assert body["cost_per_kg"] > 0
    assert "geodesic" in body["notes"].lower()


def test_estimate_to_coordinates_and_listing(
    client, api_prefix, demo_headers, demo_farm_crop
):
    farm_id, _crop_id = demo_farm_crop
    response = client.post(
        f"{api_prefix}/transport/estimate",
        headers=demo_headers,
        json={
            "farm_id": farm_id,
            "destination_name": "Test Destination",
            "destination_latitude": 19.9975,
            "destination_longitude": 73.7898,
            "quantity_quintals": 15,
            "vehicle_type": "tempo",
            "use_routing": False,
            "cost_per_km": 22,
            "fixed_cost": 200,
            "loading_cost": 100,
            "unloading_cost": 100,
        },
    )
    assert response.status_code == 201, response.text
    body = response.json()
    estimate_id = body["id"]
    assert body["buyer_id"] is None
    assert body["cost_per_km"] == 22

    listed = client.get(
        f"{api_prefix}/transport/estimates?farm_id={farm_id}", headers=demo_headers
    )
    assert listed.status_code == 200
    assert any(row["id"] == estimate_id for row in listed.json())


def test_transport_validation(client, api_prefix, demo_headers, demo_farm_crop):
    farm_id, _crop_id = demo_farm_crop

    no_destination = client.post(
        f"{api_prefix}/transport/estimate",
        headers=demo_headers,
        json={"farm_id": farm_id, "quantity_quintals": 10},
    )
    assert no_destination.status_code == 422

    zero_quantity = client.post(
        f"{api_prefix}/transport/estimate",
        headers=demo_headers,
        json={
            "farm_id": farm_id,
            "destination_latitude": 19.0,
            "destination_longitude": 73.0,
            "quantity_quintals": 0,
        },
    )
    assert zero_quantity.status_code == 422

    bad_vehicle = client.post(
        f"{api_prefix}/transport/estimate",
        headers=demo_headers,
        json={
            "farm_id": farm_id,
            "destination_latitude": 19.0,
            "destination_longitude": 73.0,
            "quantity_quintals": 10,
            "vehicle_type": "rocket",
        },
    )
    assert bad_vehicle.status_code == 422


def test_transport_ownership_isolation(
    client, api_prefix, demo_headers, other_user_headers, demo_farm_crop
):
    farm_id, _crop_id = demo_farm_crop
    response = client.post(
        f"{api_prefix}/transport/estimate",
        headers=other_user_headers,
        json={
            "farm_id": farm_id,
            "destination_latitude": 19.0,
            "destination_longitude": 73.0,
            "quantity_quintals": 10,
            "use_routing": False,
        },
    )
    assert response.status_code == 404
