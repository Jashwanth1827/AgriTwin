from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    Float,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.common import TimestampMixin


class MarketPriceRecord(Base, TimestampMixin):
    __tablename__ = "market_price_records"
    __table_args__ = (
        UniqueConstraint(
            "crop", "market", "variety", "price_date", "source", name="uq_market_price_point"
        ),
        Index("ix_market_price_crop_date", "crop", "price_date"),
        Index("ix_market_price_market_date", "market", "price_date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    crop: Mapped[str] = mapped_column(String(80), nullable=False)
    market: Mapped[str] = mapped_column(String(160), nullable=False)
    state: Mapped[str] = mapped_column(String(80), nullable=False)
    district: Mapped[str] = mapped_column(String(120), nullable=False)
    variety: Mapped[str] = mapped_column(String(120), default="Other", nullable=False)
    grade: Mapped[str] = mapped_column(String(60), default="FAQ", nullable=False)
    price_date: Mapped[date] = mapped_column(Date, nullable=False)
    min_price: Mapped[float] = mapped_column(Float, nullable=False)
    max_price: Mapped[float] = mapped_column(Float, nullable=False)
    modal_price: Mapped[float] = mapped_column(Float, nullable=False)
    unit: Mapped[str] = mapped_column(String(40), default="INR/quintal", nullable=False)
    source: Mapped[str] = mapped_column(String(120), nullable=False)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class MarketForecast(Base, TimestampMixin):
    __tablename__ = "market_forecasts"

    id: Mapped[int] = mapped_column(primary_key=True)
    crop: Mapped[str] = mapped_column(String(80), index=True, nullable=False)
    market: Mapped[str] = mapped_column(String(160), index=True, nullable=False)
    state: Mapped[str | None] = mapped_column(String(80))
    horizon_days: Mapped[int] = mapped_column(Integer, nullable=False)
    model_name: Mapped[str] = mapped_column(String(80), nullable=False)
    expected_price: Mapped[float] = mapped_column(Float, nullable=False)
    lower_bound: Mapped[float | None] = mapped_column(Float)
    upper_bound: Mapped[float | None] = mapped_column(Float)
    metrics: Mapped[dict | None] = mapped_column(JSON)
    points: Mapped[list | None] = mapped_column(JSON)
    data_freshness_days: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    latest_observation_date: Mapped[date | None] = mapped_column(Date)
    interval_method: Mapped[str | None] = mapped_column(String(120))
    is_experimental: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
