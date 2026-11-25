"""Decision engine routes."""

from __future__ import annotations

from fastapi import APIRouter, Query, status

from app.api.deps import CurrentUser, DbSession
from app.schemas.common import Message
from app.schemas.decision import DecisionListItem, DecisionOut, DecisionRequest
from app.services import decision_service
from app.services.decision.policy import get_policy

router = APIRouter(prefix="/decisions", tags=["decisions"])


@router.get("/policy")
def policy(_user: CurrentUser) -> dict:
    payload = get_policy()
    return {
        "version": payload.version,
        "finance": payload.finance.model_dump(),
        "risk": payload.risk.model_dump(),
        "policy": payload.policy.model_dump(),
        "freshness": payload.freshness.model_dump(),
        "notes": (
            "Deterministic ordered rules. INSPECT is evaluated first, then WAIT, then SELL. "
            "All money uses Decimal half-up rounding."
        ),
    }


@router.post("", response_model=DecisionOut, status_code=status.HTTP_201_CREATED)
def create_decision(
    payload: DecisionRequest, user: CurrentUser, db: DbSession
) -> DecisionOut:
    _row, output = decision_service.run(db, user, payload)
    return output


@router.get("", response_model=list[DecisionListItem])
def list_decisions(
    user: CurrentUser,
    db: DbSession,
    farm_id: int | None = Query(default=None),
    crop_id: int | None = Query(default=None),
    action: str | None = Query(default=None),
) -> list[DecisionListItem]:
    rows = decision_service.list_decisions(
        db, user, farm_id=farm_id, crop_id=crop_id, action=action
    )
    return [
        DecisionListItem(
            id=row.id,
            action=row.action,
            farm_id=row.farm_id,
            crop_id=row.crop_id,
            selected_buyer_name=row.selected_buyer_name,
            net_realization=row.net_realization,
            risk_score=row.risk_score,
            risk_category=row.risk_category,
            generated_at=row.generated_at,
        )
        for row in rows
    ]


@router.get("/{decision_id}", response_model=DecisionOut)
def get_decision(decision_id: int, user: CurrentUser, db: DbSession) -> DecisionOut:
    return decision_service.to_schema(
        decision_service.get_decision(db, user, decision_id)
    )


@router.delete("/{decision_id}", response_model=Message)
def delete_decision(decision_id: int, user: CurrentUser, db: DbSession) -> Message:
    row = decision_service.get_decision(db, user, decision_id)
    decision_service.delete_decision(db, row)
    return Message(message="Decision deleted")
