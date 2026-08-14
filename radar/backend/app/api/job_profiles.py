import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import current_user
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
        raise HTTPException(status_code=404, detail="job profile not found")
    return profile


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
) -> JobProfile:
    profile = JobProfile(
        user_id=user.id,
        name=payload.name,
        enabled=payload.enabled,
        coverage_mode=payload.coverage_mode,
        job_titles=payload.job_titles,
        locations=payload.locations,
        work_modes=[mode.value for mode in payload.work_modes],
        excluded_keywords=payload.excluded_keywords,
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
) -> JobProfile:
    profile = _owned_profile(session, user_id=user.id, profile_id=profile_id)
    updates = payload.model_dump(exclude_unset=True)
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
