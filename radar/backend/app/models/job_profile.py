import uuid

from sqlalchemy import Boolean, ForeignKey, Index, JSON, String, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin

json_type = JSON().with_variant(JSONB(), "postgresql")


class JobProfile(TimestampMixin, Base):
    __tablename__ = "job_profiles"
    __table_args__ = (Index("ix_job_profiles_user_enabled", "user_id", "enabled"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    job_titles: Mapped[list[str]] = mapped_column(json_type, default=list, nullable=False)
    locations: Mapped[list[str]] = mapped_column(json_type, default=list, nullable=False)
    work_modes: Mapped[list[str]] = mapped_column(json_type, default=list, nullable=False)
    excluded_keywords: Mapped[list[str]] = mapped_column(json_type, default=list, nullable=False)

    user = relationship("User", back_populates="job_profiles")
    matches = relationship("JobMatch", back_populates="job_profile", cascade="all, delete-orphan")
