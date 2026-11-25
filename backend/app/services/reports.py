"""Report generation from persisted farm, model and decision data."""

from __future__ import annotations

from datetime import date, datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import NotFoundError
from app.models.decision import DecisionResult
from app.models.farm import Crop, Farm
from app.models.report import Report
from app.models.user import User
from app.schemas.system import ReportRequest
from app.services import crop_health as health_service
from app.services import market as market_service
from app.services import yield_service


def list_reports(db: Session, user: User) -> list[Report]:
    return list(
        db.scalars(
            select(Report).where(Report.user_id == user.id).order_by(Report.created_at.desc())
        )
    )


def get_report(db: Session, user: User, report_id: int) -> Report:
    report = db.get(Report, report_id)
    if report is None or report.user_id != user.id:
        raise NotFoundError("Report not found")
    return report


def _jsonable(value):
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, dict):
        return {key: _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return value


def generate(db: Session, user: User, payload: ReportRequest) -> Report:
    farm: Farm | None = None
    if payload.farm_id is not None:
        farm = db.get(Farm, payload.farm_id)
        if farm is None or farm.user_id != user.id:
            raise NotFoundError("Farm not found")

    if farm is not None:
        crops = list(farm.crops)
    else:
        crops = list(
            db.scalars(
                select(Crop).join(Farm, Crop.farm_id == Farm.id).where(Farm.user_id == user.id)
            )
        )
    if payload.crop_id is not None:
        crops = [crop for crop in crops if crop.id == payload.crop_id]
        if not crops:
            raise NotFoundError("Crop not found")

    crop_sections = []
    for crop in crops:
        health = health_service.latest_for_crop(db, user, crop.id)
        yield_row = yield_service.latest_for_crop(db, user, crop.id)
        decision = db.scalar(
            select(DecisionResult)
            .where(DecisionResult.user_id == user.id, DecisionResult.crop_id == crop.id)
            .order_by(DecisionResult.generated_at.desc())
            .limit(1)
        )
        crop_sections.append(
            {
                "crop": {
                    "id": crop.id,
                    "name": crop.crop_name,
                    "variety": crop.variety,
                    "season": crop.season,
                    "area_hectares": crop.area_hectares,
                    "sowing_date": crop.sowing_date,
                    "expected_harvest_date": crop.expected_harvest_date,
                    "status": crop.status,
                },
                "harvest_readiness": yield_service.readiness_for_crop(crop),
                "crop_health": {
                    "available": health is not None,
                    "label": health.predicted_label if health else None,
                    "confidence": health.confidence if health else None,
                    "is_demo": health.is_demo if health else None,
                    "predicted_at": health.predicted_at if health else None,
                },
                "yield": {
                    "available": yield_row is not None,
                    "predicted_yield_per_hectare": yield_row.predicted_yield_per_hectare if yield_row else None,
                    "predicted_total_quintals": yield_row.predicted_total_quintals if yield_row else None,
                    "lower_total_quintals": yield_row.lower_total_quintals if yield_row else None,
                    "upper_total_quintals": yield_row.upper_total_quintals if yield_row else None,
                    "model_name": yield_row.model_name if yield_row else None,
                    "interval_method": yield_row.interval_method if yield_row else None,
                },
                "decision": {
                    "available": decision is not None,
                    "action": decision.action if decision else None,
                    "selected_buyer_name": decision.selected_buyer_name if decision else None,
                    "net_realization": decision.net_realization if decision else None,
                    "risk_score": decision.risk_score if decision else None,
                    "risk_category": decision.risk_category if decision else None,
                    "explanation": decision.explanation if decision else None,
                },
            }
        )

    market_sections = []
    for crop in crops:
        snapshot = market_service.latest_market_snapshot(db, crop.crop_name)
        if snapshot:
            market_sections.append({"crop": crop.crop_name, **snapshot})

    title = f"Farm advisory report — {farm.name}" if farm else "AgriTwin advisory report"
    payload_dict = _jsonable(
        {
            "generated_at": datetime.now(timezone.utc),
            "farm": {
                "id": farm.id,
                "name": farm.name,
                "district": farm.district,
                "state": farm.state,
                "total_area_hectares": farm.total_area_hectares,
            }
            if farm
            else None,
            "crops": crop_sections,
            "market": market_sections,
            "disclaimer": (
                "This report combines experimental ML predictions, public market data and "
                "configurable cost assumptions. It is decision support, not a guarantee of "
                "yield, price or profit. Confirm agronomic and commercial decisions locally."
            ),
        }
    )
    summary = (
        f"{len(crop_sections)} crop(s) across "
        f"{farm.total_area_hectares:g} ha in {farm.district}, {farm.state}."
        if farm
        else f"{len(crop_sections)} crop(s) across all farms."
    )
    report = Report(
        user_id=user.id,
        report_type="farm_advisory" if farm else "portfolio_advisory",
        title=title,
        summary=summary,
        payload=payload_dict,
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return report


def delete_report(db: Session, report: Report) -> None:
    db.delete(report)
    db.commit()
