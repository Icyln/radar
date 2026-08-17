import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Integer, String, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import ATSProvider, DiscoveryCandidateStatus
from app.models.mixins import TimestampMixin


class SourceCandidate(TimestampMixin, Base):
    __tablename__ = "source_candidates"
    __table_args__ = (
        UniqueConstraint("ats_provider", "ats_identifier", name="uq_source_candidate_provider_identifier"),
        Index("ix_source_candidates_status_created", "status", "created_at"),
        Index("ix_source_candidates_target", "discovery_target_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    discovery_target_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("discovery_targets.id", ondelete="SET NULL"), nullable=True
    )
    name_hint: Mapped[str | None] = mapped_column(String(255))
    ats_provider: Mapped[ATSProvider] = mapped_column(Enum(ATSProvider, name="ats_provider"), nullable=False)
    ats_identifier: Mapped[str] = mapped_column(String(255), nullable=False)
    career_url: Mapped[str] = mapped_column(String(1500), nullable=False)
    source_url: Mapped[str] = mapped_column(String(1500), nullable=False)
    status: Mapped[DiscoveryCandidateStatus] = mapped_column(
        Enum(DiscoveryCandidateStatus, name="discovery_candidate_status"),
        default=DiscoveryCandidateStatus.DISCOVERED,
        nullable=False,
    )
    validation_attempt_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_validated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_revalidated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revalidation_failure_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    jobs_seen: Mapped[int | None] = mapped_column(Integer)
    error_type: Mapped[str | None] = mapped_column(String(100))
    error_message: Mapped[str | None] = mapped_column(Text)
    promoted_company_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("companies.id", ondelete="SET NULL"), nullable=True
    )
    promoted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    discovery_target = relationship("DiscoveryTarget", back_populates="candidates")
    promoted_company = relationship("Company")
