from __future__ import annotations

from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.core.errors import AppError

T = TypeVar("T")


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class Message(BaseModel):
    message: str


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int
    pages: int


class PaginationParams(BaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


def validate_patch(schema: type[BaseModel], current: Any, updates: dict[str, Any]) -> None:
    """Validate a partial update against the full rule set of its create schema.

    PATCH payloads are partial, so field-only validators cannot check cross-field rules such as
    coordinate pairing or expiry-after-offer date. Merging the stored values into a create payload
    lets the same validators run against the *resulting* record. Raises an AppError with the
    standard 422 envelope when the merged state would be invalid.
    """
    data = {name: getattr(current, name, None) for name in schema.model_fields}
    data.update(updates)
    try:
        schema(**data)
    except ValidationError as exc:
        # Pydantic keeps the raw ValueError in ``ctx``, which is not JSON serialisable.
        details = [
            {"loc": list(error["loc"]), "msg": error["msg"], "type": error["type"]}
            for error in exc.errors()
        ]
        raise AppError(
            "Validation failed for the updated resource",
            status_code=422,
            code="validation_error",
            details=details,
        ) from exc
