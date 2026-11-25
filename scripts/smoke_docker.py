"""End-to-end smoke test against a running AgriTwin stack over HTTP.

Unlike ``smoke_api.py`` (which drives the ASGI app in-process with SQLite),
this script talks to the deployed stack through the nginx frontend, so it
exercises the reverse proxy, PostgreSQL-backed API, model artifacts inside the
container and the Grad-CAM static file route.

Usage:
    python scripts/smoke_docker.py
    python scripts/smoke_docker.py --base-url http://localhost:8000
"""

from __future__ import annotations

import argparse
import io
import sys
from pathlib import Path

import httpx
from PIL import Image

REPO_ROOT = Path(__file__).resolve().parents[1]
SAMPLE_DIR = REPO_ROOT / "ml" / "crop_health" / "data" / "plantvillage_subset"


def _leaf_image() -> tuple[str, bytes, str]:
    if SAMPLE_DIR.exists():
        sample = next(SAMPLE_DIR.glob("Tomato___Early_blight/*"), None)
        if sample is not None:
            return (sample.name, sample.read_bytes(), "image/png")
    buffer = io.BytesIO()
    Image.new("RGB", (192, 192), (40, 150, 60)).save(buffer, format="PNG")
    return ("synthetic-leaf.png", buffer.getvalue(), "image/png")


def _check(name: str, response: httpx.Response, expected: tuple[int, ...] = (200, 201)):
    ok = response.status_code in expected
    print(f"{name}: {response.status_code} {'OK' if ok else 'FAILED'}")
    if not ok:
        print(response.text[:2000])
        raise SystemExit(1)
    return response


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://localhost:5173")
    args = parser.parse_args()
    base = args.base_url.rstrip("/")
    print(f"Target: {base}")

    with httpx.Client(base_url=base, timeout=120.0) as client:
        index = _check("frontend index", client.get("/"))
        assert "AgriTwin" in index.text or "root" in index.text, "unexpected index.html"

        _check("health via proxy", client.get("/api/v1/system/health"))

        response = _check(
            "login",
            client.post(
                "/api/v1/auth/login",
                json={"email": "demo@agritwin.in", "password": "Demo@12345"},
            ),
            (200,),
        )
        headers = {"Authorization": f"Bearer {response.json()['access_token']}"}

        for path in [
            "/api/v1/auth/me",
            "/api/v1/system/status",
            "/api/v1/farms",
            "/api/v1/crops",
            "/api/v1/buyers",
            "/api/v1/market/prices?crop=Onion",
            "/api/v1/dashboard/overview",
            "/api/v1/decisions/policy",
        ]:
            _check(f"GET {path}", client.get(path, headers=headers))

        status = client.get("/api/v1/system/status", headers=headers).json()
        models = {row["name"]: row for row in status["models"]}
        print("model modes:", {name: row["mode"] for name, row in models.items()})
        assert models["crop_health"]["mode"] == "real", "crop-health is not in real mode"
        assert models["yield_prediction"]["available"] is True

        crops = client.get("/api/v1/crops", headers=headers).json()
        onion = next(item for item in crops if item["crop_name"] == "Onion")

        forecast = _check(
            "market forecast",
            client.post(
                "/api/v1/market/forecast",
                headers=headers,
                json={"crop": "Onion", "horizon_days": 14},
            ),
        )
        print("forecast model:", forecast.json()["model_name"], forecast.json()["market"])

        filename, content, mime = _leaf_image()
        health = _check(
            "crop-health predict",
            client.post(
                "/api/v1/crop-health/predict",
                headers=headers,
                data={"farm_id": onion["farm_id"], "crop_id": onion["id"]},
                files={"file": (filename, content, mime)},
            ),
        )
        payload = health.json()["prediction"]
        print(
            "crop-health:",
            payload["predicted_label"],
            f"confidence={payload['confidence']:.3f}",
            f"mode={payload['model_mode']}",
            f"gradcam={'yes' if payload.get('gradcam_url') else 'no'}",
        )
        assert payload["model_mode"] == "real"
        assert payload["gradcam_url"], "Grad-CAM was not generated"

        overlay = _check(
            "gradcam via proxy",
            client.get(payload["gradcam_url"]),
        )
        assert overlay.headers["content-type"].startswith("image/"), "overlay is not an image"
        assert len(overlay.content) > 1000, "overlay image is empty"

        decision = _check(
            "decision",
            client.post(
                "/api/v1/decisions",
                headers=headers,
                json={
                    "farm_id": onion["farm_id"],
                    "crop_id": onion["id"],
                    "risk_preference": "medium",
                },
            ),
        )
        body = decision.json()
        print(
            "decision:",
            body["action"],
            f"channel={body['outputs']['channel']}",
            f"net/q={body['net_realization_per_quintal']}",
            f"risk={body['risk_score']:.2f} ({body['risk_category']})",
        )

        report = _check(
            "report",
            client.post(
                "/api/v1/system/reports",
                headers=headers,
                json={"farm_id": onion["farm_id"]},
            ),
        )
        print("report id:", report.json()["id"])
        print("\nDOCKER SMOKE TEST PASSED")


if __name__ == "__main__":
    sys.exit(main())
