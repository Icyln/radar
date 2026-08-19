import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Index, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import DiscoveryTargetOrigin, DiscoveryTargetStatus
from app.models.mixins import TimestampMixin


class DiscoveryTarget(TimestampMixin, Base):
    __tablename__ = "discovery_targets"
    __table_args__ = (
        Index("ix_discovery_targets_status_created", "status", "created_at"),
        Index("ix_discovery_targets_user_created", "submitted_by_user_id", "created_at"),
        Index("ix_discovery_targets_origin_status", "origin", "status"),
        Index("ix_discovery_targets_signal_posted", "job_posted_at_hint", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    submitted_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    url: Mapped[str] = mapped_column(String(1500), nullable=False)
    origin: Mapped[DiscoveryTargetOrigin] = mapped_column(
        Enum(DiscoveryTargetOrigin, name="discovery_target_origin"),
        default=DiscoveryTargetOrigin.USER,
        nullable=False,
    )
    source_label: Mapped[str | None] = mapped_column(String(255))
    company_name_hint: Mapped[str | None] = mapped_column(String(255))
    signal_external_id: Mapped[str | None] = mapped_column(String(500))
    job_title_hint: Mapped[str | None] = mapped_column(String(500))
    job_location_hint: Mapped[str | None] = mapped_column(String(500))
    job_posted_at_hint: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    auto_watch: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    status: Mapped[DiscoveryTargetStatus] = mapped_column(
        Enum(DiscoveryTargetStatus, name="discovery_target_status"),
        default=DiscoveryTargetStatus.PENDING,
        nullable=False,
    )
    scan_attempt_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_scanned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    pages_scanned: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    sources_found: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_type: Mapped[str | None] = mapped_column(String(100))
    error_message: Mapped[str | None] = mapped_column(Text)

    submitted_by_user = relationship("User")
    candidates = relationship("SourceCandidate", back_populates="discovery_target")
