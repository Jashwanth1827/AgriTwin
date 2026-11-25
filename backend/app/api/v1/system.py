"""System metadata, model status, notifications and reports."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, status
from sqlalchemy import select

from app.api.deps import CurrentUser, DbSession
from app.core.config import settings
from app.core.constants import (
    BUYER_TYPES,
    CROPS,
    GROWTH_STAGES,
    INDIAN_STATES,
    RISK_PREFERENCES,
    SEASONS,
    SOIL_TYPES,
    TRANSPORT_MODES,
    UNITS,
    VEHICLE_TYPES,
)
from app.core.errors import NotFoundError
from app.models.user import Notification
from app.schemas.common import Message
from app.schemas.system import (
    HealthResponse,
    ModelStatus,
    NotificationOut,
    ReportOut,
    ReportRequest,
    SystemStatus,
)
from app.services import crop_health as health_service
from app.services import market as market_service
from app.services import reports as report_service
from app.services import yield_service

router = APIRouter(prefix="/system", tags=["system"])


@router.get("/health", response_model=HealthResponse)
def health(db: DbSession) -> HealthResponse:
    from sqlalchemy import text

    try:
        db.execute(text("SELECT 1"))
        database = "ok"
    except Exception:
        database = "unavailable"
    return HealthResponse(
        status="ok" if database == "ok" else "degraded",
        app=settings.APP_NAME,
        version=settings.APP_VERSION,
        environment=settings.ENVIRONMENT,
        demo_mode=settings.DEMO_MODE,
        database=database,
    )


@router.get("/status", response_model=SystemStatus)
def system_status(db: DbSession) -> SystemStatus:
    health_info = health_service.model_info()
    yield_info = yield_service.model_info()
    crops = market_service.available_crops(db)
    latest_market_date = max((row["latest_date"] for row in crops), default=None)
    notices: list[str] = []
    if health_info.get("mode") == "demo":
        notices.append(
            "Crop-health weights are not installed; uploads use a clearly labelled demo heuristic."
        )
    if latest_market_date is not None:
        age = (datetime.now(timezone.utc).date() - latest_market_date).days
        if age > 90:
            notices.append(
                f"The bundled Agmarknet market slice is {age} days old. Forecasts are "
                "short-horizon and flagged with data-freshness risk."
            )
    if not yield_info.get("available"):
        notices.append("The yield model artifact is missing; yield predictions are unavailable.")
    notices.append(
        "Transport costs are configurable planning assumptions, not freight quotes."
    )
    return SystemStatus(
        app=settings.APP_NAME,
        version=settings.APP_VERSION,
        environment=settings.ENVIRONMENT,
        demo_mode=settings.DEMO_MODE,
        data_mode="real",
        database_backend="sqlite" if settings.is_sqlite else "postgresql",
        models=[
            ModelStatus(
                name="crop_health",
                available=bool(health_info.get("available")),
                mode=health_info.get("mode", "unavailable"),
                version=health_info.get("model_version"),
                message=health_info.get("message"),
            ),
            ModelStatus(
                name="yield_prediction",
                available=bool(yield_info.get("available")),
                mode="real" if yield_info.get("available") else "unavailable",
                version=yield_info.get("model_version"),
                message=yield_info.get("message"),
            ),
            ModelStatus(
                name="market_forecasting",
                available=bool(crops),
                mode="on_demand",
                version="1.0.0",
                message=(
                    "Forecasts are fitted per crop/market series at request time and "
                    "validated chronologically."
                    if crops
                    else "No market observations are loaded."
                ),
            ),
        ],
        providers={
            "weather": {"name": "open-meteo", "configured": settings.WEATHER_PROVIDER != "disabled", "requires_key": False},
            "geocoding": {"name": "open-meteo", "configured": settings.GEOCODING_PROVIDER != "disabled", "requires_key": False},
            "routing": {"name": settings.ROUTING_PROVIDER, "configured": True, "requires_key": False},
        },
        notices=notices,
        server_time=datetime.now(timezone.utc),
    )


@router.get("/options")
def options() -> dict:
    return {
        "crops": CROPS,
        "states": INDIAN_STATES,
        "seasons": SEASONS,
        "growth_stages": GROWTH_STAGES,
        "soil_types": SOIL_TYPES,
        "buyer_types": BUYER_TYPES,
        "vehicle_types": VEHICLE_TYPES,
        "transport_modes": TRANSPORT_MODES,
        "risk_preferences": RISK_PREFERENCES,
        "units": UNITS,
        "demo_mode": settings.DEMO_MODE,
    }


@router.get("/notifications", response_model=list[NotificationOut])
def notifications(user: CurrentUser, db: DbSession) -> list[NotificationOut]:
    rows = db.scalars(
        select(Notification)
        .where(Notification.user_id == user.id)
        .order_by(Notification.created_at.desc())
        .limit(100)
    )
    return [NotificationOut.model_validate(row) for row in rows]


@router.post("/notifications/{notification_id}/read", response_model=NotificationOut)
def mark_read(notification_id: int, user: CurrentUser, db: DbSession) -> NotificationOut:
    row = db.get(Notification, notification_id)
    if row is None or row.user_id != user.id:
        raise NotFoundError("Notification not found")
    row.is_read = True
    db.commit()
    db.refresh(row)
    return NotificationOut.model_validate(row)


@router.post("/notifications/read-all", response_model=Message)
def mark_all_read(user: CurrentUser, db: DbSession) -> Message:
    rows = db.scalars(
        select(Notification).where(
            Notification.user_id == user.id, Notification.is_read.is_(False)
        )
    )
    count = 0
    for row in rows:
        row.is_read = True
        count += 1
    db.commit()
    return Message(message=f"{count} notification(s) marked as read")


@router.get("/reports", response_model=list[ReportOut])
def list_reports(user: CurrentUser, db: DbSession) -> list[ReportOut]:
    return [ReportOut.model_validate(row) for row in report_service.list_reports(db, user)]


@router.post("/reports", response_model=ReportOut, status_code=status.HTTP_201_CREATED)
def create_report(
    payload: ReportRequest, user: CurrentUser, db: DbSession
) -> ReportOut:
    return ReportOut.model_validate(report_service.generate(db, user, payload))


@router.get("/reports/{report_id}", response_model=ReportOut)
def get_report(report_id: int, user: CurrentUser, db: DbSession) -> ReportOut:
    return ReportOut.model_validate(report_service.get_report(db, user, report_id))


@router.delete("/reports/{report_id}", response_model=Message)
def delete_report(report_id: int, user: CurrentUser, db: DbSession) -> Message:
    row = report_service.get_report(db, user, report_id)
    report_service.delete_report(db, row)
    return Message(message="Report deleted")
