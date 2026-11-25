from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.core.constants import INDIAN_STATES
from app.schemas.common import ORMModel


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)
    full_name: str = Field(min_length=2, max_length=160)
    phone: str | None = Field(default=None, max_length=20)
    state: str | None = None
    district: str | None = Field(default=None, max_length=120)

    @field_validator("password")
    @classmethod
    def password_strength(cls, value: str) -> str:
        if not any(c.isalpha() for c in value) or not any(c.isdigit() for c in value):
            raise ValueError("Password must contain at least one letter and one digit")
        return value

    @field_validator("full_name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 2:
            raise ValueError("Full name is too short")
        return value

    @field_validator("state")
    @classmethod
    def valid_state(cls, value: str | None) -> str | None:
        if value and value not in INDIAN_STATES:
            raise ValueError("Unknown Indian state or union territory")
        return value


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=72)


class RefreshRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: str | None = None


class UserOut(ORMModel):
    id: int
    email: EmailStr
    full_name: str
    phone: str | None = None
    state: str | None = None
    district: str | None = None
    preferred_language: str
    is_demo: bool
    created_at: datetime


class UserUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=160)
    phone: str | None = Field(default=None, max_length=20)
    state: str | None = None
    district: str | None = Field(default=None, max_length=120)
    preferred_language: str | None = Field(default=None, max_length=10)

    @field_validator("full_name")
    @classmethod
    def strip_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if len(value) < 2:
            raise ValueError("Full name is too short")
        return value

    @field_validator("state")
    @classmethod
    def valid_state(cls, value: str | None) -> str | None:
        if value and value not in INDIAN_STATES:
            raise ValueError("Unknown Indian state or union territory")
        return value


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserOut
