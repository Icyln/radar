from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.discovery.hiring import HiringSignal
from app.models.enums import ATSProvider, DiscoveryCandidateStatus, DiscoveryTargetOrigin, DiscoveryTargetStatus, MonitoringPriority, ProfileCoverageMode, WorkMode
from app.models.company import Company
from app.models.discovery_target import DiscoveryTarget
from app.models.discovery_target_candidate import DiscoveryTargetCandidate
from app.models.job import Job
from app.models.job_match import JobMatch
from app.models.job_profile import JobProfile
from app.models.source_candidate import SourceCandidate
from app.models.user import User
from app.schemas.job import NormalizedJob
from app.services.discovery import DiscoveryService
from app.services.job_processor import process_successful_snapshot
from app.core.security import hash_password


def _profile(session: Session) -> JobProfile:
    user = User(
        email="phase7c@example.com",
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
        job_titles=["Frontend Engineer", "Full Stack Engineer"],
        locations=[],
        work_modes=[],
        excluded_keywords=[],
        max_job_age_days=30,
        include_unknown_posted_at=False,
    )
    session.add(profile)
    session.flush()
    return profile


def _signal() -> HiringSignal:
    return HiringSignal(
        source="himalayas",
        external_id="wide-role-1",
        url="https://himalayas.app/companies/newco/jobs/frontend-engineer",
        company_name="New Co",
        company_slug="newco",
        title="Senior Frontend Engineer",
        location="Remote",
        posted_at=datetime.now(timezone.utc) - timedelta(hours=2),
        remote=True,
        description="Build the web application.",
        employment_type="Full time",
    )


def test_wide_signal_becomes_match_without_registry_company(engine, settings) -> None:
    with Session(engine, expire_on_commit=False) as session:
        profile = _profile(session)
        session.commit()
        profile_id = profile.id

    service = DiscoveryService(engine=engine, settings=settings)
    with Session(engine) as session:
        profile = session.get(JobProfile, profile_id)
        assert profile is not None
        summary = service.ingest_hiring_signal_jobs([_signal()], profiles=[profile])

    assert summary["jobs_new"] == 1
    assert summary["matches_created"] == 1
    with Session(engine) as session:
        job = session.scalar(select(Job).where(Job.source_external_id == "wide-role-1"))
        assert job is not None
        assert job.company_id is None
        assert job.ats_provider is None
        assert job.source_kind == "WIDE_DISCOVERY"
        assert job.source_company_name == "New Co"
        assert job.work_mode is WorkMode.REMOTE
        assert session.scalar(select(JobMatch).where(JobMatch.job_id == job.id)) is not None


def test_wide_signal_refresh_is_idempotent(engine, settings) -> None:
    with Session(engine, expire_on_commit=False) as session:
        profile = _profile(session)
        session.commit()
        profile_id = profile.id

    service = DiscoveryService(engine=engine, settings=settings)
    signal = _signal()
    with Session(engine) as session:
        profile = session.get(JobProfile, profile_id)
        first = service.ingest_hiring_signal_jobs([signal], profiles=[profile])
        second = service.ingest_hiring_signal_jobs([signal], profiles=[profile])

    assert first["jobs_new"] == 1
    assert second["jobs_new"] == 0
    assert second["jobs_existing"] == 1
    with Session(engine) as session:
        assert len(list(session.scalars(select(Job)))) == 1


def test_promoted_signal_attaches_then_direct_ats_upgrades_same_job(engine, settings) -> None:
    now = datetime.now(timezone.utc)
    with Session(engine, expire_on_commit=False) as session:
        profile = _profile(session)
        session.commit()
        profile_id = profile.id

    service = DiscoveryService(engine=engine, settings=settings)
    signal = _signal()
    with Session(engine) as session:
        profile = session.get(JobProfile, profile_id)
        service.ingest_hiring_signal_jobs([signal], profiles=[profile])

    with Session(engine, expire_on_commit=False) as session:
        target = DiscoveryTarget(
            url=signal.url,
            origin=DiscoveryTargetOrigin.SYSTEM_FEED,
            source_label="hiring-signal:himalayas",
            signal_external_id=signal.external_id,
            company_name_hint="New Co",
            job_title_hint=signal.title,
            job_location_hint=signal.location,
            job_posted_at_hint=signal.posted_at,
            auto_watch=False,
            status=DiscoveryTargetStatus.COMPLETE,
        )
        session.add(target)
        session.flush()
        candidate = SourceCandidate(
            discovery_target_id=target.id,
            name_hint="New Co",
            ats_provider=ATSProvider.GREENHOUSE,
            ats_identifier="newco",
            career_url="https://boards.greenhouse.io/newco",
            source_url="https://boards.greenhouse.io/newco",
            status=DiscoveryCandidateStatus.VALID,
        )
        session.add(candidate)
        session.flush()
        session.add(DiscoveryTargetCandidate(discovery_target_id=target.id, source_candidate_id=candidate.id))
        session.commit()
        candidate_id = candidate.id

    company = service.promote_candidate(candidate_id)
    with Session(engine) as session:
        wide = session.scalar(select(Job).where(Job.source_external_id == signal.external_id))
        assert wide is not None
        assert wide.company_id == company.id
        original_job_id = wide.id

    incoming = NormalizedJob(
        company_id=company.id,
        ats_provider=ATSProvider.GREENHOUSE,
        external_job_id="gh-123",
        title=signal.title,
        description="Direct ATS description",
        location=signal.location,
        work_mode=WorkMode.REMOTE,
        employment_type="Full time",
        apply_url="https://boards.greenhouse.io/newco/jobs/gh-123",
        source_url="https://boards.greenhouse.io/newco/jobs/gh-123",
        posted_at=now - timedelta(hours=2),
    )
    with Session(engine) as session:
        db_company = session.get(Company, company.id)
        result = process_successful_snapshot(
            session,
            company=db_company,
            jobs=[incoming],
            missing_threshold=3,
            now=now,
            initial_sync=True,
        )
        session.commit()

    assert result.jobs_new == 0
    assert result.jobs_updated == 1
    with Session(engine) as session:
        jobs = list(session.scalars(select(Job)))
        assert len(jobs) == 1
        assert jobs[0].id == original_job_id
        assert jobs[0].source_kind == "DIRECT_ATS"
        assert jobs[0].ats_provider is ATSProvider.GREENHOUSE
        assert jobs[0].external_job_id == "gh-123"


def test_user_jobs_api_shows_wide_job_without_registry_company(client, engine, settings) -> None:
    registered = client.post(
        "/api/v1/auth/register",
        json={"email": "wide-ui@example.com", "password": "password123"},
    )
    assert registered.status_code == 201
    token = registered.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    created = client.post(
        "/api/v1/job-profiles",
        headers=headers,
        json={
            "name": "Web Development",
            "enabled": True,
            "coverage_mode": "WIDE",
            "job_titles": ["Frontend Engineer"],
            "locations": [],
            "work_modes": [],
            "excluded_keywords": [],
            "max_job_age_days": 30,
            "include_unknown_posted_at": False,
        },
    )
    assert created.status_code == 201
    profile_id = __import__("uuid").UUID(created.json()["id"])

    with Session(engine) as session:
        profile = session.get(JobProfile, profile_id)
        result = DiscoveryService(engine=engine, settings=settings).ingest_hiring_signal_jobs(
            [_signal()], profiles=[profile]
        )
    assert result["matches_created"] == 1

    response = client.get("/api/v1/jobs?view=matched&status=ACTIVE", headers=headers)
    assert response.status_code == 200
    rows = response.json()
    assert len(rows) == 1
    assert rows[0]["company_id"] is None
    assert rows[0]["company_name"] == "New Co"
    assert rows[0]["source_kind"] == "WIDE_DISCOVERY"
    assert rows[0]["source_verified"] is False

    detected = client.get(
        "/api/v1/jobs/detected?source=wide&freshness=30", headers=headers
    )
    assert detected.status_code == 200
    assert detected.json()["total"] == 1
