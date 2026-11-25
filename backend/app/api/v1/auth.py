"""Authentication routes."""

from __future__ import annotations

from fastapi import APIRouter, Request, status

from app.api.deps import CurrentUser, DbSession, get_token_payload
from app.schemas.auth import (
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserOut,
    UserUpdate,
)
from app.schemas.common import Message
from app.services import auth as auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: DbSession) -> TokenResponse:
    return auth_service.register(db, payload)


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: DbSession) -> TokenResponse:
    return auth_service.login(db, str(payload.email), payload.password)


@router.post("/refresh", response_model=TokenResponse)
def refresh(payload: RefreshRequest, db: DbSession) -> TokenResponse:
    return auth_service.refresh(db, payload.refresh_token)


@router.post("/logout", response_model=Message)
def logout(
    payload: LogoutRequest,
    request: Request,
    db: DbSession,
) -> Message:
    authorization = request.headers.get("Authorization", "")
    access_payload = None
    if authorization.lower().startswith("bearer "):
        from app.core.security import TokenError, decode_token

        try:
            access_payload = decode_token(authorization.split(" ", 1)[1], "access")
        except TokenError:
            access_payload = None
    auth_service.logout(db, refresh_token=payload.refresh_token, access_payload=access_payload)
    return Message(message="Signed out")


@router.get("/me", response_model=UserOut)
def me(user: CurrentUser) -> UserOut:
    return UserOut.model_validate(user)


@router.patch("/me", response_model=UserOut)
def update_me(payload: UserUpdate, user: CurrentUser, db: DbSession) -> UserOut:
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(user, key, value)
    db.commit()
    db.refresh(user)
    return UserOut.model_validate(user)
