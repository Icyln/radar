import uuid

from sqlalchemy import Enum, ForeignKey, Index, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import UserJobStateType
from app.models.mixins import TimestampMixin


class UserJobState(TimestampMixin, Base):
    __tablename__ = "user_job_states"
    __table_args__ = (
        UniqueConstraint("user_id", "job_id", name="uq_user_job_state_user_job"),
        Index("ix_user_job_states_user_state", "user_id", "state"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    state: Mapped[UserJobStateType] = mapped_column(
        Enum(UserJobStateType, name="user_job_state_type"), nullable=False
    )

    user = relationship("User", back_populates="job_states")
    job = relationship("Job", back_populates="user_states")
