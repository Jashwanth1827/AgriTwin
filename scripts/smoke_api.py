"""Manual end-to-end API smoke test (development only)."""

import io
import sys
from pathlib import Path

sys.path.insert(0, "backend")

from fastapi.testclient import TestClient  # noqa: E402
from PIL import Image  # noqa: E402

from app.main import app  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]
SAMPLE_DIR = REPO_ROOT / "ml" / "crop_health" / "data" / "plantvillage_subset"


def _leaf_image() -> tuple[str, bytes, str]:
    """Prefer a real PlantVillage leaf; otherwise send a valid synthetic PNG."""
    if SAMPLE_DIR.exists():
        sample = next(SAMPLE_DIR.glob("Tomato___Early_blight/*"), None)
        if sample is not None:
            return (sample.name, sample.read_bytes(), "image/png")
    buffer = io.BytesIO()
    Image.new("RGB", (192, 192), (40, 150, 60)).save(buffer, format="PNG")
    return ("synthetic-leaf.png", buffer.getvalue(), "image/png")


def _check(name: str, response, expected: tuple[int, ...] = (200, 201)):
    ok = response.status_code in expected
    print(f"{name}: {response.status_code} {'OK' if ok else 'FAILED'}")
    if not ok:
        print(response.text[:2000])
        raise SystemExit(1)
    return response


def main() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "demo@agritwin.in", "password": "Demo@12345"},
        )
        _check("login", response, (200,))
        token = response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        for path in [
            "/api/v1/auth/me",
            "/api/v1/system/status",
            "/api/v1/farms",
            "/api/v1/crops",
            "/api/v1/buyers",
            "/api/v1/market/crops",
            "/api/v1/market/prices?crop=Onion",
            "/api/v1/market/trends?crop=Onion",
            "/api/v1/dashboard/overview",
            "/api/v1/yield/model",
            "/api/v1/crop-health/model",
            "/api/v1/crop-health/classes",
            "/api/v1/transport/vehicles",
            "/api/v1/decisions/policy",
            "/api/v1/system/notifications",
        ]:
            _check(f"GET {path}", client.get(path, headers=headers))

        live = client.get(
            "/api/v1/market/live-rates?crop=Onion&state=Maharashtra", headers=headers
        )
        print(
            f"GET /api/v1/market/live-rates: {live.status_code} "
            f"{'OK' if live.status_code == 200 else 'UNAVAILABLE'}"
        )
        if live.status_code == 200:
            info = live.json()
            print(
                "  provider:",
                info["provider"],
                "observed:",
                info["latest_observation_date"],
                "rows:",
                len(info["records"]),
            )

        status = client.get("/api/v1/system/status").json()
        models = {row["name"]: row for row in status["models"]}
        print("model modes:", {name: row["mode"] for name, row in models.items()})
        assert models["crop_health"]["mode"] == "real", "crop-health model is not in real mode"
        assert models["yield_prediction"]["available"] is True

        crops = client.get("/api/v1/crops", headers=headers).json()
        onion = next(item for item in crops if item["crop_name"] == "Onion")
        print("onion", onion["id"], onion["farm_id"])

        _check(
            "readiness",
            client.get(f"/api/v1/yield/readiness/{onion['id']}", headers=headers),
        )
        _check(
            "yield predict",
            client.post(
                "/api/v1/yield/predict",
                headers=headers,
                json={"farm_id": onion["farm_id"], "crop_id": onion["id"]},
            ),
        )
        forecast = _check(
            "market forecast",
            client.post(
                "/api/v1/market/forecast",
                headers=headers,
                json={"crop": "Onion", "horizon_days": 14},
            ),
        )
        print("forecast model:", forecast.json()["model_name"], forecast.json()["market"])

        buyers = client.get("/api/v1/buyers", headers=headers).json()
        buyer = next(
            row
            for row in buyers
            if row["latitude"] is not None and row["longitude"] is not None
        )
        _check(
            "transport estimate",
            client.post(
                "/api/v1/transport/estimate",
                headers=headers,
                json={
                    "farm_id": onion["farm_id"],
                    "buyer_id": buyer["id"],
                    "crop_id": onion["id"],
                    "quantity_quintals": 25,
                    "vehicle_type": "truck",
                    "use_routing": False,
                },
            ),
        )

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
        _check(
            "crop-health detail",
            client.get(
                f"/api/v1/crop-health/predictions/{payload['id']}", headers=headers
            ),
        )

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

        overview = _check(
            "dashboard overview",
            client.get("/api/v1/dashboard/overview", headers=headers),
        )
        print(
            "dashboard:",
            f"farms={overview.json()['total_farms']}",
            f"crops={overview.json()['active_crops']}",
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
        print("\nSMOKE TEST PASSED")


if __name__ == "__main__":
    main()
