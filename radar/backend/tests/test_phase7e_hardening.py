from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api import discovery as discovery_api
from app.core.security import hash_password
from app.discovery.hiring import HiringSignal, PublicHiringSignalProvider
from app.models.discovery_run import DiscoveryRun
from app.models.enums import ATSProvider, CrawlerStatus, JobStatus, ProfileCoverageMode, WorkMode
from app.models.job import Job
from app.models.job_profile import JobProfile
from app.models.job_source_observation import JobSourceObservation
from app.models.monitor_run import MonitorRun
from app.models.user import User
from app.schemas.job import NormalizedJob
from app.services.discovery import DiscoveryService
from app.services.job_processor import process_successful_snapshot


def _profile(session: Session) -> JobProfile:
    user = User(
        email="phase7e@example.com",
        password_hash=hash_password("password123"),
        is_active=True,
    )
    session.add(user)
    session.flush()
    profile = JobProfile(
        user_id=user.id,
        name="Web Development",
        enabled=True,
        coverage_mode=ProfileCoverageMode.WIDE,
        job_titles=["Frontend Engineer"],
        locations=[],
        work_modes=[],
        excluded_keywords=[],
        max_job_age_days=30,
        include_unknown_posted_at=False,
    )
    session.add(profile)
    session.flush()
    return profile


def _signal(*, source: str, external_id: str) -> HiringSignal:
    return HiringSignal(
        source=source,
        external_id=external_id,
        url=f"https://{source}.example/jobs/{external_id}",
        company_name="Example Labs",
        company_slug="example-labs",
        title="Frontend Engineer",
        location="Remote",
        posted_at=datetime.now(timezone.utc) - timedelta(hours=2),
        remote=True,
        description="Build the web product.",
        employment_type="Full time",
    )


def test_cross_source_wide_jobs_merge_into_one_card(engine, settings) -> None:
    with Session(engine, expire_on_commit=False) as session:
        profile = _profile(session)
        session.commit()
        profile_id = profile.id

    service = DiscoveryService(engine=engine, settings=settings)
    with Session(engine) as session:
        profile = session.get(JobProfile, profile_id)
        assert profile is not None
        first = service.ingest_hiring_signal_jobs(
            [_signal(source="himalayas", external_id="h-1")], profiles=[profile]
        )
        second = service.ingest_hiring_signal_jobs(
            [_signal(source="arbeitnow-eu", external_id="a-1")], profiles=[profile]
        )

    assert first["jobs_new"] == 1
    assert second["jobs_new"] == 0
    assert second["jobs_deduplicated"] == 1
    with Session(engine) as session:
        jobs = list(session.scalars(select(Job)))
        observations = list(session.scalars(select(JobSourceObservation)))
        assert len(jobs) == 1
        assert len(observations) == 2
        assert {item.source_provider for item in observations} == {"himalayas", "arbeitnow-eu"}


def test_wide_signal_merges_into_existing_direct_ats_job(engine, settings, company) -> None:
    now = datetime.now(timezone.utc)
    incoming = NormalizedJob(
        company_id=company.id,
        ats_provider=ATSProvider.GREENHOUSE,
        external_job_id="direct-1",
        title="Frontend Engineer",
        description="Authoritative ATS description",
        location="Remote",
        work_mode=WorkMode.REMOTE,
        employment_type="Full time",
        apply_url="https://boards.greenhouse.io/example/jobs/direct-1",
        source_url="https://boards.greenhouse.io/example/jobs/direct-1",
        posted_at=now - timedelta(hours=2),
    )
    with Session(engine) as session:
        db_company = session.get(type(company), company.id)
        assert db_company is not None
        process_successful_snapshot(
            session,
            company=db_company,
            jobs=[incoming],
            missing_threshold=3,
            now=now,
            initial_sync=False,
        )
        profile = _profile(session)
        session.commit()
        profile_id = profile.id

    signal = HiringSignal(
        source="himalayas",
        external_id="wide-direct-1",
        url="https://himalayas.app/jobs/wide-direct-1",
        company_name="Example Co",
        company_slug="example",
        title="Frontend Engineer",
        location="Remote",
        posted_at=now - timedelta(hours=2),
        remote=True,
    )
    service = DiscoveryService(engine=engine, settings=settings)
    with Session(engine) as session:
        profile = session.get(JobProfile, profile_id)
        assert profile is not None
        result = service.ingest_hiring_signal_jobs([signal], profiles=[profile])

    assert result["jobs_new"] == 0
    assert result["jobs_deduplicated"] == 1
    with Session(engine) as session:
        jobs = list(session.scalars(select(Job)))
        assert len(jobs) == 1
        assert jobs[0].source_kind == "DIRECT_ATS"
        assert jobs[0].description == "Authoritative ATS description"
        assert len(list(session.scalars(select(JobSourceObservation)))) == 2


def test_wide_job_lifecycle_marks_unknown_then_closed(engine, settings) -> None:
    now = datetime.now(timezone.utc)
    with Session(engine) as session:
        session.add_all(
            [
                Job(
                    company_id=None,
                    ats_provider=None,
                    external_job_id=None,
                    title="Frontend Engineer",
                    description=None,
                    location="Remote",
                    work_mode=WorkMode.REMOTE,
                    employment_type=None,
                    apply_url="https://example.test/unknown",
                    source_url="https://example.test/unknown",
                    posted_at=now - timedelta(days=20),
                    discovery_signal_at=now - timedelta(days=20),
                    discovery_signal_source="himalayas",
                    source_kind="WIDE_DISCOVERY",
                    source_provider="himalayas",
                    source_external_id="unknown-role",
                    source_company_name="Unknown Co",
                    baseline_imported=False,
                    first_seen_at=now - timedelta(days=20),
                    last_seen_at=now - timedelta(days=20),
                    missing_count=0,
                    status=JobStatus.ACTIVE,
                    fingerprint="u" * 64,
                ),
                Job(
                    company_id=None,
                    ats_provider=None,
                    external_job_id=None,
                    title="Web Developer",
                    description=None,
                    location="Remote",
                    work_mode=WorkMode.REMOTE,
                    employment_type=None,
                    apply_url="https://example.test/closed",
                    source_url="https://example.test/closed",
                    posted_at=now - timedelta(days=60),
                    discovery_signal_at=now - timedelta(days=60),
                    discovery_signal_source="himalayas",
                    source_kind="WIDE_DISCOVERY",
                    source_provider="himalayas",
                    source_external_id="closed-role",
                    source_company_name="Closed Co",
                    baseline_imported=False,
                    first_seen_at=now - timedelta(days=60),
                    last_seen_at=now - timedelta(days=60),
                    missing_count=0,
                    status=JobStatus.ACTIVE,
                    fingerprint="c" * 64,
                ),
            ]
        )
        session.commit()

    result = DiscoveryService(engine=engine, settings=settings).apply_wide_job_lifecycle(now=now)
    assert result == {"jobs_marked_unknown": 1, "jobs_closed": 1}
    with Session(engine) as session:
        unknown = session.scalar(select(Job).where(Job.source_external_id == "unknown-role"))
        closed = session.scalar(select(Job).where(Job.source_external_id == "closed-role"))
        assert unknown is not None and unknown.status is JobStatus.UNKNOWN
        assert closed is not None and closed.status is JobStatus.CLOSED
        assert closed.closed_at is not None


class FakeHiringClient:
    def __init__(self) -> None:
        self.calls: list[int] = []

    async def get_json(self, url, *, params=None):
        page = int((params or {}).get("page", 1))
        self.calls.append(page)
        if page == 1:
            return {
                "jobs": [
                    {
                        "guid": "page-1",
                        "title": "Frontend Engineer",
                        "applicationLink": "https://himalayas.app/jobs/page-1",
                        "companyName": "Page One",
                        "companySlug": "page-one",
                        "pubDate": datetime.now(timezone.utc).isoformat(),
                    }
                ]
            }
        if page == 2:
            return {
                "jobs": [
                    {
                        "guid": "page-2",
                        "title": "Frontend Engineer",
                        "applicationLink": "https://himalayas.app/jobs/page-2",
                        "companyName": "Page Two",
                        "companySlug": "page-two",
                        "pubDate": datetime.now(timezone.utc).isoformat(),
                    }
                ]
            }
        return {"jobs": []}

    async def close(self):
        return None


async def test_himalayas_fetches_multiple_bounded_pages(settings) -> None:
    tuned = settings.model_copy(
        update={
            "discovery_hiring_arbeitnow_enabled": False,
            "discovery_hiring_himalayas_enabled": True,
            "discovery_hiring_himalayas_pages": 3,
        }
    )
    fake = FakeHiringClient()
    provider = PublicHiringSignalProvider(settings=tuned, client=fake)
    signals = await provider.fetch(search_terms=["Frontend Engineer"])
    assert [item.external_id for item in signals] == ["page-1", "page-2"]
    assert fake.calls == [1, 2, 3]
    assert provider.pages_fetched["himalayas"] == 3
    assert provider.successful_sources == {"himalayas"}


class PartialFailureHiringClient:
    async def get_json(self, url, *, params=None):
        if "arbeitnow" in url:
            raise RuntimeError("HTTP 403")
        page = int((params or {}).get("page", 1))
        if page > 1:
            return {"jobs": []}
        return {
            "jobs": [
                {
                    "guid": "fallback-job",
                    "title": "Frontend Engineer",
                    "applicationLink": "https://himalayas.app/jobs/fallback-job",
                    "companyName": "Fallback Co",
                    "companySlug": "fallback-co",
                    "pubDate": datetime.now(timezone.utc).isoformat(),
                }
            ]
        }

    async def close(self):
        return None


async def test_provider_failure_does_not_block_remaining_sources(settings) -> None:
    tuned = settings.model_copy(
        update={
            "discovery_hiring_arbeitnow_enabled": True,
            "discovery_hiring_arbeitnow_pages": 1,
            "discovery_hiring_himalayas_enabled": True,
            "discovery_hiring_himalayas_pages": 2,
        }
    )
    provider = PublicHiringSignalProvider(settings=tuned, client=PartialFailureHiringClient())
    signals = await provider.fetch(search_terms=["Frontend Engineer"])
    assert [item.external_id for item in signals] == ["fallback-job"]
    assert provider.successful_sources == {"himalayas"}
    assert provider.failed_provider_names == {"arbeitnow-eu", "arbeitnow-uk"}
    assert len(provider.failed_sources) == 2


async def test_full_discovery_records_automation_run(engine, settings) -> None:
    tuned = settings.model_copy(
        update={
            "discovery_run_trigger": "github-actions",
            "discovery_external_run_id": "run-123",
        }
    )
    result = await DiscoveryService(engine=engine, settings=tuned).run(
        target_batch_size=5,
        candidate_batch_size=5,
        max_concurrency=1,
        auto_promote=True,
        ingest_system_feeds=False,
        ingest_hiring_signals=False,
        revalidate_promoted=False,
    )
    assert "discovery_run_id" in result
    with Session(engine) as session:
        run = session.scalar(select(DiscoveryRun))
        assert run is not None
        assert run.trigger == "github-actions"
        assert run.external_run_id == "run-123"
        assert run.completed_at is not None
        assert run.status is CrawlerStatus.SKIPPED


def test_dashboard_exposes_separate_monitoring_and_wide_health(client, engine) -> None:
    registered = client.post(
        "/api/v1/auth/register",
        json={"email": "health@example.com", "password": "password123"},
    )
    assert registered.status_code == 201
    headers = {"Authorization": f"Bearer {registered.json()['access_token']}"}
    now = datetime.now(timezone.utc)
    with Session(engine) as session:
        session.add(
            MonitorRun(
                started_at=now - timedelta(minutes=10),
                completed_at=now - timedelta(minutes=9),
                status=CrawlerStatus.SUCCESS,
                source_scope="registry",
                priority=None,
                shard_index=0,
                shard_count=1,
                max_concurrency=3,
                companies_selected=4,
                companies_succeeded=4,
                companies_failed=0,
                companies_skipped=0,
                notifications_sent=1,
                trigger="github-actions",
                external_run_id="monitor-1",
            )
        )
        session.add(
            DiscoveryRun(
                started_at=now - timedelta(minutes=20),
                completed_at=now - timedelta(minutes=19),
                status=CrawlerStatus.PARTIAL,
                trigger="github-actions",
                external_run_id="discover-1",
                profiles=1,
                queries=3,
                signals_seen=120,
                signals_relevant=20,
                jobs_new=7,
                jobs_deduplicated=2,
                provider_failures=1,
                provider_warnings="arbeitnow-eu: HTTP 403",
                notifications_sent=5,
            )
        )
        session.commit()

    response = client.get("/api/v1/dashboard/summary", headers=headers)
    assert response.status_code == 200
    payload = response.json()
    assert payload["monitoring_automation"]["state"] == "HEALTHY"
    assert payload["monitoring_automation"]["companies_selected"] == 4
    assert payload["wide_search_automation"]["state"] == "DEGRADED"
    assert payload["wide_search_automation"]["jobs_new"] == 7
    assert payload["wide_search_automation"]["jobs_deduplicated"] == 2
    assert payload["wide_search_automation"]["warnings"] == ["arbeitnow-eu: HTTP 403"]


async def test_user_refresh_releases_request_db_connection_before_provider_io(
    engine, settings, monkeypatch
) -> None:
    with Session(engine, expire_on_commit=False) as setup_session:
        profile = _profile(setup_session)
        setup_session.commit()
        user_id = profile.user_id

    request_session = Session(engine, expire_on_commit=False)
    try:
        user = request_session.get(User, user_id)
        assert user is not None
        # Mirrors current_user: authentication has already checked out a connection
        # and opened an implicit transaction before the long async provider fetch.
        assert request_session.in_transaction() is True

        async def fake_ingest(self, *, user_id=None):
            assert user_id is not None
            # Regression guard for the production failure: the request-scoped DB
            # connection must be released before external network I/O begins.
            assert request_session.in_transaction() is False
            return {
                "profiles": 1,
                "queries": 1,
                "signals_seen": 1,
                "signals_relevant": 1,
                "jobs_new": 1,
                "jobs_updated": 0,
                "jobs_existing": 0,
                "jobs_deduplicated": 0,
                "matches_created": 1,
                "notifications_queued": 0,
                "targets_resolved": 1,
                "probe_candidates_staged": 0,
                "provider_failed": 0,
                "provider_warnings": [],
                "provider_successes": ["himalayas"],
                "provider_pages": 3,
                "_notification_ids": [],
            }

        monkeypatch.setattr(DiscoveryService, "ingest_hiring_signals", fake_ingest)
        result = await discovery_api.refresh_wide_search(
            user=user, settings=settings, session=request_session
        )
        assert result.jobs_new == 1
        assert result.telegram_ready is False
        assert result.provider_pages == 3
    finally:
        request_session.close()
