from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class HealthResponse(BaseModel):
    status: str
    app: str
    version: str
    environment: str
    demo_mode: bool
    database: str


class ModelStatus(BaseModel):
    name: str
    available: bool
    mode: str
    version: str | None = None
    message: str | None = None


class SystemStatus(BaseModel):
    app: str
    version: str
    environment: str
    demo_mode: bool
    data_mode: str
    database_backend: str
    models: list[ModelStatus]
    providers: dict
    notices: list[str] = Field(default_factory=list)
    server_time: datetime


class NotificationOut(ORMModel):
    id: int
    title: str
    message: str
    category: str
    is_read: bool
    created_at: datetime


class ReportOut(ORMModel):
    id: int
    report_type: str
    title: str
    summary: str | None
    payload: dict
    created_at: datetime


class ReportRequest(BaseModel):
    farm_id: int | None = None
    crop_id: int | None = None
