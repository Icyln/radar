import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.matching.engine import evaluate_job_profile
from app.models.job import Job
from app.models.job_match import JobMatch
from app.models.job_profile import JobProfile
from app.models.user import User


@dataclass(slots=True)
class MatchCreationResult:
    created: int
    match_ids: list[uuid.UUID]


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
    created_ids: list[uuid.UUID] = []
    for job in jobs:
        for profile in profiles:
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


def backfill_profile_matches(session: Session, *, profile: JobProfile) -> MatchCreationResult:
    from app.models.enums import JobStatus

    jobs = list(session.scalars(select(Job).where(Job.status == JobStatus.ACTIVE)))
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
