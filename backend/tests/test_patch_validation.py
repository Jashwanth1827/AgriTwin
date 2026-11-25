"""PATCH requests must enforce the same rules as POST.

A partial update can otherwise persist an enum value, an unpaired coordinate or an
invalid date range that the create endpoint would have rejected. These tests cover
the merged-state validation added to the update services.
"""

from __future__ import annotations

import uuid
from datetime import date, timedelta


def _farm_payload(name: str) -> dict:
    return {
        "name": name,
        "district": "Nashik",
        "state": "Maharashtra",
        "latitude": 20.0,
        "longitude": 73.8,
        "total_area_hectares": 4.0,
        "soil_type": "Black (Regur)",
    }


def _buyer_payload(name: str) -> dict:
    return {
        "name": name,
        "buyer_type": "Trader",
        "district": "Nashik",
        "state": "Maharashtra",
        "latitude": 20.01,
        "longitude": 73.79,
    }


def test_patch_validation_matches_create_rules(client, api_prefix, user_headers):
    suffix = uuid.uuid4().hex[:6]

    farm_response = client.post(
        f"{api_prefix}/farms",
        headers=user_headers,
        json=_farm_payload(f"Patch Farm {suffix}"),
    )
    assert farm_response.status_code == 201, farm_response.text
    farm_id = farm_response.json()["id"]

    bad_soil = client.patch(
        f"{api_prefix}/farms/{farm_id}",
        headers=user_headers,
        json={"soil_type": "Moon dust"},
    )
    assert bad_soil.status_code == 422, bad_soil.text

    # The stored farm has both coordinates; clearing only one must be rejected.
    unpaired_coordinate = client.patch(
        f"{api_prefix}/farms/{farm_id}",
        headers=user_headers,
        json={"longitude": None},
    )
    assert unpaired_coordinate.status_code == 422, unpaired_coordinate.text

    crop_response = client.post(
        f"{api_prefix}/crops",
        headers=user_headers,
        json={
            "farm_id": farm_id,
            "crop_name": "Onion",
            "season": "Kharif",
            "sowing_date": date.today().isoformat(),
            "area_hectares": 1.0,
        },
    )
    assert crop_response.status_code == 201, crop_response.text
    crop_id = crop_response.json()["id"]

    bad_crop = client.patch(
        f"{api_prefix}/crops/{crop_id}",
        headers=user_headers,
        json={"crop_name": "Dragonfruit"},
    )
    assert bad_crop.status_code == 422, bad_crop.text

    bad_harvest = client.patch(
        f"{api_prefix}/crops/{crop_id}",
        headers=user_headers,
        json={"expected_harvest_date": (date.today() - timedelta(days=3)).isoformat()},
    )
    assert bad_harvest.status_code == 422, bad_harvest.text

    buyer_response = client.post(
        f"{api_prefix}/buyers",
        headers=user_headers,
        json=_buyer_payload(f"Patch Buyer {suffix}"),
    )
    assert buyer_response.status_code == 201, buyer_response.text
    buyer_id = buyer_response.json()["id"]

    bad_state = client.patch(
        f"{api_prefix}/buyers/{buyer_id}",
        headers=user_headers,
        json={"state": "Atlantis"},
    )
    assert bad_state.status_code == 422, bad_state.text

    bad_type = client.patch(
        f"{api_prefix}/buyers/{buyer_id}",
        headers=user_headers,
        json={"buyer_type": "Alien"},
    )
    assert bad_type.status_code == 422, bad_type.text

    offer_response = client.post(
        f"{api_prefix}/buyers/{buyer_id}/offers",
        headers=user_headers,
        json={
            "crop": "Onion",
            "offered_price_per_quintal": 2500.0,
            "min_quantity_quintals": 1.0,
            "max_quantity_quintals": 10.0,
            "offer_date": date.today().isoformat(),
            "expiry_date": (date.today() + timedelta(days=7)).isoformat(),
        },
    )
    assert offer_response.status_code == 201, offer_response.text
    offer_id = offer_response.json()["id"]

    bad_dates = client.patch(
        f"{api_prefix}/offers/{offer_id}",
        headers=user_headers,
        json={"expiry_date": (date.today() - timedelta(days=1)).isoformat()},
    )
    assert bad_dates.status_code == 422, bad_dates.text

    bad_offer_crop = client.patch(
        f"{api_prefix}/offers/{offer_id}",
        headers=user_headers,
        json={"crop": "Unobtainium"},
    )
    assert bad_offer_crop.status_code == 422, bad_offer_crop.text

    bad_quantity = client.patch(
        f"{api_prefix}/offers/{offer_id}",
        headers=user_headers,
        json={"min_quantity_quintals": 100.0},
    )
    assert bad_quantity.status_code == 422, bad_quantity.text

    bad_profile = client.patch(
        f"{api_prefix}/auth/me",
        headers=user_headers,
        json={"state": "Atlantis"},
    )
    assert bad_profile.status_code == 422, bad_profile.text

    assert client.delete(
        f"{api_prefix}/buyers/{buyer_id}", headers=user_headers
    ).status_code == 200
    assert client.delete(f"{api_prefix}/farms/{farm_id}", headers=user_headers).status_code == 200
