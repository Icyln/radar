from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import distinct, func, select
from sqlalchemy.orm import Session

from app.api.deps import current_user
from app.db.session import get_db
from app.models.company import Company
from app.models.crawler_log import CrawlerLog
from app.models.enums import CrawlerStatus, NotificationStatus
from app.models.job import Job
from app.models.job_match import JobMatch
from app.models.job_profile import JobProfile
from app.models.notification import Notification
from app.models.user import User
from app.models.user_company_watchlist import UserCompanyWatchlist
from app.models.user_job_state import UserJobState
from app.matching.freshness import job_freshness_evidence
from app.matching.service import profile_job_is_current_match
from app.schemas.dashboard import DashboardSummary
from app.schemas.jobs_api import JobListItem

router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"])


def _start_of_today() -> datetime:
    now = datetime.now(timezone.utc)
    return datetime(now.year, now.month, now.day, tzinfo=timezone.utc)


@router.get("/summary", response_model=DashboardSummary)
def summary(
    user: User = Depends(current_user), session: Session = Depends(get_db)
) -> DashboardSummary:
    today = _start_of_today()
    active_profiles = session.scalar(
        select(func.count(JobProfile.id)).where(
            JobProfile.user_id == user.id, JobProfile.enabled.is_(True)
        )
    ) or 0
    monitored_companies = session.scalar(
        select(func.count(Company.id)).where(Company.active.is_(True))
    ) or 0
    watched_companies = session.scalar(
        select(func.count(UserCompanyWatchlist.id)).where(UserCompanyWatchlist.user_id == user.id)
    ) or 0
    jobs_discovered_today = session.scalar(
        select(func.count(distinct(JobMatch.job_id)))
        .join(Job, Job.id == JobMatch.job_id)
        .where(JobMatch.user_id == user.id, Job.first_seen_at >= today)
    ) or 0
    matches_today = session.scalar(
        select(func.count(JobMatch.id)).where(
            JobMatch.user_id == user.id, JobMatch.matched_at >= today
        )
    ) or 0
    alerts_sent_today = session.scalar(
        select(func.count(Notification.id)).where(
            Notification.user_id == user.id,
            Notification.status == NotificationStatus.SENT,
            Notification.sent_at >= today,
        )
    ) or 0
    last_successful_crawler_run = session.scalar(
        select(func.max(CrawlerLog.completed_at)).where(CrawlerLog.status == CrawlerStatus.SUCCESS)
    )

    candidate_rows = session.execute(
        select(Job, Company.name, JobProfile)
        .join(Company, Company.id == Job.company_id)
        .join(JobMatch, JobMatch.job_id == Job.id)
        .join(JobProfile, JobProfile.id == JobMatch.job_profile_id)
        .where(JobMatch.user_id == user.id, JobProfile.enabled.is_(True))
        .order_by(Job.first_seen_at.desc(), Job.id.desc())
    ).all()
    watch_pairs = set(
        session.execute(
            select(UserCompanyWatchlist.user_id, UserCompanyWatchlist.company_id).where(
                UserCompanyWatchlist.user_id == user.id
            )
        ).all()
    )
    rows: list[tuple[Job, str]] = []
    seen: set = set()
    for job, company_name, profile in candidate_rows:
        if job.id in seen:
            continue
        if profile_job_is_current_match(profile=profile, job=job, watch_pairs=watch_pairs):
            seen.add(job.id)
            rows.append((job, company_name))
            if len(rows) == 5:
                break
    job_ids = [job.id for job, _ in rows]
    states = {
        job_id: state
        for job_id, state in session.execute(
            select(UserJobState.job_id, UserJobState.state).where(
                UserJobState.user_id == user.id,
                UserJobState.job_id.in_(job_ids) if job_ids else False,
            )
        )
    }
    recent = [
        JobListItem(
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
            user_state=states.get(job.id),
            freshness_at=job_freshness_evidence(job).at,
            freshness_source=job_freshness_evidence(job).source,
        )
        for job, company_name in rows
    ]
    return DashboardSummary(
        active_profiles=int(active_profiles),
        monitored_companies=int(monitored_companies),
        watched_companies=int(watched_companies),
        jobs_discovered_today=int(jobs_discovered_today),
        matches_today=int(matches_today),
        alerts_sent_today=int(alerts_sent_today),
        last_successful_crawler_run=last_successful_crawler_run,
        recent_matching_jobs=recent,
    )
