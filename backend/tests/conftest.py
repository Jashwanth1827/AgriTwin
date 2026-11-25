"""Shared pytest fixtures.

The application reads configuration at import time, so the environment is
prepared *before* ``app`` is imported.  Each test session gets its own SQLite
file and upload directory, which keeps tests isolated from the development
database and from each other.
"""

from __future__ import annotations

import os
import uuid
from pathlib import Path

import pytest

TEST_ROOT = Path(os.environ.get("TEMP", ".")) / f"agritwin-tests-{uuid.uuid4().hex[:12]}"
TEST_ROOT.mkdir(parents=True, exist_ok=True)

os.environ.update(
    {
        "ENVIRONMENT": "test",
        "DATABASE_URL": f"sqlite:///{(TEST_ROOT / 'test.db').as_posix()}",
        "UPLOAD_DIR": str(TEST_ROOT / "uploads"),
        "DEMO_MODE": "true",
        "RATE_LIMIT_ENABLED": "false",
        "JWT_SECRET_KEY": "test-secret-key-not-for-production",
        "LOG_LEVEL": "WARNING",
    }
)

from fastapi.testclient import TestClient  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.main import app  # noqa: E402

API = settings.API_V1_PREFIX


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(scope="session")
def api_prefix() -> str:
    return API


@pytest.fixture(scope="session")
def demo_headers(client: TestClient) -> dict[str, str]:
    response = client.post(
        f"{API}/auth/login",
        json={
            "email": settings.SEED_DEMO_USER_EMAIL,
            "password": settings.SEED_DEMO_USER_PASSWORD,
        },
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.fixture(scope="session")
def demo_farm_crop(client: TestClient, demo_headers: dict[str, str]) -> tuple[int, int]:
    """Return (farm_id, crop_id) for the demo onion crop."""
    farms = client.get(f"{API}/farms", headers=demo_headers).json()
    for farm in farms:
        crops = client.get(
            f"{API}/farms/{farm['id']}/crops", headers=demo_headers
        ).json()
        for crop in crops:
            if crop["crop_name"] == "Onion":
                return farm["id"], crop["id"]
    raise AssertionError("Demo onion farm/crop not found in seed data")


@pytest.fixture(scope="session")
def registered_user(client: TestClient):
    """Create an isolated non-demo account and return its tokens."""
    email = f"farmer-{uuid.uuid4().hex[:10]}@example.com"
    response = client.post(
        f"{API}/auth/register",
        json={
            "email": email,
            "password": "TestPass@123",
            "full_name": "Test Farmer",
            "state": "Maharashtra",
            "district": "Nashik",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


@pytest.fixture(scope="session")
def user_headers(registered_user) -> dict[str, str]:
    return {"Authorization": f"Bearer {registered_user['access_token']}"}


@pytest.fixture(scope="session")
def other_user_headers(client: TestClient) -> dict[str, str]:
    email = f"other-{uuid.uuid4().hex[:10]}@example.com"
    response = client.post(
        f"{API}/auth/register",
        json={
            "email": email,
            "password": "TestPass@123",
            "full_name": "Other Farmer",
            "state": "Maharashtra",
            "district": "Pune",
        },
    )
    assert response.status_code == 201, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}
