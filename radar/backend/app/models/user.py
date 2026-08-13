import uuid

from sqlalchemy import Boolean, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(500), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    job_profiles = relationship("JobProfile", back_populates="user", cascade="all, delete-orphan")
    job_matches = relationship("JobMatch", back_populates="user", cascade="all, delete-orphan")
    job_states = relationship("UserJobState", back_populates="user", cascade="all, delete-orphan")
    telegram_connection = relationship(
        "TelegramConnection", back_populates="user", cascade="all, delete-orphan", uselist=False
    )
    telegram_link_tokens = relationship(
        "TelegramLinkToken", back_populates="user", cascade="all, delete-orphan"
    )
    notifications = relationship("Notification", back_populates="user")
