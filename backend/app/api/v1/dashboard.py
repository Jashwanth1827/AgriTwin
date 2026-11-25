"""Dashboard routes."""

from __future__ import annotations

from fastapi import APIRouter, Query

from app.api.deps import CurrentUser, DbSession
from app.schemas.dashboard import (
    DashboardCropHealth,
    DashboardDecisions,
    DashboardMarket,
    DashboardOverview,
)
from app.services import dashboard as dashboard_service

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/overview", response_model=DashboardOverview)
def overview(user: CurrentUser, db: DbSession) -> DashboardOverview:
    return DashboardOverview(**dashboard_service.overview(db, user))


@router.get("/crop-health", response_model=DashboardCropHealth)
def crop_health(user: CurrentUser, db: DbSession) -> DashboardCropHealth:
    return DashboardCropHealth(**dashboard_service.crop_health_summary(db, user))


@router.get("/market", response_model=DashboardMarket)
def market(
    user: CurrentUser,
    db: DbSession,
    crop: str | None = Query(default=None),
) -> DashboardMarket:
    return DashboardMarket(**dashboard_service.market_summary(db, user, crop))


@router.get("/decisions", response_model=DashboardDecisions)
def decisions(user: CurrentUser, db: DbSession) -> DashboardDecisions:
    return DashboardDecisions(**dashboard_service.decisions_summary(db, user))
