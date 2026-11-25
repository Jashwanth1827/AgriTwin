"""Authentication service: registration, login, refresh and revocation."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import ConflictError, UnauthorizedError
from app.core.security import (
    TokenError,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    token_expiry,
    verify_password,
)
from app.models.user import RevokedToken, User
from app.schemas.auth import RegisterRequest, TokenResponse, UserOut


def _tokens_for(user: User) -> TokenResponse:
    access, _, _ = create_access_token(str(user.id))
    refresh, _, _ = create_refresh_token(str(user.id))
    return TokenResponse(
        access_token=access,
        refresh_token=refresh,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=UserOut.model_validate(user),
    )


def register(db: Session, payload: RegisterRequest) -> TokenResponse:
    email = payload.email.strip().lower()
    existing = db.scalar(select(User).where(User.email == email))
    if existing is not None:
        raise ConflictError("An account with this email already exists")
    user = User(
        email=email,
        full_name=payload.full_name.strip(),
        password_hash=hash_password(payload.password),
        phone=payload.phone,
        state=payload.state,
        district=payload.district,
        is_demo=False,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return _tokens_for(user)


def login(db: Session, email: str, password: str) -> TokenResponse:
    user = db.scalar(select(User).where(User.email == email.strip().lower()))
    if user is None or not verify_password(password, user.password_hash):
        raise UnauthorizedError("Incorrect email or password")
    if not user.is_active:
        raise UnauthorizedError("This account is disabled")
    return _tokens_for(user)


def refresh(db: Session, refresh_token: str) -> TokenResponse:
    try:
        payload = decode_token(refresh_token, "refresh")
    except TokenError as exc:
        raise UnauthorizedError(str(exc)) from exc
    if db.scalar(select(RevokedToken).where(RevokedToken.jti == payload["jti"])):
        raise UnauthorizedError("Refresh token has already been used")
    user = db.get(User, int(payload["sub"]))
    if user is None or not user.is_active:
        raise UnauthorizedError("User account is not active")
    # Rotate the refresh token: the old one is revoked immediately.
    db.add(
        RevokedToken(
            jti=payload["jti"],
            token_type="refresh",
            expires_at=token_expiry(payload),
            revoked_at=datetime.now(timezone.utc),
        )
    )
    db.commit()
    return _tokens_for(user)


def revoke(db: Session, jti: str, token_type: str, expires_at: datetime) -> None:
    if db.scalar(select(RevokedToken).where(RevokedToken.jti == jti)):
        return
    db.add(
        RevokedToken(
            jti=jti,
            token_type=token_type,
            expires_at=expires_at,
            revoked_at=datetime.now(timezone.utc),
        )
    )
    db.commit()


def logout(db: Session, *, refresh_token: str | None, access_payload: dict | None) -> None:
    if access_payload:
        revoke(db, access_payload["jti"], "access", token_expiry(access_payload))
    if refresh_token:
        try:
            payload = decode_token(refresh_token, "refresh")
        except TokenError:
            payload = None
        if payload:
            revoke(db, payload["jti"], "refresh", token_expiry(payload))
