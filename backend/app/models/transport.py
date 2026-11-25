from __future__ import annotations

from sqlalchemy import Boolean, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.common import TimestampMixin


class TransportationEstimate(Base, TimestampMixin):
    __tablename__ = "transportation_estimates"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    farm_id: Mapped[int] = mapped_column(
        ForeignKey("farms.id", ondelete="CASCADE"), index=True, nullable=False
    )
    buyer_id: Mapped[int | None] = mapped_column(
        ForeignKey("buyers.id", ondelete="SET NULL"), index=True
    )
    crop_id: Mapped[int | None] = mapped_column(ForeignKey("crops.id", ondelete="SET NULL"))
    quantity_quintals: Mapped[float] = mapped_column(Float, nullable=False)
    transport_mode: Mapped[str] = mapped_column(String(30), default="road", nullable=False)
    vehicle_type: Mapped[str] = mapped_column(String(40), nullable=False)
    vehicle_capacity_quintals: Mapped[float] = mapped_column(Float, nullable=False)
    trips: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    distance_km: Mapped[float] = mapped_column(Float, nullable=False)
    distance_method: Mapped[str] = mapped_column(String(60), nullable=False)
    cost_per_km: Mapped[float] = mapped_column(Float, nullable=False)
    fixed_cost: Mapped[float] = mapped_column(Float, nullable=False)
    loading_cost: Mapped[float] = mapped_column(Float, nullable=False)
    unloading_cost: Mapped[float] = mapped_column(Float, nullable=False)
    total_cost: Mapped[float] = mapped_column(Float, nullable=False)
    cost_per_quintal: Mapped[float] = mapped_column(Float, nullable=False)
    cost_per_kg: Mapped[float] = mapped_column(Float, nullable=False)
    is_approximate: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    provider: Mapped[str] = mapped_column(String(60), default="osrm", nullable=False)
    notes: Mapped[str | None] = mapped_column(String(500))
