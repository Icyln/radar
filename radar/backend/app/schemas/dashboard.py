from datetime import datetime

from pydantic import BaseModel

from app.schemas.jobs_api import JobListItem


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
    recent_matching_jobs: list[JobListItem]
