import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import ProfileCoverageMode, WorkMode


def _clean_list(values: list[str]) -> list[str]:
    cleaned: list[str] = []
    seen: set[str] = set()
    for value in values:
        item = value.strip()
        key = item.casefold()
        if item and key not in seen:
            cleaned.append(item)
            seen.add(key)
    return cleaned


class JobProfileCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    enabled: bool = True
    coverage_mode: ProfileCoverageMode = ProfileCoverageMode.WIDE
    job_titles: list[str] = Field(min_length=1, max_length=25)
    locations: list[str] = Field(default_factory=list, max_length=25)
    work_modes: list[WorkMode] = Field(default_factory=list, max_length=4)
    excluded_keywords: list[str] = Field(default_factory=list, max_length=50)
    max_job_age_days: int | None = Field(default=30, ge=1, le=3650)
    include_unknown_posted_at: bool = False

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        return value.strip()

    @field_validator("job_titles", "locations", "excluded_keywords")
    @classmethod
    def clean_strings(cls, value: list[str]) -> list[str]:
        return _clean_list(value)


class JobProfileUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    enabled: bool | None = None
    coverage_mode: ProfileCoverageMode | None = None
    job_titles: list[str] | None = Field(default=None, min_length=1, max_length=25)
    locations: list[str] | None = Field(default=None, max_length=25)
    work_modes: list[WorkMode] | None = Field(default=None, max_length=4)
    excluded_keywords: list[str] | None = Field(default=None, max_length=50)
    max_job_age_days: int | None = Field(default=None, ge=1, le=3650)
    include_unknown_posted_at: bool | None = None

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else None

    @field_validator("job_titles", "locations", "excluded_keywords")
    @classmethod
    def clean_strings(cls, value: list[str] | None) -> list[str] | None:
        return _clean_list(value) if value is not None else None


class JobProfileRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    name: str
    enabled: bool
    coverage_mode: ProfileCoverageMode
    job_titles: list[str]
    locations: list[str]
    work_modes: list[WorkMode]
    excluded_keywords: list[str]
    max_job_age_days: int | None
    include_unknown_posted_at: bool
    created_at: datetime
    updated_at: datetime
