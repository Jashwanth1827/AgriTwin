"""Authentication, token rotation, profile and access-control tests."""

from __future__ import annotations

import uuid

PASSWORD = "TestPass@123"


def _email(prefix: str = "user") -> str:
    return f"{prefix}-{uuid.uuid4().hex[:10]}@example.com"


def _register(client, api_prefix: str, *, email: str | None = None, password: str = PASSWORD):
    return client.post(
        f"{api_prefix}/auth/register",
        json={
            "email": email or _email(),
            "password": password,
            "full_name": "Automated Test Farmer",
            "state": "Maharashtra",
            "district": "Nashik",
        },
    )


def test_demo_login_returns_demo_user(client, api_prefix):
    response = client.post(
        f"{api_prefix}/auth/login",
        json={"email": "demo@agritwin.in", "password": "Demo@12345"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["expires_in"] > 0
    assert body["user"]["is_demo"] is True
    assert body["user"]["email"] == "demo@agritwin.in"


def test_register_refresh_me_and_logout(client, api_prefix):
    email = _email("rotate")
    response = _register(client, api_prefix, email=email)
    assert response.status_code == 201, response.text
    tokens = response.json()

    headers = {"Authorization": f"Bearer {tokens['access_token']}"}
    me = client.get(f"{api_prefix}/auth/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["email"] == email
    assert me.json()["is_demo"] is False

    refreshed = client.post(
        f"{api_prefix}/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]},
    )
    assert refreshed.status_code == 200, refreshed.text
    new_tokens = refreshed.json()
    assert new_tokens["refresh_token"] != tokens["refresh_token"]

    # Refresh tokens are single-use.
    reuse = client.post(
        f"{api_prefix}/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]},
    )
    assert reuse.status_code == 401
    assert reuse.json()["error"]["code"] == "unauthorized"

    new_headers = {"Authorization": f"Bearer {new_tokens['access_token']}"}
    logout = client.post(
        f"{api_prefix}/auth/logout",
        headers=new_headers,
        json={"refresh_token": new_tokens["refresh_token"]},
    )
    assert logout.status_code == 200

    # The access token is revoked immediately after logout.
    assert client.get(f"{api_prefix}/auth/me", headers=new_headers).status_code == 401


def test_duplicate_registration_conflicts(client, api_prefix):
    email = _email("dupe")
    assert _register(client, api_prefix, email=email).status_code == 201
    duplicate = _register(client, api_prefix, email=email)
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "conflict"


def test_registration_validation(client, api_prefix):
    short_password = client.post(
        f"{api_prefix}/auth/register",
        json={
            "email": _email("short"),
            "password": "abc",
            "full_name": "Test Farmer",
        },
    )
    assert short_password.status_code == 422

    no_digit = client.post(
        f"{api_prefix}/auth/register",
        json={
            "email": _email("nodigit"),
            "password": "OnlyLetters",
            "full_name": "Test Farmer",
        },
    )
    assert no_digit.status_code == 422

    bad_state = client.post(
        f"{api_prefix}/auth/register",
        json={
            "email": _email("state"),
            "password": PASSWORD,
            "full_name": "Test Farmer",
            "state": "Atlantis",
        },
    )
    assert bad_state.status_code == 422

    bad_email = client.post(
        f"{api_prefix}/auth/register",
        json={"email": "not-an-email", "password": PASSWORD, "full_name": "Test Farmer"},
    )
    assert bad_email.status_code == 422


def test_wrong_password_is_rejected(client, api_prefix, registered_user):
    response = client.post(
        f"{api_prefix}/auth/login",
        json={"email": registered_user["user"]["email"], "password": "WrongPass@123"},
    )
    assert response.status_code == 401


def test_protected_routes_require_token(client, api_prefix):
    for path in ("/farms", "/auth/me", "/decisions", "/dashboard/overview"):
        response = client.get(f"{api_prefix}{path}")
        assert response.status_code == 401, path
        assert response.json()["error"]["code"] == "unauthorized"


def test_invalid_refresh_token(client, api_prefix):
    response = client.post(
        f"{api_prefix}/auth/refresh", json={"refresh_token": "not-a-real-token"}
    )
    assert response.status_code == 401


def test_update_profile(client, api_prefix):
    response = _register(client, api_prefix)
    assert response.status_code == 201
    headers = {"Authorization": f"Bearer {response.json()['access_token']}"}

    updated = client.patch(
        f"{api_prefix}/auth/me",
        headers=headers,
        json={
            "full_name": "Updated Farmer",
            "district": "Pune",
            "preferred_language": "hi",
        },
    )
    assert updated.status_code == 200, updated.text
    body = updated.json()
    assert body["full_name"] == "Updated Farmer"
    assert body["district"] == "Pune"
    assert body["preferred_language"] == "hi"
