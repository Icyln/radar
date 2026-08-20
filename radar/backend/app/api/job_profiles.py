import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import current_user
from app.core.config import Settings, get_settings
from app.db.session import get_db
from app.matching.service import backfill_profile_matches, prune_profile_scope_matches
from app.models.job_profile import JobProfile
from app.models.user import User
from app.schemas.job_profile import JobProfileCreate, JobProfileRead, JobProfileUpdate

router = APIRouter(prefix="/api/v1/job-profiles", tags=["job-profiles"])


def _owned_profile(session: Session, *, user_id: uuid.UUID, profile_id: uuid.UUID) -> JobProfile:
    profile = session.scalar(
        select(JobProfile).where(JobProfile.id == profile_id, JobProfile.user_id == user_id)
    )
    if profile is None:
        raise HTTPException(status_code=404, detail="job alert not found")
    return profile


def _active_profiles(session: Session, *, user_id: uuid.UUID, exclude_id: uuid.UUID | None = None) -> list[JobProfile]:
    statement = select(JobProfile).where(
        JobProfile.user_id == user_id,
        JobProfile.enabled.is_(True),
    )
    if exclude_id is not None:
        statement = statement.where(JobProfile.id != exclude_id)
    return list(session.scalars(statement))


def _validate_profile_limits(
    session: Session,
    *,
    user_id: uuid.UUID,
    settings: Settings,
    enabled: bool,
    job_titles: list[str],
    exclude_id: uuid.UUID | None = None,
    creating: bool = False,
) -> None:
    if len(job_titles) > settings.max_job_titles_per_profile:
        raise HTTPException(
            status_code=422,
            detail=f"A job alert can contain up to {settings.max_job_titles_per_profile} job titles.",
        )

    if creating:
        total = int(
            session.scalar(
                select(func.count(JobProfile.id)).where(JobProfile.user_id == user_id)
            )
            or 0
        )
        if total >= settings.max_job_profiles_total:
            raise HTTPException(
                status_code=409,
                detail=f"You can keep up to {settings.max_job_profiles_total} job alerts. Delete an old alert before creating another.",
            )

    if not enabled:
        return

    active = _active_profiles(session, user_id=user_id, exclude_id=exclude_id)
    if len(active) >= settings.max_active_job_profiles:
        raise HTTPException(
            status_code=409,
            detail=f"You can have up to {settings.max_active_job_profiles} active job alerts. Pause one before enabling another.",
        )
    active_title_count = sum(len(profile.job_titles or []) for profile in active) + len(job_titles)
    if active_title_count > settings.max_active_job_titles_per_user:
        raise HTTPException(
            status_code=409,
            detail=(
                f"Active job alerts can contain up to {settings.max_active_job_titles_per_user} "
                "job titles in total. Reduce titles or pause another alert."
            ),
        )


@router.get("", response_model=list[JobProfileRead])
def list_profiles(
    user: User = Depends(current_user), session: Session = Depends(get_db)
) -> list[JobProfile]:
    return list(
        session.scalars(
            select(JobProfile).where(JobProfile.user_id == user.id).order_by(JobProfile.created_at.asc())
        )
    )


@router.post("", response_model=JobProfileRead, status_code=status.HTTP_201_CREATED)
def create_profile(
    payload: JobProfileCreate,
    user: User = Depends(current_user),
    session: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> JobProfile:
    _validate_profile_limits(
        session,
        user_id=user.id,
        settings=settings,
        enabled=payload.enabled,
        job_titles=payload.job_titles,
        creating=True,
    )
    profile = JobProfile(
        user_id=user.id,
        name=payload.name,
        enabled=payload.enabled,
        coverage_mode=payload.coverage_mode,
        job_titles=payload.job_titles,
        locations=payload.locations,
        work_modes=[mode.value for mode in payload.work_modes],
        excluded_keywords=payload.excluded_keywords,
        max_job_age_days=payload.max_job_age_days,
        include_unknown_posted_at=payload.include_unknown_posted_at,
    )
    session.add(profile)
    session.flush()
    if profile.enabled:
        backfill_profile_matches(session, profile=profile)
    session.commit()
    session.refresh(profile)
    return profile


@router.get("/{profile_id}", response_model=JobProfileRead)
def get_profile(
    profile_id: uuid.UUID,
    user: User = Depends(current_user),
    session: Session = Depends(get_db),
) -> JobProfile:
    return _owned_profile(session, user_id=user.id, profile_id=profile_id)


@router.patch("/{profile_id}", response_model=JobProfileRead)
def update_profile(
    profile_id: uuid.UUID,
    payload: JobProfileUpdate,
    user: User = Depends(current_user),
    session: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> JobProfile:
    profile = _owned_profile(session, user_id=user.id, profile_id=profile_id)
    updates = payload.model_dump(exclude_unset=True)
    next_enabled = bool(updates.get("enabled", profile.enabled))
    next_titles = updates.get("job_titles", profile.job_titles)
    assert next_titles is not None
    _validate_profile_limits(
        session,
        user_id=user.id,
        settings=settings,
        enabled=next_enabled,
        job_titles=next_titles,
        exclude_id=profile.id,
    )
    if "work_modes" in updates:
        updates["work_modes"] = [mode.value for mode in updates["work_modes"]]
    for field, value in updates.items():
        setattr(profile, field, value)
    session.flush()
    prune_profile_scope_matches(session, profile=profile)
    if profile.enabled:
        backfill_profile_matches(session, profile=profile)
    session.commit()
    session.refresh(profile)
    return profile


@router.delete("/{profile_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_profile(
    profile_id: uuid.UUID,
    user: User = Depends(current_user),
    session: Session = Depends(get_db),
) -> None:
    profile = _owned_profile(session, user_id=user.id, profile_id=profile_id)
    session.delete(profile)
    session.commit()
