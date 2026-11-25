from __future__ import annotations

from datetime import date

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    Float,
    ForeignKey,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.common import TimestampMixin


class Buyer(Base, TimestampMixin):
    __tablename__ = "buyers"
    __table_args__ = (
        CheckConstraint("latitude IS NULL OR (latitude >= -90 AND latitude <= 90)", name="ck_buyer_lat"),
        CheckConstraint(
            "longitude IS NULL OR (longitude >= -180 AND longitude <= 180)", name="ck_buyer_lon"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    buyer_type: Mapped[str] = mapped_column(String(60), nullable=False)
    contact_name: Mapped[str | None] = mapped_column(String(120))
    contact_phone: Mapped[str | None] = mapped_column(String(30))
    market_name: Mapped[str | None] = mapped_column(String(160))
    district: Mapped[str] = mapped_column(String(120), nullable=False)
    state: Mapped[str] = mapped_column(String(80), nullable=False)
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)
    notes: Mapped[str | None] = mapped_column(Text)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    user = relationship("User", back_populates="buyers")
    offers = relationship("BuyerOffer", back_populates="buyer", cascade="all, delete-orphan")


class BuyerOffer(Base, TimestampMixin):
    __tablename__ = "buyer_offers"
    __table_args__ = (
        CheckConstraint("offered_price_per_quintal > 0", name="ck_offer_price_positive"),
        CheckConstraint("min_quantity_quintals > 0", name="ck_offer_min_qty_positive"),
        CheckConstraint(
            "max_quantity_quintals IS NULL OR max_quantity_quintals >= min_quantity_quintals",
            name="ck_offer_max_gte_min",
        ),
        CheckConstraint("expiry_date >= offer_date", name="ck_offer_expiry_after_offer"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    buyer_id: Mapped[int] = mapped_column(
        ForeignKey("buyers.id", ondelete="CASCADE"), index=True, nullable=False
    )
    crop: Mapped[str] = mapped_column(String(80), index=True, nullable=False)
    variety: Mapped[str | None] = mapped_column(String(120))
    offered_price_per_quintal: Mapped[float] = mapped_column(Float, nullable=False)
    min_quantity_quintals: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    max_quantity_quintals: Mapped[float | None] = mapped_column(Float)
    offer_date: Mapped[date] = mapped_column(Date, nullable=False)
    expiry_date: Mapped[date] = mapped_column(Date, nullable=False)
    conditions: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    buyer = relationship("Buyer", back_populates="offers")
