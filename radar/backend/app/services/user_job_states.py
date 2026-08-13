import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.enums import UserJobStateType
from app.models.job import Job
from app.models.job_match import JobMatch
from app.models.user_job_state import UserJobState


class JobStateError(Exception):
    pass


def user_can_manage_job(session: Session, *, user_id: uuid.UUID, job_id: uuid.UUID) -> bool:
    return session.scalar(
        select(JobMatch.id).where(JobMatch.user_id == user_id, JobMatch.job_id == job_id).limit(1)
    ) is not None


def set_job_state(
    session: Session,
    *,
    user_id: uuid.UUID,
    job_id: uuid.UUID,
    state: UserJobStateType | None,
    require_match: bool = True,
) -> UserJobState | None:
    if session.get(Job, job_id) is None:
        raise JobStateError("job not found")
    if require_match and not user_can_manage_job(session, user_id=user_id, job_id=job_id):
        raise JobStateError("job is not available to this user")

    current = session.scalar(
        select(UserJobState).where(
            UserJobState.user_id == user_id,
            UserJobState.job_id == job_id,
        )
    )
    if state is None:
        if current is not None:
            session.delete(current)
            session.flush()
        return None
    if current is None:
        current = UserJobState(user_id=user_id, job_id=job_id, state=state)
        session.add(current)
    else:
        current.state = state
    session.flush()
    return current
