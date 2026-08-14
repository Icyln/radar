import uuid
from dataclasses import dataclass

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.matching.engine import evaluate_job_profile
from app.models.enums import JobStatus, ProfileCoverageMode
from app.models.job import Job
from app.models.job_match import JobMatch
from app.models.job_profile import JobProfile
from app.models.user import User
from app.models.user_company_watchlist import UserCompanyWatchlist


@dataclass(slots=True)
class MatchCreationResult:
    created: int
    match_ids: list[uuid.UUID]


def _create_profile_job_matches(
    session: Session, *, profile: JobProfile, jobs: list[Job]
) -> MatchCreationResult:
    created_ids: list[uuid.UUID] = []
    for job in jobs:
        decision = evaluate_job_profile(job, profile)
        if not decision.matched:
            continue
        match = JobMatch(
            user_id=profile.user_id,
            job_profile_id=profile.id,
            job_id=job.id,
            match_reason=decision.reason,
        )
        try:
            with session.begin_nested():
                session.add(match)
                session.flush()
            created_ids.append(match.id)
        except IntegrityError:
            continue
    session.flush()
    return MatchCreationResult(created=len(created_ids), match_ids=created_ids)


def create_matches_for_jobs(session: Session, *, job_ids: list[uuid.UUID]) -> MatchCreationResult:
    if not job_ids:
        return MatchCreationResult(created=0, match_ids=[])

    jobs = list(session.scalars(select(Job).where(Job.id.in_(job_ids))))
    profiles = list(
        session.scalars(
            select(JobProfile)
            .join(User, User.id == JobProfile.user_id)
            .where(JobProfile.enabled.is_(True), User.is_active.is_(True))
        )
    )
    watch_pairs = set(
        session.execute(
            select(UserCompanyWatchlist.user_id, UserCompanyWatchlist.company_id)
        ).all()
    )

    created_ids: list[uuid.UUID] = []
    for profile in profiles:
        in_scope = [
            job
            for job in jobs
            if profile.coverage_mode is ProfileCoverageMode.WIDE
            or (profile.user_id, job.company_id) in watch_pairs
        ]
        result = _create_profile_job_matches(session, profile=profile, jobs=in_scope)
        created_ids.extend(result.match_ids)
    return MatchCreationResult(created=len(created_ids), match_ids=created_ids)


def backfill_profile_matches(session: Session, *, profile: JobProfile) -> MatchCreationResult:
    statement = select(Job).where(Job.status == JobStatus.ACTIVE)
    if profile.coverage_mode is ProfileCoverageMode.WATCHLIST:
        watched_company_ids = list(
            session.scalars(
                select(UserCompanyWatchlist.company_id).where(
                    UserCompanyWatchlist.user_id == profile.user_id
                )
            )
        )
        if not watched_company_ids:
            return MatchCreationResult(created=0, match_ids=[])
        statement = statement.where(Job.company_id.in_(watched_company_ids))
    jobs = list(session.scalars(statement))
    return _create_profile_job_matches(session, profile=profile, jobs=jobs)


def prune_profile_scope_matches(session: Session, *, profile: JobProfile) -> int:
    """Remove matches that are no longer inside a WATCHLIST profile's source scope.

    WIDE profiles retain all existing matches. This intentionally only reconciles coverage,
    not historical title/location rule changes.
    """
    if profile.coverage_mode is ProfileCoverageMode.WIDE:
        return 0

    watched_company_ids = set(
        session.scalars(
            select(UserCompanyWatchlist.company_id).where(
                UserCompanyWatchlist.user_id == profile.user_id
            )
        )
    )
    rows = session.execute(
        select(JobMatch.id, Job.company_id)
        .join(Job, Job.id == JobMatch.job_id)
        .where(JobMatch.job_profile_id == profile.id)
    ).all()
    remove_ids = [match_id for match_id, company_id in rows if company_id not in watched_company_ids]
    if remove_ids:
        session.execute(delete(JobMatch).where(JobMatch.id.in_(remove_ids)))
        session.flush()
    return len(remove_ids)


def backfill_watchlist_profiles_for_company(
    session: Session, *, user_id: uuid.UUID, company_id: uuid.UUID
) -> MatchCreationResult:
    profiles = list(
        session.scalars(
            select(JobProfile).where(
                JobProfile.user_id == user_id,
                JobProfile.enabled.is_(True),
                JobProfile.coverage_mode == ProfileCoverageMode.WATCHLIST,
            )
        )
    )
    jobs = list(
        session.scalars(
            select(Job).where(Job.company_id == company_id, Job.status == JobStatus.ACTIVE)
        )
    )
    created_ids: list[uuid.UUID] = []
    for profile in profiles:
        result = _create_profile_job_matches(session, profile=profile, jobs=jobs)
        created_ids.extend(result.match_ids)
    return MatchCreationResult(created=len(created_ids), match_ids=created_ids)


def prune_watchlist_company_matches(
    session: Session, *, user_id: uuid.UUID, company_id: uuid.UUID
) -> int:
    profile_ids = list(
        session.scalars(
            select(JobProfile.id).where(
                JobProfile.user_id == user_id,
                JobProfile.coverage_mode == ProfileCoverageMode.WATCHLIST,
            )
        )
    )
    if not profile_ids:
        return 0
    remove_ids = list(
        session.scalars(
            select(JobMatch.id)
            .join(Job, Job.id == JobMatch.job_id)
            .where(
                JobMatch.job_profile_id.in_(profile_ids),
                Job.company_id == company_id,
            )
        )
    )
    if remove_ids:
        session.execute(delete(JobMatch).where(JobMatch.id.in_(remove_ids)))
        session.flush()
    return len(remove_ids)
