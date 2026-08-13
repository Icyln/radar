import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Callable

from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.collectors.base import BaseCollector, CollectorError
from app.collectors.registry import build_collector
from app.core.config import Settings
from app.matching.service import create_matches_for_jobs
from app.models.company import Company
from app.models.crawler_log import CrawlerLog
from app.models.enums import ATSProvider, CrawlerStatus, MonitoringPriority
from app.schemas.company import CompanyTarget
from app.services.job_processor import process_successful_snapshot
from app.services.locking import release_company_lock, try_company_lock
from app.services.notifications import (
    deliver_pending_notifications,
    enqueue_match_notifications,
    enqueue_phase1_notifications,
)

logger = logging.getLogger(__name__)
CollectorFactory = Callable[[ATSProvider, Settings], BaseCollector]


class MonitorService:
    def __init__(
        self,
        *,
        engine: Engine,
        settings: Settings,
        collector_factory: CollectorFactory = build_collector,
    ) -> None:
        self.engine = engine
        self.settings = settings
        self.collector_factory = collector_factory

    def eligible_company_ids(
        self,
        *,
        company_id: uuid.UUID | None = None,
        ats_identifier: str | None = None,
        priority: MonitoringPriority | None = None,
    ) -> list[uuid.UUID]:
        with Session(self.engine) as session:
            statement = select(Company.id).where(Company.active.is_(True))
            if company_id:
                statement = statement.where(Company.id == company_id)
            if ats_identifier:
                statement = statement.where(Company.ats_identifier == ats_identifier)
            if priority:
                statement = statement.where(Company.monitoring_priority == priority)
            return list(session.scalars(statement.order_by(Company.name.asc())))

    async def run(
        self,
        *,
        company_id: uuid.UUID | None = None,
        ats_identifier: str | None = None,
        priority: MonitoringPriority | None = None,
    ) -> dict[str, int]:
        summary = {
            "companies": 0,
            "success": 0,
            "failed": 0,
            "skipped": 0,
            "notifications_sent": 0,
        }
        for candidate_id in self.eligible_company_ids(
            company_id=company_id, ats_identifier=ats_identifier, priority=priority
        ):
            summary["companies"] += 1
            try:
                status = await self.run_company(candidate_id)
            except Exception:
                logger.exception(
                    "unexpected company monitor failure", extra={"company_id": str(candidate_id)}
                )
                status = "failed"
            summary[status] += 1
        summary["notifications_sent"] = await deliver_pending_notifications(
            engine=self.engine, settings=self.settings
        )
        return summary

    async def run_company(self, company_id: uuid.UUID) -> str:
        started = datetime.now(timezone.utc)
        monotonic_started = time.monotonic()
        collector: BaseCollector | None = None

        with self.engine.connect() as connection:
            if not try_company_lock(connection, company_id):
                with Session(bind=connection) as session:
                    company = session.get(Company, company_id)
                    if company is not None:
                        session.add(
                            CrawlerLog(
                                company_id=company.id,
                                ats_provider=company.ats_provider,
                                started_at=started,
                                completed_at=datetime.now(timezone.utc),
                                status=CrawlerStatus.SKIPPED,
                                error_type="overlap",
                                error_message="another monitor owns the company advisory lock",
                                duration_ms=int((time.monotonic() - monotonic_started) * 1000),
                            )
                        )
                        session.commit()
                return "skipped"

            try:
                with Session(bind=connection, expire_on_commit=False) as session:
                    company = session.get(Company, company_id)
                    if company is None or not company.active:
                        return "skipped"
                    initial_sync = company.last_successful_check_at is None
                    company.last_checked_at = started
                    crawler_log = CrawlerLog(
                        company_id=company.id,
                        ats_provider=company.ats_provider,
                        started_at=started,
                        status=CrawlerStatus.FAILED,
                    )
                    session.add(crawler_log)
                    session.commit()
                    log_id = crawler_log.id
                    target = CompanyTarget.model_validate(company)

                try:
                    collector = self.collector_factory(target.ats_provider, self.settings)
                    jobs = await collector.fetch_jobs(target)
                except CollectorError as exc:
                    completed = datetime.now(timezone.utc)
                    with Session(bind=connection) as session:
                        company = session.get(Company, company_id)
                        crawler_log = session.get(CrawlerLog, log_id)
                        if company is not None:
                            company.last_error_at = completed
                            company.consecutive_failures += 1
                        if crawler_log is not None:
                            crawler_log.completed_at = completed
                            crawler_log.status = CrawlerStatus.FAILED
                            crawler_log.error_type = exc.category
                            crawler_log.error_message = str(exc)[:2000]
                            crawler_log.duration_ms = int(
                                (time.monotonic() - monotonic_started) * 1000
                            )
                        session.commit()
                    logger.warning(
                        "company monitor failed",
                        extra={"company_id": str(company_id), "error_type": exc.category},
                    )
                    return "failed"

                completed = datetime.now(timezone.utc)
                with Session(bind=connection, expire_on_commit=False) as session:
                    company = session.get(Company, company_id)
                    crawler_log = session.get(CrawlerLog, log_id)
                    if company is None or crawler_log is None:
                        raise RuntimeError("company or crawler log disappeared during monitor run")
                    result = process_successful_snapshot(
                        session,
                        company=company,
                        jobs=jobs,
                        missing_threshold=self.settings.job_missing_threshold,
                        now=completed,
                    )
                    match_result = create_matches_for_jobs(
                        session,
                        job_ids=[*result.new_job_ids, *result.updated_job_ids],
                    )
                    # Initial source sync establishes a baseline. Matches are persisted for
                    # the dashboard, but existing board contents are not pushed as alerts.
                    if not initial_sync:
                        enqueue_match_notifications(
                            session,
                            match_ids=match_result.match_ids,
                            crawler_log_id=crawler_log.id,
                        )
                    # Retain the Phase-1 single-recipient path for local smoke testing.
                    enqueue_phase1_notifications(
                        session,
                        company=company,
                        new_job_ids=result.new_job_ids,
                        settings=self.settings,
                        initial_sync=initial_sync,
                        crawler_log_id=crawler_log.id,
                    )
                    company.last_successful_check_at = completed
                    company.consecutive_failures = 0
                    crawler_log.completed_at = completed
                    crawler_log.status = CrawlerStatus.SUCCESS
                    crawler_log.jobs_received = result.jobs_received
                    crawler_log.jobs_new = result.jobs_new
                    crawler_log.jobs_updated = result.jobs_updated
                    crawler_log.jobs_closed = result.jobs_closed
                    crawler_log.matches_created = match_result.created
                    crawler_log.duration_ms = int((time.monotonic() - monotonic_started) * 1000)
                    session.commit()
                return "success"
            finally:
                if collector is not None:
                    try:
                        await collector.close()
                    except Exception:
                        logger.warning(
                            "collector cleanup failed",
                            extra={"company_id": str(company_id)},
                            exc_info=True,
                        )
                release_company_lock(connection, company_id)
