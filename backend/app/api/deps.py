"""Shared FastAPI dependencies: authentication, ownership and pagination."""

from __future__ import annotations

from collections.abc import Generator
from typing import Annotated, Any

from fastapi import Depends, Query
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.errors import ForbiddenError, NotFoundError, UnauthorizedError
from app.core.security import TokenError, decode_token
from app.models.farm import Crop, Farm
from app.models.user import RevokedToken, User

bearer_scheme = HTTPBearer(auto_error=False)

DbSession = Annotated[Session, Depends(get_db)]


def get_token_payload(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> dict[str, Any]:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise UnauthorizedError("A bearer access token is required")
    try:
        payload = decode_token(credentials.credentials, "access")
    except TokenError as exc:
        raise UnauthorizedError(str(exc)) from exc
    return payload


def get_current_user(
    db: DbSession,
    payload: Annotated[dict[str, Any], Depends(get_token_payload)],
) -> User:
    revoked = db.scalar(select(RevokedToken).where(RevokedToken.jti == payload["jti"]))
    if revoked is not None:
        raise UnauthorizedError("Token has been revoked")
    user = db.get(User, int(payload["sub"]))
    if user is None or not user.is_active:
        raise UnauthorizedError("User account is not active")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def get_farm(db: Session, user: User, farm_id: int) -> Farm:
    farm = db.get(Farm, farm_id)
    if farm is None:
        raise NotFoundError("Farm not found")
    if farm.user_id != user.id:
        raise ForbiddenError("You do not have access to this farm")
    return farm


def get_crop(db: Session, user: User, crop_id: int) -> Crop:
    crop = db.get(Crop, crop_id)
    if crop is None:
        raise NotFoundError("Crop not found")
    farm = db.get(Farm, crop.farm_id)
    if farm is None or farm.user_id != user.id:
        raise ForbiddenError("You do not have access to this crop")
    return crop


def owned_crop_query(user: User):
    return select(Crop).join(Farm, Crop.farm_id == Farm.id).where(Farm.user_id == user.id)


class Pagination:
    def __init__(
        self,
        page: int = Query(default=1, ge=1),
        page_size: int = Query(default=20, ge=1, le=100),
    ) -> None:
        self.page = page
        self.page_size = page_size
        self.offset = (page - 1) * page_size

    def pages(self, total: int) -> int:
        return max(1, (total + self.page_size - 1) // self.page_size)


PaginationDep = Annotated[Pagination, Depends(Pagination)]
