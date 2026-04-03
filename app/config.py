"""
TG PRO QUANTUM - Application Configuration
Settings loaded from environment variables with sensible defaults.
"""
from functools import lru_cache
from typing import List, Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # ── Application ──────────────────────────────────────────────────────────
    APP_NAME: str = "TG PRO QUANTUM"
    APP_VERSION: str = "7.0.0"
    DEBUG: bool = False
    SECRET_KEY: str = "change-me-in-production-secret-key-min-32-chars"
    ALLOWED_HOSTS: List[str] = ["*"]

    # ── Database ─────────────────────────────────────────────────────────────
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/tg_quantum"

    # ── Redis / Celery ────────────────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/1"

    # ── JWT ──────────────────────────────────────────────────────────────────
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # ── OTP / SMS Activate ────────────────────────────────────────────────────
    SMS_ACTIVATE_API_KEY: str = ""
    SMS_ACTIVATE_BASE_URL: str = "https://api.sms-activate.org/stubs/handler_api.php"
    OTP_EXPIRE_MINUTES: int = 10
    OTP_MAX_ATTEMPTS: int = 3

    # ── Telegram ──────────────────────────────────────────────────────────────
    TELEGRAM_API_ID: int = 0
    TELEGRAM_API_HASH: str = ""
    SESSIONS_DIR: str = "sessions"

    # ── Rate Limiting ─────────────────────────────────────────────────────────
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_PERIOD: int = 60  # seconds

    # ── Broadcast defaults ────────────────────────────────────────────────────
    DEFAULT_DELAY_MIN: float = 3.0   # seconds between messages
    DEFAULT_DELAY_MAX: float = 8.0
    MAX_RETRIES: int = 3

    # ── Email (optional notifications) ────────────────────────────────────────
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    EMAIL_FROM: str = "noreply@tgquantum.io"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
