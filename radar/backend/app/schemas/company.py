import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import ATSProvider, MonitoringPriority


class CompanyTarget(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    ats_provider: ATSProvider
    ats_identifier: str
    career_url: str


class CompanyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    website: str | None = Field(default=None, max_length=1000)
    career_url: str = Field(min_length=1, max_length=1000)
    ats_provider: ATSProvider
    ats_identifier: str = Field(min_length=1, max_length=255)
    monitoring_priority: MonitoringPriority = MonitoringPriority.NORMAL
    active: bool = True


class CompanyUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    website: str | None = Field(default=None, max_length=1000)
    career_url: str | None = Field(default=None, min_length=1, max_length=1000)
    ats_provider: ATSProvider | None = None
    ats_identifier: str | None = Field(default=None, min_length=1, max_length=255)
    monitoring_priority: MonitoringPriority | None = None
    active: bool | None = None


class CompanyRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    website: str | None
    career_url: str
    ats_provider: ATSProvider
    ats_identifier: str
    monitoring_priority: MonitoringPriority
    active: bool
    discovery_boost_until: datetime | None
    last_checked_at: datetime | None
    last_successful_check_at: datetime | None
    last_error_at: datetime | None
    consecutive_failures: int
    created_at: datetime
    updated_at: datetime
