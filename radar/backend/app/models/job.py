import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Index, Integer, String, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import ATSProvider, JobStatus, WorkMode
from app.models.mixins import TimestampMixin, utc_now


class Job(TimestampMixin, Base):
    __tablename__ = "jobs"
    __table_args__ = (
        UniqueConstraint(
            "company_id", "ats_provider", "external_job_id", name="uq_job_provider_external_id"
        ),
        UniqueConstraint("company_id", "fingerprint", name="uq_job_company_fingerprint"),
        UniqueConstraint(
            "source_provider", "source_external_id", name="uq_job_discovery_source_external_id"
        ),
        Index("ix_jobs_company_status", "company_id", "status"),
        Index("ix_jobs_status_last_seen", "status", "last_seen_at"),
        Index("ix_jobs_status_first_seen", "status", "first_seen_at"),
        Index("ix_jobs_status_posted_at", "status", "posted_at"),
        Index("ix_jobs_status_discovery_signal_at", "status", "discovery_signal_at"),
        Index("ix_jobs_source_kind_status", "source_kind", "status", "first_seen_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    # Broad-search jobs can exist before Radar resolves the employer to a
    # supported direct ATS source. Direct ATS jobs keep a normal company FK.
    company_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("companies.id", ondelete="CASCADE"), nullable=True, index=True
    )
    ats_provider: Mapped[ATSProvider | None] = mapped_column(
        Enum(ATSProvider, name="ats_provider"), nullable=True
    )
    external_job_id: Mapped[str | None] = mapped_column(String(255))
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    location: Mapped[str | None] = mapped_column(String(500))
    work_mode: Mapped[WorkMode] = mapped_column(
        Enum(WorkMode, name="work_mode"), default=WorkMode.UNKNOWN, nullable=False
    )
    employment_type: Mapped[str | None] = mapped_column(String(100))
    apply_url: Mapped[str] = mapped_column(String(2000), nullable=False)
    source_url: Mapped[str] = mapped_column(String(2000), nullable=False)
    posted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    discovery_signal_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    discovery_signal_source: Mapped[str | None] = mapped_column(String(100))

    # Provenance is deliberately independent from ATS identity. A WIDE_DISCOVERY job
    # is immediately usable even when company_id/ats_provider are still unknown.
    source_kind: Mapped[str] = mapped_column(String(32), default="DIRECT_ATS", nullable=False)
    source_provider: Mapped[str | None] = mapped_column(String(100))
    source_external_id: Mapped[str | None] = mapped_column(String(500))
    source_company_name: Mapped[str | None] = mapped_column(String(255))

    baseline_imported: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    missing_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[JobStatus] = mapped_column(
        Enum(JobStatus, name="job_status"), default=JobStatus.ACTIVE, nullable=False
    )
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)

    company = relationship("Company", back_populates="jobs")
    notifications = relationship("Notification", back_populates="job", cascade="all, delete-orphan")
    matches = relationship("JobMatch", back_populates="job", cascade="all, delete-orphan")
    user_states = relationship("UserJobState", back_populates="job", cascade="all, delete-orphan")
    source_observations = relationship(
        "JobSourceObservation", back_populates="job", cascade="all, delete-orphan"
    )
