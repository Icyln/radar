from functools import lru_cache

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=("../.env", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    environment: str = "development"
    log_level: str = "INFO"
    database_url: str
    frontend_url: str = "http://localhost:3000"
    backend_url: str = "http://localhost:8000"

    jwt_secret: str = "development-only-change-me"
    jwt_access_token_minutes: int = Field(default=60, ge=5, le=10080)
    admin_emails: str = ""

    job_missing_threshold: int = Field(default=3, ge=1, le=20)
    monitor_http_connect_timeout_seconds: float = Field(default=5.0, gt=0, le=60)
    monitor_http_read_timeout_seconds: float = Field(default=15.0, gt=0, le=120)
    monitor_http_max_retries: int = Field(default=2, ge=0, le=5)
    monitor_user_agent: str = "RadarJobMonitor/0.5 (+personal job monitoring)"
    monitor_max_concurrency: int = Field(default=3, ge=1, le=20)
    monitor_run_trigger: str | None = None
    monitor_external_run_id: str | None = None

    telegram_bot_token: str | None = None
    telegram_bot_username: str | None = None
    telegram_webhook_secret: str | None = None
    telegram_link_token_minutes: int = Field(default=10, ge=1, le=60)
    phase1_telegram_chat_id: str | None = None
    phase1_notify_title_keywords: str = ""
    phase1_notify_all_new_jobs: bool = False
    phase1_notify_on_initial_sync: bool = False
    phase1_max_notifications_per_run: int = Field(default=10, ge=1, le=100)
    telegram_request_timeout_seconds: float = Field(default=10.0, gt=0, le=60)
    telegram_max_attempts: int = Field(default=3, ge=1, le=5)
    telegram_sending_stale_minutes: int = Field(default=10, ge=1, le=120)

    @field_validator("telegram_bot_username")
    @classmethod
    def normalize_telegram_username(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip().lstrip("@")
        return cleaned or None

    @field_validator("database_url")
    @classmethod
    def normalize_database_url(cls, value: str) -> str:
        if value.startswith("postgres://"):
            return value.replace("postgres://", "postgresql+psycopg://", 1)
        if value.startswith("postgresql://") and "+" not in value.split("://", 1)[0]:
            return value.replace("postgresql://", "postgresql+psycopg://", 1)
        return value

    @model_validator(mode="after")
    def validate_production_secrets(self) -> "Settings":
        if self.environment.casefold() == "production" and (
            self.jwt_secret == "development-only-change-me" or len(self.jwt_secret) < 32
        ):
            raise ValueError("JWT_SECRET must be at least 32 characters in production")
        return self

    @property
    def phase1_keywords(self) -> tuple[str, ...]:
        return tuple(
            part.strip().casefold()
            for part in self.phase1_notify_title_keywords.split(",")
            if part.strip()
        )

    @property
    def admin_email_set(self) -> set[str]:
        return {item.strip().casefold() for item in self.admin_emails.split(",") if item.strip()}


@lru_cache
def get_settings() -> Settings:
    return Settings()
