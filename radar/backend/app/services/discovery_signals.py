from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.discovery_target import DiscoveryTarget
from app.models.discovery_target_candidate import DiscoveryTargetCandidate
from app.models.job import Job
from app.models.source_candidate import SourceCandidate
from app.services.text import normalize_for_match


def _aware(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _normalized_url(value: str | None) -> str:
    if not value:
        return ""
    parsed = urlparse(value)
    host = (parsed.hostname or "").casefold()
    path = parsed.path.rstrip("/").casefold()
    return f"{host}{path}"


def _select_signal_job(target: DiscoveryTarget, jobs: list[Job]) -> Job | None:
    wanted_title = normalize_for_match(target.job_title_hint)
    if not wanted_title:
        return None

    exact = [job for job in jobs if normalize_for_match(job.title) == wanted_title]
    if not exact:
        return None
    if len(exact) == 1:
        return exact[0]

    target_url = _normalized_url(target.url)
    if target_url:
        url_matches = [
            job
            for job in exact
            if target_url in {_normalized_url(job.apply_url), _normalized_url(job.source_url)}
        ]
        if len(url_matches) == 1:
            return url_matches[0]

    wanted_location = normalize_for_match(target.job_location_hint)
    if wanted_location:
        location_matches = []
        for job in exact:
            job_location = normalize_for_match(job.location)
            if not job_location:
                continue
            if (
                job_location == wanted_location
                or wanted_location in job_location
                or job_location in wanted_location
            ):
                location_matches.append(job)
        if len(location_matches) == 1:
            return location_matches[0]

    # Multiple baseline roles with the same title are intentionally ambiguous. Do not
    # turn a single external signal into several "new job" alerts.
    return None


def apply_discovery_signals_to_jobs(
    session: Session,
    *,
    company_id: uuid.UUID,
    job_ids: list[uuid.UUID],
    max_signal_age_days: int,
    now: datetime | None = None,
) -> list[uuid.UUID]:
    """Attach fresh external-signal evidence to one safely identified baseline job.

    Returns baseline job IDs that are eligible for the narrow initial-sync notification
    exception. Provider publication timestamps still remain the primary freshness source.
    """
    if not job_ids:
        return []
    current = _aware(now) or datetime.now(timezone.utc)
    cutoff = current - timedelta(days=max_signal_age_days)

    jobs = list(session.scalars(select(Job).where(Job.id.in_(job_ids))))
    targets = list(
        session.scalars(
            select(DiscoveryTarget)
            .join(
                DiscoveryTargetCandidate,
                DiscoveryTargetCandidate.discovery_target_id == DiscoveryTarget.id,
            )
            .join(
                SourceCandidate,
                SourceCandidate.id == DiscoveryTargetCandidate.source_candidate_id,
            )
            .where(
                SourceCandidate.promoted_company_id == company_id,
                DiscoveryTarget.job_title_hint.is_not(None),
                DiscoveryTarget.job_posted_at_hint.is_not(None),
            )
            .order_by(DiscoveryTarget.job_posted_at_hint.desc())
        )
    )

    alertable: set[uuid.UUID] = set()
    claimed_jobs: set[uuid.UUID] = set()
    for target in targets:
        signal_at = _aware(target.job_posted_at_hint)
        if signal_at is None or signal_at < cutoff or signal_at > current + timedelta(days=1):
            continue
        job = _select_signal_job(target, jobs)
        if job is None or job.id in claimed_jobs:
            continue
        claimed_jobs.add(job.id)
        if job.discovery_signal_at is None or signal_at > _aware(job.discovery_signal_at):
            job.discovery_signal_at = signal_at
            job.discovery_signal_source = (target.source_label or "hiring-signal")[:100]
        if job.baseline_imported:
            alertable.add(job.id)
    session.flush()
    return list(alertable)


__all__ = ["apply_discovery_signals_to_jobs"]
