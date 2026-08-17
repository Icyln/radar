import uuid
from datetime import datetime

from pydantic import BaseModel
from typing import Literal

from app.models.enums import JobStatus, UserJobStateType, WorkMode


class JobListItem(BaseModel):
    id: uuid.UUID
    company_id: uuid.UUID
    company_name: str
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
    freshness_source: Literal["POSTED_AT", "FIRST_SEEN", "UNKNOWN"] = "UNKNOWN"


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
