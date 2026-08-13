from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.enums import ATSProvider, JobStatus, WorkMode
from app.models.job import Job
from app.schemas.job import NormalizedJob
from app.services.job_processor import process_successful_snapshot


def payload(company_id, external_id: str, title: str = "Backend Engineer") -> NormalizedJob:
    return NormalizedJob(
        company_id=company_id,
        ats_provider=ATSProvider.GREENHOUSE,
        external_job_id=external_id,
        title=title,
        description="Build APIs",
        location="Remote",
        work_mode=WorkMode.REMOTE,
        apply_url=f"https://example.com/jobs/{external_id}",
        source_url=f"https://example.com/jobs/{external_id}",
    )


def test_deduplication_and_lifecycle(engine, company) -> None:
    t0 = datetime(2026, 8, 13, tzinfo=timezone.utc)
    with Session(engine, expire_on_commit=False) as session:
        db_company = session.get(type(company), company.id)
        first = process_successful_snapshot(
            session,
            company=db_company,
            jobs=[payload(company.id, "1"), payload(company.id, "2")],
            missing_threshold=2,
            now=t0,
        )
        session.commit()
        assert first.jobs_new == 2

    with Session(engine, expire_on_commit=False) as session:
        db_company = session.get(type(company), company.id)
        second = process_successful_snapshot(
            session,
            company=db_company,
            jobs=[payload(company.id, "1"), payload(company.id, "2")],
            missing_threshold=2,
            now=t0 + timedelta(minutes=1),
        )
        session.commit()
        assert second.jobs_new == 0
        assert len(list(session.scalars(select(Job)))) == 2

    with Session(engine, expire_on_commit=False) as session:
        db_company = session.get(type(company), company.id)
        process_successful_snapshot(
            session,
            company=db_company,
            jobs=[payload(company.id, "2")],
            missing_threshold=2,
            now=t0 + timedelta(minutes=2),
        )
        session.commit()
        missing = session.scalar(select(Job).where(Job.external_job_id == "1"))
        assert missing.status is JobStatus.UNKNOWN
        assert missing.missing_count == 1

    with Session(engine, expire_on_commit=False) as session:
        db_company = session.get(type(company), company.id)
        result = process_successful_snapshot(
            session,
            company=db_company,
            jobs=[payload(company.id, "2")],
            missing_threshold=2,
            now=t0 + timedelta(minutes=3),
        )
        session.commit()
        missing = session.scalar(select(Job).where(Job.external_job_id == "1"))
        assert result.jobs_closed == 1
        assert missing.status is JobStatus.CLOSED
        assert missing.closed_at is not None

    with Session(engine, expire_on_commit=False) as session:
        db_company = session.get(type(company), company.id)
        process_successful_snapshot(
            session,
            company=db_company,
            jobs=[payload(company.id, "1"), payload(company.id, "2")],
            missing_threshold=2,
            now=t0 + timedelta(minutes=4),
        )
        session.commit()
        reappeared = session.scalar(select(Job).where(Job.external_job_id == "1"))
        assert reappeared.status is JobStatus.ACTIVE
        assert reappeared.missing_count == 0
        assert reappeared.closed_at is None
