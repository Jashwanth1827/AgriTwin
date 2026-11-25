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


class ModelVersion(Base, TimestampMixin):
    __tablename__ = "model_versions"
    __table_args__ = (UniqueConstraint("model_type", "version", name="uq_model_type_version"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    model_type: Mapped[str] = mapped_column(String(40), index=True, nullable=False)
    version: Mapped[str] = mapped_column(String(80), nullable=False)
    artifact_path: Mapped[str | None] = mapped_column(String(500))
    dataset_provenance: Mapped[str | None] = mapped_column(Text)
    metrics: Mapped[dict | None] = mapped_column(JSON)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class DiseaseClass(Base, TimestampMixin):
    __tablename__ = "disease_classes"
    __table_args__ = (UniqueConstraint("crop", "name", name="uq_disease_crop_name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    crop: Mapped[str] = mapped_column(String(80), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    is_healthy: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    severity: Mapped[str | None] = mapped_column(String(20))
    inspection_steps: Mapped[list | None] = mapped_column(JSON)
    preventive_practices: Mapped[list | None] = mapped_column(JSON)
    expert_advice: Mapped[str | None] = mapped_column(Text)


class CropHealthPrediction(Base, TimestampMixin):
    __tablename__ = "crop_health_predictions"

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
    file_id: Mapped[int | None] = mapped_column(ForeignKey("uploaded_files.id", ondelete="SET NULL"))
    model_version_id: Mapped[int | None] = mapped_column(
        ForeignKey("model_versions.id", ondelete="SET NULL")
    )
    predicted_label: Mapped[str] = mapped_column(String(200), nullable=False)
    predicted_crop: Mapped[str] = mapped_column(String(80), nullable=False)
    is_healthy: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    severity: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    probabilities: Mapped[dict] = mapped_column(JSON, nullable=False)
    gradcam_path: Mapped[str | None] = mapped_column(String(500))
    inference_ms: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    model_version: Mapped[str] = mapped_column(String(80), nullable=False)
    model_mode: Mapped[str] = mapped_column(String(20), default="real", nullable=False)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    predicted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    farm = relationship("Farm")
    crop = relationship("Crop", back_populates="health_predictions")
    file = relationship("UploadedFile")
    model_version_ref = relationship("ModelVersion")
    recommendations = relationship(
        "Recommendation", back_populates="prediction", cascade="all, delete-orphan"
    )


class Recommendation(Base, TimestampMixin):
    __tablename__ = "recommendations"

    id: Mapped[int] = mapped_column(primary_key=True)
    prediction_id: Mapped[int] = mapped_column(
        ForeignKey("crop_health_predictions.id", ondelete="CASCADE"), index=True, nullable=False
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(40), default="general", nullable=False)
    source: Mapped[str] = mapped_column(String(120), default="agritwin_rules", nullable=False)

    prediction = relationship("CropHealthPrediction", back_populates="recommendations")
