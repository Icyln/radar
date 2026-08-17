import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.matching.engine import evaluate_job_profile
from app.models.enums import ATSProvider, JobStatus, WorkMode
from app.models.job import Job
from app.models.job_profile import JobProfile
from app.models.user import User
from app.schemas.job import NormalizedJob
from app.services.job_processor import process_successful_snapshot


def make_job(company_id: uuid.UUID, *, posted_at=None, baseline_imported=False, first_seen_at=None):
    return Job(
        company_id=company_id,
        ats_provider=ATSProvider.GREENHOUSE,
        external_job_id=str(uuid.uuid4()),
        title="Frontend Engineer",
        description="React TypeScript web application",
        location="Remote",
        work_mode=WorkMode.REMOTE,
        employment_type="FULL_TIME",
        apply_url=f"https://example.com/{uuid.uuid4()}",
        source_url="https://example.com/jobs",
        posted_at=posted_at,
        baseline_imported=baseline_imported,
        first_seen_at=first_seen_at or datetime.now(timezone.utc),
        last_seen_at=first_seen_at or datetime.now(timezone.utc),
        status=JobStatus.ACTIVE,
        fingerprint=uuid.uuid4().hex * 2,
    )


def profile(*, max_age=30, include_unknown=False):
    return JobProfile(
        user_id=uuid.uuid4(),
        name="Fresh frontend",
        job_titles=["frontend engineer"],
        locations=[],
        work_modes=[],
        excluded_keywords=[],
        max_job_age_days=max_age,
        include_unknown_posted_at=include_unknown,
    )


def test_freshness_accepts_30_days_and_rejects_31(company) -> None:
    now = datetime(2026, 8, 17, 12, 0, tzinfo=timezone.utc)
    exactly_30 = make_job(company.id, posted_at=now - timedelta(days=30))
    too_old = make_job(company.id, posted_at=now - timedelta(days=31))
    p = profile(max_age=30)
    assert evaluate_job_profile(exactly_30, p, now=now).matched is True
    decision = evaluate_job_profile(too_old, p, now=now)
    assert decision.matched is False
    assert decision.reason["rejection_reason"] == "job is older than 30 days"


def test_unknown_baseline_is_strictly_excluded_but_can_be_opted_in(company) -> None:
    now = datetime.now(timezone.utc)
    job = make_job(company.id, posted_at=None, baseline_imported=True, first_seen_at=now)
    strict = profile(max_age=30, include_unknown=False)
    assert evaluate_job_profile(job, strict, now=now).matched is False
    permissive = profile(max_age=30, include_unknown=True)
    assert evaluate_job_profile(job, permissive, now=now).matched is True


def test_post_baseline_unknown_date_uses_first_seen(company) -> None:
    now = datetime.now(timezone.utc)
    recent = make_job(
        company.id,
        posted_at=None,
        baseline_imported=False,
        first_seen_at=now - timedelta(days=2),
    )
    assert evaluate_job_profile(recent, profile(max_age=7), now=now).matched is True


def test_any_age_allows_unknown_baseline(company) -> None:
    now = datetime.now(timezone.utc)
    job = make_job(company.id, posted_at=None, baseline_imported=True, first_seen_at=now)
    assert evaluate_job_profile(job, profile(max_age=None), now=now).matched is True


def test_initial_snapshot_marks_new_jobs_as_baseline(engine, company) -> None:
    with Session(engine, expire_on_commit=False) as session:
        db_company = session.get(type(company), company.id)
        result = process_successful_snapshot(
            session,
            company=db_company,
            jobs=[
                NormalizedJob(
                    company_id=company.id,
                    ats_provider=ATSProvider.GREENHOUSE,
                    external_job_id="baseline-job",
                    title="Frontend Engineer",
                    location="Remote",
                    work_mode=WorkMode.REMOTE,
                    apply_url="https://example.com/baseline",
                    source_url="https://example.com/baseline",
                )
            ],
            missing_threshold=3,
            initial_sync=True,
        )
        job = session.get(Job, result.new_job_ids[0])
        assert job.baseline_imported is True


def test_profile_api_defaults_to_30_day_strict_freshness(client) -> None:
    registered = client.post(
        "/api/v1/auth/register",
        json={"email": "freshness@example.com", "password": "password123"},
    ).json()
    headers = {"Authorization": f"Bearer {registered['access_token']}"}
    response = client.post(
        "/api/v1/job-profiles",
        headers=headers,
        json={"name": "Fresh web", "job_titles": ["frontend engineer"]},
    )
    assert response.status_code == 201, response.text
    data = response.json()
    assert data["max_job_age_days"] == 30
    assert data["include_unknown_posted_at"] is False


def test_detected_freshness_filter_excludes_old_and_unknown_baseline(client, engine, company) -> None:
    now = datetime.now(timezone.utc)
    with Session(engine) as session:
        session.add_all(
            [
                make_job(company.id, posted_at=now - timedelta(days=3)),
                make_job(company.id, posted_at=now - timedelta(days=45)),
                make_job(company.id, posted_at=None, baseline_imported=True, first_seen_at=now),
            ]
        )
        session.commit()
    registered = client.post(
        "/api/v1/auth/register",
        json={"email": "detected-fresh@example.com", "password": "password123"},
    ).json()
    headers = {"Authorization": f"Bearer {registered['access_token']}"}
    fresh = client.get("/api/v1/jobs/detected?freshness=30", headers=headers).json()
    unknown = client.get("/api/v1/jobs/detected?freshness=unknown", headers=headers).json()
    assert fresh["total"] == 1
    assert unknown["total"] == 1


def test_matched_view_hides_historical_match_that_aged_out(client, engine, company) -> None:
    from app.models.job_match import JobMatch

    registered = client.post(
        "/api/v1/auth/register",
        json={"email": "aged-match@example.com", "password": "password123"},
    ).json()
    user_id = uuid.UUID(registered["user"]["id"])
    headers = {"Authorization": f"Bearer {registered['access_token']}"}
    with Session(engine) as session:
        p = JobProfile(
            user_id=user_id,
            name="Fresh only",
            job_titles=["frontend engineer"],
            locations=[],
            work_modes=[],
            excluded_keywords=[],
            max_job_age_days=30,
            include_unknown_posted_at=False,
        )
        old = make_job(company.id, posted_at=datetime.now(timezone.utc) - timedelta(days=90))
        session.add_all([p, old])
        session.flush()
        session.add(
            JobMatch(
                user_id=user_id,
                job_profile_id=p.id,
                job_id=old.id,
                match_reason={"legacy": "historical"},
            )
        )
        session.commit()

    response = client.get("/api/v1/jobs?view=matched&status=ACTIVE", headers=headers)
    assert response.status_code == 200
    assert response.json() == []


async def test_existing_job_update_can_match_without_new_job_notification(engine, company) -> None:
    from sqlalchemy import func, select
    from app.collectors.base import BaseCollector
    from app.core.config import Settings
    from app.models.job_match import JobMatch
    from app.models.notification import Notification
    from app.models.telegram_connection import TelegramConnection
    from app.services.monitor import MonitorService

    now = datetime.now(timezone.utc)
    with Session(engine) as session:
        user = User(email="update-no-alert@example.com", password_hash=hash_password("password123"))
        session.add(user)
        session.flush()
        session.add(
            JobProfile(
                user_id=user.id,
                name="Frontend",
                job_titles=["frontend engineer"],
                locations=[],
                work_modes=[],
                excluded_keywords=[],
                max_job_age_days=30,
            )
        )
        session.add(
            TelegramConnection(
                user_id=user.id,
                telegram_user_id=987,
                telegram_chat_id=654,
                verified=True,
                connected_at=now,
            )
        )
        session.commit()

    titles = iter(["Accountant", "Frontend Engineer"])

    class UpdatingCollector(BaseCollector):
        async def fetch_jobs(self, target):
            return [
                NormalizedJob(
                    company_id=target.id,
                    ats_provider=ATSProvider.GREENHOUSE,
                    external_job_id="same-existing-job",
                    title=next(titles),
                    location="Remote",
                    work_mode=WorkMode.REMOTE,
                    apply_url="https://example.com/same",
                    source_url="https://example.com/same",
                    posted_at=now - timedelta(days=2),
                )
            ]

    service = MonitorService(
        engine=engine,
        settings=Settings(database_url="sqlite://", telegram_bot_token="test-token"),
        collector_factory=lambda provider, settings: UpdatingCollector(),
    )
    assert await service.run_company(company.id) == "success"
    assert await service.run_company(company.id) == "success"

    with Session(engine) as session:
        assert session.scalar(select(func.count(JobMatch.id))) == 1
        assert session.scalar(select(func.count(Notification.id))) == 0
