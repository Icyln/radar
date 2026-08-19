import asyncio
import logging
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Callable, Literal

from sqlalchemy import and_, or_, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.collectors.base import BaseCollector, CollectorError
from app.collectors.registry import build_collector
from app.core.config import Settings
from app.matching.service import create_matches_for_jobs
from app.models.company import Company
from app.models.crawler_log import CrawlerLog
from app.models.enums import ATSProvider, CrawlerStatus, MonitoringPriority
from app.models.job_match import JobMatch
from app.models.monitor_run import MonitorRun
from app.models.user_company_watchlist import UserCompanyWatchlist
from app.schemas.company import CompanyTarget
from app.services.discovery_signals import apply_discovery_signals_to_jobs
from app.services.job_processor import process_successful_snapshot
from app.services.locking import release_company_lock, try_company_lock
from app.services.notifications import (
    deliver_pending_notifications,
    enqueue_match_notifications,
    enqueue_phase1_notifications,
)

logger = logging.getLogger(__name__)
CollectorFactory = Callable[[ATSProvider, Settings], BaseCollector]
SourceScope = Literal["all", "watchlist", "registry"]


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
        source_scope: SourceScope = "all",
        shard_index: int = 0,
        shard_count: int = 1,
        batch_size: int | None = None,
        min_age_minutes: int | None = None,
    ) -> list[uuid.UUID]:
        if shard_count < 1:
            raise ValueError("shard_count must be at least 1")
        if shard_index < 0 or shard_index >= shard_count:
            raise ValueError("shard_index must be between 0 and shard_count - 1")
        if batch_size is not None and batch_size < 1:
            raise ValueError("batch_size must be at least 1 when provided")
        if min_age_minutes is not None and min_age_minutes < 0:
            raise ValueError("min_age_minutes cannot be negative")

        with Session(self.engine) as session:
            statement = select(Company.id).where(Company.active.is_(True))
            watched = select(UserCompanyWatchlist.id).where(
                UserCompanyWatchlist.company_id == Company.id
            ).exists()
            if source_scope == "watchlist":
                statement = statement.where(watched)
            elif source_scope == "registry":
                statement = statement.where(~watched)
            if company_id:
                statement = statement.where(Company.id == company_id)
            if ats_identifier:
                statement = statement.where(Company.ats_identifier == ats_identifier)
            if priority:
                now = datetime.now(timezone.utc)
                if priority is MonitoringPriority.NORMAL:
                    statement = statement.where(
                        or_(
                            Company.monitoring_priority == MonitoringPriority.NORMAL,
                            and_(
                                Company.monitoring_priority == MonitoringPriority.LOW,
                                Company.discovery_boost_until.is_not(None),
                                Company.discovery_boost_until > now,
                            ),
                        )
                    )
                elif priority is MonitoringPriority.LOW:
                    statement = statement.where(
                        and_(
                            Company.monitoring_priority == MonitoringPriority.LOW,
                            or_(
                                Company.discovery_boost_until.is_(None),
                                Company.discovery_boost_until <= now,
                            ),
                        )
                    )
                else:
                    statement = statement.where(Company.monitoring_priority == priority)
            if min_age_minutes is not None:
                due_before = datetime.now(timezone.utc) - timedelta(minutes=min_age_minutes)
                statement = statement.where(
                    (Company.last_checked_at.is_(None)) | (Company.last_checked_at <= due_before)
                )

            # Least-recently checked sources are selected first. Combined with a bounded
            # batch this creates a natural rotation instead of starving companies that sort
            # later by name. UUID modulo provides stable, database-independent sharding.
            candidates = list(
                session.scalars(
                    statement.order_by(
                        Company.last_checked_at.asc().nullsfirst(), Company.name.asc(), Company.id.asc()
                    )
                )
            )

        sharded = [item for item in candidates if item.int % shard_count == shard_index]
        return sharded[:batch_size] if batch_size is not None else sharded

    def _create_monitor_run(
        self,
        *,
        source_scope: SourceScope,
        priority: MonitoringPriority | None,
        shard_index: int,
        shard_count: int,
        batch_size: int | None,
        min_age_minutes: int | None,
        max_concurrency: int,
    ) -> uuid.UUID:
        with Session(self.engine, expire_on_commit=False) as session:
            item = MonitorRun(
                started_at=datetime.now(timezone.utc),
                status=CrawlerStatus.FAILED,
                source_scope=source_scope,
                priority=priority,
                shard_index=shard_index,
                shard_count=shard_count,
                batch_size=batch_size,
                min_age_minutes=min_age_minutes,
                max_concurrency=max_concurrency,
                trigger=self.settings.monitor_run_trigger,
                external_run_id=self.settings.monitor_external_run_id,
            )
            session.add(item)
            session.commit()
            return item.id

    def _complete_monitor_run(
        self,
        run_id: uuid.UUID,
        *,
        summary: dict[str, int],
        error: Exception | None = None,
    ) -> CrawlerStatus:
        selected = summary["companies"]
        if error is not None:
            status = CrawlerStatus.PARTIAL if summary["success"] else CrawlerStatus.FAILED
        elif selected == 0 or summary["skipped"] == selected:
            status = CrawlerStatus.SKIPPED
        elif summary["failed"] == selected:
            status = CrawlerStatus.FAILED
        elif summary["failed"]:
            status = CrawlerStatus.PARTIAL
        else:
            status = CrawlerStatus.SUCCESS

        with Session(self.engine) as session:
            item = session.get(MonitorRun, run_id)
            if item is not None:
                item.completed_at = datetime.now(timezone.utc)
                item.status = status
                item.companies_selected = summary["companies"]
                item.companies_succeeded = summary["success"]
                item.companies_failed = summary["failed"]
                item.companies_skipped = summary["skipped"]
                item.notifications_sent = summary["notifications_sent"]
                if error is not None:
                    item.error_type = error.__class__.__name__
                    item.error_message = str(error)[:2000]
                session.commit()
        return status

    async def run(
        self,
        *,
        company_id: uuid.UUID | None = None,
        ats_identifier: str | None = None,
        priority: MonitoringPriority | None = None,
        source_scope: SourceScope = "all",
        shard_index: int = 0,
        shard_count: int = 1,
        batch_size: int | None = None,
        min_age_minutes: int | None = None,
        max_concurrency: int = 1,
    ) -> dict[str, int | str]:
        if max_concurrency < 1:
            raise ValueError("max_concurrency must be at least 1")

        run_id = self._create_monitor_run(
            source_scope=source_scope,
            priority=priority,
            shard_index=shard_index,
            shard_count=shard_count,
            batch_size=batch_size,
            min_age_minutes=min_age_minutes,
            max_concurrency=max_concurrency,
        )
        summary: dict[str, int] = {
            "companies": 0,
            "success": 0,
            "failed": 0,
            "skipped": 0,
            "notifications_sent": 0,
        }
        error: Exception | None = None
        try:
            candidate_ids = self.eligible_company_ids(
                company_id=company_id,
                ats_identifier=ats_identifier,
                priority=priority,
                source_scope=source_scope,
                shard_index=shard_index,
                shard_count=shard_count,
                batch_size=batch_size,
                min_age_minutes=min_age_minutes,
            )
            summary["companies"] = len(candidate_ids)
            semaphore = asyncio.Semaphore(max_concurrency)

            async def process(candidate_id: uuid.UUID) -> str:
                async with semaphore:
                    try:
                        return await self.run_company(candidate_id, monitor_run_id=run_id)
                    except Exception:
                        logger.exception(
                            "unexpected company monitor failure",
                            extra={"company_id": str(candidate_id), "monitor_run_id": str(run_id)},
                        )
                        return "failed"

            if candidate_ids:
                statuses = await asyncio.gather(*(process(item) for item in candidate_ids))
                for status in statuses:
                    summary[status] += 1

            summary["notifications_sent"] = await deliver_pending_notifications(
                engine=self.engine, settings=self.settings
            )
        except Exception as exc:
            error = exc
            logger.exception("monitor run failed", extra={"monitor_run_id": str(run_id)})
            raise
        finally:
            status = self._complete_monitor_run(run_id, summary=summary, error=error)
            logger.info(
                "monitor run completed",
                extra={
                    "monitor_run_id": str(run_id),
                    "monitor_run_status": status.value,
                    "source_scope": source_scope,
                    "shard_index": shard_index,
                    "shard_count": shard_count,
                },
            )

        result: dict[str, int | str] = dict(summary)
        result["monitor_run_id"] = str(run_id)
        return result

    async def run_company(
        self, company_id: uuid.UUID, *, monitor_run_id: uuid.UUID | None = None
    ) -> str:
        started = datetime.now(timezone.utc)
        monotonic_started = time.monotonic()
        collector: BaseCollector | None = None
        log_id: uuid.UUID | None = None

        with self.engine.connect() as connection:
            if not try_company_lock(connection, company_id):
                with Session(self.engine) as session:
                    company = session.get(Company, company_id)
                    if company is not None:
                        session.add(
                            CrawlerLog(
                                company_id=company.id,
                                monitor_run_id=monitor_run_id,
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
                with Session(self.engine, expire_on_commit=False) as session:
                    company = session.get(Company, company_id)
                    if company is None or not company.active:
                        return "skipped"
                    initial_sync = company.last_successful_check_at is None
                    company.last_checked_at = started
                    crawler_log = CrawlerLog(
                        company_id=company.id,
                        monitor_run_id=monitor_run_id,
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
                    with Session(self.engine) as session:
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
                        extra={
                            "company_id": str(company_id),
                            "error_type": exc.category,
                            "monitor_run_id": str(monitor_run_id) if monitor_run_id else None,
                        },
                    )
                    return "failed"

                completed = datetime.now(timezone.utc)
                with Session(self.engine, expire_on_commit=False) as session:
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
                        initial_sync=initial_sync,
                    )
                    signal_alertable_job_ids = apply_discovery_signals_to_jobs(
                        session,
                        company_id=company.id,
                        job_ids=result.new_job_ids,
                        max_signal_age_days=self.settings.discovery_hiring_max_age_days,
                        now=completed,
                    )
                    new_match_result = create_matches_for_jobs(
                        session, job_ids=result.new_job_ids
                    )
                    updated_match_result = create_matches_for_jobs(
                        session, job_ids=result.updated_job_ids
                    )
                    matches_created = new_match_result.created + updated_match_result.created
                    # Initial source sync normally establishes a silent baseline. Phase 7 has
                    # one narrow exception: a fresh external hiring signal may identify one
                    # specific baseline role that caused the source to be discovered.
                    alert_match_ids = new_match_result.match_ids
                    if initial_sync:
                        if signal_alertable_job_ids and alert_match_ids:
                            alert_match_ids = list(
                                session.scalars(
                                    select(JobMatch.id).where(
                                        JobMatch.id.in_(alert_match_ids),
                                        JobMatch.job_id.in_(signal_alertable_job_ids),
                                    )
                                )
                            )
                        else:
                            alert_match_ids = []
                    enqueue_match_notifications(
                        session,
                        match_ids=alert_match_ids,
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
                    crawler_log.matches_created = matches_created
                    crawler_log.duration_ms = int((time.monotonic() - monotonic_started) * 1000)
                    session.commit()
                return "success"
            except Exception as exc:
                completed = datetime.now(timezone.utc)
                # CollectorError is handled above with its structured category. This block
                # catches unexpected parsing/database/domain failures so scheduled runs do
                # not leave an unfinished FAILED crawler row with no diagnostic context.
                with Session(self.engine) as session:
                    company = session.get(Company, company_id)
                    crawler_log = session.get(CrawlerLog, log_id) if log_id is not None else None
                    if company is not None:
                        company.last_error_at = completed
                        company.consecutive_failures += 1
                    if crawler_log is not None:
                        crawler_log.completed_at = completed
                        crawler_log.status = CrawlerStatus.FAILED
                        crawler_log.error_type = exc.__class__.__name__
                        crawler_log.error_message = str(exc)[:2000]
                        crawler_log.duration_ms = int(
                            (time.monotonic() - monotonic_started) * 1000
                        )
                    session.commit()
                raise
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
