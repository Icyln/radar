import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import utc_now


class JobSourceObservation(Base):
    __tablename__ = "job_source_observations"
    __table_args__ = (
        UniqueConstraint(
            "source_provider",
            "source_external_id",
            name="uq_job_source_observation_provider_external",
        ),
        Index("ix_job_source_observations_job_seen", "job_id", "last_seen_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    job_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    source_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    source_provider: Mapped[str] = mapped_column(String(255), nullable=False)
    source_external_id: Mapped[str] = mapped_column(String(500), nullable=False)
    source_url: Mapped[str] = mapped_column(String(2000), nullable=False)
    apply_url: Mapped[str] = mapped_column(String(2000), nullable=False)
    company_name: Mapped[str | None] = mapped_column(String(255))
    posted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    job = relationship("Job", back_populates="source_observations")
