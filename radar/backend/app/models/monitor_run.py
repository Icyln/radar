import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import CrawlerStatus, MonitoringPriority


class MonitorRun(Base):
    __tablename__ = "monitor_runs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[CrawlerStatus] = mapped_column(
        Enum(CrawlerStatus, name="crawler_status"), nullable=False
    )
    source_scope: Mapped[str] = mapped_column(String(20), nullable=False)
    priority: Mapped[MonitoringPriority | None] = mapped_column(
        Enum(MonitoringPriority, name="monitoring_priority")
    )
    shard_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    shard_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    batch_size: Mapped[int | None] = mapped_column(Integer)
    min_age_minutes: Mapped[int | None] = mapped_column(Integer)
    max_concurrency: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    companies_selected: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    companies_succeeded: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    companies_failed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    companies_skipped: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    notifications_sent: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    trigger: Mapped[str | None] = mapped_column(String(100))
    external_run_id: Mapped[str | None] = mapped_column(String(255))
    error_type: Mapped[str | None] = mapped_column(String(100))
    error_message: Mapped[str | None] = mapped_column(Text)

    crawler_logs = relationship("CrawlerLog", back_populates="monitor_run")
