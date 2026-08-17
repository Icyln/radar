from dataclasses import dataclass
from datetime import datetime

from app.models.enums import WorkMode
from app.models.job import Job
from app.models.job_profile import JobProfile
from app.matching.freshness import job_freshness_evidence, job_matches_profile_freshness
from app.services.text import normalize_for_match


@dataclass(frozen=True, slots=True)
class MatchDecision:
    matched: bool
    reason: dict[str, str | None]


def _tokens(value: str) -> set[str]:
    return {token for token in normalize_for_match(value).split(" ") if token}


def _token_subset(needle: str, haystack: str) -> bool:
    wanted = _tokens(needle)
    available = _tokens(haystack)
    return bool(wanted) and wanted.issubset(available)


def evaluate_job_profile(job: Job, profile: JobProfile, *, now: datetime | None = None) -> MatchDecision:
    title = normalize_for_match(job.title)
    location = normalize_for_match(job.location or "")
    searchable = normalize_for_match(" ".join([job.title, job.location or "", job.description or ""]))

    if not job_matches_profile_freshness(job, profile, now=now):
        evidence = job_freshness_evidence(job)
        if evidence.source == "UNKNOWN":
            rejection = "posting date unavailable"
        else:
            rejection = f"job is older than {profile.max_job_age_days} days"
        return MatchDecision(
            matched=False,
            reason={
                "matched_title": None,
                "matched_location": None,
                "matched_work_mode": None,
                "matched_freshness": None,
                "rejection_reason": rejection,
            },
        )

    for keyword in profile.excluded_keywords or []:
        normalized = normalize_for_match(keyword)
        if normalized and normalized in searchable:
            return MatchDecision(
                matched=False,
                reason={
                    "matched_title": None,
                    "matched_location": None,
                    "matched_work_mode": None,
                    "matched_freshness": None,
                    "rejection_reason": f"excluded keyword: {keyword}",
                },
            )

    matched_title = next(
        (candidate for candidate in (profile.job_titles or []) if _token_subset(candidate, title)),
        None,
    )
    if matched_title is None:
        return MatchDecision(
            matched=False,
            reason={
                "matched_title": None,
                "matched_location": None,
                "matched_work_mode": None,
                "matched_freshness": None,
                "rejection_reason": "title did not match",
            },
        )

    matched_location: str | None = None
    locations = profile.locations or []
    if locations:
        for candidate in locations:
            normalized_candidate = normalize_for_match(candidate)
            if normalized_candidate == "remote" and job.work_mode is WorkMode.REMOTE:
                matched_location = candidate
                break
            if _token_subset(candidate, location) or (location and _token_subset(location, candidate)):
                matched_location = candidate
                break
        if matched_location is None:
            return MatchDecision(
                matched=False,
                reason={
                    "matched_title": matched_title,
                    "matched_location": None,
                    "matched_work_mode": None,
                    "matched_freshness": None,
                    "rejection_reason": "location did not match",
                },
            )

    allowed_modes = {str(value).upper() for value in (profile.work_modes or [])}
    matched_work_mode: str | None = None
    if allowed_modes:
        if job.work_mode.value not in allowed_modes:
            return MatchDecision(
                matched=False,
                reason={
                    "matched_title": matched_title,
                    "matched_location": matched_location,
                    "matched_work_mode": None,
                    "matched_freshness": None,
                    "rejection_reason": "work mode did not match",
                },
            )
        matched_work_mode = job.work_mode.value

    freshness = job_freshness_evidence(job)
    return MatchDecision(
        matched=True,
        reason={
            "matched_title": matched_title,
            "matched_location": matched_location,
            "matched_work_mode": matched_work_mode,
            "matched_freshness": freshness.source,
            "rejection_reason": None,
        },
    )
