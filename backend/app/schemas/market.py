from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, Field, field_validator

from app.core.constants import CROPS
from app.schemas.common import ORMModel


class MarketPriceOut(ORMModel):
    id: int
    crop: str
    market: str
    state: str
    district: str
    variety: str
    grade: str
    price_date: date
    min_price: float
    max_price: float
    modal_price: float
    unit: str
    source: str
    is_demo: bool


class PriceSeriesPoint(BaseModel):
    date: date
    min_price: float
    max_price: float
    modal_price: float


class LiveRatePoint(BaseModel):
    date: date
    state: str
    district: str
    market: str
    commodity: str
    commodity_code: str | None = None
    variety: str
    grade: str
    min_price: float
    max_price: float
    modal_price: float
    source: str | None = None
    source_resource_id: str | None = None
    fetched_at: datetime


class LiveSourceInfo(BaseModel):
    resource_id: str
    name: str
    url: str
    record_count: int
    observation_date: date | None = None


class LiveRatesResponse(BaseModel):
    crop: str
    state: str | None
    market: str | None
    unit: str = "INR/quintal"
    provider: str
    source_name: str
    source_url: str
    license: str
    commodity_query: str
    records: list[LiveRatePoint]
    sources: list[LiveSourceInfo] = Field(default_factory=list)
    latest_observation_date: date | None
    data_freshness_days: int | None
    fetched_at: datetime
    is_demo: bool = False
    is_official: bool
    disclaimer: str
    coverage_note: str


class MarketPricesResponse(BaseModel):
    crop: str
    market: str | None
    unit: str = "INR/quintal"
    points: list[PriceSeriesPoint]
    latest_observation_date: date | None
    data_freshness_days: int | None
    source: str | None
    is_demo: bool = False
    available_markets: list[str] = Field(default_factory=list)


class ForecastRequest(BaseModel):
    crop: str
    market: str | None = None
    horizon_days: int = Field(default=14, ge=7, le=60)

    @field_validator("crop")
    @classmethod
    def valid_crop(cls, value: str) -> str:
        if value not in CROPS:
            raise ValueError("Unsupported crop")
        return value


class ForecastPoint(BaseModel):
    date: date
    expected_price: float
    lower_bound: float | None
    upper_bound: float | None


class MarketForecastOut(BaseModel):
    id: int | None = None
    crop: str
    market: str
    state: str | None
    horizon_days: int
    model_name: str
    expected_price: float
    lower_bound: float | None
    upper_bound: float | None
    metrics: dict | None
    points: list[ForecastPoint]
    data_freshness_days: int
    latest_observation_date: date | None
    interval_method: str | None
    is_experimental: bool
    is_demo: bool
    generated_at: datetime
    model_comparison: list[dict] = Field(default_factory=list)
    disclaimer: str


class MarketComparisonRow(BaseModel):
    market: str
    state: str
    latest_date: date
    modal_price: float
    min_price: float
    max_price: float
    observations: int


class MarketTrendsResponse(BaseModel):
    crop: str
    rows: list[MarketComparisonRow]
    best_market: str | None
    average_modal_price: float | None
    unit: str = "INR/quintal"
    is_demo: bool = False


class MarketImportRequest(BaseModel):
    csv_content: str = Field(min_length=10)
    source: str = Field(default="user_csv", max_length=120)


class MarketImportResponse(BaseModel):
    inserted: int
    skipped: int
    errors: list[str]
    source: str
