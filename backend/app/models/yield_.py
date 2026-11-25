from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.common import TimestampMixin


class HistoricalYieldRecord(Base, TimestampMixin):
    __tablename__ = "historical_yield_records"
    __table_args__ = (
        UniqueConstraint(
            "state", "district", "crop", "season", "year", name="uq_hist_yield_scope"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    state: Mapped[str] = mapped_column(String(80), index=True, nullable=False)
    district: Mapped[str] = mapped_column(String(120), index=True, nullable=False)
    crop: Mapped[str] = mapped_column(String(80), index=True, nullable=False)
    season: Mapped[str] = mapped_column(String(40), nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    area_hectares: Mapped[float] = mapped_column(Float, nullable=False)
    production_quintals: Mapped[float] = mapped_column(Float, nullable=False)
    yield_per_hectare: Mapped[float] = mapped_column(Float, nullable=False)
    source: Mapped[str] = mapped_column(String(120), nullable=False)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class YieldPrediction(Base, TimestampMixin):
    __tablename__ = "yield_predictions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    farm_id: Mapped[int] = mapped_column(
        ForeignKey("farms.id", ondelete="CASCADE"), index=True, nullable=False
    )
    crop_id: Mapped[int] = mapped_column(
        ForeignKey("crops.id", ondelete="CASCADE"), index=True, nullable=False
    )
    model_version: Mapped[str] = mapped_column(String(80), nullable=False)
    model_name: Mapped[str] = mapped_column(String(80), nullable=False)
    predicted_yield_per_hectare: Mapped[float] = mapped_column(Float, nullable=False)
    predicted_total_quintals: Mapped[float | None] = mapped_column(Float)
    lower_yield_per_hectare: Mapped[float | None] = mapped_column(Float)
    upper_yield_per_hectare: Mapped[float | None] = mapped_column(Float)
    lower_total_quintals: Mapped[float | None] = mapped_column(Float)
    upper_total_quintals: Mapped[float | None] = mapped_column(Float)
    interval_method: Mapped[str] = mapped_column(String(80), nullable=False)
    interval_coverage: Mapped[float | None] = mapped_column(Float)
    confidence: Mapped[float] = mapped_column(Float, default=0.5, nullable=False)
    input_completeness: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    is_experimental: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    inputs: Mapped[dict] = mapped_column(JSON, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    predicted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    farm = relationship("Farm")
    crop = relationship("Crop", back_populates="yield_predictions")


class WeatherRecord(Base, TimestampMixin):
    __tablename__ = "weather_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    farm_id: Mapped[int] = mapped_column(
        ForeignKey("farms.id", ondelete="CASCADE"), index=True, nullable=False
    )
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    temperature_c: Mapped[float | None] = mapped_column(Float)
    humidity_pct: Mapped[float | None] = mapped_column(Float)
    rainfall_mm: Mapped[float | None] = mapped_column(Float)
    wind_speed_kmh: Mapped[float | None] = mapped_column(Float)
    forecast_days: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    source: Mapped[str] = mapped_column(String(80), default="open-meteo", nullable=False)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    raw: Mapped[dict | None] = mapped_column(JSON)

    farm = relationship("Farm", back_populates="weather_records")
