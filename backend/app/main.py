"""FastAPI application entrypoint."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.v1 import api_router
from app.core.config import settings
from app.core.database import Base, SessionLocal, engine
from app.core.errors import register_exception_handlers
from app.core.logging import RequestContextMiddleware, configure_logging
from app.core.rate_limit import RateLimitMiddleware

# Importing models registers every table on Base.metadata.
from app import models  # noqa: F401
from app.db.seed import seed

configure_logging(settings.LOG_LEVEL)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    (settings.UPLOAD_DIR / "gradcam").mkdir(parents=True, exist_ok=True)
    if settings.ENVIRONMENT != "production":
        Base.metadata.create_all(bind=engine)
    if settings.DEMO_MODE:
        with SessionLocal() as db:
            try:
                seed(db)
            except Exception:
                db.rollback()
                logger.exception("Demo seed failed")
    logger.info("AgriTwin %s started (%s)", settings.APP_VERSION, settings.ENVIRONMENT)
    yield


app = FastAPI(
    title="AgriTwin API",
    version=settings.APP_VERSION,
    description=(
        "AI crop-health, yield, market-intelligence and uncertainty-aware "
        "decision support for Indian farmers."
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RequestContextMiddleware)
app.add_middleware(RateLimitMiddleware)

register_exception_handlers(app)

settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(settings.UPLOAD_DIR)), name="uploads")
app.include_router(api_router, prefix=settings.API_V1_PREFIX)


@app.get("/", tags=["system"])
def root() -> dict:
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "api": settings.API_V1_PREFIX,
        "demo_mode": settings.DEMO_MODE,
    }
