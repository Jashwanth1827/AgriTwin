"""Buyer and buyer-offer CRUD, validation and ownership tests."""

from __future__ import annotations

import uuid
from datetime import date, timedelta


def _buyer_payload(name: str = "Test Buyer", **overrides) -> dict:
    payload = {
        "name": name,
        "buyer_type": "Trader",
        "contact_name": "Buyer Contact",
        "contact_phone": "+91-90000-11111",
        "market_name": "Test APMC",
        "district": "Nashik",
        "state": "Maharashtra",
        "latitude": 20.01,
        "longitude": 73.79,
        "notes": "Created by the automated test suite.",
    }
    payload.update(overrides)
    return payload


def _offer_payload(crop: str = "Onion", **overrides) -> dict:
    payload = {
        "crop": crop,
        "variety": "Test variety",
        "offered_price_per_quintal": 5100.0,
        "min_quantity_quintals": 1.0,
        "max_quantity_quintals": 100.0,
        "offer_date": date.today().isoformat(),
        "expiry_date": (date.today() + timedelta(days=14)).isoformat(),
        "conditions": "Test conditions",
        "is_active": True,
    }
    payload.update(overrides)
    return payload


def test_demo_buyers_are_labelled(client, api_prefix, demo_headers):
    response = client.get(f"{api_prefix}/buyers", headers=demo_headers)
    assert response.status_code == 200
    buyers = response.json()
    assert len(buyers) >= 5
    assert all(buyer["is_demo"] is True for buyer in buyers)


def test_buyer_and_offer_crud(client, api_prefix, user_headers):
    created = client.post(
        f"{api_prefix}/buyers",
        headers=user_headers,
        json=_buyer_payload("CRUD Buyer"),
    )
    assert created.status_code == 201, created.text
    buyer = created.json()
    buyer_id = buyer["id"]
    assert buyer["is_demo"] is False

    detail = client.get(f"{api_prefix}/buyers/{buyer_id}", headers=user_headers)
    assert detail.status_code == 200
    assert detail.json()["offers"] == []

    patched = client.patch(
        f"{api_prefix}/buyers/{buyer_id}",
        headers=user_headers,
        json={"name": "CRUD Buyer Renamed", "buyer_type": "FPO"},
    )
    assert patched.status_code == 200
    assert patched.json()["name"] == "CRUD Buyer Renamed"
    assert patched.json()["buyer_type"] == "FPO"

    offer_response = client.post(
        f"{api_prefix}/buyers/{buyer_id}/offers",
        headers=user_headers,
        json=_offer_payload("Onion"),
    )
    assert offer_response.status_code == 201, offer_response.text
    offer = offer_response.json()
    offer_id = offer["id"]
    assert offer["buyer_id"] == buyer_id
    assert offer["is_demo"] is False

    offers = client.get(f"{api_prefix}/buyers/{buyer_id}/offers", headers=user_headers)
    assert offers.status_code == 200
    assert [row["id"] for row in offers.json()] == [offer_id]

    # The buyer list can be filtered by a crop that has an active offer.
    filtered = client.get(f"{api_prefix}/buyers?crop=Onion", headers=user_headers)
    assert filtered.status_code == 200
    assert any(row["id"] == buyer_id for row in filtered.json())

    offer_patch = client.patch(
        f"{api_prefix}/offers/{offer_id}",
        headers=user_headers,
        json={"offered_price_per_quintal": 5250.0, "is_active": False},
    )
    assert offer_patch.status_code == 200
    assert offer_patch.json()["offered_price_per_quintal"] == 5250.0
    assert offer_patch.json()["is_active"] is False

    # Inactive offers drop the buyer from the crop filter.
    filtered_after = client.get(f"{api_prefix}/buyers?crop=Onion", headers=user_headers)
    assert filtered_after.status_code == 200
    assert all(row["id"] != buyer_id for row in filtered_after.json())

    assert client.delete(f"{api_prefix}/offers/{offer_id}", headers=user_headers).status_code == 200
    assert client.delete(f"{api_prefix}/buyers/{buyer_id}", headers=user_headers).status_code == 200
    assert client.get(f"{api_prefix}/buyers/{buyer_id}", headers=user_headers).status_code == 404


def test_buyer_validation(client, api_prefix, user_headers):
    bad_type = client.post(
        f"{api_prefix}/buyers",
        headers=user_headers,
        json=_buyer_payload("Bad Type", buyer_type="Alien"),
    )
    assert bad_type.status_code == 422

    lone_coordinate = client.post(
        f"{api_prefix}/buyers",
        headers=user_headers,
        json=_buyer_payload("Lone Coord", longitude=None),
    )
    assert lone_coordinate.status_code == 422

    buyer = client.post(
        f"{api_prefix}/buyers", headers=user_headers, json=_buyer_payload("Offer Validation")
    ).json()
    bad_crop = client.post(
        f"{api_prefix}/buyers/{buyer['id']}/offers",
        headers=user_headers,
        json=_offer_payload("Dragonfruit"),
    )
    assert bad_crop.status_code == 422

    reversed_dates = client.post(
        f"{api_prefix}/buyers/{buyer['id']}/offers",
        headers=user_headers,
        json=_offer_payload(
            expiry_date=(date.today() - timedelta(days=1)).isoformat(),
            offer_date=date.today().isoformat(),
        ),
    )
    assert reversed_dates.status_code == 422

    bad_quantity = client.post(
        f"{api_prefix}/buyers/{buyer['id']}/offers",
        headers=user_headers,
        json=_offer_payload(min_quantity_quintals=100, max_quantity_quintals=10),
    )
    assert bad_quantity.status_code == 422
    client.delete(f"{api_prefix}/buyers/{buyer['id']}", headers=user_headers)


def test_buyer_ownership_isolation(client, api_prefix, user_headers, other_user_headers):
    buyer = client.post(
        f"{api_prefix}/buyers",
        headers=user_headers,
        json=_buyer_payload(f"Private Buyer {uuid.uuid4().hex[:6]}"),
    ).json()
    buyer_id = buyer["id"]

    assert client.get(f"{api_prefix}/buyers/{buyer_id}", headers=other_user_headers).status_code == 404
    assert (
        client.patch(
            f"{api_prefix}/buyers/{buyer_id}",
            headers=other_user_headers,
            json={"name": "Hijacked Buyer"},
        ).status_code
        == 404
    )
    assert (
        client.post(
            f"{api_prefix}/buyers/{buyer_id}/offers",
            headers=other_user_headers,
            json=_offer_payload("Onion"),
        ).status_code
        == 404
    )
    assert (
        client.delete(f"{api_prefix}/buyers/{buyer_id}", headers=other_user_headers).status_code
        == 404
    )
    client.delete(f"{api_prefix}/buyers/{buyer_id}", headers=user_headers)
