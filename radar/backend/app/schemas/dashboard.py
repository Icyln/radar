from datetime import datetime
from typing import Literal

from pydantic import BaseModel

from app.schemas.jobs_api import JobListItem

AutomationState = Literal["HEALTHY", "DEGRADED", "FAILED", "STALE", "RUNNING", "UNKNOWN"]


class MonitoringAutomationHealth(BaseModel):
    state: AutomationState
    last_run_at: datetime | None
    trigger: str | None
    companies_selected: int = 0
    companies_succeeded: int = 0
    companies_failed: int = 0
    notifications_sent: int = 0


class WideAutomationHealth(BaseModel):
    state: AutomationState
    last_run_at: datetime | None
    trigger: str | None
    signals_seen: int = 0
    signals_relevant: int = 0
    jobs_new: int = 0
    jobs_deduplicated: int = 0
    provider_failures: int = 0
    notifications_sent: int = 0
    warnings: list[str] = []


class DashboardSummary(BaseModel):
    active_profiles: int
    monitored_companies: int
    watched_companies: int
    jobs_discovered_today: int
    wide_jobs_today: int
    direct_jobs_today: int
    matches_today: int
    alerts_sent_today: int
    last_successful_crawler_run: datetime | None
    wide_jobs_unknown: int
    monitoring_automation: MonitoringAutomationHealth
    wide_search_automation: WideAutomationHealth
    recent_matching_jobs: list[JobListItem]
