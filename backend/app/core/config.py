"""Application configuration.

All tunable values are read from environment variables (or a local ``.env``
file).  Secrets are never committed: ``.env.example`` documents the variables
and the development defaults are intentionally obvious so that they cannot be
mistaken for production configuration.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]
REPO_ROOT = BACKEND_DIR.parent
CONFIG_DIR = BACKEND_DIR / "app" / "config"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(REPO_ROOT / ".env", BACKEND_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # ---------------------------------------------------------------- app
    APP_NAME: str = "AgriTwin"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: Literal["development", "test", "production"] = "development"
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"
    DEMO_MODE: bool = True
    LOG_LEVEL: str = "INFO"

    # ------------------------------------------------------------- database
    DATABASE_URL: str = f"sqlite:///{(BACKEND_DIR / 'agritwin.db').as_posix()}"
    SQL_ECHO: bool = False

    # ----------------------------------------------------------------- auth
    JWT_SECRET_KEY: str = "dev-only-insecure-secret-change-me"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    PASSWORD_MIN_LENGTH: int = 8

    # --------------------------------------------------------------- uploads
    UPLOAD_DIR: Path = BACKEND_DIR / "uploads"
    MAX_UPLOAD_SIZE_MB: int = 8
    MAX_IMAGE_DIMENSION: int = 4096
    ALLOWED_IMAGE_MIME: str = "image/jpeg,image/png,image/webp"

    # ------------------------------------------------------------- ML paths
    CROP_HEALTH_ARTIFACT_DIR: Path = BACKEND_DIR / "app" / "ml" / "artifacts" / "crop_health"
    YIELD_ARTIFACT_DIR: Path = BACKEND_DIR / "app" / "ml" / "artifacts" / "yield_prediction"
    MARKET_ARTIFACT_DIR: Path = BACKEND_DIR / "app" / "ml" / "artifacts" / "market_forecasting"
    CROP_HEALTH_CONFIDENCE_THRESHOLD: float = 0.55

    # ------------------------------------------------------------- providers
    WEATHER_PROVIDER: Literal["open-meteo", "disabled"] = "open-meteo"
    OPEN_METEO_BASE_URL: str = "https://api.open-meteo.com/v1"
    GEOCODING_PROVIDER: Literal["open-meteo", "disabled"] = "open-meteo"
    GEOCODING_BASE_URL: str = "https://geocoding-api.open-meteo.com/v1"
    ROUTING_PROVIDER: Literal["osrm", "geodesic"] = "osrm"
    OSRM_BASE_URL: str = "https://router.project-osrm.org"
    HTTP_TIMEOUT_SECONDS: float = 10.0
    EXTERNAL_CACHE_TTL_SECONDS: int = 900

    # ----------------------------------------------------------- live market
    # ``auto`` uses official Agmarknet/data.gov.in when DATA_GOV_API_KEY is set,
    # otherwise it uses the keyless five-state Mandi Price API mirror.
    LIVE_MARKET_PROVIDER: Literal["auto", "data_gov", "mandi_api", "disabled"] = "auto"
    DATA_GOV_API_KEY: str | None = None
    DATA_GOV_BASE_URL: str = "https://api.data.gov.in/resource"
    DATA_GOV_RESOURCE_ID: str = "9ef84268-d588-465a-a308-a864a43d0070"
    DATA_GOV_VARIETY_RESOURCE_ID: str = "35985678-0d79-46b4-9ed6-6f13308a1d24"
    LIVE_MARKET_USE_VARIETY_SOURCE: bool = True
    DATA_GOV_PAGE_SIZE: int = 200
    LIVE_MARKET_TIMEOUT_SECONDS: float = 30.0
    MANDI_API_BASE_URL: str = "https://mandi-api.onrender.com/v1"

    # ------------------------------------------------------------- transport
    DEFAULT_COST_PER_KM_INR: float = 18.0
    DEFAULT_FIXED_COST_INR: float = 350.0
    DEFAULT_LOADING_COST_INR: float = 120.0
    DEFAULT_UNLOADING_COST_INR: float = 120.0
    DEFAULT_VEHICLE_CAPACITY_QUINTALS: float = 100.0
    GEODESIC_DETOUR_FACTOR: float = 1.25
    SELLING_COMMISSION_PCT: float = 0.01
    OTHER_SELLING_COST_PER_QUINTAL: float = 5.0

    # ------------------------------------------------------------- decisions
    DECISION_POLICY_PATH: Path = CONFIG_DIR / "decision_policy.json"
    CROP_CALENDAR_PATH: Path = CONFIG_DIR / "crop_calendar.json"
    TRANSPORT_DEFAULTS_PATH: Path = CONFIG_DIR / "transport_defaults.json"

    # ------------------------------------------------------------ rate limit
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_REQUESTS: int = 120
    RATE_LIMIT_WINDOW_SECONDS: int = 60
    AUTH_RATE_LIMIT_REQUESTS: int = 20

    # ------------------------------------------------------------------ cors
    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"

    # ------------------------------------------------------------------ seed
    SEED_DEMO_USER_EMAIL: str = "demo@agritwin.in"
    SEED_DEMO_USER_PASSWORD: str = "Demo@12345"

    @field_validator("UPLOAD_DIR", "CROP_HEALTH_ARTIFACT_DIR", "YIELD_ARTIFACT_DIR", "MARKET_ARTIFACT_DIR", mode="before")
    @classmethod
    def _to_path(cls, value: Any) -> Path:
        return Path(value)

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    @property
    def allowed_image_mime(self) -> set[str]:
        return {m.strip().lower() for m in self.ALLOWED_IMAGE_MIME.split(",") if m.strip()}

    @property
    def max_upload_bytes(self) -> int:
        return self.MAX_UPLOAD_SIZE_MB * 1024 * 1024

    def read_json_config(self, path: Path) -> dict[str, Any]:
        if not path.exists():
            raise FileNotFoundError(f"Configuration file not found: {path}")
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)

    @property
    def is_sqlite(self) -> bool:
        return self.DATABASE_URL.startswith("sqlite")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
