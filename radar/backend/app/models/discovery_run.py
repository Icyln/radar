import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.enums import CrawlerStatus


class DiscoveryRun(Base):
    __tablename__ = "discovery_runs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    status: Mapped[CrawlerStatus] = mapped_column(
        Enum(CrawlerStatus, name="crawler_status"), nullable=False
    )
    trigger: Mapped[str | None] = mapped_column(String(100), index=True)
    external_run_id: Mapped[str | None] = mapped_column(String(255), index=True)

    profiles: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    queries: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    signals_seen: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    signals_relevant: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    jobs_new: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    jobs_updated: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    jobs_existing: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    jobs_deduplicated: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    matches_created: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    notifications_sent: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    provider_failures: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    provider_warnings: Mapped[str | None] = mapped_column(Text)
    candidates_promoted: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    jobs_marked_unknown: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    jobs_closed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    error_type: Mapped[str | None] = mapped_column(String(100))
    error_message: Mapped[str | None] = mapped_column(Text)
