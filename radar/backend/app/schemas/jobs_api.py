import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel

from app.models.enums import ATSProvider, JobStatus, UserJobStateType, WorkMode


JobSourceKind = Literal["DIRECT_ATS", "WIDE_DISCOVERY"]


class JobListItem(BaseModel):
    id: uuid.UUID
    company_id: uuid.UUID | None
    company_name: str
    ats_provider: ATSProvider | None = None
    title: str
    location: str | None
    work_mode: WorkMode
    employment_type: str | None
    apply_url: str
    source_url: str
    posted_at: datetime | None
    first_seen_at: datetime
    last_seen_at: datetime
    status: JobStatus
    closed_at: datetime | None
    user_state: UserJobStateType | None = None
    freshness_at: datetime | None = None
    freshness_source: Literal["POSTED_AT", "DISCOVERY_SIGNAL", "FIRST_SEEN", "UNKNOWN"] = "UNKNOWN"
    source_kind: JobSourceKind = "DIRECT_ATS"
    source_provider: str | None = None
    source_verified: bool = True


class DetectedJobPage(BaseModel):
    items: list[JobListItem]
    total: int
    limit: int
    offset: int
    has_more: bool


class JobDetail(JobListItem):
    description: str | None


class JobStateRequest(BaseModel):
    state: UserJobStateType | None
