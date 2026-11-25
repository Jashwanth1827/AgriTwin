"""Centralised API error handling with a stable error envelope."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)


class AppError(Exception):
    def __init__(
        self,
        message: str,
        *,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        code: str = "bad_request",
        details: Any | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.code = code
        self.details = details


class NotFoundError(AppError):
    def __init__(self, message: str = "Resource not found", details: Any | None = None) -> None:
        super().__init__(message, status_code=404, code="not_found", details=details)


class ForbiddenError(AppError):
    def __init__(self, message: str = "You do not have access to this resource") -> None:
        super().__init__(message, status_code=403, code="forbidden")


class ConflictError(AppError):
    def __init__(self, message: str, details: Any | None = None) -> None:
        super().__init__(message, status_code=409, code="conflict", details=details)


class UnauthorizedError(AppError):
    def __init__(self, message: str = "Authentication required") -> None:
        super().__init__(
            message,
            status_code=401,
            code="unauthorized",
            details=None,
        )


class ServiceUnavailableError(AppError):
    def __init__(self, message: str, details: Any | None = None) -> None:
        super().__init__(message, status_code=503, code="service_unavailable", details=details)


def _envelope(code: str, message: str, details: Any | None = None) -> dict[str, Any]:
    body: dict[str, Any] = {"error": {"code": code, "message": message}}
    if details is not None:
        body["error"]["details"] = details
    return body


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _app_error(_: Request, exc: AppError) -> JSONResponse:
        headers = {"WWW-Authenticate": "Bearer"} if exc.status_code == 401 else None
        return JSONResponse(
            status_code=exc.status_code,
            content=_envelope(exc.code, exc.message, exc.details),
            headers=headers,
        )

    @app.exception_handler(RequestValidationError)
    async def _validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        errors = []
        for err in exc.errors():
            errors.append(
                {
                    "field": ".".join(str(p) for p in err.get("loc", []) if p != "body"),
                    "message": err.get("msg", "Invalid value"),
                    "type": err.get("type"),
                }
            )
        return JSONResponse(
            status_code=422,
            content=_envelope("validation_error", "Request validation failed", errors),
        )

    @app.exception_handler(IntegrityError)
    async def _integrity_error(_: Request, exc: IntegrityError) -> JSONResponse:
        logger.warning("Database integrity error: %s", exc)
        return JSONResponse(
            status_code=409,
            content=_envelope("conflict", "The request conflicts with existing data"),
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http_error(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = "http_error"
        if exc.status_code == 404:
            code = "not_found"
        elif exc.status_code == 401:
            code = "unauthorized"
        elif exc.status_code == 403:
            code = "forbidden"
        return JSONResponse(
            status_code=exc.status_code,
            content=_envelope(code, str(exc.detail)),
        )

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled error on %s %s", request.method, request.url.path)
        return JSONResponse(
            status_code=500,
            content=_envelope("internal_error", "An unexpected error occurred"),
        )
