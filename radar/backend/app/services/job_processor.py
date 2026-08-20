from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.company import Company
from app.models.enums import JobStatus
from app.models.job import Job
from app.models.job_source_observation import JobSourceObservation
from app.schemas.job import NormalizedJob
from app.services.fingerprint import build_job_fingerprint
from app.services.text import normalize_for_match


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


def _wide_upgrade_candidate(incoming: NormalizedJob, jobs: list[Job]) -> Job | None:
    wanted_title = normalize_for_match(incoming.title)
    wanted_location = normalize_for_match(incoming.location or "")
    candidates: list[Job] = []
    for job in jobs:
        if job.source_kind != "WIDE_DISCOVERY" or job.ats_provider is not None:
            continue
        if normalize_for_match(job.title) != wanted_title:
            continue
        job_location = normalize_for_match(job.location or "")
        if wanted_location and job_location and not (
            wanted_location == job_location
            or wanted_location in job_location
            or job_location in wanted_location
        ):
            continue
        candidates.append(job)
    return candidates[0] if len(candidates) == 1 else None


def _upsert_direct_observation(
    session: Session,
    *,
    job: Job,
    company: Company,
    incoming: NormalizedJob,
    observed_at: datetime,
) -> None:
    provider_key = f"{company.ats_provider.value}:{company.ats_identifier}"[:255]
    external_id = (incoming.external_job_id or job.fingerprint)[:500]
    observation = session.scalar(
        select(JobSourceObservation).where(
            JobSourceObservation.source_provider == provider_key,
            JobSourceObservation.source_external_id == external_id,
        )
    )
    if observation is None:
        session.add(
            JobSourceObservation(
                job_id=job.id,
                source_kind="DIRECT_ATS",
                source_provider=provider_key,
                source_external_id=external_id,
                source_url=incoming.source_url,
                apply_url=incoming.apply_url,
                company_name=company.name,
                posted_at=incoming.posted_at,
                first_seen_at=observed_at,
                last_seen_at=observed_at,
                verified=True,
            )
        )
    else:
        observation.job_id = job.id
        observation.source_url = incoming.source_url
        observation.apply_url = incoming.apply_url
        observation.company_name = company.name
        observation.posted_at = incoming.posted_at
        observation.last_seen_at = observed_at
        observation.verified = True


def process_successful_snapshot(
    session: Session,
    *,
    company: Company,
    jobs: list[NormalizedJob],
    missing_threshold: int,
    now: datetime | None = None,
    initial_sync: bool = False,
) -> JobProcessingResult:
    """Persist one complete successful source snapshot and advance lifecycle.

    Broad-search rows can be upgraded in place when the direct company source
    later returns one unambiguous role with the same normalized title/location.
    """
    observed_at = now or datetime.now(timezone.utc)
    existing_jobs = list(
        session.scalars(
            select(Job).where(
                Job.company_id == company.id,
                or_(
                    Job.ats_provider == company.ats_provider,
                    Job.source_kind == "WIDE_DISCOVERY",
                ),
            )
        )
    )
    by_external = {
        job.external_job_id: job
        for job in existing_jobs
        if job.ats_provider == company.ats_provider and job.external_job_id
    }
    by_fingerprint = {
        job.fingerprint: job
        for job in existing_jobs
        if job.ats_provider == company.ats_provider
    }
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
        upgraded_from_wide = False
        if current is None:
            current = _wide_upgrade_candidate(incoming, existing_jobs)
            upgraded_from_wide = current is not None

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
                source_kind="DIRECT_ATS",
                baseline_imported=initial_sync,
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
        else:
            changed = current.status is not JobStatus.ACTIVE or current.missing_count != 0
            if upgraded_from_wide:
                current.ats_provider = incoming.ats_provider
                current.external_job_id = incoming.external_job_id
                current.source_kind = "DIRECT_ATS"
                current.source_provider = None
                current.source_external_id = None
                current.source_company_name = None
                changed = True
            for field in _MUTABLE_FIELDS:
                value = getattr(incoming, field)
                if getattr(current, field) != value:
                    setattr(current, field, value)
                    changed = True
            if current.fingerprint != fingerprint:
                current.fingerprint = fingerprint
                changed = True
            current.last_seen_at = observed_at
            current.missing_count = 0
            current.status = JobStatus.ACTIVE
            current.closed_at = None
            if changed:
                updated += 1
                updated_ids.append(current.id)

        _upsert_direct_observation(
            session,
            job=current,
            company=company,
            incoming=incoming,
            observed_at=observed_at,
        )
        if current.external_job_id:
            by_external[current.external_job_id] = current
        by_fingerprint[current.fingerprint] = current
        observed_ids.add(current.id)

    closed = 0
    for current in existing_jobs:
        # Discovery-feed jobs not yet upgraded to this ATS are not part of the direct
        # source's complete snapshot and must not be closed because the ATS omitted them.
        if current.ats_provider != company.ats_provider:
            continue
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
