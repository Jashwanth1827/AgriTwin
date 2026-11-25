"""Version 1 API router."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1 import (
    auth,
    buyers,
    crop_health,
    dashboard,
    decisions,
    farms,
    market,
    system,
    transport,
    weather,
    yield_,
)

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(system.router)
api_router.include_router(farms.router)
api_router.include_router(crop_health.router)
api_router.include_router(yield_.router)
api_router.include_router(market.router)
api_router.include_router(buyers.router)
api_router.include_router(transport.router)
api_router.include_router(weather.router)
api_router.include_router(decisions.router)
api_router.include_router(dashboard.router)

__all__ = ["api_router"]
