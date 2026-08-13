import uuid
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import current_user
from app.db.session import get_db
from app.models.company import Company
from app.models.enums import JobStatus, UserJobStateType
from app.models.job import Job
from app.models.job_match import JobMatch
from app.models.user import User
from app.models.user_job_state import UserJobState
from app.schemas.jobs_api import JobDetail, JobListItem, JobStateRequest
from app.services.user_job_states import JobStateError, set_job_state, user_can_manage_job

router = APIRouter(prefix="/api/v1/jobs", tags=["jobs"])


def _state_map(session: Session, user_id: uuid.UUID, job_ids: list[uuid.UUID]) -> dict[uuid.UUID, UserJobStateType]:
    if not job_ids:
        return {}
    states = session.execute(
        select(UserJobState.job_id, UserJobState.state).where(
            UserJobState.user_id == user_id, UserJobState.job_id.in_(job_ids)
        )
    )
    return {job_id: state for job_id, state in states}


def _serialize(job: Job, company_name: str, state: UserJobStateType | None) -> JobListItem:
    return JobListItem(
        id=job.id,
        company_id=job.company_id,
        company_name=company_name,
        title=job.title,
        location=job.location,
        work_mode=job.work_mode,
        employment_type=job.employment_type,
        apply_url=job.apply_url,
        source_url=job.source_url,
        posted_at=job.posted_at,
        first_seen_at=job.first_seen_at,
        last_seen_at=job.last_seen_at,
        status=job.status,
        closed_at=job.closed_at,
        user_state=state,
    )


@router.get("", response_model=list[JobListItem])
def list_jobs(
    view: Literal["matched", "saved", "ignored"] = "matched",
    job_status: JobStatus | None = Query(default=JobStatus.ACTIVE, alias="status"),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(current_user),
    session: Session = Depends(get_db),
) -> list[JobListItem]:
    if view == "matched":
        statement = (
            select(Job, Company.name)
            .join(Company, Company.id == Job.company_id)
            .join(JobMatch, JobMatch.job_id == Job.id)
            .where(JobMatch.user_id == user.id)
            .distinct()
        )
    else:
        desired = UserJobStateType.SAVED if view == "saved" else UserJobStateType.IGNORED
        statement = (
            select(Job, Company.name)
            .join(Company, Company.id == Job.company_id)
            .join(UserJobState, UserJobState.job_id == Job.id)
            .where(UserJobState.user_id == user.id, UserJobState.state == desired)
        )
    if job_status is not None:
        statement = statement.where(Job.status == job_status)
    rows = session.execute(
        statement.order_by(Job.first_seen_at.desc()).limit(limit).offset(offset)
    ).all()
    states = _state_map(session, user.id, [job.id for job, _ in rows])
    return [_serialize(job, company_name, states.get(job.id)) for job, company_name in rows]


@router.get("/{job_id}", response_model=JobDetail)
def get_job(
    job_id: uuid.UUID,
    user: User = Depends(current_user),
    session: Session = Depends(get_db),
) -> JobDetail:
    if not user_can_manage_job(session, user_id=user.id, job_id=job_id):
        raise HTTPException(status_code=404, detail="job not found")
    row = session.execute(
        select(Job, Company.name).join(Company, Company.id == Job.company_id).where(Job.id == job_id)
    ).one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="job not found")
    job, company_name = row
    state = session.scalar(
        select(UserJobState.state).where(
            UserJobState.user_id == user.id, UserJobState.job_id == job.id
        )
    )
    base = _serialize(job, company_name, state).model_dump()
    return JobDetail(**base, description=job.description)


@router.put("/{job_id}/state", response_model=JobListItem)
def update_job_state(
    job_id: uuid.UUID,
    payload: JobStateRequest,
    user: User = Depends(current_user),
    session: Session = Depends(get_db),
) -> JobListItem:
    try:
        state_record = set_job_state(
            session,
            user_id=user.id,
            job_id=job_id,
            state=payload.state,
            require_match=True,
        )
        row = session.execute(
            select(Job, Company.name)
            .join(Company, Company.id == Job.company_id)
            .where(Job.id == job_id)
        ).one()
        session.commit()
    except JobStateError as exc:
        session.rollback()
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    job, company_name = row
    return _serialize(job, company_name, state_record.state if state_record else None)
