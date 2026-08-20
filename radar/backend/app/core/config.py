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

    # Database pool sizing is deliberately conservative for Render + Supabase.
    # The target deployment is tens, not tens of thousands, of concurrent users.
    database_pool_size: int = Field(default=5, ge=1, le=20)
    database_max_overflow: int = Field(default=5, ge=0, le=20)
    database_pool_timeout_seconds: int = Field(default=10, ge=1, le=60)
    database_pool_recycle_seconds: int = Field(default=300, ge=30, le=3600)

    jwt_secret: str = "development-only-change-me"
    jwt_access_token_minutes: int = Field(default=60, ge=5, le=10080)
    admin_emails: str = ""

    # Product guardrails. These bounds keep each account understandable and keep
    # profile-driven discovery predictable at the intended 50-100 user scale.
    max_job_profiles_total: int = Field(default=10, ge=1, le=50)
    max_active_job_profiles: int = Field(default=5, ge=1, le=25)
    max_job_titles_per_profile: int = Field(default=5, ge=1, le=25)
    max_active_job_titles_per_user: int = Field(default=25, ge=1, le=100)

    # Lightweight per-process abuse protection. Render currently runs a small
    # deployment, so an in-memory limiter is sufficient without another service.
    auth_login_rate_limit: int = Field(default=10, ge=1, le=100)
    auth_login_rate_window_seconds: int = Field(default=60, ge=1, le=3600)
    auth_register_rate_limit: int = Field(default=5, ge=1, le=50)
    auth_register_rate_window_seconds: int = Field(default=3600, ge=60, le=86400)
    wide_refresh_rate_limit: int = Field(default=3, ge=1, le=20)
    wide_refresh_rate_window_seconds: int = Field(default=300, ge=30, le=3600)
    discovery_request_rate_limit: int = Field(default=10, ge=1, le=100)
    discovery_request_rate_window_seconds: int = Field(default=3600, ge=60, le=86400)
    telegram_test_rate_limit: int = Field(default=5, ge=1, le=50)
    telegram_test_rate_window_seconds: int = Field(default=300, ge=30, le=3600)
    api_max_request_bytes: int = Field(default=524_288, ge=16_384, le=5_242_880)

    job_missing_threshold: int = Field(default=3, ge=1, le=20)
    monitor_http_connect_timeout_seconds: float = Field(default=5.0, gt=0, le=60)
    monitor_http_read_timeout_seconds: float = Field(default=15.0, gt=0, le=120)
    monitor_http_max_retries: int = Field(default=2, ge=0, le=5)
    monitor_user_agent: str = "RadarJobMonitor/0.8.0 (+personal job monitoring)"
    monitor_max_concurrency: int = Field(default=3, ge=1, le=20)
    monitor_run_trigger: str | None = None
    monitor_external_run_id: str | None = None

    discovery_user_agent: str = "RadarDiscovery/0.8.0 (+wide job discovery and ATS source resolution)"
    discovery_max_pages_per_target: int = Field(default=6, ge=1, le=20)
    discovery_html_max_bytes: int = Field(default=2_000_000, ge=65_536, le=10_000_000)
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
    discovery_hiring_max_signals_per_run: int = Field(default=1000, ge=1, le=5000)
    discovery_hiring_max_identifier_guesses: int = Field(default=3, ge=1, le=5)
    discovery_hiring_max_probe_candidates_per_run: int = Field(default=150, ge=1, le=2000)
    discovery_hiring_request_total_timeout_seconds: float = Field(default=25.0, gt=0, le=120)
    discovery_hiring_arbeitnow_enabled: bool = True
    discovery_hiring_arbeitnow_pages: int = Field(default=4, ge=1, le=10)
    discovery_hiring_himalayas_pages: int = Field(default=3, ge=1, le=10)
    discovery_hiring_himalayas_enabled: bool = True
    discovery_hiring_priority_boost_days: int = Field(default=7, ge=1, le=30)
    discovery_wide_dedup_window_days: int = Field(default=45, ge=7, le=180)
    discovery_wide_unknown_after_days: int = Field(default=14, ge=1, le=90)
    discovery_wide_close_after_days: int = Field(default=45, ge=7, le=180)
    discovery_run_trigger: str | None = None
    discovery_external_run_id: str | None = None
    monitor_health_stale_minutes: int = Field(default=90, ge=30, le=1440)
    discovery_health_stale_minutes: int = Field(default=480, ge=60, le=2880)

    telegram_bot_token: str | None = None
    telegram_bot_username: str | None = None
    telegram_webhook_secret: str | None = None
    telegram_require_webhook_secret_in_production: bool = True
    telegram_link_token_minutes: int = Field(default=10, ge=1, le=60)
    telegram_request_timeout_seconds: float = Field(default=10.0, gt=0, le=60)
    telegram_max_attempts: int = Field(default=3, ge=1, le=5)
    telegram_sending_stale_minutes: int = Field(default=10, ge=1, le=120)
    telegram_max_notifications_per_run: int = Field(default=100, ge=1, le=500)

    @model_validator(mode="after")
    def validate_wide_lifecycle(self) -> "Settings":
        if self.discovery_wide_close_after_days <= self.discovery_wide_unknown_after_days:
            raise ValueError(
                "DISCOVERY_WIDE_CLOSE_AFTER_DAYS must be greater than "
                "DISCOVERY_WIDE_UNKNOWN_AFTER_DAYS"
            )
        if self.max_active_job_profiles > self.max_job_profiles_total:
            raise ValueError("MAX_ACTIVE_JOB_PROFILES cannot exceed MAX_JOB_PROFILES_TOTAL")
        if (
            self.max_active_job_profiles * self.max_job_titles_per_profile
            > self.max_active_job_titles_per_user
        ):
            # The active-title cap can be stricter than the mathematical maximum,
            # but it must never be smaller than one full profile.
            if self.max_active_job_titles_per_user < self.max_job_titles_per_profile:
                raise ValueError(
                    "MAX_ACTIVE_JOB_TITLES_PER_USER must allow at least one full profile"
                )
        return self

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
        if self.environment.casefold() != "production":
            return self
        if self.jwt_secret == "development-only-change-me" or len(self.jwt_secret) < 32:
            raise ValueError("JWT_SECRET must be at least 32 characters in production")
        if (
            self.telegram_bot_token
            and self.telegram_require_webhook_secret_in_production
            and not self.telegram_webhook_secret
        ):
            raise ValueError(
                "TELEGRAM_WEBHOOK_SECRET is required in production when Telegram is enabled"
            )
        return self

    @property
    def admin_email_set(self) -> set[str]:
        return {item.strip().casefold() for item in self.admin_emails.split(",") if item.strip()}

    @property
    def discovery_system_feed_url_list(self) -> tuple[str, ...]:
        return tuple(part.strip() for part in self.discovery_system_feed_urls.split(",") if part.strip())


@lru_cache
def get_settings() -> Settings:
    return Settings()
