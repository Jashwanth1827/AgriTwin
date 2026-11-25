from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    JSON,
    DateTime,
    Float,
    ForeignKey,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.common import TimestampMixin


class DecisionResult(Base, TimestampMixin):
    __tablename__ = "decision_results"

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
    action: Mapped[str] = mapped_column(String(20), index=True, nullable=False)
    selected_buyer_id: Mapped[int | None] = mapped_column(
        ForeignKey("buyers.id", ondelete="SET NULL")
    )
    selected_offer_id: Mapped[int | None] = mapped_column(
        ForeignKey("buyer_offers.id", ondelete="SET NULL")
    )
    selected_buyer_name: Mapped[str | None] = mapped_column(String(160))
    expected_yield_quintals: Mapped[float] = mapped_column(Float, nullable=False)
    yield_low_quintals: Mapped[float | None] = mapped_column(Float)
    yield_high_quintals: Mapped[float | None] = mapped_column(Float)
    expected_price_per_quintal: Mapped[float | None] = mapped_column(Float)
    price_low_per_quintal: Mapped[float | None] = mapped_column(Float)
    price_high_per_quintal: Mapped[float | None] = mapped_column(Float)
    gross_revenue: Mapped[float | None] = mapped_column(Float)
    transport_cost: Mapped[float | None] = mapped_column(Float)
    other_costs: Mapped[float | None] = mapped_column(Float)
    net_realization: Mapped[float | None] = mapped_column(Float)
    net_realization_per_quintal: Mapped[float | None] = mapped_column(Float)
    wait_expected_net: Mapped[float | None] = mapped_column(Float)
    risk_score: Mapped[float] = mapped_column(Float, nullable=False)
    risk_category: Mapped[str] = mapped_column(String(20), nullable=False)
    data_completeness: Mapped[float] = mapped_column(Float, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    policy_version: Mapped[str] = mapped_column(String(40), nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    inputs_snapshot: Mapped[dict] = mapped_column(JSON, nullable=False)
    outputs: Mapped[dict] = mapped_column(JSON, nullable=False)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    factors = relationship(
        "DecisionFactor", back_populates="decision", cascade="all, delete-orphan"
    )


class DecisionFactor(Base):
    __tablename__ = "decision_factors"

    id: Mapped[int] = mapped_column(primary_key=True)
    decision_id: Mapped[int] = mapped_column(
        ForeignKey("decision_results.id", ondelete="CASCADE"), index=True, nullable=False
    )
    factor: Mapped[str] = mapped_column(String(80), nullable=False)
    direction: Mapped[str] = mapped_column(String(20), nullable=False)
    weight: Mapped[float | None] = mapped_column(Float)
    value: Mapped[float | None] = mapped_column(Float)
    description: Mapped[str] = mapped_column(Text, nullable=False)

    decision = relationship("DecisionResult", back_populates="factors")
