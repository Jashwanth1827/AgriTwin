"""Transportation estimation routes."""

from __future__ import annotations

from fastapi import APIRouter, Query, status

from app.api.deps import CurrentUser, DbSession
from app.schemas.transport import TransportEstimateOut, TransportEstimateRequest
from app.services import transport as transport_service

router = APIRouter(prefix="/transport", tags=["transport"])


@router.get("/vehicles")
def vehicles() -> dict:
    return {
        "vehicles": transport_service.vehicle_options(),
        "notes": (
            "Costs are configurable planning defaults, not freight quotes. "
            "OSRM road distance is used when available."
        ),
    }


@router.post(
    "/estimate", response_model=TransportEstimateOut, status_code=status.HTTP_201_CREATED
)
def estimate(
    payload: TransportEstimateRequest, user: CurrentUser, db: DbSession
) -> TransportEstimateOut:
    return TransportEstimateOut.model_validate(
        transport_service.estimate(db, user, payload)
    )


@router.get("/estimates", response_model=list[TransportEstimateOut])
def list_estimates(
    user: CurrentUser,
    db: DbSession,
    farm_id: int | None = Query(default=None),
) -> list[TransportEstimateOut]:
    return [
        TransportEstimateOut.model_validate(row)
        for row in transport_service.list_estimates(db, user, farm_id)
    ]
