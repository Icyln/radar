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

    discovery_user_agent: str = "RadarDiscovery/0.7.3 (+wide job discovery and ATS source resolution)"
    discovery_max_pages_per_target: int = Field(default=6, ge=1, le=20)
    discovery_target_batch_size: int = Field(default=25, ge=1, le=200)
    discovery_candidate_batch_size: int = Field(default=50, ge=1, le=500)
    discovery_max_concurrency: int = Field(default=3, ge=1, le=10)
    discovery_stale_minutes: int = Field(default=30, ge=5, le=1440)
    discovery_target_total_timeout_seconds: float = Field(default=30.0, gt=0, le=300)
    discovery_candidate_total_timeout_seconds: float = Field(default=30.0, gt=0, le=300)
    discovery_system_feed_urls: str = ""
    discovery_system_feed_max_bytes: int = Field(default=1_000_000, ge=1024, le=10_000_000)
    discovery_system_feed_max_entries: int = Field(default=1000, ge=1, le=10000)
    discovery_system_target_refresh_days: int = Field(default=30, ge=1, le=365)
    discovery_revalidate_days: int = Field(default=14, ge=1, le=365)
    discovery_invalid_retry_days: int = Field(default=7, ge=1, le=365)
    discovery_revalidate_batch_size: int = Field(default=50, ge=1, le=500)
    discovery_hiring_signals_enabled: bool = True
    discovery_hiring_max_age_days: int = Field(default=30, ge=1, le=90)
    discovery_hiring_max_queries: int = Field(default=25, ge=1, le=100)
    discovery_hiring_max_signals_per_run: int = Field(default=500, ge=1, le=5000)
    discovery_hiring_max_identifier_guesses: int = Field(default=3, ge=1, le=5)
    discovery_hiring_max_probe_candidates_per_run: int = Field(default=150, ge=1, le=2000)
    discovery_hiring_request_total_timeout_seconds: float = Field(default=25.0, gt=0, le=120)
    discovery_hiring_arbeitnow_enabled: bool = True
    discovery_hiring_arbeitnow_pages: int = Field(default=2, ge=1, le=10)
    discovery_hiring_himalayas_enabled: bool = True
    discovery_hiring_priority_boost_days: int = Field(default=7, ge=1, le=30)

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

    @property
    def discovery_system_feed_url_list(self) -> tuple[str, ...]:
        return tuple(part.strip() for part in self.discovery_system_feed_urls.split(",") if part.strip())


@lru_cache
def get_settings() -> Settings:
    return Settings()
