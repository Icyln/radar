import asyncio
import hashlib
import logging
import re
import unicodedata
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
from app.discovery.detector import DetectedSource, detect_ats_source
from app.discovery.feeds import DiscoveryFeedEntry, RemoteDiscoveryFeedFetcher, load_bundled_feed
from app.discovery.hiring import HiringSignal, HiringSignalProvider, PublicHiringSignalProvider
from app.matching.service import backfill_watchlist_profiles_for_company, create_matches_for_jobs
from app.models.company import Company
from app.models.discovery_target import DiscoveryTarget
from app.models.discovery_target_candidate import DiscoveryTargetCandidate
from app.models.discovery_run import DiscoveryRun
from app.models.enums import (
    ATSProvider,
    CrawlerStatus,
    DiscoveryCandidateStatus,
    DiscoveryTargetOrigin,
    DiscoveryTargetStatus,
    MonitoringPriority,
    ProfileCoverageMode,
    JobStatus,
    WorkMode,
)
from app.models.job import Job
from app.models.job_source_observation import JobSourceObservation
from app.models.job_match import JobMatch
from app.models.job_profile import JobProfile
from app.models.source_candidate import SourceCandidate
from app.models.user import User
from app.models.user_company_watchlist import UserCompanyWatchlist
from app.schemas.company import CompanyTarget
from app.services.notifications import deliver_pending_notifications, enqueue_match_notifications
from app.services.text import normalize_for_match

logger = logging.getLogger(__name__)
CollectorFactory = Callable[[ATSProvider, Settings], BaseCollector]
HiringProviderFactory = Callable[[Settings], HiringSignalProvider]


class DiscoveryService:
    _CORPORATE_SUFFIXES = {
        "inc",
        "incorporated",
        "llc",
        "ltd",
        "limited",
        "corp",
        "corporation",
        "company",
        "co",
        "plc",
        "gmbh",
        "com",
    }

    def __init__(
        self,
        *,
        engine: Engine,
        settings: Settings,
        collector_factory: CollectorFactory = build_collector,
        crawler_factory: Callable[[], TargetCrawler] | None = None,
        hiring_provider_factory: HiringProviderFactory | None = None,
    ) -> None:
        self.engine = engine
        self.settings = settings
        self.collector_factory = collector_factory
        self._crawler_factory = crawler_factory
        self._hiring_provider_factory = hiring_provider_factory or (
            lambda settings: PublicHiringSignalProvider(settings=settings)
        )

    def _build_crawler(self) -> TargetCrawler:
        if self._crawler_factory is not None:
            return self._crawler_factory()
        fetcher = SafeHtmlFetcher(
            connect_timeout=self.settings.monitor_http_connect_timeout_seconds,
            read_timeout=self.settings.monitor_http_read_timeout_seconds,
            user_agent=self.settings.discovery_user_agent,
            max_bytes=self.settings.discovery_html_max_bytes,
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

    def _extend_hiring_boost(
        self, company: Company, target: DiscoveryTarget | None
    ) -> None:
        if target is None or target.job_posted_at_hint is None:
            return
        signal_at = target.job_posted_at_hint
        if signal_at.tzinfo is None:
            signal_at = signal_at.replace(tzinfo=timezone.utc)
        else:
            signal_at = signal_at.astimezone(timezone.utc)
        boost_until = signal_at + timedelta(days=self.settings.discovery_hiring_priority_boost_days)
        now = datetime.now(timezone.utc)
        if boost_until <= now:
            return
        current = company.discovery_boost_until
        if current is not None:
            if current.tzinfo is None:
                current = current.replace(tzinfo=timezone.utc)
            else:
                current = current.astimezone(timezone.utc)
        if current is None or boost_until > current:
            company.discovery_boost_until = boost_until

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
            result = await asyncio.wait_for(
                crawler.scan(
                    target_url, max_pages=self.settings.discovery_max_pages_per_target
                ),
                timeout=self.settings.discovery_target_total_timeout_seconds,
            )
        except asyncio.TimeoutError:
            error_type = "TimeoutError"
            error_message = (
                "target scan exceeded "
                f"{self.settings.discovery_target_total_timeout_seconds:g}s total timeout"
            )
            with Session(self.engine) as session:
                target = session.get(DiscoveryTarget, target_id)
                if target is not None:
                    target.status = DiscoveryTargetStatus.FAILED
                    target.last_scanned_at = datetime.now(timezone.utc)
                    target.error_type = error_type
                    target.error_message = error_message
                    session.commit()
            logger.warning(
                "discovery target scan failed: %s (%s: %s)",
                target_url,
                error_type,
                error_message,
            )
            return "failed"
        except Exception as exc:
            error_type = exc.__class__.__name__
            error_message = str(exc) or repr(exc)
            with Session(self.engine) as session:
                target = session.get(DiscoveryTarget, target_id)
                if target is not None:
                    target.status = DiscoveryTargetStatus.FAILED
                    target.last_scanned_at = datetime.now(timezone.utc)
                    target.error_type = error_type
                    target.error_message = error_message[:2000]
                    session.commit()
            logger.warning(
                "discovery target scan failed: %s (%s: %s)",
                target_url,
                error_type,
                error_message[:500],
            )
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
                if company is not None:
                    self._extend_hiring_boost(company, target)
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
            jobs = await asyncio.wait_for(
                collector.fetch_jobs(target),
                timeout=self.settings.discovery_candidate_total_timeout_seconds,
            )
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
            hiring_targets = list(
                session.scalars(
                    select(DiscoveryTarget)
                    .join(
                        DiscoveryTargetCandidate,
                        DiscoveryTargetCandidate.discovery_target_id == DiscoveryTarget.id,
                    )
                    .where(
                        DiscoveryTargetCandidate.source_candidate_id == candidate_id,
                        DiscoveryTarget.source_label.like("hiring-signal:%"),
                        DiscoveryTarget.job_title_hint.is_not(None),
                    )
                )
            )

        if hiring_targets:
            job_titles = {normalize_for_match(job.title) for job in jobs if job.title}
            signal_titles = {
                normalize_for_match(target.job_title_hint)
                for target in hiring_targets
                if target.job_title_hint
            }
            signal_titles.discard("")
            if not job_titles.intersection(signal_titles):
                with Session(self.engine) as session:
                    candidate = session.get(SourceCandidate, candidate_id)
                    if candidate is not None:
                        candidate.status = DiscoveryCandidateStatus.INVALID
                        candidate.last_validated_at = datetime.now(timezone.utc)
                        candidate.error_type = "signal-mismatch"
                        candidate.error_message = (
                            "ATS tenant probe did not contain any fresh hiring-signal title; "
                            "candidate rejected to prevent company-slug collisions"
                        )
                        session.commit()
                return "invalid"

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
            for linked_target in linked_targets:
                self._extend_hiring_boost(company, linked_target)
                if (
                    linked_target.source_label
                    and linked_target.source_label.startswith("hiring-signal:")
                    and linked_target.signal_external_id
                ):
                    source_provider = linked_target.source_label.split(":", 1)[1][:100]
                    wide_job = session.scalar(
                        select(Job).where(
                            Job.source_provider == source_provider,
                            Job.source_external_id == linked_target.signal_external_id,
                        )
                    )
                    if wide_job is not None and wide_job.company_id is None:
                        # Preserve WIDE provenance while attaching the newly verified
                        # employer. The next direct monitor can upgrade this same row.
                        wide_job.company_id = company.id

            candidate.promoted_company_id = company.id
            candidate.promoted_at = datetime.now(timezone.utc)
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

    def active_wide_profiles(self, *, user_id: uuid.UUID | None = None) -> list[JobProfile]:
        with Session(self.engine) as session:
            statement = (
                select(JobProfile)
                .join(User, User.id == JobProfile.user_id)
                .where(
                    JobProfile.enabled.is_(True),
                    JobProfile.coverage_mode == ProfileCoverageMode.WIDE,
                    User.is_active.is_(True),
                )
                .order_by(JobProfile.created_at.asc())
            )
            if user_id is not None:
                statement = statement.where(JobProfile.user_id == user_id)
            return list(session.scalars(statement))

    def hiring_search_terms(self, profiles: list[JobProfile]) -> list[str]:
        """Return a fair rotating slice of unique active search terms.

        The previous implementation always selected the first N titles by profile
        creation time. Once the global query cap was reached, later users could be
        starved indefinitely. Radar now deduplicates all terms, interleaves users,
        and rotates the capped window hourly. No extra queue/database service is
        needed at the intended 50-100 user scale.
        """
        per_user: dict[uuid.UUID, list[tuple[str, str]]] = {}
        global_seen: set[str] = set()
        for profile in profiles:
            bucket = per_user.setdefault(profile.user_id, [])
            for title in profile.job_titles or []:
                clean = title.strip()
                normalized = normalize_for_match(clean)
                if not normalized or normalized in global_seen:
                    continue
                global_seen.add(normalized)
                bucket.append((normalized, clean))

        # Interleave one term per user at a time so one account cannot consume the
        # entire discovery budget before another account is considered.
        ordered: list[str] = []
        user_ids = list(per_user)
        round_index = 0
        while True:
            added = False
            for user_id in user_ids:
                values = per_user[user_id]
                if round_index < len(values):
                    ordered.append(values[round_index][1])
                    added = True
            if not added:
                break
            round_index += 1

        cap = self.settings.discovery_hiring_max_queries
        if len(ordered) <= cap:
            return ordered

        hour_bucket = int(datetime.now(timezone.utc).timestamp() // 3600)
        start = (hour_bucket * cap) % len(ordered)
        return [ordered[(start + index) % len(ordered)] for index in range(cap)]

    @staticmethod
    def _signal_matches_title(signal: HiringSignal, profile: JobProfile) -> bool:
        signal_tokens = set(normalize_for_match(signal.title).split())
        if not signal_tokens:
            return False
        for title in profile.job_titles or []:
            wanted = set(normalize_for_match(title).split())
            if wanted and wanted.issubset(signal_tokens):
                return True
        return False

    def _signal_matches_profile(
        self,
        signal: HiringSignal,
        profile: JobProfile,
        *,
        now: datetime,
    ) -> bool:
        if signal.posted_at is None or not self._signal_matches_title(signal, profile):
            return False
        posted_at = signal.posted_at
        if posted_at.tzinfo is None:
            posted_at = posted_at.replace(tzinfo=timezone.utc)
        else:
            posted_at = posted_at.astimezone(timezone.utc)
        if posted_at > now + timedelta(days=1):
            return False
        max_age = self.settings.discovery_hiring_max_age_days
        if profile.max_job_age_days is not None:
            max_age = min(max_age, profile.max_job_age_days)
        return posted_at >= now - timedelta(days=max_age)

    @staticmethod
    def _wide_job_fingerprint(signal: HiringSignal) -> str:
        raw = f"wide|{signal.source}|{signal.external_id}".encode()
        return hashlib.sha256(raw).hexdigest()

    @classmethod
    def _company_match_key(cls, value: str | None) -> str:
        slug = cls._slugify_company_identifier(value)
        if not slug:
            return ""
        tokens = slug.split("-")
        while tokens and tokens[-1] in cls._CORPORATE_SUFFIXES:
            tokens.pop()
        return "-".join(tokens) or slug

    @staticmethod
    def _locations_compatible(left: str | None, right: str | None) -> bool:
        left_norm = normalize_for_match(left or "")
        right_norm = normalize_for_match(right or "")
        if not left_norm or not right_norm:
            return True
        return (
            left_norm == right_norm
            or left_norm in right_norm
            or right_norm in left_norm
        )

    def _cross_source_job_candidate(
        self,
        session: Session,
        *,
        signal: HiringSignal,
        now: datetime,
    ) -> Job | None:
        """Find one conservative duplicate across discovery feeds or a direct ATS row.

        Cross-source identity is intentionally stricter than profile matching: same
        normalized company, exact normalized title, compatible location, and (when
        both sides expose one) publication dates within three days. Ambiguous results
        are never merged.
        """
        wanted_company = self._company_match_key(signal.company_name or signal.company_slug)
        wanted_title = normalize_for_match(signal.title)
        if not wanted_company or not wanted_title:
            return None
        cutoff = now - timedelta(days=self.settings.discovery_wide_dedup_window_days)
        rows = session.execute(
            select(Job, Company.name)
            .outerjoin(Company, Company.id == Job.company_id)
            .where(
                Job.status != JobStatus.CLOSED,
                Job.last_seen_at >= cutoff,
            )
        ).all()
        candidates: list[Job] = []
        for job, company_name in rows:
            existing_company = company_name or job.source_company_name
            if self._company_match_key(existing_company) != wanted_company:
                continue
            if normalize_for_match(job.title) != wanted_title:
                continue
            if not self._locations_compatible(job.location, signal.location):
                continue
            if job.posted_at is not None and signal.posted_at is not None:
                left = job.posted_at
                right = signal.posted_at
                if left.tzinfo is None:
                    left = left.replace(tzinfo=timezone.utc)
                if right.tzinfo is None:
                    right = right.replace(tzinfo=timezone.utc)
                if abs((left.astimezone(timezone.utc) - right.astimezone(timezone.utc)).total_seconds()) > 259200:
                    continue
            candidates.append(job)
        return candidates[0] if len(candidates) == 1 else None

    @staticmethod
    def _upsert_wide_observation(
        session: Session,
        *,
        job: Job,
        signal: HiringSignal,
        now: datetime,
    ) -> JobSourceObservation:
        provider = signal.source[:255]
        external_id = signal.external_id[:500]
        observation = session.scalar(
            select(JobSourceObservation).where(
                JobSourceObservation.source_provider == provider,
                JobSourceObservation.source_external_id == external_id,
            )
        )
        company_name = (signal.company_name or signal.company_slug or "Unknown company")[:255]
        if observation is None:
            observation = JobSourceObservation(
                job_id=job.id,
                source_kind="WIDE_DISCOVERY",
                source_provider=provider,
                source_external_id=external_id,
                source_url=signal.url[:2000],
                apply_url=signal.url[:2000],
                company_name=company_name,
                posted_at=signal.posted_at,
                first_seen_at=now,
                last_seen_at=now,
                verified=False,
            )
            session.add(observation)
        else:
            observation.job_id = job.id
            observation.source_url = signal.url[:2000]
            observation.apply_url = signal.url[:2000]
            observation.company_name = company_name
            observation.posted_at = signal.posted_at
            observation.last_seen_at = now
        return observation

    def apply_wide_job_lifecycle(self, *, now: datetime | None = None) -> dict[str, int]:
        """Age discovery-feed jobs conservatively without deleting history.

        A job becomes UNKNOWN when Radar has not observed it for the configured grace
        period and CLOSED after the longer retirement window. Any later source
        observation reactivates the WIDE row during ingestion. Direct ATS rows retain
        their authoritative snapshot lifecycle.
        """
        observed_at = now or datetime.now(timezone.utc)
        unknown_before = observed_at - timedelta(
            days=self.settings.discovery_wide_unknown_after_days
        )
        close_before = observed_at - timedelta(
            days=self.settings.discovery_wide_close_after_days
        )
        summary = {"jobs_marked_unknown": 0, "jobs_closed": 0}
        with Session(self.engine) as session:
            jobs = list(
                session.scalars(
                    select(Job).where(
                        Job.source_kind == "WIDE_DISCOVERY",
                        Job.status != JobStatus.CLOSED,
                    )
                )
            )
            for job in jobs:
                last_seen = job.last_seen_at
                if last_seen.tzinfo is None:
                    last_seen = last_seen.replace(tzinfo=timezone.utc)
                freshness_at = job.posted_at or job.discovery_signal_at
                if freshness_at is not None and freshness_at.tzinfo is None:
                    freshness_at = freshness_at.replace(tzinfo=timezone.utc)
                should_close = last_seen <= close_before or (
                    freshness_at is not None and freshness_at <= close_before
                )
                if should_close:
                    job.status = JobStatus.CLOSED
                    job.closed_at = observed_at
                    summary["jobs_closed"] += 1
                elif last_seen <= unknown_before and job.status == JobStatus.ACTIVE:
                    job.status = JobStatus.UNKNOWN
                    job.closed_at = None
                    summary["jobs_marked_unknown"] += 1
            session.commit()
        return summary

    def _relevant_hiring_signals(
        self,
        signals: list[HiringSignal],
        *,
        profiles: list[JobProfile],
    ) -> list[HiringSignal]:
        if not profiles:
            return []
        now = datetime.now(timezone.utc)
        relevant: list[HiringSignal] = []
        for signal in signals:
            if len(signal.url) > 2000:
                continue
            if any(self._signal_matches_profile(signal, profile, now=now) for profile in profiles):
                relevant.append(signal)
                if len(relevant) >= self.settings.discovery_hiring_max_signals_per_run:
                    break
        return relevant

    def ingest_hiring_signal_jobs(
        self,
        signals: list[HiringSignal],
        *,
        profiles: list[JobProfile],
    ) -> dict[str, int | list[uuid.UUID]]:
        """Persist fresh WIDE jobs first, with cross-source duplicate convergence."""
        relevant = self._relevant_hiring_signals(signals, profiles=profiles)
        summary: dict[str, int | list[uuid.UUID]] = {
            "signals_relevant": len(relevant),
            "jobs_new": 0,
            "jobs_updated": 0,
            "jobs_existing": 0,
            "jobs_deduplicated": 0,
            "matches_created": 0,
            "notifications_queued": 0,
            "_notification_ids": [],
        }
        if not relevant:
            return summary

        now = datetime.now(timezone.utc)
        profile_ids = [profile.id for profile in profiles]
        touched_ids: list[uuid.UUID] = []
        new_ids: list[uuid.UUID] = []
        with Session(self.engine, expire_on_commit=False) as session:
            for signal in relevant:
                source_provider = signal.source[:255]
                source_external_id = signal.external_id[:500]
                observation = session.scalar(
                    select(JobSourceObservation).where(
                        JobSourceObservation.source_provider == source_provider,
                        JobSourceObservation.source_external_id == source_external_id,
                    )
                )
                job = session.get(Job, observation.job_id) if observation is not None else None
                merged_cross_source = False
                if job is None:
                    # Backward compatibility for a database that has not yet received the
                    # 0010 observation backfill during an in-process test/upgrade.
                    job = session.scalar(
                        select(Job).where(
                            Job.source_provider == source_provider[:100],
                            Job.source_external_id == source_external_id,
                        )
                    )
                if job is None:
                    job = self._cross_source_job_candidate(session, signal=signal, now=now)
                    merged_cross_source = job is not None

                company_name = (signal.company_name or signal.company_slug or "Unknown company")[:255]
                work_mode = WorkMode.REMOTE if signal.remote is True else WorkMode.UNKNOWN
                employment_type = (signal.employment_type or "").strip()[:100] or None
                description = signal.description

                if job is None:
                    job = Job(
                        company_id=None,
                        ats_provider=None,
                        external_job_id=None,
                        title=signal.title[:500],
                        description=description,
                        location=(signal.location or "")[:500] or None,
                        work_mode=work_mode,
                        employment_type=employment_type,
                        apply_url=signal.url[:2000],
                        source_url=signal.url[:2000],
                        posted_at=signal.posted_at,
                        discovery_signal_at=signal.posted_at,
                        discovery_signal_source=source_provider[:100],
                        source_kind="WIDE_DISCOVERY",
                        source_provider=source_provider[:100],
                        source_external_id=source_external_id,
                        source_company_name=company_name,
                        baseline_imported=False,
                        first_seen_at=now,
                        last_seen_at=now,
                        missing_count=0,
                        status=JobStatus.ACTIVE,
                        fingerprint=self._wide_job_fingerprint(signal),
                    )
                    session.add(job)
                    session.flush()
                    self._upsert_wide_observation(session, job=job, signal=signal, now=now)
                    summary["jobs_new"] = int(summary["jobs_new"]) + 1
                    new_ids.append(job.id)
                else:
                    self._upsert_wide_observation(session, job=job, signal=signal, now=now)
                    if merged_cross_source:
                        summary["jobs_deduplicated"] = int(summary["jobs_deduplicated"]) + 1

                    # A direct ATS row is authoritative. The discovery observation is
                    # retained for provenance, but cannot overwrite or reactivate it.
                    if job.source_kind == "DIRECT_ATS":
                        summary["jobs_existing"] = int(summary["jobs_existing"]) + 1
                        touched_ids.append(job.id)
                        continue

                    changed = False
                    updates = {
                        "title": signal.title[:500],
                        "description": description,
                        "location": (signal.location or "")[:500] or None,
                        "work_mode": work_mode,
                        "employment_type": employment_type,
                        "apply_url": signal.url[:2000],
                        "source_url": signal.url[:2000],
                        "posted_at": signal.posted_at,
                        "discovery_signal_at": signal.posted_at,
                        "discovery_signal_source": source_provider[:100],
                        "source_company_name": company_name,
                    }
                    for field, value in updates.items():
                        current_value = getattr(job, field)
                        if isinstance(current_value, datetime) and isinstance(value, datetime):
                            left = current_value if current_value.tzinfo else current_value.replace(tzinfo=timezone.utc)
                            right = value if value.tzinfo else value.replace(tzinfo=timezone.utc)
                            same = left.astimezone(timezone.utc) == right.astimezone(timezone.utc)
                        else:
                            same = current_value == value
                        if not same:
                            setattr(job, field, value)
                            changed = True
                    job.last_seen_at = now
                    job.status = JobStatus.ACTIVE
                    job.closed_at = None
                    if changed:
                        summary["jobs_updated"] = int(summary["jobs_updated"]) + 1
                    else:
                        summary["jobs_existing"] = int(summary["jobs_existing"]) + 1
                touched_ids.append(job.id)

            match_result = create_matches_for_jobs(
                session,
                job_ids=list(dict.fromkeys(touched_ids)),
                profile_ids=profile_ids,
            )
            summary["matches_created"] = match_result.created
            if new_ids and match_result.match_ids:
                new_match_ids = list(
                    session.scalars(
                        select(JobMatch.id).where(
                            JobMatch.id.in_(match_result.match_ids),
                            JobMatch.job_id.in_(new_ids),
                        )
                    )
                )
                notification_ids = enqueue_match_notifications(session, match_ids=new_match_ids)
                summary["notifications_queued"] = len(notification_ids)
                summary["_notification_ids"] = notification_ids
            session.commit()
        return summary

    @classmethod
    def _slugify_company_identifier(cls, value: str | None) -> str | None:
        if not value:
            return None
        normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
        slug = re.sub(r"[^a-z0-9]+", "-", normalized.casefold()).strip("-")
        return slug or None

    @classmethod
    def _company_identifier_guesses(
        cls,
        signal: HiringSignal,
        *,
        limit: int,
    ) -> list[str]:
        """Return a small, deterministic set of plausible public ATS tenant slugs.

        Hiring indexes expose company identity but often intentionally keep their own
        application URL. We therefore probe supported ATS APIs directly instead of
        crawling the index's HTML page. Guesses are always corroborated against the
        signal job title before promotion, so a slug collision cannot silently add an
        unrelated employer.
        """
        guesses: list[str] = []
        seen: set[str] = set()

        def add(value: str | None) -> None:
            slug = cls._slugify_company_identifier(value)
            if not slug or slug in seen or len(guesses) >= limit:
                return
            seen.add(slug)
            guesses.append(slug)

        bases = [signal.company_slug, signal.company_name]
        for base in bases:
            slug = cls._slugify_company_identifier(base)
            if not slug:
                continue
            add(slug)
            tokens = slug.split("-")
            while tokens and tokens[-1] in cls._CORPORATE_SUFFIXES:
                tokens.pop()
            stripped = "-".join(tokens)
            add(stripped)
            add(stripped.replace("-", "") if stripped else None)
            if len(guesses) >= limit:
                break
        return guesses

    def _hiring_probe_sources(self, signal: HiringSignal) -> list[DetectedSource]:
        """Resolve a signal to exact or bounded guessed direct ATS sources.

        Crucially, aggregator job URLs (for example Himalayas application pages) are
        never sent to the HTML crawler. Himalayas documents applicationLink as a
        Himalayas application page, so crawling it is both unnecessary and commonly
        blocked with HTTP 403.
        """
        exact: dict[tuple[ATSProvider, str], DetectedSource] = {}
        direct = detect_ats_source(signal.url)
        if direct is not None:
            exact[(direct.provider, direct.identifier)] = direct
        for source in signal.ats_sources:
            exact[(source.provider, source.identifier)] = source
        if exact:
            return list(exact.values())

        providers = list(signal.provider_hints) or [
            ATSProvider.GREENHOUSE,
            ATSProvider.ASHBY,
            ATSProvider.LEVER,
        ]
        guesses = self._company_identifier_guesses(
            signal,
            limit=self.settings.discovery_hiring_max_identifier_guesses,
        )
        results: list[DetectedSource] = []
        for identifier in guesses:
            for provider in providers:
                if provider is ATSProvider.GREENHOUSE:
                    career_url = f"https://boards.greenhouse.io/{identifier}"
                elif provider is ATSProvider.ASHBY:
                    career_url = f"https://jobs.ashbyhq.com/{identifier}"
                else:
                    career_url = f"https://jobs.lever.co/{identifier}"
                results.append(
                    DetectedSource(
                        provider=provider,
                        identifier=identifier,
                        career_url=career_url,
                        source_url=career_url,
                    )
                )
        return results

    def _stage_hiring_candidate(
        self,
        session: Session,
        *,
        target: DiscoveryTarget,
        source: DetectedSource,
    ) -> tuple[bool, bool]:
        """Create/link one direct ATS candidate. Returns (created, linked)."""
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
        created = False
        if candidate is None:
            candidate = SourceCandidate(
                discovery_target_id=target.id,
                name_hint=target.company_name_hint,
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
                promoted_at=datetime.now(timezone.utc) if company is not None else None,
            )
            session.add(candidate)
            session.flush()
            created = True
        elif company is not None and candidate.promoted_company_id is None:
            # A company may already be present from the starter/system registry even
            # when an older speculative probe for the same tenant was invalid. The
            # registry identity is authoritative here, so attach the signal to that
            # known company instead of leaving freshness evidence stranded.
            candidate.status = DiscoveryCandidateStatus.VALID
            candidate.promoted_company_id = company.id
            candidate.promoted_at = datetime.now(timezone.utc)
            candidate.career_url = company.career_url
            candidate.error_type = None
            candidate.error_message = None
            session.flush()

        link = session.get(DiscoveryTargetCandidate, (target.id, candidate.id))
        linked = False
        if link is None:
            session.add(
                DiscoveryTargetCandidate(
                    discovery_target_id=target.id,
                    source_candidate_id=candidate.id,
                )
            )
            session.flush()
            linked = True

        if company is not None:
            self._extend_hiring_boost(company, target)
        return created, linked

    def queue_hiring_signals(
        self,
        signals: list[HiringSignal],
        *,
        profiles: list[JobProfile],
    ) -> dict[str, int]:
        summary = {
            "signals_seen": len(signals),
            "signals_relevant": 0,
            "targets_queued": 0,
            "targets_existing": 0,
            "targets_resolved": 0,
            "probe_candidates_staged": 0,
            "probe_candidates_existing": 0,
        }
        if not profiles:
            return summary
        now = datetime.now(timezone.utc)
        with Session(self.engine, expire_on_commit=False) as session:
            for signal in signals:
                if len(signal.url) > 1500 or not any(
                    self._signal_matches_profile(signal, profile, now=now) for profile in profiles
                ):
                    continue
                if summary["signals_relevant"] >= self.settings.discovery_hiring_max_signals_per_run:
                    break
                summary["signals_relevant"] += 1
                source_label = f"hiring-signal:{signal.source}"[:255]
                existing = session.scalar(
                    select(DiscoveryTarget)
                    .where(
                        DiscoveryTarget.origin == DiscoveryTargetOrigin.SYSTEM_FEED,
                        DiscoveryTarget.source_label == source_label,
                        DiscoveryTarget.signal_external_id == signal.external_id[:500],
                    )
                    .order_by(DiscoveryTarget.created_at.desc())
                )
                if existing is None:
                    target = DiscoveryTarget(
                        submitted_by_user_id=None,
                        url=signal.url,
                        company_name_hint=signal.company_name,
                        auto_watch=False,
                        origin=DiscoveryTargetOrigin.SYSTEM_FEED,
                        source_label=source_label,
                        signal_external_id=signal.external_id[:500],
                        job_title_hint=signal.title[:500],
                        job_location_hint=(signal.location or "")[:500] or None,
                        job_posted_at_hint=signal.posted_at,
                        # Hiring signals are resolved directly to ATS probes;
                        # the public index page itself is provenance, not a crawl target.
                        status=DiscoveryTargetStatus.COMPLETE,
                    )
                    session.add(target)
                    session.flush()
                    summary["targets_queued"] += 1
                else:
                    target = existing
                    target.url = signal.url
                    target.company_name_hint = signal.company_name or target.company_name_hint
                    target.job_title_hint = signal.title[:500]
                    target.job_location_hint = (signal.location or "")[:500] or None
                    target.job_posted_at_hint = signal.posted_at
                    summary["targets_existing"] += 1

                sources = self._hiring_probe_sources(signal)
                for source in sources:
                    existing_candidate_id = session.scalar(
                        select(SourceCandidate.id).where(
                            SourceCandidate.ats_provider == source.provider,
                            SourceCandidate.ats_identifier == source.identifier,
                        )
                    )
                    if (
                        existing_candidate_id is None
                        and summary["probe_candidates_staged"]
                        >= self.settings.discovery_hiring_max_probe_candidates_per_run
                    ):
                        continue
                    created, linked = self._stage_hiring_candidate(
                        session,
                        target=target,
                        source=source,
                    )
                    if created:
                        summary["probe_candidates_staged"] += 1
                    else:
                        summary["probe_candidates_existing"] += 1

                # Repair older targets that predate direct ATS probe resolution.
                # Those targets pointed at Himalayas/Arbeitnow HTML and commonly
                # ended as HTTP 403/timeout failures. They now become completed
                # provenance records linked to direct ATS candidates.
                target.status = DiscoveryTargetStatus.COMPLETE
                target.last_scanned_at = now
                target.pages_scanned = 0
                target.sources_found = int(
                    session.scalar(
                        select(func.count(DiscoveryTargetCandidate.source_candidate_id)).where(
                            DiscoveryTargetCandidate.discovery_target_id == target.id
                        )
                    )
                    or 0
                )
                target.error_type = None
                target.error_message = None
                summary["targets_resolved"] += 1
            session.commit()
        return summary

    async def ingest_hiring_signals(
        self, *, user_id: uuid.UUID | None = None
    ) -> dict[str, int | list[str] | list[uuid.UUID]]:
        profiles = self.active_wide_profiles(user_id=user_id)
        terms = self.hiring_search_terms(profiles)
        summary: dict[str, int | list[str] | list[uuid.UUID]] = {
            "profiles": len(profiles),
            "queries": len(terms),
            "signals_seen": 0,
            "signals_relevant": 0,
            "jobs_new": 0,
            "jobs_updated": 0,
            "jobs_existing": 0,
            "jobs_deduplicated": 0,
            "matches_created": 0,
            "notifications_queued": 0,
            "targets_queued": 0,
            "targets_existing": 0,
            "targets_resolved": 0,
            "probe_candidates_staged": 0,
            "probe_candidates_existing": 0,
            "provider_failed": 0,
            "provider_warnings": [],
            "provider_successes": [],
            "provider_pages": 0,
            "jobs_marked_unknown": 0,
            "jobs_closed": 0,
            "_notification_ids": [],
        }
        if not profiles or not terms:
            return summary

        provider = self._hiring_provider_factory(self.settings)
        try:
            signals = await provider.fetch(search_terms=terms)
        except Exception as exc:
            logger.warning(
                "profile-driven hiring signal ingestion unavailable: %s: %s",
                exc.__class__.__name__,
                str(exc) or repr(exc),
            )
            summary["provider_failed"] = 1
            summary["provider_warnings"] = [
                f"provider: {exc.__class__.__name__}: {str(exc) or repr(exc)}"[:500]
            ]
            return summary
        finally:
            try:
                await provider.close()
            except Exception as exc:
                logger.warning("hiring signal provider close failed: %s", exc)

        failures = list(getattr(provider, "failed_sources", []) or [])
        failed_provider_names = set(getattr(provider, "failed_provider_names", set()) or set())
        successes = sorted(set(getattr(provider, "successful_sources", set()) or set()))
        pages = getattr(provider, "pages_fetched", {}) or {}
        summary["provider_failed"] = len(failed_provider_names) or (1 if failures and not successes else 0)
        summary["provider_warnings"] = failures
        summary["provider_successes"] = successes
        summary["provider_pages"] = sum(int(value) for value in pages.values())
        summary["signals_seen"] = len(signals)

        job_summary = self.ingest_hiring_signal_jobs(signals, profiles=profiles)
        summary["signals_relevant"] = job_summary["signals_relevant"]
        for key in (
            "jobs_new",
            "jobs_updated",
            "jobs_existing",
            "jobs_deduplicated",
            "matches_created",
            "notifications_queued",
        ):
            summary[key] = job_summary[key]
        summary["_notification_ids"] = list(job_summary.get("_notification_ids", []))

        # ATS resolution remains a parallel upgrade path. These targets/candidates are
        # staged after jobs are already usable, so an unresolved company never blocks WIDE.
        queued = self.queue_hiring_signals(signals, profiles=profiles)
        for key in (
            "targets_queued",
            "targets_existing",
            "targets_resolved",
            "probe_candidates_staged",
            "probe_candidates_existing",
        ):
            summary[key] = queued[key]

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
            jobs = await asyncio.wait_for(
                collector.fetch_jobs(target),
                timeout=self.settings.discovery_candidate_total_timeout_seconds,
            )
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

    def start_discovery_run(
        self, *, trigger: str | None = None, external_run_id: str | None = None
    ) -> uuid.UUID:
        with Session(self.engine, expire_on_commit=False) as session:
            item = DiscoveryRun(
                started_at=datetime.now(timezone.utc),
                status=CrawlerStatus.FAILED,
                trigger=trigger,
                external_run_id=external_run_id,
            )
            session.add(item)
            session.commit()
            return item.id

    def complete_discovery_run(
        self,
        run_id: uuid.UUID,
        *,
        summary: dict[str, object],
        error: Exception | None = None,
    ) -> CrawlerStatus:
        def number(*keys: str) -> int:
            for key in keys:
                value = summary.get(key)
                if isinstance(value, bool):
                    continue
                if isinstance(value, (int, float)):
                    return int(value)
            return 0

        warnings_value = summary.get("hiring_provider_warnings", summary.get("provider_warnings", []))
        warnings = [str(item)[:500] for item in warnings_value] if isinstance(warnings_value, list) else []
        provider_failures = number("hiring_provider_failed", "provider_failed")
        if error is not None:
            status = CrawlerStatus.FAILED
        elif (
            provider_failures
            or number("system_feeds_failed")
            or number("targets_failed")
            or number("revalidation_failed")
        ):
            status = CrawlerStatus.PARTIAL
        elif not any(
            number(key)
            for key in (
                "hiring_profiles",
                "profiles",
                "targets_selected",
                "candidates_selected",
                "revalidation_selected",
                "system_entries_seen",
            )
        ):
            status = CrawlerStatus.SKIPPED
        else:
            status = CrawlerStatus.SUCCESS

        with Session(self.engine) as session:
            item = session.get(DiscoveryRun, run_id)
            if item is not None:
                item.completed_at = datetime.now(timezone.utc)
                item.status = status
                item.profiles = number("hiring_profiles", "profiles")
                item.queries = number("hiring_queries", "queries")
                item.signals_seen = number("hiring_signals_seen", "signals_seen")
                item.signals_relevant = number("hiring_signals_relevant", "signals_relevant")
                item.jobs_new = number("wide_jobs_new", "jobs_new")
                item.jobs_updated = number("wide_jobs_updated", "jobs_updated")
                item.jobs_existing = number("wide_jobs_existing", "jobs_existing")
                item.jobs_deduplicated = number("wide_jobs_deduplicated", "jobs_deduplicated")
                item.matches_created = number("wide_matches_created", "matches_created")
                item.notifications_sent = number("wide_notifications_sent", "notifications_sent")
                item.provider_failures = provider_failures
                item.provider_warnings = "\n".join(warnings) or None
                item.candidates_promoted = number("candidates_promoted")
                item.jobs_marked_unknown = number("wide_jobs_marked_unknown", "jobs_marked_unknown")
                item.jobs_closed = number("wide_jobs_closed", "jobs_closed")
                if error is not None:
                    item.error_type = error.__class__.__name__
                    item.error_message = str(error)[:2000]
                session.commit()
        return status

    async def run(
        self,
        *,
        target_batch_size: int,
        candidate_batch_size: int,
        max_concurrency: int,
        auto_promote: bool,
        ingest_system_feeds: bool = False,
        ingest_hiring_signals: bool = False,
        revalidate_promoted: bool = False,
        revalidate_batch_size: int | None = None,
    ) -> dict[str, object]:
        run_id = self.start_discovery_run(
            trigger=self.settings.discovery_run_trigger,
            external_run_id=self.settings.discovery_external_run_id,
        )
        try:
            summary = await self._run_core(
                target_batch_size=target_batch_size,
                candidate_batch_size=candidate_batch_size,
                max_concurrency=max_concurrency,
                auto_promote=auto_promote,
                ingest_system_feeds=ingest_system_feeds,
                ingest_hiring_signals=ingest_hiring_signals,
                revalidate_promoted=revalidate_promoted,
                revalidate_batch_size=revalidate_batch_size,
            )
        except Exception as exc:
            self.complete_discovery_run(run_id, summary={}, error=exc)
            raise
        self.complete_discovery_run(run_id, summary=summary)
        summary["discovery_run_id"] = str(run_id)
        return summary

    async def _run_core(
        self,
        *,
        target_batch_size: int,
        candidate_batch_size: int,
        max_concurrency: int,
        auto_promote: bool,
        ingest_system_feeds: bool = False,
        ingest_hiring_signals: bool = False,
        revalidate_promoted: bool = False,
        revalidate_batch_size: int | None = None,
    ) -> dict[str, object]:
        semaphore = asyncio.Semaphore(max_concurrency)
        summary: dict[str, object] = {
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
            "hiring_profiles": 0,
            "hiring_queries": 0,
            "hiring_signals_seen": 0,
            "hiring_signals_relevant": 0,
            "wide_jobs_new": 0,
            "wide_jobs_updated": 0,
            "wide_jobs_existing": 0,
            "wide_jobs_deduplicated": 0,
            "wide_jobs_marked_unknown": 0,
            "wide_jobs_closed": 0,
            "wide_matches_created": 0,
            "wide_notifications_queued": 0,
            "wide_notifications_sent": 0,
            "hiring_targets_queued": 0,
            "hiring_targets_existing": 0,
            "hiring_targets_resolved": 0,
            "hiring_probe_candidates_staged": 0,
            "hiring_probe_candidates_existing": 0,
            "hiring_provider_failed": 0,
            "hiring_provider_warnings": [],
            "hiring_provider_successes": [],
            "hiring_provider_pages": 0,
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

        if ingest_hiring_signals and self.settings.discovery_hiring_signals_enabled:
            hiring_summary = await self.ingest_hiring_signals()
            summary["hiring_profiles"] = hiring_summary["profiles"]
            summary["hiring_queries"] = hiring_summary["queries"]
            summary["hiring_signals_seen"] = hiring_summary["signals_seen"]
            summary["hiring_signals_relevant"] = int(hiring_summary["signals_relevant"])
            summary["wide_jobs_new"] = int(hiring_summary["jobs_new"])
            summary["wide_jobs_updated"] = int(hiring_summary["jobs_updated"])
            summary["wide_jobs_existing"] = int(hiring_summary["jobs_existing"])
            summary["wide_jobs_deduplicated"] = int(hiring_summary["jobs_deduplicated"])
            summary["wide_jobs_marked_unknown"] = int(hiring_summary["jobs_marked_unknown"])
            summary["wide_jobs_closed"] = int(hiring_summary["jobs_closed"])
            summary["wide_matches_created"] = int(hiring_summary["matches_created"])
            summary["wide_notifications_queued"] = int(hiring_summary["notifications_queued"])
            notification_ids = list(hiring_summary.get("_notification_ids", []))
            if notification_ids:
                summary["wide_notifications_sent"] = await deliver_pending_notifications(
                    engine=self.engine,
                    settings=self.settings,
                    notification_ids=notification_ids,
                )
            summary["hiring_targets_queued"] = int(hiring_summary["targets_queued"])
            summary["hiring_targets_existing"] = hiring_summary["targets_existing"]
            summary["hiring_targets_resolved"] = hiring_summary["targets_resolved"]
            summary["hiring_probe_candidates_staged"] = hiring_summary[
                "probe_candidates_staged"
            ]
            summary["hiring_probe_candidates_existing"] = hiring_summary[
                "probe_candidates_existing"
            ]
            summary["hiring_provider_failed"] = int(hiring_summary["provider_failed"])
            summary["hiring_provider_warnings"] = list(hiring_summary.get("provider_warnings", []))
            summary["hiring_provider_successes"] = list(hiring_summary.get("provider_successes", []))
            summary["hiring_provider_pages"] = int(hiring_summary.get("provider_pages", 0))

            lifecycle = self.apply_wide_job_lifecycle()
            summary["wide_jobs_marked_unknown"] = lifecycle["jobs_marked_unknown"]
            summary["wide_jobs_closed"] = lifecycle["jobs_closed"]

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
    hiring_signal_targets = int(
        session.scalar(
            select(func.count())
            .select_from(DiscoveryTarget)
            .where(DiscoveryTarget.job_title_hint.is_not(None))
        )
        or 0
    )
    hiring_signal_promoted_sources = int(
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
                DiscoveryTarget.job_title_hint.is_not(None),
                SourceCandidate.promoted_company_id.is_not(None),
            )
        )
        or 0
    )
    fresh_signal_jobs = int(
        session.scalar(
            select(func.count()).select_from(Job).where(Job.discovery_signal_at.is_not(None))
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
        "hiring_signal_targets": hiring_signal_targets,
        "hiring_signal_promoted_sources": hiring_signal_promoted_sources,
        "fresh_signal_jobs": fresh_signal_jobs,
    }
