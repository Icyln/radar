import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Enum, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import ATSProvider, CrawlerStatus


class CrawlerLog(Base):
    __tablename__ = "crawler_logs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    ats_provider: Mapped[ATSProvider] = mapped_column(Enum(ATSProvider, name="ats_provider"), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[CrawlerStatus] = mapped_column(
        Enum(CrawlerStatus, name="crawler_status"), nullable=False
    )
    jobs_received: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    jobs_new: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    jobs_updated: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    jobs_closed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    matches_created: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    notifications_sent: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_type: Mapped[str | None] = mapped_column(String(100))
    error_message: Mapped[str | None] = mapped_column(Text)
    duration_ms: Mapped[int | None] = mapped_column(BigInteger)

    company = relationship("Company", back_populates="crawler_logs")
