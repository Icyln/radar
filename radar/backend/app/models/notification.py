import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Integer, String, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import NotificationChannel, NotificationStatus
from app.models.mixins import TimestampMixin


class Notification(TimestampMixin, Base):
    __tablename__ = "notifications"
    __table_args__ = (
        # Retained for Phase-1 compatibility and also protects the same Telegram chat
        # from duplicate alerts if two workers race.
        UniqueConstraint("job_id", "channel", "recipient", name="uq_notification_job_channel_recipient"),
        UniqueConstraint("user_id", "job_id", "channel", name="uq_notification_user_job_channel"),
        Index("ix_notifications_delivery", "status", "created_at"),
        Index("ix_notifications_user_status", "user_id", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    crawler_log_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("crawler_logs.id", ondelete="SET NULL"), nullable=True, index=True
    )
    channel: Mapped[NotificationChannel] = mapped_column(
        Enum(NotificationChannel, name="notification_channel"), nullable=False
    )
    recipient: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[NotificationStatus] = mapped_column(
        Enum(NotificationStatus, name="notification_status"),
        default=NotificationStatus.PENDING,
        nullable=False,
    )
    attempt_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_message: Mapped[str | None] = mapped_column(Text)
    telegram_message_id: Mapped[str | None] = mapped_column(String(100))

    user = relationship("User", back_populates="notifications")
    job = relationship("Job", back_populates="notifications")
