import asyncio
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.collectors.base import BaseCollector
from app.discovery.hiring import HiringSignal, PublicHiringSignalProvider
from app.matching.freshness import job_freshness_evidence
from app.models.company import Company
from app.models.discovery_target import DiscoveryTarget
from app.models.discovery_target_candidate import DiscoveryTargetCandidate
from app.models.enums import (
    ATSProvider,
    DiscoveryCandidateStatus,
    DiscoveryTargetOrigin,
    DiscoveryTargetStatus,
    MonitoringPriority,
    ProfileCoverageMode,
    WorkMode,
)
from app.models.job import Job
from app.models.job_match import JobMatch
from app.models.job_profile import JobProfile
from app.models.notification import Notification
from app.models.source_candidate import SourceCandidate
from app.models.telegram_connection import TelegramConnection
from app.models.user import User
from app.schemas.job import NormalizedJob
from app.services.discovery import DiscoveryService, discovery_summary
from app.services.discovery_signals import apply_discovery_signals_to_jobs
from app.services.monitor import MonitorService
from app.core.security import hash_password


class FakeHiringProvider:
    def __init__(self, signals: list[HiringSignal]) -> None:
        self.signals = signals
        self.search_terms: list[str] = []
        self.closed = False

    async def fetch(self, *, search_terms: list[str]) -> list[HiringSignal]:
        self.search_terms = search_terms
        return self.signals

    async def close(self) -> None:
        self.closed = True


def _wide_profile(session: Session, *, title: str = "Frontend Engineer") -> JobProfile:
    user = User(
        email=f"phase7-{uuid.uuid4()}@example.com",
        password_hash=hash_password("password123"),
        is_active=True,
    )
    session.add(user)
    session.flush()
    profile = JobProfile(
        user_id=user.id,
        name="Wide web",
        enabled=True,
        coverage_mode=ProfileCoverageMode.WIDE,
        job_titles=[title],
        locations=[],
        work_modes=[],
        excluded_keywords=[],
        max_job_age_days=30,
        include_unknown_posted_at=False,
    )
    session.add(profile)
    session.flush()
    return profile


async def test_wide_profiles_seed_relevant_fresh_hiring_targets(engine, settings) -> None:
    now = datetime.now(timezone.utc)
    with Session(engine) as session:
        _wide_profile(session)
        session.commit()

    signals = [
        HiringSignal(
            source="test-index",
            external_id="fresh-front-end",
            url="https://jobs.lever.co/freshco/role-1",
            company_name="Fresh Co",
            title="Senior Frontend Engineer",
            location="Remote",
            posted_at=now - timedelta(hours=3),
            remote=True,
        ),
        HiringSignal(
            source="test-index",
            external_id="wrong-title",
            url="https://jobs.lever.co/other/role-2",
            company_name="Other Co",
            title="Accountant",
            location="Remote",
            posted_at=now - timedelta(hours=1),
        ),
        HiringSignal(
            source="test-index",
            external_id="stale-front-end",
            url="https://jobs.lever.co/stale/role-3",
            company_name="Stale Co",
            title="Frontend Engineer",
            location="Remote",
            posted_at=now - timedelta(days=45),
        ),
    ]
    fake = FakeHiringProvider(signals)
    service = DiscoveryService(
        engine=engine,
        settings=settings,
        hiring_provider_factory=lambda _: fake,
    )
    summary = await service.ingest_hiring_signals()

    assert summary["profiles"] == 1
    assert summary["queries"] == 1
    assert summary["signals_seen"] == 3
    assert summary["signals_relevant"] == 1
    assert summary["targets_queued"] == 1
    assert fake.search_terms == ["Frontend Engineer"]
    assert fake.closed is True

    with Session(engine) as session:
        target = session.scalar(select(DiscoveryTarget))
        assert target is not None
        assert target.origin is DiscoveryTargetOrigin.SYSTEM_FEED
        assert target.submitted_by_user_id is None
        assert target.auto_watch is False
        assert target.source_label == "hiring-signal:test-index"
        assert target.signal_external_id == "fresh-front-end"
        assert target.job_title_hint == "Senior Frontend Engineer"
        assert target.job_posted_at_hint is not None


def test_hiring_signal_promotion_gets_temporary_monitoring_boost(engine, settings) -> None:
    now = datetime.now(timezone.utc)
    with Session(engine, expire_on_commit=False) as session:
        target = DiscoveryTarget(
            url="https://jobs.lever.co/freshco/role-1",
            origin=DiscoveryTargetOrigin.SYSTEM_FEED,
            source_label="hiring-signal:test-index",
            signal_external_id="fresh-role",
            job_title_hint="Frontend Engineer",
            job_posted_at_hint=now,
            company_name_hint="Fresh Co",
            auto_watch=False,
            status=DiscoveryTargetStatus.COMPLETE,
        )
        session.add(target)
        session.flush()
        candidate = SourceCandidate(
            discovery_target_id=target.id,
            name_hint="Fresh Co",
            ats_provider=ATSProvider.LEVER,
            ats_identifier="freshco",
            career_url="https://jobs.lever.co/freshco",
            source_url=target.url,
            status=DiscoveryCandidateStatus.VALID,
        )
        session.add(candidate)
        session.flush()
        session.add(
            DiscoveryTargetCandidate(
                discovery_target_id=target.id,
                source_candidate_id=candidate.id,
            )
        )
        session.commit()
        candidate_id = candidate.id

    company = DiscoveryService(engine=engine, settings=settings).promote_candidate(candidate_id)
    assert company.monitoring_priority is MonitoringPriority.LOW
    assert company.discovery_boost_until is not None
    boost_until = company.discovery_boost_until
    if boost_until.tzinfo is None:
        boost_until = boost_until.replace(tzinfo=timezone.utc)
    assert boost_until > now




async def test_hiring_signal_request_has_total_timeout(settings) -> None:
    class SlowClient:
        async def get_json(self, url, *, params=None):
            await asyncio.sleep(1)
            return {}

        async def close(self):
            return None

    bounded_settings = settings.model_copy(
        update={"discovery_hiring_request_total_timeout_seconds": 0.01}
    )
    provider = PublicHiringSignalProvider(settings=bounded_settings, client=SlowClient())

    with pytest.raises(asyncio.TimeoutError):
        await provider._get_json_bounded("https://example.invalid/feed")

def test_himalayas_millisecond_timestamp_is_normalized() -> None:
    now = datetime.now(timezone.utc).replace(microsecond=0)
    signal = PublicHiringSignalProvider._himalayas_signal(
        {
            "guid": "remote-role-1",
            "title": "Frontend Engineer",
            "companyName": "Remote Co",
            "companySlug": "remote-co",
            "applicationLink": "https://himalayas.app/companies/remote-co/jobs/frontend-engineer",
            "pubDate": int(now.timestamp() * 1000),
            "locationRestrictions": [
                {"alpha2": "US", "name": "United States", "slug": "united-states"}
            ],
        }
    )

    assert signal is not None
    assert signal.posted_at == now
    assert signal.location == "United States"
    assert signal.company_slug == "remote-co"


def test_himalayas_signal_is_resolved_to_direct_ats_probes_without_html_crawl(
    engine, settings
) -> None:
    now = datetime.now(timezone.utc)
    with Session(engine) as session:
        _wide_profile(session)
        session.commit()

    signal = HiringSignal(
        source="himalayas",
        external_id="gitlab-role-1",
        url="https://himalayas.app/companies/gitlab-com/jobs/frontend-engineer",
        company_name="GitLab.com",
        company_slug="gitlab-com",
        title="Frontend Engineer",
        location="Remote",
        posted_at=now - timedelta(hours=1),
    )
    service = DiscoveryService(engine=engine, settings=settings)
    summary = service.queue_hiring_signals([signal], profiles=service.active_wide_profiles())

    assert summary["signals_relevant"] == 1
    assert summary["targets_resolved"] == 1
    assert summary["probe_candidates_staged"] > 0
    assert service.pending_target_ids(limit=100) == []

    with Session(engine) as session:
        target = session.scalar(select(DiscoveryTarget))
        assert target is not None
        assert target.status is DiscoveryTargetStatus.COMPLETE
        assert target.pages_scanned == 0
        assert target.error_type is None
        candidates = list(
            session.scalars(
                select(SourceCandidate)
                .join(
                    DiscoveryTargetCandidate,
                    DiscoveryTargetCandidate.source_candidate_id == SourceCandidate.id,
                )
                .where(DiscoveryTargetCandidate.discovery_target_id == target.id)
            )
        )
        assert any(
            item.ats_provider is ATSProvider.GREENHOUSE and item.ats_identifier == "gitlab"
            for item in candidates
        )


def test_existing_failed_himalayas_target_is_repaired_without_retrying_html(
    engine, settings
) -> None:
    now = datetime.now(timezone.utc)
    with Session(engine, expire_on_commit=False) as session:
        profile = _wide_profile(session)
        target = DiscoveryTarget(
            url="https://himalayas.app/companies/clickhouse/jobs/frontend-engineer",
            origin=DiscoveryTargetOrigin.SYSTEM_FEED,
            source_label="hiring-signal:himalayas",
            signal_external_id="clickhouse-role",
            company_name_hint="ClickHouse",
            job_title_hint="Frontend Engineer",
            job_posted_at_hint=now - timedelta(hours=2),
            auto_watch=False,
            status=DiscoveryTargetStatus.FAILED,
            error_type="RuntimeError",
            error_message="discovery page returned HTTP 403",
        )
        session.add(target)
        session.commit()
        target_id = target.id
        profile_id = profile.id

    signal = HiringSignal(
        source="himalayas",
        external_id="clickhouse-role",
        url="https://himalayas.app/companies/clickhouse/jobs/frontend-engineer",
        company_name="ClickHouse",
        company_slug="clickhouse",
        title="Frontend Engineer",
        location="Remote",
        posted_at=now - timedelta(hours=2),
    )
    with Session(engine) as session:
        profile = session.get(JobProfile, profile_id)
        assert profile is not None
        summary = DiscoveryService(engine=engine, settings=settings).queue_hiring_signals(
            [signal], profiles=[profile]
        )

    assert summary["targets_existing"] == 1
    assert summary["targets_resolved"] == 1
    with Session(engine) as session:
        repaired = session.get(DiscoveryTarget, target_id)
        assert repaired is not None
        assert repaired.status is DiscoveryTargetStatus.COMPLETE
        assert repaired.error_type is None
        assert repaired.error_message is None
        assert repaired.pages_scanned == 0


async def test_hiring_probe_requires_signal_title_before_promotion(engine, settings) -> None:
    now = datetime.now(timezone.utc)
    with Session(engine, expire_on_commit=False) as session:
        target = DiscoveryTarget(
            url="https://himalayas.app/companies/example/jobs/frontend-engineer",
            origin=DiscoveryTargetOrigin.SYSTEM_FEED,
            source_label="hiring-signal:himalayas",
            signal_external_id="example-role",
            company_name_hint="Example",
            job_title_hint="Frontend Engineer",
            job_posted_at_hint=now,
            auto_watch=False,
            status=DiscoveryTargetStatus.COMPLETE,
        )
        session.add(target)
        session.flush()
        candidate = SourceCandidate(
            discovery_target_id=target.id,
            name_hint="Example",
            ats_provider=ATSProvider.GREENHOUSE,
            ats_identifier="example",
            career_url="https://boards.greenhouse.io/example",
            source_url="https://boards.greenhouse.io/example",
            status=DiscoveryCandidateStatus.DISCOVERED,
        )
        session.add(candidate)
        session.flush()
        session.add(
            DiscoveryTargetCandidate(
                discovery_target_id=target.id,
                source_candidate_id=candidate.id,
            )
        )
        session.commit()
        candidate_id = candidate.id

    class WrongTenantCollector(BaseCollector):
        async def fetch_jobs(self, company):
            return [
                NormalizedJob(
                    company_id=company.id,
                    ats_provider=ATSProvider.GREENHOUSE,
                    external_job_id="backend-1",
                    title="Backend Engineer",
                    location="Remote",
                    work_mode=WorkMode.REMOTE,
                    apply_url="https://boards.greenhouse.io/example/jobs/backend-1",
                    source_url="https://boards.greenhouse.io/example/jobs/backend-1",
                    posted_at=None,
                )
            ]

    service = DiscoveryService(
        engine=engine,
        settings=settings,
        collector_factory=lambda provider, config: WrongTenantCollector(),
    )
    assert await service.validate_candidate(candidate_id, auto_promote=True) == "invalid"
    with Session(engine) as session:
        candidate = session.get(SourceCandidate, candidate_id)
        assert candidate is not None
        assert candidate.status is DiscoveryCandidateStatus.INVALID
        assert candidate.error_type == "signal-mismatch"
        assert candidate.promoted_company_id is None


def test_discovery_boost_routes_low_company_through_normal_tier(engine, settings) -> None:
    now = datetime.now(timezone.utc)
    with Session(engine, expire_on_commit=False) as session:
        normal = Company(
            name="Normal Co",
            career_url="https://jobs.lever.co/normal-co",
            ats_provider=ATSProvider.LEVER,
            ats_identifier="normal-co",
            monitoring_priority=MonitoringPriority.NORMAL,
            active=True,
        )
        boosted = Company(
            name="Boosted Co",
            career_url="https://jobs.lever.co/boosted-co",
            ats_provider=ATSProvider.LEVER,
            ats_identifier="boosted-co",
            monitoring_priority=MonitoringPriority.LOW,
            discovery_boost_until=now + timedelta(days=2),
            active=True,
        )
        expired = Company(
            name="Expired Co",
            career_url="https://jobs.lever.co/expired-co",
            ats_provider=ATSProvider.LEVER,
            ats_identifier="expired-co",
            monitoring_priority=MonitoringPriority.LOW,
            discovery_boost_until=now - timedelta(hours=1),
            active=True,
        )
        low = Company(
            name="Low Co",
            career_url="https://jobs.lever.co/low-co",
            ats_provider=ATSProvider.LEVER,
            ats_identifier="low-co",
            monitoring_priority=MonitoringPriority.LOW,
            active=True,
        )
        session.add_all([normal, boosted, expired, low])
        session.commit()
        expected_normal = {normal.id, boosted.id}
        expected_low = {expired.id, low.id}

    service = MonitorService(engine=engine, settings=settings)
    assert set(service.eligible_company_ids(priority=MonitoringPriority.NORMAL)) == expected_normal
    assert set(service.eligible_company_ids(priority=MonitoringPriority.LOW)) == expected_low

def test_signal_evidence_makes_only_unambiguous_baseline_job_fresh(engine, company) -> None:
    now = datetime.now(timezone.utc)
    with Session(engine, expire_on_commit=False) as session:
        db_company = session.get(Company, company.id)
        target = DiscoveryTarget(
            url="https://boards.greenhouse.io/example/jobs/123",
            origin=DiscoveryTargetOrigin.SYSTEM_FEED,
            source_label="hiring-signal:test-index",
            signal_external_id="role-123",
            job_title_hint="Frontend Engineer",
            job_location_hint="Remote",
            job_posted_at_hint=now - timedelta(hours=2),
            auto_watch=False,
            status=DiscoveryTargetStatus.COMPLETE,
        )
        session.add(target)
        session.flush()
        candidate = SourceCandidate(
            discovery_target_id=target.id,
            ats_provider=ATSProvider.GREENHOUSE,
            ats_identifier="example",
            career_url=db_company.career_url,
            source_url=target.url,
            status=DiscoveryCandidateStatus.VALID,
            promoted_company_id=db_company.id,
            promoted_at=now,
        )
        session.add(candidate)
        session.flush()
        session.add(
            DiscoveryTargetCandidate(
                discovery_target_id=target.id,
                source_candidate_id=candidate.id,
            )
        )
        matching = Job(
            company_id=db_company.id,
            ats_provider=ATSProvider.GREENHOUSE,
            external_job_id="123",
            title="Frontend Engineer",
            location="Remote",
            work_mode=WorkMode.REMOTE,
            apply_url=target.url,
            source_url=target.url,
            posted_at=None,
            baseline_imported=True,
            first_seen_at=now,
            last_seen_at=now,
            fingerprint="a" * 64,
        )
        unrelated = Job(
            company_id=db_company.id,
            ats_provider=ATSProvider.GREENHOUSE,
            external_job_id="456",
            title="Backend Engineer",
            location="Remote",
            work_mode=WorkMode.REMOTE,
            apply_url="https://boards.greenhouse.io/example/jobs/456",
            source_url="https://boards.greenhouse.io/example/jobs/456",
            posted_at=None,
            baseline_imported=True,
            first_seen_at=now,
            last_seen_at=now,
            fingerprint="b" * 64,
        )
        session.add_all([matching, unrelated])
        session.flush()

        alertable = apply_discovery_signals_to_jobs(
            session,
            company_id=db_company.id,
            job_ids=[matching.id, unrelated.id],
            max_signal_age_days=30,
            now=now,
        )
        assert alertable == [matching.id]
        assert job_freshness_evidence(matching).source == "DISCOVERY_SIGNAL"
        assert job_freshness_evidence(unrelated).source == "UNKNOWN"


def test_provider_posted_at_still_wins_over_discovery_signal(company) -> None:
    now = datetime.now(timezone.utc)
    job = Job(
        company_id=company.id,
        ats_provider=ATSProvider.GREENHOUSE,
        external_job_id="provider-date",
        title="Frontend Engineer",
        location="Remote",
        work_mode=WorkMode.REMOTE,
        apply_url="https://example.com/provider-date",
        source_url="https://example.com/provider-date",
        posted_at=now - timedelta(days=10),
        discovery_signal_at=now - timedelta(hours=1),
        discovery_signal_source="hiring-signal:test",
        baseline_imported=True,
        first_seen_at=now,
        last_seen_at=now,
        fingerprint="c" * 64,
    )
    evidence = job_freshness_evidence(job)
    assert evidence.source == "POSTED_AT"
    assert evidence.at == job.posted_at


async def test_initial_sync_alerts_only_signal_identified_baseline_match(engine, settings, company) -> None:
    now = datetime.now(timezone.utc)
    with Session(engine, expire_on_commit=False) as session:
        user = User(
            email="phase7-alert@example.com",
            password_hash=hash_password("password123"),
            is_active=True,
        )
        session.add(user)
        session.flush()
        session.add(
            JobProfile(
                user_id=user.id,
                name="Wide frontend",
                enabled=True,
                coverage_mode=ProfileCoverageMode.WIDE,
                job_titles=["frontend engineer"],
                locations=[],
                work_modes=[],
                excluded_keywords=[],
                max_job_age_days=30,
                include_unknown_posted_at=True,
            )
        )
        session.add(
            TelegramConnection(
                user_id=user.id,
                telegram_user_id=111,
                telegram_chat_id=222,
                verified=True,
                connected_at=now,
            )
        )
        target = DiscoveryTarget(
            url="https://boards.greenhouse.io/example/jobs/phase7-fresh",
            origin=DiscoveryTargetOrigin.SYSTEM_FEED,
            source_label="hiring-signal:test-index",
            signal_external_id="phase7-fresh",
            job_title_hint="Frontend Engineer",
            job_location_hint="Remote",
            job_posted_at_hint=now - timedelta(hours=1),
            auto_watch=False,
            status=DiscoveryTargetStatus.COMPLETE,
        )
        session.add(target)
        session.flush()
        candidate = SourceCandidate(
            discovery_target_id=target.id,
            ats_provider=ATSProvider.GREENHOUSE,
            ats_identifier="example",
            career_url=company.career_url,
            source_url=target.url,
            status=DiscoveryCandidateStatus.VALID,
            promoted_company_id=company.id,
            promoted_at=now,
        )
        session.add(candidate)
        session.flush()
        session.add(
            DiscoveryTargetCandidate(
                discovery_target_id=target.id,
                source_candidate_id=candidate.id,
            )
        )
        session.commit()

    class BaselineCollector(BaseCollector):
        async def fetch_jobs(self, target):
            return [
                NormalizedJob(
                    company_id=target.id,
                    ats_provider=ATSProvider.GREENHOUSE,
                    external_job_id="phase7-fresh",
                    title="Frontend Engineer",
                    location="Remote",
                    work_mode=WorkMode.REMOTE,
                    apply_url="https://boards.greenhouse.io/example/jobs/phase7-fresh",
                    source_url="https://boards.greenhouse.io/example/jobs/phase7-fresh",
                    posted_at=None,
                ),
                NormalizedJob(
                    company_id=target.id,
                    ats_provider=ATSProvider.GREENHOUSE,
                    external_job_id="old-baseline",
                    title="Senior Frontend Engineer",
                    location="Remote",
                    work_mode=WorkMode.REMOTE,
                    apply_url="https://boards.greenhouse.io/example/jobs/old-baseline",
                    source_url="https://boards.greenhouse.io/example/jobs/old-baseline",
                    posted_at=None,
                ),
            ]

    service = MonitorService(
        engine=engine,
        settings=settings,
        collector_factory=lambda provider, config: BaselineCollector(),
    )
    assert await service.run_company(company.id) == "success"

    with Session(engine) as session:
        assert session.scalar(select(func.count(JobMatch.id))) == 2
        notifications = list(session.scalars(select(Notification)))
        assert len(notifications) == 1
        notified_job = session.get(Job, notifications[0].job_id)
        assert notified_job is not None
        assert notified_job.external_job_id == "phase7-fresh"
        old = session.scalar(select(Job).where(Job.external_job_id == "old-baseline"))
        assert old is not None
        assert old.discovery_signal_at is None


def test_phase7_summary_and_workflow_surface_active_hiring(engine) -> None:
    with Session(engine) as session:
        summary = discovery_summary(session)
    assert summary["hiring_signal_targets"] == 0
    assert summary["hiring_signal_promoted_sources"] == 0
    assert summary["fresh_signal_jobs"] == 0

    workflow = Path(__file__).parents[2] / ".github" / "workflows" / "discovery.yml"
    text = workflow.read_text(encoding="utf-8")
    assert 'cron: "23 0 * * *"' in text
    assert 'cron: "23 6 * * *"' in text
    assert "DISCOVERY_HIRING_HIMALAYAS_ENABLED" in text
    assert "--ingest-hiring-signals" in text
