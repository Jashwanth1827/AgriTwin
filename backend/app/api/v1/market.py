"""Market price, comparison, forecast and import routes."""

from __future__ import annotations

from fastapi import APIRouter, Query, status

from app.api.deps import CurrentUser, DbSession
from app.core.errors import NotFoundError
from app.models.market import MarketForecast
from app.schemas.market import (
    ForecastRequest,
    LiveRatesResponse,
    MarketForecastOut,
    MarketImportRequest,
    MarketImportResponse,
    MarketPricesResponse,
    MarketTrendsResponse,
)
from app.services import live_market as live_market_service
from app.services import market as market_service

router = APIRouter(prefix="/market", tags=["market"])

FORECAST_DISCLAIMER = (
    "Experimental short-horizon forecast trained on a limited public Agmarknet "
    "window. Bounds are empirical residual intervals, not guarantees. Prices are "
    "INR per quintal."
)


def _forecast_out(forecast: MarketForecast) -> MarketForecastOut:
    metrics = forecast.metrics or {}
    return MarketForecastOut(
        id=forecast.id,
        crop=forecast.crop,
        market=forecast.market,
        state=forecast.state,
        horizon_days=forecast.horizon_days,
        model_name=forecast.model_name,
        expected_price=forecast.expected_price,
        lower_bound=forecast.lower_bound,
        upper_bound=forecast.upper_bound,
        metrics=metrics,
        points=forecast.points or [],
        data_freshness_days=forecast.data_freshness_days,
        latest_observation_date=forecast.latest_observation_date,
        interval_method=forecast.interval_method,
        is_experimental=forecast.is_experimental,
        is_demo=forecast.is_demo,
        generated_at=forecast.generated_at,
        model_comparison=metrics.get("comparison", []),
        disclaimer=FORECAST_DISCLAIMER,
    )


@router.get("/crops")
def crops(db: DbSession, _user: CurrentUser) -> dict:
    return {"crops": market_service.available_crops(db), "unit": "INR/quintal"}


@router.get("/prices", response_model=MarketPricesResponse)
def prices(
    _user: CurrentUser,
    db: DbSession,
    crop: str = Query(...),
    market: str | None = Query(default=None),
    days: int = Query(default=180, ge=7, le=3650),
) -> MarketPricesResponse:
    return MarketPricesResponse(**market_service.series_payload(db, crop, market, days))


@router.get("/live-rates", response_model=LiveRatesResponse)
def live_rates(
    _user: CurrentUser,
    crop: str = Query(...),
    state: str | None = Query(default=None),
    market: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    refresh: bool = Query(default=False),
) -> LiveRatesResponse:
    """Current wholesale mandi rates from a real public government feed."""
    return LiveRatesResponse(
        **live_market_service.fetch_live_rates(
            crop=crop,
            state=state,
            market=market,
            limit=limit,
            force_refresh=refresh,
        )
    )


@router.get("/markets")
def markets(_user: CurrentUser, db: DbSession, crop: str = Query(...)) -> dict:
    return {
        "crop": crop,
        "markets": market_service.available_markets(db, crop),
        "unit": "INR/quintal",
    }


@router.get("/trends", response_model=MarketTrendsResponse)
def trends(_user: CurrentUser, db: DbSession, crop: str = Query(...)) -> MarketTrendsResponse:
    return MarketTrendsResponse(**market_service.trends(db, crop))


@router.post(
    "/forecast", response_model=MarketForecastOut, status_code=status.HTTP_201_CREATED
)
def create_forecast(
    payload: ForecastRequest, _user: CurrentUser, db: DbSession
) -> MarketForecastOut:
    forecast = market_service.create_forecast(
        db, crop=payload.crop, market=payload.market, horizon_days=payload.horizon_days
    )
    return _forecast_out(forecast)


@router.get("/forecasts", response_model=list[MarketForecastOut])
def list_forecasts(
    _user: CurrentUser,
    db: DbSession,
    crop: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
) -> list[MarketForecastOut]:
    return [_forecast_out(row) for row in market_service.list_forecasts(db, crop, limit)]


@router.get("/forecasts/{forecast_id}", response_model=MarketForecastOut)
def get_forecast(forecast_id: int, _user: CurrentUser, db: DbSession) -> MarketForecastOut:
    forecast = db.get(MarketForecast, forecast_id)
    if forecast is None:
        raise NotFoundError("Forecast not found")
    return _forecast_out(forecast)


@router.post("/import", response_model=MarketImportResponse)
def import_prices(
    payload: MarketImportRequest, user: CurrentUser, db: DbSession
) -> MarketImportResponse:
    return market_service.import_csv(db, user, payload.csv_content, payload.source)
