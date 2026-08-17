import asyncio
import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Callable
from urllib.parse import urlparse

from sqlalchemy import and_, func, or_, select
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.collectors.base import BaseCollector, CollectorError
from app.collectors.registry import build_collector
from app.core.config import Settings
from app.discovery.crawler import SafeHtmlFetcher, TargetCrawler
from app.discovery.detector import detect_ats_source
from app.discovery.feeds import DiscoveryFeedEntry, RemoteDiscoveryFeedFetcher, load_bundled_feed
from app.matching.service import backfill_watchlist_profiles_for_company
from app.models.company import Company
from app.models.discovery_target import DiscoveryTarget
from app.models.discovery_target_candidate import DiscoveryTargetCandidate
from app.models.enums import (
    ATSProvider,
    DiscoveryCandidateStatus,
    DiscoveryTargetOrigin,
    DiscoveryTargetStatus,
    MonitoringPriority,
)
from app.models.source_candidate import SourceCandidate
from app.models.user_company_watchlist import UserCompanyWatchlist
from app.schemas.company import CompanyTarget

logger = logging.getLogger(__name__)
CollectorFactory = Callable[[ATSProvider, Settings], BaseCollector]


class DiscoveryService:
    def __init__(
        self,
        *,
        engine: Engine,
        settings: Settings,
        collector_factory: CollectorFactory = build_collector,
        crawler_factory: Callable[[], TargetCrawler] | None = None,
    ) -> None:
        self.engine = engine
        self.settings = settings
        self.collector_factory = collector_factory
        self._crawler_factory = crawler_factory

    def _build_crawler(self) -> TargetCrawler:
        if self._crawler_factory is not None:
            return self._crawler_factory()
        fetcher = SafeHtmlFetcher(
            connect_timeout=self.settings.monitor_http_connect_timeout_seconds,
            read_timeout=self.settings.monitor_http_read_timeout_seconds,
            user_agent=self.settings.discovery_user_agent,
        )
        return TargetCrawler(fetcher)

    @staticmethod
    def _website_for_target(target: DiscoveryTarget | None) -> str | None:
        if target is None:
            return None
        parsed = urlparse(target.url)
        host = (parsed.hostname or "").casefold()
        if host.endswith("greenhouse.io") or host.endswith("lever.co") or host.endswith("ashbyhq.com"):
            return None
        if not parsed.scheme or not parsed.netloc:
            return None
        return f"{parsed.scheme}://{parsed.netloc}"

    @staticmethod
    def _ensure_watchlist(session: Session, *, user_id: uuid.UUID, company_id: uuid.UUID) -> None:
        existing = session.scalar(
            select(UserCompanyWatchlist).where(
                UserCompanyWatchlist.user_id == user_id,
                UserCompanyWatchlist.company_id == company_id,
            )
        )
        if existing is not None:
            return
        session.add(UserCompanyWatchlist(user_id=user_id, company_id=company_id))
        session.flush()
        backfill_watchlist_profiles_for_company(session, user_id=user_id, company_id=company_id)

    async def scan_target(self, target_id: uuid.UUID) -> str:
        with Session(self.engine, expire_on_commit=False) as session:
            target = session.get(DiscoveryTarget, target_id)
            if target is None:
                return "missing"
            target.status = DiscoveryTargetStatus.SCANNING
            target.scan_attempt_count += 1
            target.error_type = None
            target.error_message = None
            session.commit()
            target_url = target.url

        crawler = self._build_crawler()
        try:
            result = await crawler.scan(
                target_url, max_pages=self.settings.discovery_max_pages_per_target
            )
        except Exception as exc:
            with Session(self.engine) as session:
                target = session.get(DiscoveryTarget, target_id)
                if target is not None:
                    target.status = DiscoveryTargetStatus.FAILED
                    target.last_scanned_at = datetime.now(timezone.utc)
                    target.error_type = exc.__class__.__name__
                    target.error_message = str(exc)[:2000]
                    session.commit()
            logger.warning("discovery target scan failed", extra={"target_id": str(target_id)})
            return "failed"
        finally:
            await crawler.fetcher.close()

        now = datetime.now(timezone.utc)
        with Session(self.engine, expire_on_commit=False) as session:
            target = session.get(DiscoveryTarget, target_id)
            if target is None:
                return "missing"
            found = 0
            for source in result.sources:
                company = session.scalar(
                    select(Company).where(
                        Company.ats_provider == source.provider,
                        Company.ats_identifier == source.identifier,
                    )
                )
                candidate = session.scalar(
                    select(SourceCandidate).where(
                        SourceCandidate.ats_provider == source.provider,
                        SourceCandidate.ats_identifier == source.identifier,
                    )
                )
                if candidate is None:
                    candidate = SourceCandidate(
                        discovery_target_id=target.id,
                        name_hint=target.company_name_hint or result.title_hint,
                        ats_provider=source.provider,
                        ats_identifier=source.identifier,
                        career_url=source.career_url,
                        source_url=source.source_url,
                        status=(
                            DiscoveryCandidateStatus.VALID
                            if company is not None
                            else DiscoveryCandidateStatus.DISCOVERED
                        ),
                        promoted_company_id=company.id if company is not None else None,
                        promoted_at=now if company is not None else None,
                    )
                    session.add(candidate)
                    try:
                        session.flush()
                    except IntegrityError:
                        session.rollback()
                        candidate = session.scalar(
                            select(SourceCandidate).where(
                                SourceCandidate.ats_provider == source.provider,
                                SourceCandidate.ats_identifier == source.identifier,
                            )
                        )
                        target = session.get(DiscoveryTarget, target_id)
                        if target is None:
                            return "missing"
                link = session.get(DiscoveryTargetCandidate, (target.id, candidate.id))
                if link is None:
                    session.add(
                        DiscoveryTargetCandidate(
                            discovery_target_id=target.id, source_candidate_id=candidate.id
                        )
                    )
                    session.flush()
                found += 1
                if company is not None and target.auto_watch and target.submitted_by_user_id:
                    self._ensure_watchlist(
                        session,
                        user_id=target.submitted_by_user_id,
                        company_id=company.id,
                    )

            target.status = DiscoveryTargetStatus.COMPLETE
            target.last_scanned_at = now
            target.pages_scanned = result.pages_scanned
            target.sources_found = found
            target.error_type = None
            target.error_message = None
            session.commit()
        return "complete"

    async def validate_candidate(self, candidate_id: uuid.UUID, *, auto_promote: bool) -> str:
        with Session(self.engine, expire_on_commit=False) as session:
            candidate = session.get(SourceCandidate, candidate_id)
            if candidate is None:
                return "missing"
            candidate.status = DiscoveryCandidateStatus.VALIDATING
            candidate.validation_attempt_count += 1
            candidate.error_type = None
            candidate.error_message = None
            session.commit()
            target = CompanyTarget(
                id=uuid.uuid4(),
                name=candidate.name_hint or candidate.ats_identifier,
                ats_provider=candidate.ats_provider,
                ats_identifier=candidate.ats_identifier,
                career_url=candidate.career_url,
            )
            provider = candidate.ats_provider

        collector: BaseCollector | None = None
        try:
            collector = self.collector_factory(provider, self.settings)
            jobs = await collector.fetch_jobs(target)
        except CollectorError as exc:
            with Session(self.engine) as session:
                candidate = session.get(SourceCandidate, candidate_id)
                if candidate is not None:
                    candidate.status = DiscoveryCandidateStatus.INVALID
                    candidate.last_validated_at = datetime.now(timezone.utc)
                    candidate.error_type = exc.category
                    candidate.error_message = str(exc)[:2000]
                    session.commit()
            return "invalid"
        except Exception as exc:
            with Session(self.engine) as session:
                candidate = session.get(SourceCandidate, candidate_id)
                if candidate is not None:
                    candidate.status = DiscoveryCandidateStatus.INVALID
                    candidate.last_validated_at = datetime.now(timezone.utc)
                    candidate.error_type = exc.__class__.__name__
                    candidate.error_message = str(exc)[:2000]
                    session.commit()
            return "invalid"
        finally:
            if collector is not None:
                await collector.close()

        with Session(self.engine) as session:
            candidate = session.get(SourceCandidate, candidate_id)
            if candidate is None:
                return "missing"
            candidate.status = DiscoveryCandidateStatus.VALID
            candidate.last_validated_at = datetime.now(timezone.utc)
            candidate.jobs_seen = len(jobs)
            candidate.error_type = None
            candidate.error_message = None
            session.commit()

        if auto_promote:
            self.promote_candidate(candidate_id)
            return "promoted"
        return "valid"

    def promote_candidate(self, candidate_id: uuid.UUID) -> Company:
        with Session(self.engine, expire_on_commit=False) as session:
            candidate = session.get(SourceCandidate, candidate_id)
            if candidate is None:
                raise ValueError("candidate not found")
            if candidate.status is not DiscoveryCandidateStatus.VALID:
                raise ValueError("candidate must be VALID before promotion")

            target = (
                session.get(DiscoveryTarget, candidate.discovery_target_id)
                if candidate.discovery_target_id
                else None
            )
            company = session.scalar(
                select(Company).where(
                    Company.ats_provider == candidate.ats_provider,
                    Company.ats_identifier == candidate.ats_identifier,
                )
            )
            if company is None:
                company = Company(
                    name=(candidate.name_hint or candidate.ats_identifier).strip(),
                    website=self._website_for_target(target),
                    career_url=candidate.career_url,
                    ats_provider=candidate.ats_provider,
                    ats_identifier=candidate.ats_identifier,
                    monitoring_priority=MonitoringPriority.LOW,
                    active=True,
                )
                session.add(company)
                session.flush()

            candidate.promoted_company_id = company.id
            candidate.promoted_at = datetime.now(timezone.utc)
            linked_targets = list(
                session.scalars(
                    select(DiscoveryTarget)
                    .join(
                        DiscoveryTargetCandidate,
                        DiscoveryTargetCandidate.discovery_target_id == DiscoveryTarget.id,
                    )
                    .where(DiscoveryTargetCandidate.source_candidate_id == candidate.id)
                )
            )
            if not linked_targets and target is not None:
                linked_targets = [target]
            for linked_target in linked_targets:
                if linked_target.auto_watch and linked_target.submitted_by_user_id:
                    self._ensure_watchlist(
                        session,
                        user_id=linked_target.submitted_by_user_id,
                        company_id=company.id,
                    )
            session.commit()
            session.refresh(company)
            return company

    def queue_system_feed_entries(
        self,
        entries: list[DiscoveryFeedEntry],
        *,
        source_label: str,
    ) -> dict[str, int]:
        """Queue feed entries without creating duplicate registry work.

        Direct ATS URLs are skipped when the provider/identifier already exists as a
        company or source candidate. Non-direct targets are refreshed only after the
        configured system-target refresh window.
        """
        summary = {"entries_seen": len(entries), "targets_queued": 0, "entries_existing": 0}
        refresh_before = datetime.now(timezone.utc) - timedelta(
            days=self.settings.discovery_system_target_refresh_days
        )
        with Session(self.engine, expire_on_commit=False) as session:
            for entry in entries:
                if len(entry.url) > 1500:
                    summary["entries_existing"] += 1
                    continue
                direct = detect_ats_source(entry.url)
                if direct is not None:
                    company_exists = session.scalar(
                        select(Company.id).where(
                            Company.ats_provider == direct.provider,
                            Company.ats_identifier == direct.identifier,
                        )
                    )
                    candidate_exists = session.scalar(
                        select(SourceCandidate.id).where(
                            SourceCandidate.ats_provider == direct.provider,
                            SourceCandidate.ats_identifier == direct.identifier,
                        )
                    )
                    if company_exists is not None or candidate_exists is not None:
                        summary["entries_existing"] += 1
                        continue

                existing = session.scalar(
                    select(DiscoveryTarget)
                    .where(
                        DiscoveryTarget.origin == DiscoveryTargetOrigin.SYSTEM_FEED,
                        DiscoveryTarget.url == entry.url,
                    )
                    .order_by(DiscoveryTarget.created_at.desc())
                )
                if existing is not None:
                    if (
                        existing.status in {DiscoveryTargetStatus.FAILED, DiscoveryTargetStatus.COMPLETE}
                        and (existing.last_scanned_at is None or existing.last_scanned_at <= refresh_before)
                    ):
                        existing.status = DiscoveryTargetStatus.PENDING
                        existing.company_name_hint = entry.company_name or existing.company_name_hint
                        existing.source_label = source_label
                        existing.error_type = None
                        existing.error_message = None
                        summary["targets_queued"] += 1
                    else:
                        summary["entries_existing"] += 1
                    continue

                session.add(
                    DiscoveryTarget(
                        submitted_by_user_id=None,
                        url=entry.url,
                        company_name_hint=entry.company_name,
                        auto_watch=False,
                        origin=DiscoveryTargetOrigin.SYSTEM_FEED,
                        source_label=source_label[:255],
                        status=DiscoveryTargetStatus.PENDING,
                    )
                )
                summary["targets_queued"] += 1
            session.commit()
        return summary

    async def ingest_system_feeds(self) -> dict[str, int]:
        """Ingest the bundled starter catalog and optional configured remote feeds."""
        summary = {
            "feeds_processed": 0,
            "feeds_failed": 0,
            "entries_seen": 0,
            "targets_queued": 0,
            "entries_existing": 0,
        }
        bundled = load_bundled_feed()[: self.settings.discovery_system_feed_max_entries]
        result = self.queue_system_feed_entries(bundled, source_label="bundled-starter")
        summary["feeds_processed"] += 1
        for key in ("entries_seen", "targets_queued", "entries_existing"):
            summary[key] += result[key]

        if self.settings.discovery_system_feed_url_list:
            fetcher = RemoteDiscoveryFeedFetcher(
                connect_timeout=self.settings.monitor_http_connect_timeout_seconds,
                read_timeout=self.settings.monitor_http_read_timeout_seconds,
                user_agent=self.settings.discovery_user_agent,
                max_bytes=self.settings.discovery_system_feed_max_bytes,
            )
            try:
                for url in self.settings.discovery_system_feed_url_list:
                    try:
                        entries = (await fetcher.fetch(url))[
                            : self.settings.discovery_system_feed_max_entries
                        ]
                        result = self.queue_system_feed_entries(entries, source_label=url)
                    except Exception:
                        logger.exception("system discovery feed ingestion failed", extra={"feed_url": url})
                        summary["feeds_failed"] += 1
                        continue
                    summary["feeds_processed"] += 1
                    for key in ("entries_seen", "targets_queued", "entries_existing"):
                        summary[key] += result[key]
            finally:
                await fetcher.close()
        return summary

    def candidate_ids_for_revalidation(self, *, limit: int) -> list[uuid.UUID]:
        due_before = datetime.now(timezone.utc) - timedelta(days=self.settings.discovery_revalidate_days)
        with Session(self.engine) as session:
            return list(
                session.scalars(
                    select(SourceCandidate.id)
                    .where(
                        SourceCandidate.promoted_company_id.is_not(None),
                        SourceCandidate.status == DiscoveryCandidateStatus.VALID,
                        or_(
                            SourceCandidate.last_validated_at.is_(None),
                            SourceCandidate.last_validated_at <= due_before,
                        ),
                    )
                    .order_by(SourceCandidate.last_validated_at.asc().nullsfirst())
                    .limit(limit)
                )
            )

    async def revalidate_candidate(self, candidate_id: uuid.UUID) -> str:
        """Revalidate a promoted source without disabling it on a transient failure."""
        with Session(self.engine, expire_on_commit=False) as session:
            candidate = session.get(SourceCandidate, candidate_id)
            if candidate is None or candidate.promoted_company_id is None:
                return "missing"
            target = CompanyTarget(
                id=candidate.promoted_company_id,
                name=candidate.name_hint or candidate.ats_identifier,
                ats_provider=candidate.ats_provider,
                ats_identifier=candidate.ats_identifier,
                career_url=candidate.career_url,
            )
            provider = candidate.ats_provider

        collector: BaseCollector | None = None
        now = datetime.now(timezone.utc)
        try:
            collector = self.collector_factory(provider, self.settings)
            jobs = await collector.fetch_jobs(target)
        except Exception as exc:
            with Session(self.engine) as session:
                candidate = session.get(SourceCandidate, candidate_id)
                if candidate is not None:
                    candidate.last_revalidated_at = now
                    candidate.revalidation_failure_count += 1
                    candidate.error_type = (
                        exc.category if isinstance(exc, CollectorError) else exc.__class__.__name__
                    )
                    candidate.error_message = str(exc)[:2000]
                    session.commit()
            return "revalidation_failed"
        finally:
            if collector is not None:
                await collector.close()

        with Session(self.engine) as session:
            candidate = session.get(SourceCandidate, candidate_id)
            if candidate is None:
                return "missing"
            candidate.status = DiscoveryCandidateStatus.VALID
            candidate.last_validated_at = now
            candidate.last_revalidated_at = now
            candidate.revalidation_failure_count = 0
            candidate.jobs_seen = len(jobs)
            candidate.error_type = None
            candidate.error_message = None
            session.commit()
        return "revalidated"

    def pending_target_ids(self, *, limit: int) -> list[uuid.UUID]:
        stale_before = datetime.now(timezone.utc) - timedelta(
            minutes=self.settings.discovery_stale_minutes
        )
        with Session(self.engine) as session:
            return list(
                session.scalars(
                    select(DiscoveryTarget.id)
                    .where(
                        or_(
                            DiscoveryTarget.status == DiscoveryTargetStatus.PENDING,
                            and_(
                                DiscoveryTarget.status == DiscoveryTargetStatus.SCANNING,
                                DiscoveryTarget.updated_at <= stale_before,
                            ),
                        )
                    )
                    .order_by(DiscoveryTarget.created_at.asc())
                    .limit(limit)
                )
            )

    def candidate_ids_for_validation(self, *, limit: int) -> list[uuid.UUID]:
        now = datetime.now(timezone.utc)
        stale_before = now - timedelta(minutes=self.settings.discovery_stale_minutes)
        retry_before = now - timedelta(days=self.settings.discovery_invalid_retry_days)
        system_candidate_ids = (
            select(DiscoveryTargetCandidate.source_candidate_id)
            .join(
                DiscoveryTarget,
                DiscoveryTarget.id == DiscoveryTargetCandidate.discovery_target_id,
            )
            .where(DiscoveryTarget.origin == DiscoveryTargetOrigin.SYSTEM_FEED)
        )
        with Session(self.engine) as session:
            return list(
                session.scalars(
                    select(SourceCandidate.id)
                    .where(
                        SourceCandidate.promoted_company_id.is_(None),
                        or_(
                            SourceCandidate.status == DiscoveryCandidateStatus.DISCOVERED,
                            and_(
                                SourceCandidate.status == DiscoveryCandidateStatus.VALIDATING,
                                SourceCandidate.updated_at <= stale_before,
                            ),
                            and_(
                                SourceCandidate.status == DiscoveryCandidateStatus.INVALID,
                                SourceCandidate.id.in_(system_candidate_ids),
                                SourceCandidate.last_validated_at.is_not(None),
                                SourceCandidate.last_validated_at <= retry_before,
                            ),
                        ),
                    )
                    .order_by(SourceCandidate.created_at.asc())
                    .limit(limit)
                )
            )

    def valid_candidate_ids_for_promotion(self, *, limit: int) -> list[uuid.UUID]:
        with Session(self.engine) as session:
            return list(
                session.scalars(
                    select(SourceCandidate.id)
                    .where(
                        SourceCandidate.status == DiscoveryCandidateStatus.VALID,
                        SourceCandidate.promoted_company_id.is_(None),
                    )
                    .order_by(SourceCandidate.created_at.asc())
                    .limit(limit)
                )
            )

    async def run(
        self,
        *,
        target_batch_size: int,
        candidate_batch_size: int,
        max_concurrency: int,
        auto_promote: bool,
        ingest_system_feeds: bool = False,
        revalidate_promoted: bool = False,
        revalidate_batch_size: int | None = None,
    ) -> dict[str, int]:
        semaphore = asyncio.Semaphore(max_concurrency)
        summary = {
            "targets_selected": 0,
            "targets_complete": 0,
            "targets_failed": 0,
            "candidates_selected": 0,
            "candidates_valid": 0,
            "candidates_invalid": 0,
            "candidates_promoted": 0,
            "system_feeds_processed": 0,
            "system_feeds_failed": 0,
            "system_entries_seen": 0,
            "system_targets_queued": 0,
            "system_entries_existing": 0,
            "revalidation_selected": 0,
            "revalidated": 0,
            "revalidation_failed": 0,
        }

        if ingest_system_feeds:
            feed_summary = await self.ingest_system_feeds()
            summary["system_feeds_processed"] = feed_summary["feeds_processed"]
            summary["system_feeds_failed"] = feed_summary["feeds_failed"]
            summary["system_entries_seen"] = feed_summary["entries_seen"]
            summary["system_targets_queued"] = feed_summary["targets_queued"]
            summary["system_entries_existing"] = feed_summary["entries_existing"]

        target_ids = self.pending_target_ids(limit=target_batch_size)
        summary["targets_selected"] = len(target_ids)

        async def scan(item_id: uuid.UUID) -> str:
            async with semaphore:
                return await self.scan_target(item_id)

        if target_ids:
            statuses = await asyncio.gather(*(scan(item_id) for item_id in target_ids))
            summary["targets_complete"] = statuses.count("complete")
            summary["targets_failed"] = statuses.count("failed")

        candidate_ids = self.candidate_ids_for_validation(limit=candidate_batch_size)
        summary["candidates_selected"] = len(candidate_ids)

        async def validate(item_id: uuid.UUID) -> str:
            async with semaphore:
                return await self.validate_candidate(item_id, auto_promote=auto_promote)

        if candidate_ids:
            statuses = await asyncio.gather(*(validate(item_id) for item_id in candidate_ids))
            summary["candidates_valid"] = statuses.count("valid") + statuses.count("promoted")
            summary["candidates_invalid"] = statuses.count("invalid")
            summary["candidates_promoted"] = statuses.count("promoted")

        if auto_promote:
            for candidate_id in self.valid_candidate_ids_for_promotion(
                limit=candidate_batch_size
            ):
                try:
                    self.promote_candidate(candidate_id)
                except Exception:
                    logger.exception(
                        "validated discovery candidate promotion failed",
                        extra={"candidate_id": str(candidate_id)},
                    )
                else:
                    summary["candidates_promoted"] += 1

        if revalidate_promoted:
            revalidation_ids = self.candidate_ids_for_revalidation(
                limit=revalidate_batch_size or self.settings.discovery_revalidate_batch_size
            )
            summary["revalidation_selected"] = len(revalidation_ids)

            async def revalidate(item_id: uuid.UUID) -> str:
                async with semaphore:
                    return await self.revalidate_candidate(item_id)

            if revalidation_ids:
                statuses = await asyncio.gather(*(revalidate(item_id) for item_id in revalidation_ids))
                summary["revalidated"] = statuses.count("revalidated")
                summary["revalidation_failed"] = statuses.count("revalidation_failed")
        return summary


def discovery_summary(session: Session) -> dict[str, int]:
    def count_targets(status: DiscoveryTargetStatus) -> int:
        return int(
            session.scalar(
                select(func.count()).select_from(DiscoveryTarget).where(DiscoveryTarget.status == status)
            )
            or 0
        )

    def count_candidates(status: DiscoveryCandidateStatus) -> int:
        return int(
            session.scalar(
                select(func.count()).select_from(SourceCandidate).where(SourceCandidate.status == status)
            )
            or 0
        )

    promoted = int(
        session.scalar(
            select(func.count())
            .select_from(SourceCandidate)
            .where(SourceCandidate.promoted_company_id.is_not(None))
        )
        or 0
    )
    system_targets = int(
        session.scalar(
            select(func.count())
            .select_from(DiscoveryTarget)
            .where(DiscoveryTarget.origin == DiscoveryTargetOrigin.SYSTEM_FEED)
        )
        or 0
    )
    system_promoted = int(
        session.scalar(
            select(func.count(func.distinct(SourceCandidate.id)))
            .select_from(SourceCandidate)
            .join(
                DiscoveryTargetCandidate,
                DiscoveryTargetCandidate.source_candidate_id == SourceCandidate.id,
            )
            .join(
                DiscoveryTarget,
                DiscoveryTarget.id == DiscoveryTargetCandidate.discovery_target_id,
            )
            .where(
                DiscoveryTarget.origin == DiscoveryTargetOrigin.SYSTEM_FEED,
                SourceCandidate.promoted_company_id.is_not(None),
            )
        )
        or 0
    )
    revalidation_failures = int(
        session.scalar(
            select(func.count())
            .select_from(SourceCandidate)
            .where(SourceCandidate.revalidation_failure_count > 0)
        )
        or 0
    )
    return {
        "pending_targets": count_targets(DiscoveryTargetStatus.PENDING),
        "failed_targets": count_targets(DiscoveryTargetStatus.FAILED),
        "discovered_candidates": count_candidates(DiscoveryCandidateStatus.DISCOVERED),
        "valid_candidates": count_candidates(DiscoveryCandidateStatus.VALID),
        "invalid_candidates": count_candidates(DiscoveryCandidateStatus.INVALID),
        "promoted_candidates": promoted,
        "system_targets": system_targets,
        "system_promoted_candidates": system_promoted,
        "revalidation_failures": revalidation_failures,
    }
