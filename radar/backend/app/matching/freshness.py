from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Literal

from app.models.job import Job
from app.models.job_profile import JobProfile

FreshnessSource = Literal["POSTED_AT", "DISCOVERY_SIGNAL", "FIRST_SEEN", "UNKNOWN"]


@dataclass(frozen=True, slots=True)
class FreshnessEvidence:
    at: datetime | None
    source: FreshnessSource


def _aware(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def job_freshness_evidence(job: Job) -> FreshnessEvidence:
    """Return the safest timestamp Radar can use for freshness.

    Provider publication time wins. A fresh external hiring signal may provide
    secondary evidence for one unambiguously identified baseline job. If neither exists, Radar
    may use first_seen_at only for jobs discovered after the company's baseline sync.
    Other baseline inventory remains UNKNOWN rather than being made to look freshly
    posted merely because Radar learned about the source today.
    """
    posted_at = _aware(job.posted_at)
    if posted_at is not None:
        return FreshnessEvidence(at=posted_at, source="POSTED_AT")
    discovery_signal_at = _aware(job.discovery_signal_at)
    if discovery_signal_at is not None:
        return FreshnessEvidence(at=discovery_signal_at, source="DISCOVERY_SIGNAL")
    if not job.baseline_imported:
        return FreshnessEvidence(at=_aware(job.first_seen_at), source="FIRST_SEEN")
    return FreshnessEvidence(at=None, source="UNKNOWN")


def job_matches_profile_freshness(
    job: Job,
    profile: JobProfile,
    *,
    now: datetime | None = None,
) -> bool:
    max_age_days = profile.max_job_age_days
    if max_age_days is None:
        return True

    evidence = job_freshness_evidence(job)
    if evidence.at is None:
        return bool(profile.include_unknown_posted_at)

    current = _aware(now) or datetime.now(timezone.utc)
    return evidence.at >= current - timedelta(days=max_age_days)
