"""Crop-health model metadata, upload validation and inference API tests."""

from __future__ import annotations

import io

from PIL import Image


def _png_bytes(size: tuple[int, int] = (96, 96), colour: tuple[int, int, int] = (30, 170, 40)) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", size, colour).save(buffer, format="PNG")
    return buffer.getvalue()


def test_model_metadata_and_disease_classes(client, api_prefix, user_headers):
    info = client.get(f"{api_prefix}/crop-health/model")
    assert info.status_code == 200
    body = info.json()
    assert body["mode"] in {"real", "demo", "unavailable"}
    if body["mode"] == "real":
        assert body["available"] is True
        assert body["model_version"]
        assert body["architecture"]
        assert body["tta_views"] in {1, 2, 4}
        assert 0.0 <= body["crop_prior_alpha"] <= 1.0
        assert len(body["classes"]) == 38
        assert body["metrics"]
    elif body["mode"] == "demo":
        assert body["available"] is False
        assert body["message"]

    classes = client.get(f"{api_prefix}/crop-health/classes", headers=user_headers)
    assert classes.status_code == 200
    rows = classes.json()
    assert len(rows) == 38
    assert any(row["name"].endswith("healthy") for row in rows)
    assert all(row["crop"] for row in rows)
    assert all(row["display_name"] for row in rows)


def test_reject_non_image_upload(client, api_prefix, demo_headers, demo_farm_crop):
    farm_id, crop_id = demo_farm_crop
    response = client.post(
        f"{api_prefix}/crop-health/predict",
        headers=demo_headers,
        data={"farm_id": farm_id, "crop_id": crop_id},
        files={"file": ("leaf.png", b"this is not an image", "image/png")},
    )
    assert response.status_code == 422
    assert "not a valid image" in response.json()["error"]["message"]


def test_reject_unsupported_mime_type(client, api_prefix, demo_headers, demo_farm_crop):
    farm_id, crop_id = demo_farm_crop
    response = client.post(
        f"{api_prefix}/crop-health/predict",
        headers=demo_headers,
        data={"farm_id": farm_id, "crop_id": crop_id},
        files={"file": ("leaf.gif", _png_bytes(), "image/gif")},
    )
    assert response.status_code == 415


def test_reject_tiny_image(client, api_prefix, demo_headers, demo_farm_crop):
    farm_id, crop_id = demo_farm_crop
    response = client.post(
        f"{api_prefix}/crop-health/predict",
        headers=demo_headers,
        data={"farm_id": farm_id, "crop_id": crop_id},
        files={"file": ("tiny.png", _png_bytes((8, 8)), "image/png")},
    )
    assert response.status_code == 422
    assert "too small" in response.json()["error"]["message"]


def test_prediction_flow_and_history(client, api_prefix, demo_headers, demo_farm_crop):
    farm_id, crop_id = demo_farm_crop
    response = client.post(
        f"{api_prefix}/crop-health/predict",
        headers=demo_headers,
        data={"farm_id": farm_id, "crop_id": crop_id},
        files={"file": ("leaf.png", _png_bytes(), "image/png")},
    )
    assert response.status_code == 201, response.text
    body = response.json()
    prediction = body["prediction"]
    assert prediction["farm_id"] == farm_id
    assert prediction["crop_id"] == crop_id
    assert prediction["predicted_label"]
    assert prediction["predicted_crop"]
    assert 0.0 <= prediction["confidence"] <= 1.0
    assert 0.0 <= prediction["severity"] <= 1.0
    assert prediction["probabilities"]
    assert prediction["model_mode"] in {"real", "demo"}
    assert prediction["image_url"].startswith("/uploads/")
    assert prediction["recommendations"]
    assert all(item["title"] and item["body"] for item in prediction["recommendations"])
    assert "AI-assisted screening" in body["disclaimer"]

    if prediction["model_mode"] == "demo":
        assert prediction["is_demo"] is True
        assert "DEMO" in (prediction["notes"] or "").upper()
        assert body["model"]["mode"] == "demo"
    else:
        assert prediction["is_demo"] is False
        assert body["model"]["mode"] == "real"
        assert body["model"]["available"] is True

    prediction_id = prediction["id"]
    listed = client.get(
        f"{api_prefix}/crop-health/predictions?farm_id={farm_id}&crop_id={crop_id}",
        headers=demo_headers,
    )
    assert listed.status_code == 200
    assert any(row["id"] == prediction_id for row in listed.json())

    detail = client.get(
        f"{api_prefix}/crop-health/predictions/{prediction_id}", headers=demo_headers
    )
    assert detail.status_code == 200
    assert detail.json()["id"] == prediction_id

    deleted = client.delete(
        f"{api_prefix}/crop-health/predictions/{prediction_id}", headers=demo_headers
    )
    assert deleted.status_code == 200
    assert (
        client.get(
            f"{api_prefix}/crop-health/predictions/{prediction_id}", headers=demo_headers
        ).status_code
        == 404
    )


def test_prediction_passes_selected_crop_to_inference(
    client, api_prefix, demo_headers, demo_farm_crop, monkeypatch
):
    from app.ml.crop_health.service import CropHealthService

    farm_id, crop_id = demo_farm_crop
    crops = client.get(f"{api_prefix}/crops", headers=demo_headers).json()
    crop_name = next(crop["crop_name"] for crop in crops if crop["id"] == crop_id)

    service = CropHealthService.instance()
    original_predict = service.predict
    seen: dict[str, object] = {}

    def spy_predict(image_path, **kwargs):
        seen["crop_hint"] = kwargs.get("crop_hint")
        return original_predict(image_path, **kwargs)

    monkeypatch.setattr(service, "predict", spy_predict)
    response = client.post(
        f"{api_prefix}/crop-health/predict",
        headers=demo_headers,
        data={"farm_id": farm_id, "crop_id": crop_id},
        files={"file": ("leaf.png", _png_bytes(), "image/png")},
    )
    assert response.status_code == 201, response.text
    assert seen["crop_hint"] == crop_name


def test_upload_requires_matching_farm_and_crop(
    client, api_prefix, demo_headers, demo_farm_crop
):
    farm_id, crop_id = demo_farm_crop
    farms = client.get(f"{api_prefix}/farms", headers=demo_headers).json()
    other_farm = next(farm for farm in farms if farm["id"] != farm_id)
    response = client.post(
        f"{api_prefix}/crop-health/predict",
        headers=demo_headers,
        data={"farm_id": other_farm["id"], "crop_id": crop_id},
        files={"file": ("leaf.png", _png_bytes(), "image/png")},
    )
    assert response.status_code == 422
    assert "does not belong" in response.json()["error"]["message"]


def test_prediction_ownership_isolation(
    client, api_prefix, demo_headers, other_user_headers, demo_farm_crop
):
    farm_id, crop_id = demo_farm_crop
    created = client.post(
        f"{api_prefix}/crop-health/predict",
        headers=demo_headers,
        data={"farm_id": farm_id, "crop_id": crop_id},
        files={"file": ("leaf.png", _png_bytes(), "image/png")},
    )
    assert created.status_code == 201
    prediction_id = created.json()["prediction"]["id"]

    assert (
        client.get(
            f"{api_prefix}/crop-health/predictions/{prediction_id}",
            headers=other_user_headers,
        ).status_code
        == 404
    )
    assert (
        client.delete(
            f"{api_prefix}/crop-health/predictions/{prediction_id}",
            headers=other_user_headers,
        ).status_code
        == 404
    )
    client.delete(
        f"{api_prefix}/crop-health/predictions/{prediction_id}", headers=demo_headers
    )
