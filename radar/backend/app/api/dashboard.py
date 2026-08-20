from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import distinct, func, select
from sqlalchemy.orm import Session

from app.api.deps import current_user
from app.db.session import get_db
from app.core.config import Settings, get_settings
from app.models.company import Company
from app.models.crawler_log import CrawlerLog
from app.models.discovery_run import DiscoveryRun
from app.models.enums import CrawlerStatus, JobStatus, NotificationStatus
from app.models.job import Job
from app.models.job_match import JobMatch
from app.models.job_profile import JobProfile
from app.models.monitor_run import MonitorRun
from app.models.notification import Notification
from app.models.user import User
from app.models.user_company_watchlist import UserCompanyWatchlist
from app.models.user_job_state import UserJobState
from app.matching.freshness import job_freshness_evidence
from app.matching.service import profile_job_is_current_match
from app.schemas.dashboard import DashboardSummary, MonitoringAutomationHealth, WideAutomationHealth
from app.schemas.jobs_api import JobListItem

router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"])


def _start_of_today() -> datetime:
    now = datetime.now(timezone.utc)
    return datetime(now.year, now.month, now.day, tzinfo=timezone.utc)


def _state_from_age(state: str, *, completed_at: datetime | None, stale_minutes: int) -> str:
    if completed_at is None:
        return state
    completed = completed_at if completed_at.tzinfo else completed_at.replace(tzinfo=timezone.utc)
    if datetime.now(timezone.utc) - completed.astimezone(timezone.utc) > timedelta(minutes=stale_minutes):
        return "STALE"
    return state


def _monitoring_health(session: Session, settings: Settings) -> MonitoringAutomationHealth:
    rows = list(
        session.scalars(
            select(MonitorRun)
            .where(MonitorRun.trigger == "github-actions")
            .order_by(MonitorRun.started_at.desc())
            .limit(20)
        )
    )
    if not rows:
        rows = list(session.scalars(select(MonitorRun).order_by(MonitorRun.started_at.desc()).limit(20)))
    if not rows:
        return MonitoringAutomationHealth(state="UNKNOWN", last_run_at=None, trigger=None)
    latest = rows[0]
    if latest.external_run_id:
        group = [row for row in rows if row.external_run_id == latest.external_run_id]
    else:
        group = [latest]
    if any(row.completed_at is None for row in group):
        state = "RUNNING"
    else:
        failures = sum(row.companies_failed for row in group)
        successes = sum(row.companies_succeeded for row in group)
        partial = any(row.status == CrawlerStatus.PARTIAL for row in group)
        hard_failed = any(row.status == CrawlerStatus.FAILED for row in group)
        if hard_failed and successes == 0:
            state = "FAILED"
        elif failures or partial or hard_failed:
            state = "DEGRADED"
        else:
            state = "HEALTHY"
    completed_values = [row.completed_at for row in group if row.completed_at is not None]
    last_run_at = max(completed_values) if completed_values else max(row.started_at for row in group)
    if state not in {"RUNNING", "FAILED"}:
        state = _state_from_age(
            state, completed_at=last_run_at, stale_minutes=settings.monitor_health_stale_minutes
        )
    return MonitoringAutomationHealth(
        state=state,
        last_run_at=last_run_at,
        trigger=latest.trigger,
        companies_selected=sum(row.companies_selected for row in group),
        companies_succeeded=sum(row.companies_succeeded for row in group),
        companies_failed=sum(row.companies_failed for row in group),
        notifications_sent=sum(row.notifications_sent for row in group),
    )


def _wide_health(session: Session, settings: Settings) -> WideAutomationHealth:
    run = session.scalar(
        select(DiscoveryRun)
        .where(DiscoveryRun.trigger == "github-actions")
        .order_by(DiscoveryRun.started_at.desc())
    )
    if run is None:
        run = session.scalar(select(DiscoveryRun).order_by(DiscoveryRun.started_at.desc()))
    if run is None:
        return WideAutomationHealth(state="UNKNOWN", last_run_at=None, trigger=None)
    if run.completed_at is None:
        state = "RUNNING"
        last_run_at = run.started_at
    else:
        last_run_at = run.completed_at
        if run.status == CrawlerStatus.FAILED:
            state = "FAILED"
        elif run.status == CrawlerStatus.PARTIAL or run.provider_failures:
            state = "DEGRADED"
        else:
            state = "HEALTHY"
        if state != "FAILED":
            state = _state_from_age(
                state, completed_at=last_run_at, stale_minutes=settings.discovery_health_stale_minutes
            )
    warnings = [line for line in (run.provider_warnings or "").splitlines() if line][:4]
    return WideAutomationHealth(
        state=state,
        last_run_at=last_run_at,
        trigger=run.trigger,
        signals_seen=run.signals_seen,
        signals_relevant=run.signals_relevant,
        jobs_new=run.jobs_new,
        jobs_deduplicated=run.jobs_deduplicated,
        provider_failures=run.provider_failures,
        notifications_sent=run.notifications_sent,
        warnings=warnings,
    )


@router.get("/summary", response_model=DashboardSummary)
def summary(
    user: User = Depends(current_user),
    session: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
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
    wide_jobs_today = session.scalar(
        select(func.count(distinct(JobMatch.job_id)))
        .join(Job, Job.id == JobMatch.job_id)
        .where(
            JobMatch.user_id == user.id,
            Job.first_seen_at >= today,
            Job.source_kind == "WIDE_DISCOVERY",
        )
    ) or 0
    direct_jobs_today = session.scalar(
        select(func.count(distinct(JobMatch.job_id)))
        .join(Job, Job.id == JobMatch.job_id)
        .where(
            JobMatch.user_id == user.id,
            Job.first_seen_at >= today,
            Job.source_kind == "DIRECT_ATS",
        )
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
    wide_jobs_unknown = session.scalar(
        select(func.count(Job.id)).where(
            Job.source_kind == "WIDE_DISCOVERY",
            Job.status == JobStatus.UNKNOWN,
        )
    ) or 0
    last_successful_crawler_run = session.scalar(
        select(func.max(CrawlerLog.completed_at)).where(CrawlerLog.status == CrawlerStatus.SUCCESS)
    )

    candidate_rows = session.execute(
        select(Job, Company.name, JobProfile)
        .outerjoin(Company, Company.id == Job.company_id)
        .join(JobMatch, JobMatch.job_id == Job.id)
        .join(JobProfile, JobProfile.id == JobMatch.job_profile_id)
        .where(JobMatch.user_id == user.id, JobProfile.enabled.is_(True))
        .order_by(Job.first_seen_at.desc(), Job.id.desc())
        .limit(250)
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
            company_name=company_name or job.source_company_name or "Unknown company",
            ats_provider=job.ats_provider,
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
            source_kind=job.source_kind,
            source_provider=job.source_provider or (job.ats_provider.value if job.ats_provider else None),
            source_verified=job.source_kind == "DIRECT_ATS",
        )
        for job, company_name in rows
    ]
    return DashboardSummary(
        active_profiles=int(active_profiles),
        monitored_companies=int(monitored_companies),
        watched_companies=int(watched_companies),
        jobs_discovered_today=int(jobs_discovered_today),
        wide_jobs_today=int(wide_jobs_today),
        direct_jobs_today=int(direct_jobs_today),
        matches_today=int(matches_today),
        alerts_sent_today=int(alerts_sent_today),
        last_successful_crawler_run=last_successful_crawler_run,
        wide_jobs_unknown=int(wide_jobs_unknown),
        monitoring_automation=_monitoring_health(session, settings),
        wide_search_automation=_wide_health(session, settings),
        recent_matching_jobs=recent,
    )
