import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, Index, Integer, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import ATSProvider, MonitoringPriority
from app.models.mixins import TimestampMixin


class Company(TimestampMixin, Base):
    __tablename__ = "companies"
    __table_args__ = (
        UniqueConstraint("ats_provider", "ats_identifier", name="uq_company_provider_identifier"),
        Index("ix_companies_monitoring", "active", "monitoring_priority", "last_checked_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    website: Mapped[str | None] = mapped_column(String(1000))
    career_url: Mapped[str] = mapped_column(String(1000), nullable=False)
    ats_provider: Mapped[ATSProvider] = mapped_column(Enum(ATSProvider, name="ats_provider"), nullable=False)
    ats_identifier: Mapped[str] = mapped_column(String(255), nullable=False)
    monitoring_priority: Mapped[MonitoringPriority] = mapped_column(
        Enum(MonitoringPriority, name="monitoring_priority"),
        default=MonitoringPriority.NORMAL,
        nullable=False,
    )
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_successful_check_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    consecutive_failures: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    jobs = relationship("Job", back_populates="company", cascade="all, delete-orphan")
    crawler_logs = relationship("CrawlerLog", back_populates="company", cascade="all, delete-orphan")
