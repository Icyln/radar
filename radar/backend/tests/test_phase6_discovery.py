import uuid
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.collectors.base import BaseCollector, CollectorError
from app.discovery.crawler import DiscoveryScanResult
from app.discovery.detector import DetectedSource, detect_ats_source
from app.models.company import Company
from app.models.discovery_target import DiscoveryTarget
from app.models.enums import (
    ATSProvider,
    DiscoveryCandidateStatus,
    DiscoveryTargetStatus,
    ProfileCoverageMode,
    WorkMode,
)
from app.models.job_profile import JobProfile
from app.models.source_candidate import SourceCandidate
from app.models.user import User
from app.models.user_company_watchlist import UserCompanyWatchlist
from app.schemas.job import NormalizedJob
from app.services.discovery import DiscoveryService


def register(client, email: str) -> dict:
    response = client.post(
        "/api/v1/auth/register", json={"email": email, "password": "password123"}
    )
    assert response.status_code == 201, response.text
    return response.json()


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_direct_ats_url_detection() -> None:
    greenhouse = detect_ats_source("https://boards.greenhouse.io/cloudflare/jobs/123")
    assert greenhouse is not None
    assert greenhouse.provider is ATSProvider.GREENHOUSE
    assert greenhouse.identifier == "cloudflare"
    embedded = detect_ats_source(
        "https://boards.greenhouse.io/embed/job_board?for=cloudflare"
    )
    assert embedded is not None
    assert embedded.identifier == "cloudflare"

    lever = detect_ats_source("https://jobs.eu.lever.co/example/abc")
    assert lever is not None
    assert lever.provider is ATSProvider.LEVER
    assert lever.identifier == "example"
    assert "jobs.eu.lever.co" in lever.career_url

    ashby = detect_ats_source("https://jobs.ashbyhq.com/Example/123")
    assert ashby is not None
    assert ashby.provider is ATSProvider.ASHBY
    assert ashby.identifier == "Example"


class FakeFetcher:
    async def close(self) -> None:
        return None


@dataclass
class FakeCrawler:
    result: DiscoveryScanResult

    def __post_init__(self) -> None:
        self.fetcher = FakeFetcher()

    async def scan(self, url: str, *, max_pages: int):
        return self.result


class ValidCollector(BaseCollector):
    async def fetch_jobs(self, company):
        return [
            NormalizedJob(
                company_id=company.id,
                ats_provider=company.ats_provider,
                external_job_id="job-1",
                title="Frontend Engineer",
                location="Remote",
                work_mode=WorkMode.REMOTE,
                apply_url="https://example.com/apply",
                source_url="https://example.com/job",
            )
        ]


class InvalidCollector(BaseCollector):
    async def fetch_jobs(self, company):
        raise CollectorError("board not found", category="configuration")


def valid_factory(provider, settings):
    return ValidCollector()


def invalid_factory(provider, settings):
    return InvalidCollector()


async def test_discovery_scans_validates_promotes_and_auto_watches(engine, settings) -> None:
    with Session(engine, expire_on_commit=False) as session:
        user = User(
            email="discover@example.com",
            password_hash="not-used",
            is_active=True,
        )
        session.add(user)
        session.flush()
        session.add(
            JobProfile(
                user_id=user.id,
                name="Watchlist web",
                enabled=True,
                coverage_mode=ProfileCoverageMode.WATCHLIST,
                job_titles=["frontend engineer"],
                locations=[],
                work_modes=[],
                excluded_keywords=[],
            )
        )
        target = DiscoveryTarget(
            submitted_by_user_id=user.id,
            url="https://example.com/careers",
            company_name_hint="Example",
            auto_watch=True,
        )
        session.add(target)
        session.commit()
        target_id = target.id
        user_id = user.id

    source = DetectedSource(
        ATSProvider.LEVER,
        "example",
        "https://jobs.lever.co/example",
        "https://jobs.lever.co/example",
    )
    service = DiscoveryService(
        engine=engine,
        settings=settings,
        collector_factory=valid_factory,
        crawler_factory=lambda: FakeCrawler(DiscoveryScanResult([source], 2, "Example Careers")),
    )
    assert await service.scan_target(target_id) == "complete"

    with Session(engine, expire_on_commit=False) as session:
        target = session.get(DiscoveryTarget, target_id)
        assert target is not None
        assert target.status is DiscoveryTargetStatus.COMPLETE
        assert target.sources_found == 1
        candidate = session.scalar(select(SourceCandidate))
        assert candidate is not None
        assert candidate.status is DiscoveryCandidateStatus.DISCOVERED
        candidate_id = candidate.id

    assert await service.validate_candidate(candidate_id, auto_promote=True) == "promoted"

    with Session(engine) as session:
        candidate = session.get(SourceCandidate, candidate_id)
        assert candidate is not None
        assert candidate.status is DiscoveryCandidateStatus.VALID
        assert candidate.jobs_seen == 1
        assert candidate.promoted_company_id is not None
        company = session.get(Company, candidate.promoted_company_id)
        assert company is not None
        assert company.ats_provider is ATSProvider.LEVER
        assert company.ats_identifier == "example"
        assert company.active is True
        watch = session.scalar(
            select(UserCompanyWatchlist).where(
                UserCompanyWatchlist.user_id == user_id,
                UserCompanyWatchlist.company_id == company.id,
            )
        )
        assert watch is not None


async def test_invalid_candidate_is_not_promoted(engine, settings) -> None:
    with Session(engine, expire_on_commit=False) as session:
        target = DiscoveryTarget(url="https://jobs.lever.co/missing", auto_watch=False)
        session.add(target)
        session.flush()
        candidate = SourceCandidate(
            discovery_target_id=target.id,
            ats_provider=ATSProvider.LEVER,
            ats_identifier="missing",
            career_url="https://jobs.lever.co/missing",
            source_url="https://jobs.lever.co/missing",
        )
        session.add(candidate)
        session.commit()
        candidate_id = candidate.id

    service = DiscoveryService(engine=engine, settings=settings, collector_factory=invalid_factory)
    assert await service.validate_candidate(candidate_id, auto_promote=True) == "invalid"
    with Session(engine) as session:
        candidate = session.get(SourceCandidate, candidate_id)
        assert candidate is not None
        assert candidate.status is DiscoveryCandidateStatus.INVALID
        assert candidate.promoted_company_id is None
        assert session.scalar(select(Company.id)) is None


def test_discovery_api_is_authenticated_and_user_scoped(client) -> None:
    first = register(client, "first-discovery@example.com")
    second = register(client, "second-discovery@example.com")
    assert client.post(
        "/api/v1/discovery/targets",
        json={"url": "https://example.com/careers"},
    ).status_code == 401

    created = client.post(
        "/api/v1/discovery/targets",
        headers=auth(first["access_token"]),
        json={
            "url": "https://example.com/careers",
            "company_name_hint": "Example",
            "auto_watch": True,
        },
    )
    assert created.status_code == 202, created.text
    assert len(client.get("/api/v1/discovery/targets", headers=auth(first["access_token"])).json()) == 1
    assert client.get("/api/v1/discovery/targets", headers=auth(second["access_token"])).json() == []
    assert client.get("/api/v1/discovery/candidates", headers=auth(first["access_token"])).status_code == 403


def test_phase6_discovery_workflow_is_bounded_and_database_only() -> None:
    workflow = Path(__file__).parents[2] / ".github" / "workflows" / "discovery.yml"
    text = workflow.read_text(encoding="utf-8")
    assert 'cron: "23 3 * * *"' in text
    assert "workflow_dispatch:" in text
    assert "secrets.DATABASE_URL" in text
    assert "TELEGRAM_BOT_TOKEN" not in text
    assert "--target-batch-size 25" in text
    assert "--candidate-batch-size 50" in text
    assert "--max-concurrency 3" in text
    assert "--auto-promote" in text

async def test_discovery_rejects_private_network_urls() -> None:
    from app.discovery.security import UnsafeDiscoveryUrl, ensure_public_url

    try:
        await ensure_public_url("http://127.0.0.1/careers")
    except UnsafeDiscoveryUrl as exc:
        assert "non-public" in str(exc)
    else:
        raise AssertionError("private loopback URL should be rejected")


async def test_multiple_requests_share_candidate_and_all_auto_watch(engine, settings) -> None:
    with Session(engine, expire_on_commit=False) as session:
        users = [
            User(email="one@example.com", password_hash="x", is_active=True),
            User(email="two@example.com", password_hash="x", is_active=True),
        ]
        session.add_all(users)
        session.flush()
        targets = [
            DiscoveryTarget(
                submitted_by_user_id=user.id,
                url=f"https://company.example/careers?request={index}",
                company_name_hint="Shared Company",
                auto_watch=True,
            )
            for index, user in enumerate(users)
        ]
        session.add_all(targets)
        session.commit()
        target_ids = [item.id for item in targets]
        user_ids = [item.id for item in users]

    source = DetectedSource(
        ATSProvider.GREENHOUSE,
        "shared-company",
        "https://boards.greenhouse.io/shared-company",
        "https://boards.greenhouse.io/shared-company",
    )
    service = DiscoveryService(
        engine=engine,
        settings=settings,
        collector_factory=valid_factory,
        crawler_factory=lambda: FakeCrawler(DiscoveryScanResult([source], 1, "Shared Company")),
    )
    for target_id in target_ids:
        assert await service.scan_target(target_id) == "complete"

    with Session(engine) as session:
        candidates = list(session.scalars(select(SourceCandidate)))
        assert len(candidates) == 1
        candidate_id = candidates[0].id

    assert await service.validate_candidate(candidate_id, auto_promote=True) == "promoted"
    with Session(engine) as session:
        company = session.scalar(select(Company))
        assert company is not None
        watcher_ids = set(
            session.scalars(
                select(UserCompanyWatchlist.user_id).where(
                    UserCompanyWatchlist.company_id == company.id
                )
            )
        )
        assert watcher_ids == set(user_ids)

async def test_bounded_target_crawler_follows_career_link_and_finds_ats(monkeypatch) -> None:
    from app.discovery import crawler as crawler_module
    from app.discovery.crawler import FetchedPage, TargetCrawler

    async def public(url: str) -> str:
        return url

    monkeypatch.setattr(crawler_module, "ensure_public_url", public)

    class Pages:
        def __init__(self) -> None:
            self.calls: list[str] = []

        async def close(self) -> None:
            return None

        async def fetch(self, url: str):
            self.calls.append(url)
            if url == "https://company.example":
                return FetchedPage(
                    url,
                    '<a href="/about">About</a><a href="/careers">Careers</a>',
                    "Company",
                    ["/about", "/careers"],
                )
            return FetchedPage(
                "https://company.example/careers",
                '<a href="https://jobs.ashbyhq.com/company">Open roles</a>',
                "Careers",
                ["https://jobs.ashbyhq.com/company"],
            )

    fetcher = Pages()
    result = await TargetCrawler(fetcher).scan("https://company.example", max_pages=3)
    assert fetcher.calls == ["https://company.example", "https://company.example/careers"]
    assert result.pages_scanned == 2
    assert len(result.sources) == 1
    assert result.sources[0].provider is ATSProvider.ASHBY
    assert result.sources[0].identifier == "company"

async def test_discovery_recovers_stale_in_progress_rows_and_valid_promotion(engine, settings) -> None:
    from datetime import datetime, timedelta, timezone

    stale = datetime.now(timezone.utc) - timedelta(hours=2)
    with Session(engine, expire_on_commit=False) as session:
        target = DiscoveryTarget(
            url="https://jobs.lever.co/recover",
            auto_watch=False,
            status=DiscoveryTargetStatus.SCANNING,
        )
        session.add(target)
        session.flush()
        target.updated_at = stale
        validating = SourceCandidate(
            ats_provider=ATSProvider.LEVER,
            ats_identifier="validating",
            career_url="https://jobs.lever.co/validating",
            source_url="https://jobs.lever.co/validating",
            status=DiscoveryCandidateStatus.VALIDATING,
        )
        valid = SourceCandidate(
            ats_provider=ATSProvider.LEVER,
            ats_identifier="already-valid",
            career_url="https://jobs.lever.co/already-valid",
            source_url="https://jobs.lever.co/already-valid",
            status=DiscoveryCandidateStatus.VALID,
        )
        session.add_all([validating, valid])
        session.flush()
        validating.updated_at = stale
        session.commit()
        target_id = target.id
        validating_id = validating.id
        valid_id = valid.id

    service = DiscoveryService(engine=engine, settings=settings, collector_factory=valid_factory)
    assert target_id in service.pending_target_ids(limit=10)
    assert validating_id in service.candidate_ids_for_validation(limit=10)
    assert valid_id in service.valid_candidate_ids_for_promotion(limit=10)

    company = service.promote_candidate(valid_id)
    assert company.ats_identifier == "already-valid"


def test_phase6b_bundled_system_feed_queues_without_user(engine, settings) -> None:
    from app.models.enums import DiscoveryTargetOrigin

    service = DiscoveryService(engine=engine, settings=settings)
    summary = service.queue_system_feed_entries(
        [
            __import__("app.discovery.feeds", fromlist=["DiscoveryFeedEntry"]).DiscoveryFeedEntry(
                "https://jobs.ashbyhq.com/system-example", "System Example"
            )
        ],
        source_label="test-system-feed",
    )
    assert summary == {"entries_seen": 1, "targets_queued": 1, "entries_existing": 0}
    with Session(engine) as session:
        target = session.scalar(select(DiscoveryTarget))
        assert target is not None
        assert target.submitted_by_user_id is None
        assert target.origin is DiscoveryTargetOrigin.SYSTEM_FEED
        assert target.source_label == "test-system-feed"
        assert target.auto_watch is False

    # A second ingest is idempotent while that target is still pending.
    second = service.queue_system_feed_entries(
        [
            __import__("app.discovery.feeds", fromlist=["DiscoveryFeedEntry"]).DiscoveryFeedEntry(
                "https://jobs.ashbyhq.com/system-example", "System Example"
            )
        ],
        source_label="test-system-feed",
    )
    assert second["targets_queued"] == 0
    assert second["entries_existing"] == 1


def test_phase6b_feed_parser_supports_csv_and_json() -> None:
    from app.discovery.feeds import parse_feed_text

    csv_entries = parse_feed_text(
        "url,company_name\nhttps://jobs.lever.co/example,Example\n",
        content_type="text/csv",
    )
    assert csv_entries[0].url == "https://jobs.lever.co/example"
    assert csv_entries[0].company_name == "Example"

    json_entries = parse_feed_text(
        '[{"career_url":"https://jobs.ashbyhq.com/example-two","name":"Example Two"}]',
        content_type="application/json",
    )
    assert json_entries[0].url == "https://jobs.ashbyhq.com/example-two"
    assert json_entries[0].company_name == "Example Two"


async def test_phase6b_revalidates_promoted_candidate_without_disabling_on_failure(engine, settings) -> None:
    from datetime import datetime, timedelta, timezone
    from app.models.enums import MonitoringPriority

    with Session(engine, expire_on_commit=False) as session:
        company = Company(
            name="Revalidate Co",
            career_url="https://jobs.lever.co/revalidate",
            ats_provider=ATSProvider.LEVER,
            ats_identifier="revalidate",
            monitoring_priority=MonitoringPriority.LOW,
            active=True,
        )
        session.add(company)
        session.flush()
        candidate = SourceCandidate(
            name_hint="Revalidate Co",
            ats_provider=ATSProvider.LEVER,
            ats_identifier="revalidate",
            career_url="https://jobs.lever.co/revalidate",
            source_url="https://jobs.lever.co/revalidate",
            status=DiscoveryCandidateStatus.VALID,
            promoted_company_id=company.id,
            promoted_at=datetime.now(timezone.utc),
            last_validated_at=datetime.now(timezone.utc) - timedelta(days=30),
        )
        session.add(candidate)
        session.commit()
        candidate_id = candidate.id
        company_id = company.id

    failing = DiscoveryService(engine=engine, settings=settings, collector_factory=invalid_factory)
    assert await failing.revalidate_candidate(candidate_id) == "revalidation_failed"
    with Session(engine) as session:
        candidate = session.get(SourceCandidate, candidate_id)
        company = session.get(Company, company_id)
        assert candidate is not None and company is not None
        assert candidate.status is DiscoveryCandidateStatus.VALID
        assert candidate.revalidation_failure_count == 1
        assert candidate.last_revalidated_at is not None
        assert company.active is True

    healthy = DiscoveryService(engine=engine, settings=settings, collector_factory=valid_factory)
    assert await healthy.revalidate_candidate(candidate_id) == "revalidated"
    with Session(engine) as session:
        candidate = session.get(SourceCandidate, candidate_id)
        assert candidate is not None
        assert candidate.revalidation_failure_count == 0
        assert candidate.jobs_seen == 1
        assert candidate.error_message is None


def test_phase6b_workflow_ingests_system_feeds_and_revalidates() -> None:
    workflow = Path(__file__).parents[2] / ".github" / "workflows" / "discovery.yml"
    text = workflow.read_text(encoding="utf-8")
    assert "DISCOVERY_SYSTEM_FEED_URLS" in text
    assert "--ingest-system-feeds" in text
    assert "--revalidate-promoted" in text
    assert "--revalidate-batch-size 50" in text


def test_phase6b_old_invalid_system_candidate_becomes_retryable(engine, settings) -> None:
    from datetime import datetime, timedelta, timezone
    from app.models.discovery_target_candidate import DiscoveryTargetCandidate
    from app.models.enums import DiscoveryTargetOrigin

    with Session(engine, expire_on_commit=False) as session:
        target = DiscoveryTarget(
            url="https://jobs.lever.co/retry-system",
            origin=DiscoveryTargetOrigin.SYSTEM_FEED,
            source_label="system-test",
            auto_watch=False,
            status=DiscoveryTargetStatus.COMPLETE,
        )
        session.add(target)
        session.flush()
        candidate = SourceCandidate(
            discovery_target_id=target.id,
            ats_provider=ATSProvider.LEVER,
            ats_identifier="retry-system",
            career_url="https://jobs.lever.co/retry-system",
            source_url="https://jobs.lever.co/retry-system",
            status=DiscoveryCandidateStatus.INVALID,
            last_validated_at=datetime.now(timezone.utc) - timedelta(days=30),
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

    service = DiscoveryService(engine=engine, settings=settings)
    assert candidate_id in service.candidate_ids_for_validation(limit=10)
