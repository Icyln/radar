import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

from app.models.enums import (
    ATSProvider,
    DiscoveryCandidateStatus,
    DiscoveryTargetOrigin,
    DiscoveryTargetStatus,
)


class DiscoveryTargetCreate(BaseModel):
    url: HttpUrl
    company_name_hint: str | None = Field(default=None, max_length=255)
    auto_watch: bool = True


class DiscoveryTargetRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    submitted_by_user_id: uuid.UUID | None
    url: str
    origin: DiscoveryTargetOrigin
    source_label: str | None
    company_name_hint: str | None
    signal_external_id: str | None
    job_title_hint: str | None
    job_location_hint: str | None
    job_posted_at_hint: datetime | None
    auto_watch: bool
    status: DiscoveryTargetStatus
    scan_attempt_count: int
    last_scanned_at: datetime | None
    pages_scanned: int
    sources_found: int
    error_type: str | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime


class SourceCandidateRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    discovery_target_id: uuid.UUID | None
    name_hint: str | None
    ats_provider: ATSProvider
    ats_identifier: str
    career_url: str
    source_url: str
    status: DiscoveryCandidateStatus
    validation_attempt_count: int
    last_validated_at: datetime | None
    last_revalidated_at: datetime | None
    revalidation_failure_count: int
    jobs_seen: int | None
    error_type: str | None
    error_message: str | None
    promoted_company_id: uuid.UUID | None
    promoted_at: datetime | None
    created_at: datetime
    updated_at: datetime


class DiscoverySummaryRead(BaseModel):
    pending_targets: int
    failed_targets: int
    discovered_candidates: int
    valid_candidates: int
    invalid_candidates: int
    promoted_candidates: int
    system_targets: int
    system_promoted_candidates: int
    revalidation_failures: int
    hiring_signal_targets: int
    hiring_signal_promoted_sources: int
    fresh_signal_jobs: int


class WideSearchRefreshRead(BaseModel):
    profiles: int
    queries: int
    signals_seen: int
    signals_relevant: int
    jobs_new: int
    jobs_updated: int
    jobs_existing: int
    matches_created: int
    notifications_queued: int
    notifications_sent: int
    telegram_ready: bool
    targets_resolved: int
    probe_candidates_staged: int
    provider_failed: int
    provider_warnings: list[str] = []
