import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.matching.engine import evaluate_job_profile
from app.matching.service import create_matches_for_jobs
from app.models.enums import ATSProvider, JobStatus, WorkMode
from app.models.job import Job
from app.models.job_match import JobMatch
from app.models.job_profile import JobProfile
from app.models.user import User
from app.core.security import hash_password


def make_job(company_id: uuid.UUID, *, title="Backend Software Engineer", location="Remote") -> Job:
    return Job(
        company_id=company_id,
        ats_provider=ATSProvider.GREENHOUSE,
        external_job_id="job-1",
        title=title,
        description="Python APIs and distributed systems",
        location=location,
        work_mode=WorkMode.REMOTE,
        employment_type="FULL_TIME",
        apply_url="https://example.com/apply",
        source_url="https://example.com/job",
        status=JobStatus.ACTIVE,
        fingerprint="a" * 64,
    )


def test_matching_rules(company) -> None:
    job = make_job(company.id)
    profile = JobProfile(
        user_id=uuid.uuid4(),
        name="Backend",
        job_titles=["backend engineer"],
        locations=["remote"],
        work_modes=["REMOTE"],
        excluded_keywords=[],
    )
    decision = evaluate_job_profile(job, profile)
    assert decision.matched is True
    assert decision.reason["matched_title"] == "backend engineer"

    profile.excluded_keywords = ["distributed"]
    assert evaluate_job_profile(job, profile).matched is False
    profile.excluded_keywords = []
    profile.locations = ["London"]
    assert evaluate_job_profile(job, profile).matched is False
    profile.locations = ["remote"]
    profile.work_modes = ["ONSITE"]
    assert evaluate_job_profile(job, profile).matched is False


def test_match_creation_is_idempotent(engine, company) -> None:
    with Session(engine, expire_on_commit=False) as session:
        user = User(email="match@example.com", password_hash=hash_password("password123"))
        session.add(user)
        session.flush()
        profile = JobProfile(
            user_id=user.id,
            name="Backend",
            job_titles=["backend engineer"],
            locations=["remote"],
            work_modes=["REMOTE"],
            excluded_keywords=[],
        )
        job = make_job(company.id)
        session.add_all([profile, job])
        session.flush()
        first = create_matches_for_jobs(session, job_ids=[job.id])
        second = create_matches_for_jobs(session, job_ids=[job.id])
        session.commit()
        assert first.created == 1
        assert second.created == 0
        assert session.scalar(select(func.count(JobMatch.id))) == 1
