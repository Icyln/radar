from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.company import Company
from app.models.enums import JobStatus
from app.models.job import Job
from app.schemas.job import NormalizedJob
from app.services.fingerprint import build_job_fingerprint


@dataclass(slots=True)
class JobProcessingResult:
    jobs_received: int
    jobs_new: int
    jobs_updated: int
    jobs_closed: int
    new_job_ids: list
    updated_job_ids: list


_MUTABLE_FIELDS = (
    "title",
    "description",
    "location",
    "work_mode",
    "employment_type",
    "apply_url",
    "source_url",
    "posted_at",
)


def process_successful_snapshot(
    session: Session,
    *,
    company: Company,
    jobs: list[NormalizedJob],
    missing_threshold: int,
    now: datetime | None = None,
) -> JobProcessingResult:
    """Persist one complete successful source snapshot and advance lifecycle."""
    observed_at = now or datetime.now(timezone.utc)
    existing_jobs = list(
        session.scalars(
            select(Job).where(Job.company_id == company.id, Job.ats_provider == company.ats_provider)
        )
    )
    by_external = {job.external_job_id: job for job in existing_jobs if job.external_job_id}
    by_fingerprint = {job.fingerprint: job for job in existing_jobs}
    observed_ids: set = set()
    new_ids: list = []
    updated = 0
    updated_ids: list = []

    for incoming in jobs:
        fingerprint = build_job_fingerprint(
            provider=incoming.ats_provider,
            company_id=company.id,
            external_job_id=incoming.external_job_id,
            title=incoming.title,
            location=incoming.location,
            apply_url=incoming.apply_url,
        )
        current = None
        if incoming.external_job_id:
            current = by_external.get(incoming.external_job_id)
        current = current or by_fingerprint.get(fingerprint)

        if current is None:
            current = Job(
                company_id=company.id,
                ats_provider=incoming.ats_provider,
                external_job_id=incoming.external_job_id,
                title=incoming.title,
                description=incoming.description,
                location=incoming.location,
                work_mode=incoming.work_mode,
                employment_type=incoming.employment_type,
                apply_url=incoming.apply_url,
                source_url=incoming.source_url,
                posted_at=incoming.posted_at,
                first_seen_at=observed_at,
                last_seen_at=observed_at,
                missing_count=0,
                status=JobStatus.ACTIVE,
                fingerprint=fingerprint,
            )
            session.add(current)
            session.flush()
            new_ids.append(current.id)
            existing_jobs.append(current)
            if current.external_job_id:
                by_external[current.external_job_id] = current
            by_fingerprint[current.fingerprint] = current
        else:
            changed = current.status is not JobStatus.ACTIVE or current.missing_count != 0
            for field in _MUTABLE_FIELDS:
                value = getattr(incoming, field)
                if getattr(current, field) != value:
                    setattr(current, field, value)
                    changed = True
            if current.fingerprint != fingerprint:
                # External IDs keep source identity stable while descriptive fields can change.
                current.fingerprint = fingerprint
                changed = True
            current.last_seen_at = observed_at
            current.missing_count = 0
            current.status = JobStatus.ACTIVE
            current.closed_at = None
            if changed:
                updated += 1
                updated_ids.append(current.id)
            observed_ids.add(current.id)

        observed_ids.add(current.id)

    closed = 0
    for current in existing_jobs:
        if current.id in observed_ids or current.status is JobStatus.CLOSED:
            continue
        current.missing_count += 1
        if current.missing_count >= missing_threshold:
            current.status = JobStatus.CLOSED
            current.closed_at = observed_at
            closed += 1
        else:
            current.status = JobStatus.UNKNOWN

    session.flush()
    return JobProcessingResult(
        jobs_received=len(jobs),
        jobs_new=len(new_ids),
        jobs_updated=updated,
        jobs_closed=closed,
        new_job_ids=new_ids,
        updated_job_ids=updated_ids,
    )
