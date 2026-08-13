import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.enums import ATSProvider, WorkMode


class NormalizedJob(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    company_id: uuid.UUID
    ats_provider: ATSProvider
    external_job_id: str | None = None
    title: str = Field(min_length=1, max_length=500)
    description: str | None = None
    location: str | None = Field(default=None, max_length=500)
    work_mode: WorkMode = WorkMode.UNKNOWN
    employment_type: str | None = Field(default=None, max_length=100)
    apply_url: str = Field(min_length=1, max_length=2000)
    source_url: str = Field(min_length=1, max_length=2000)
    posted_at: datetime | None = None

    @model_validator(mode="after")
    def require_fallback_identity_inputs(self) -> "NormalizedJob":
        if not self.external_job_id and not self.apply_url:
            raise ValueError("job requires an external_job_id or apply_url")
        return self
