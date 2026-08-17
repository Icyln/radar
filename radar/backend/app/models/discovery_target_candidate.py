import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import utc_now


class DiscoveryTargetCandidate(Base):
    __tablename__ = "discovery_target_candidates"

    discovery_target_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("discovery_targets.id", ondelete="CASCADE"), primary_key=True
    )
    source_candidate_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("source_candidates.id", ondelete="CASCADE"), primary_key=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
