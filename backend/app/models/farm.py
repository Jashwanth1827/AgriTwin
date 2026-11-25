from __future__ import annotations

from datetime import date

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
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


class Farm(Base, TimestampMixin):
    __tablename__ = "farms"
    __table_args__ = (
        CheckConstraint("total_area_hectares > 0", name="ck_farm_area_positive"),
        CheckConstraint("latitude IS NULL OR (latitude >= -90 AND latitude <= 90)", name="ck_farm_lat"),
        CheckConstraint(
            "longitude IS NULL OR (longitude >= -180 AND longitude <= 180)", name="ck_farm_lon"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    village: Mapped[str | None] = mapped_column(String(160))
    district: Mapped[str] = mapped_column(String(120), nullable=False)
    state: Mapped[str] = mapped_column(String(80), nullable=False)
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)
    total_area_hectares: Mapped[float] = mapped_column(Float, nullable=False)
    soil_type: Mapped[str | None] = mapped_column(String(60))
    soil_ph: Mapped[float | None] = mapped_column(Float)
    nitrogen_kg_per_ha: Mapped[float | None] = mapped_column(Float)
    phosphorus_kg_per_ha: Mapped[float | None] = mapped_column(Float)
    potassium_kg_per_ha: Mapped[float | None] = mapped_column(Float)
    soil_moisture_pct: Mapped[float | None] = mapped_column(Float)
    notes: Mapped[str | None] = mapped_column(Text)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    user = relationship("User", back_populates="farms")
    crops = relationship("Crop", back_populates="farm", cascade="all, delete-orphan")
    weather_records = relationship(
        "WeatherRecord", back_populates="farm", cascade="all, delete-orphan"
    )


class Crop(Base, TimestampMixin):
    __tablename__ = "crops"
    __table_args__ = (
        CheckConstraint("area_hectares > 0", name="ck_crop_area_positive"),
        CheckConstraint(
            "expected_harvest_date IS NULL OR expected_harvest_date >= sowing_date",
            name="ck_crop_harvest_after_sowing",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    farm_id: Mapped[int] = mapped_column(
        ForeignKey("farms.id", ondelete="CASCADE"), index=True, nullable=False
    )
    crop_name: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    variety: Mapped[str | None] = mapped_column(String(120))
    season: Mapped[str] = mapped_column(String(40), nullable=False)
    sowing_date: Mapped[date] = mapped_column(Date, nullable=False)
    expected_harvest_date: Mapped[date | None] = mapped_column(Date)
    growth_stage: Mapped[str | None] = mapped_column(String(60))
    area_hectares: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    farm = relationship("Farm", back_populates="crops")
    health_predictions = relationship(
        "CropHealthPrediction", back_populates="crop", cascade="all, delete-orphan"
    )
    yield_predictions = relationship(
        "YieldPrediction", back_populates="crop", cascade="all, delete-orphan"
    )


class UploadedFile(Base, TimestampMixin):
    __tablename__ = "uploaded_files"
    __table_args__ = (UniqueConstraint("sha256", "user_id", name="uq_file_sha_user"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    farm_id: Mapped[int | None] = mapped_column(
        ForeignKey("farms.id", ondelete="SET NULL"), index=True
    )
    crop_id: Mapped[int | None] = mapped_column(
        ForeignKey("crops.id", ondelete="SET NULL"), index=True
    )
    original_name: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_path: Mapped[str] = mapped_column(String(500), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(80), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    width: Mapped[int] = mapped_column(Integer, nullable=False)
    height: Mapped[int] = mapped_column(Integer, nullable=False)
