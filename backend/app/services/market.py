"""Market price queries, CSV import and forecasting."""

from __future__ import annotations

import io
from datetime import date, datetime, timezone

import pandas as pd
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.constants import CROPS
from app.core.errors import AppError
from app.ml.market_forecasting.forecast import (
    InsufficientMarketData,
    forecast_prices,
)
from app.models.market import MarketForecast, MarketPriceRecord
from app.models.user import User
from app.schemas.market import MarketImportResponse

CROP_ALIASES = {
    "rice": "Rice",
    "wheat": "Wheat",
    "maize": "Maize",
    "corn": "Maize",
    "cotton": "Cotton",
    "cotton(lint)": "Cotton",
    "soyabean": "Soyabean",
    "soybean": "Soyabean",
    "groundnut": "Groundnut",
    "onion": "Onion",
    "tomato": "Tomato",
    "potato": "Potato",
    "sugarcane": "Sugarcane",
    "gram": "Chickpea",
    "chickpea": "Chickpea",
    "mustard": "Mustard",
    "rapeseed &mustard": "Mustard",
    "chilli": "Chilli",
    "green chilli": "Chilli",
    "dry chillies": "Chilli",
    "banana": "Banana",
}

REQUIRED_IMPORT_COLUMNS = {
    "crop",
    "market",
    "state",
    "district",
    "price_date",
    "min_price",
    "max_price",
    "modal_price",
}


def available_crops(db: Session) -> list[dict]:
    rows = db.execute(
        select(
            MarketPriceRecord.crop,
            func.count(func.distinct(MarketPriceRecord.price_date)).label("observations"),
            func.count(func.distinct(MarketPriceRecord.market)).label("markets"),
            func.max(MarketPriceRecord.price_date).label("latest_date"),
        )
        .group_by(MarketPriceRecord.crop)
        .order_by(MarketPriceRecord.crop)
    ).all()
    return [
        {
            "crop": crop,
            "observations": int(observations),
            "markets": int(markets),
            "latest_date": latest_date,
        }
        for crop, observations, markets, latest_date in rows
    ]


def available_markets(db: Session, crop: str) -> list[dict]:
    rows = db.execute(
        select(
            MarketPriceRecord.market,
            MarketPriceRecord.state,
            MarketPriceRecord.district,
            func.count(func.distinct(MarketPriceRecord.price_date)).label("observations"),
            func.max(MarketPriceRecord.price_date).label("latest_date"),
        )
        .where(MarketPriceRecord.crop == crop)
        .group_by(MarketPriceRecord.market, MarketPriceRecord.state, MarketPriceRecord.district)
        .order_by(func.count(func.distinct(MarketPriceRecord.price_date)).desc())
    ).all()
    result = []
    for market, state, district, observations, latest_date in rows:
        latest_price = db.scalar(
            select(MarketPriceRecord.modal_price)
            .where(
                MarketPriceRecord.crop == crop,
                MarketPriceRecord.market == market,
                MarketPriceRecord.price_date == latest_date,
            )
            .limit(1)
        )
        result.append(
            {
                "market": market,
                "state": state,
                "district": district,
                "observations": int(observations),
                "latest_date": latest_date,
                "latest_modal_price": float(latest_price) if latest_price is not None else None,
            }
        )
    return result


def pick_market(
    db: Session,
    crop: str,
    market: str | None = None,
    preferred_state: str | None = None,
) -> str:
    options = available_markets(db, crop)
    if not options:
        raise AppError(f"No market price records are available for {crop}", status_code=404)
    if market:
        names = {row["market"] for row in options}
        if market not in names:
            raise AppError(
                f"Market '{market}' has no records for {crop}",
                status_code=404,
                details={"available_markets": sorted(names)},
            )
        return market
    sufficient = [row for row in options if row["observations"] >= 21]
    candidates = sufficient or options
    if preferred_state:
        local = [row for row in candidates if row["state"] == preferred_state]
        if local:
            return local[0]["market"]
    return candidates[0]["market"]


def price_points(
    db: Session, crop: str, market: str, days: int | None = 180
) -> list[tuple[date, float]]:
    latest = db.scalar(
        select(func.max(MarketPriceRecord.price_date)).where(
            MarketPriceRecord.crop == crop, MarketPriceRecord.market == market
        )
    )
    if latest is None:
        return []
    query = select(
        MarketPriceRecord.price_date,
        func.avg(MarketPriceRecord.modal_price).label("price"),
    ).where(MarketPriceRecord.crop == crop, MarketPriceRecord.market == market)
    if days:
        query = query.where(MarketPriceRecord.price_date >= date.fromordinal(latest.toordinal() - days))
    query = query.group_by(MarketPriceRecord.price_date).order_by(MarketPriceRecord.price_date)
    return [(row[0], float(row[1])) for row in db.execute(query).all()]


def series_payload(
    db: Session, crop: str, market: str | None = None, days: int = 180
) -> dict:
    options = available_markets(db, crop)
    if not options:
        raise AppError(f"No market price records are available for {crop}", status_code=404)
    chosen = pick_market(db, crop, market)
    points = price_points(db, crop, chosen, days)
    latest = points[-1][0] if points else None
    query = select(MarketPriceRecord).where(
        MarketPriceRecord.crop == crop,
        MarketPriceRecord.market == chosen,
    )
    if latest is not None:
        query = query.where(
            MarketPriceRecord.price_date >= date.fromordinal(latest.toordinal() - days)
        )
    rows = db.scalars(query.order_by(MarketPriceRecord.price_date)).all()
    by_date: dict[date, dict] = {}
    for row in rows:
        bucket = by_date.setdefault(
            row.price_date,
            {"date": row.price_date, "min_price": [], "max_price": [], "modal_price": []},
        )
        bucket["min_price"].append(row.min_price)
        bucket["max_price"].append(row.max_price)
        bucket["modal_price"].append(row.modal_price)
    points_out = [
        {
            "date": bucket["date"],
            "min_price": round(sum(bucket["min_price"]) / len(bucket["min_price"]), 2),
            "max_price": round(sum(bucket["max_price"]) / len(bucket["max_price"]), 2),
            "modal_price": round(sum(bucket["modal_price"]) / len(bucket["modal_price"]), 2),
        }
        for bucket in sorted(by_date.values(), key=lambda item: item["date"])
    ]
    source = db.scalar(
        select(MarketPriceRecord.source).where(
            MarketPriceRecord.crop == crop, MarketPriceRecord.market == chosen
        ).limit(1)
    )
    return {
        "crop": crop,
        "market": chosen,
        "unit": "INR/quintal",
        "points": points_out,
        "latest_observation_date": latest,
        "data_freshness_days": (date.today() - latest).days if latest else None,
        "source": source,
        "is_demo": False,
        "available_markets": [row["market"] for row in options],
    }


def latest_market_snapshot(
    db: Session,
    crop: str,
    market: str | None = None,
    preferred_state: str | None = None,
) -> dict | None:
    options = available_markets(db, crop)
    if not options:
        return None
    chosen = market or pick_market(db, crop, market, preferred_state)
    row = db.scalar(
        select(MarketPriceRecord)
        .where(MarketPriceRecord.crop == crop, MarketPriceRecord.market == chosen)
        .order_by(MarketPriceRecord.price_date.desc(), MarketPriceRecord.id.desc())
        .limit(1)
    )
    if row is None:
        return None
    return {
        "market": row.market,
        "state": row.state,
        "latest_price": row.modal_price,
        "min_price": row.min_price,
        "max_price": row.max_price,
        "latest_observation_date": row.price_date,
        "data_freshness_days": (date.today() - row.price_date).days,
        "source": row.source,
    }


def create_forecast(
    db: Session,
    *,
    crop: str,
    market: str | None = None,
    horizon_days: int = 14,
    preferred_state: str | None = None,
) -> MarketForecast:
    chosen = pick_market(db, crop, market, preferred_state)
    points = price_points(db, crop, chosen, days=None)
    try:
        result = forecast_prices(points, horizon_days=horizon_days)
    except InsufficientMarketData as exc:
        raise AppError(
            f"Not enough price history to forecast {crop} at {chosen}: {exc}",
            status_code=422,
            code="insufficient_data",
            details={"observations": len(points), "market": chosen},
        ) from exc

    state = db.scalar(
        select(MarketPriceRecord.state)
        .where(MarketPriceRecord.crop == crop, MarketPriceRecord.market == chosen)
        .limit(1)
    )
    metrics = dict(result.metrics)
    metrics["comparison"] = result.comparison
    forecast = MarketForecast(
        crop=crop,
        market=chosen,
        state=state,
        horizon_days=horizon_days,
        model_name=result.model_name,
        expected_price=result.expected_price,
        lower_bound=result.lower_bound,
        upper_bound=result.upper_bound,
        metrics=metrics,
        points=[
            {
                "date": point["date"].isoformat(),
                "expected_price": point["expected_price"],
                "lower_bound": point["lower_bound"],
                "upper_bound": point["upper_bound"],
            }
            for point in result.points
        ],
        data_freshness_days=(date.today() - result.latest_date).days,
        latest_observation_date=result.latest_date,
        interval_method=result.interval_method,
        is_experimental=True,
        is_demo=False,
        generated_at=datetime.now(timezone.utc),
    )
    db.add(forecast)
    db.commit()
    db.refresh(forecast)
    return forecast


def list_forecasts(db: Session, crop: str | None = None, limit: int = 50) -> list[MarketForecast]:
    query = select(MarketForecast).order_by(MarketForecast.generated_at.desc()).limit(limit)
    if crop:
        query = query.where(MarketForecast.crop == crop)
    return list(db.scalars(query))


def latest_forecast(db: Session, crop: str, market: str | None = None) -> MarketForecast | None:
    query = select(MarketForecast).where(MarketForecast.crop == crop)
    if market:
        query = query.where(MarketForecast.market == market)
    return db.scalar(query.order_by(MarketForecast.generated_at.desc()).limit(1))


def trends(db: Session, crop: str) -> dict:
    rows = list(
        db.scalars(
            select(MarketPriceRecord)
            .where(MarketPriceRecord.crop == crop)
            .order_by(MarketPriceRecord.market, MarketPriceRecord.price_date.desc())
        )
    )
    latest_by_market: dict[str, MarketPriceRecord] = {}
    counts: dict[str, int] = {}
    for row in rows:
        counts[row.market] = counts.get(row.market, 0) + 1
        if row.market not in latest_by_market:
            latest_by_market[row.market] = row
    output = [
        {
            "market": row.market,
            "state": row.state,
            "latest_date": row.price_date,
            "modal_price": row.modal_price,
            "min_price": row.min_price,
            "max_price": row.max_price,
            "observations": counts[row.market],
        }
        for row in latest_by_market.values()
    ]
    output.sort(key=lambda item: item["modal_price"], reverse=True)
    return {
        "crop": crop,
        "rows": output,
        "best_market": output[0]["market"] if output else None,
        "average_modal_price": (
            round(sum(item["modal_price"] for item in output) / len(output), 2)
            if output
            else None
        ),
        "unit": "INR/quintal",
        "is_demo": False,
    }


def import_csv(
    db: Session, user: User, csv_content: str, source: str
) -> MarketImportResponse:
    try:
        frame = pd.read_csv(io.StringIO(csv_content))
    except Exception as exc:
        raise AppError(f"Could not parse CSV: {exc}", status_code=422) from exc
    missing = REQUIRED_IMPORT_COLUMNS - set(frame.columns)
    if missing:
        raise AppError(
            f"CSV is missing required columns: {', '.join(sorted(missing))}",
            status_code=422,
        )

    inserted = 0
    skipped = 0
    errors: list[str] = []
    for index, row in frame.iterrows():
        crop_raw = str(row.get("crop", "")).strip().lower()
        crop = CROP_ALIASES.get(crop_raw)
        if crop is None and str(row.get("crop", "")).strip() in CROPS:
            crop = str(row["crop"]).strip()
        if crop is None:
            errors.append(f"Row {index + 2}: unsupported crop '{row.get('crop')}'")
            skipped += 1
            continue
        try:
            raw_date = str(row["price_date"]).strip()
            # ISO dates (2026-07-02) must be parsed before day-first dates
            # (02/07/2026); dayfirst=True alone turns ISO dates into February.
            price_date = pd.to_datetime(raw_date, format="ISO8601").date() if "-" in raw_date else pd.to_datetime(
                raw_date, dayfirst=True
            ).date()
            min_price = float(row["min_price"])
            max_price = float(row["max_price"])
            modal_price = float(row["modal_price"])
        except Exception as exc:
            errors.append(f"Row {index + 2}: invalid date or price ({exc})")
            skipped += 1
            continue
        if not (min_price > 0 and max_price >= min_price and min_price <= modal_price <= max_price):
            errors.append(f"Row {index + 2}: prices are inconsistent")
            skipped += 1
            continue
        market = str(row["market"]).strip()
        existing = db.scalar(
            select(MarketPriceRecord).where(
                MarketPriceRecord.crop == crop,
                MarketPriceRecord.market == market,
                MarketPriceRecord.variety == str(row.get("variety") or "Other").strip(),
                MarketPriceRecord.price_date == price_date,
                MarketPriceRecord.source == source,
            )
        )
        if existing is not None:
            skipped += 1
            continue
        db.add(
            MarketPriceRecord(
                crop=crop,
                market=market,
                state=str(row["state"]).strip(),
                district=str(row["district"]).strip(),
                variety=str(row.get("variety") or "Other").strip() or "Other",
                grade=str(row.get("grade") or "FAQ").strip() or "FAQ",
                price_date=price_date,
                min_price=min_price,
                max_price=max_price,
                modal_price=modal_price,
                unit=str(row.get("unit") or "INR/quintal").strip() or "INR/quintal",
                source=source,
                is_demo=False,
            )
        )
        inserted += 1
    db.commit()
    return MarketImportResponse(
        inserted=inserted, skipped=skipped, errors=errors[:50], source=source
    )
