import uuid

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, JSON, UniqueConstraint, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin, utc_now

json_type = JSON().with_variant(JSONB(), "postgresql")


class JobMatch(TimestampMixin, Base):
    __tablename__ = "job_matches"
    __table_args__ = (
        UniqueConstraint("job_profile_id", "job_id", name="uq_job_match_profile_job"),
        Index("ix_job_matches_user_matched", "user_id", "matched_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    job_profile_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("job_profiles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    matched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    match_reason: Mapped[dict] = mapped_column(json_type, default=dict, nullable=False)

    user = relationship("User", back_populates="job_matches")
    job_profile = relationship("JobProfile", back_populates="matches")
    job = relationship("Job", back_populates="matches")
