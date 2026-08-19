import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import admin_user, current_user
from app.db.session import get_db
from app.models.discovery_target import DiscoveryTarget
from app.models.enums import (
    DiscoveryCandidateStatus,
    DiscoveryTargetOrigin,
    DiscoveryTargetStatus,
)
from app.models.source_candidate import SourceCandidate
from app.models.telegram_connection import TelegramConnection
from app.models.user import User
from app.schemas.discovery import (
    DiscoverySummaryRead,
    DiscoveryTargetCreate,
    DiscoveryTargetRead,
    SourceCandidateRead,
    WideSearchRefreshRead,
)
from app.services.discovery import DiscoveryService, discovery_summary
from app.services.notifications import deliver_pending_notifications
from app.core.config import Settings, get_settings

router = APIRouter(prefix="/api/v1/discovery", tags=["discovery"])


@router.post("/targets", response_model=DiscoveryTargetRead, status_code=status.HTTP_202_ACCEPTED)
def create_target(
    payload: DiscoveryTargetCreate,
    user: User = Depends(current_user),
    session: Session = Depends(get_db),
) -> DiscoveryTarget:
    url = str(payload.url)
    if len(url) > 1500:
        raise HTTPException(status_code=422, detail="discovery URL is too long")
    outstanding = int(
        session.scalar(
            select(func.count())
            .select_from(DiscoveryTarget)
            .where(
                DiscoveryTarget.submitted_by_user_id == user.id,
                DiscoveryTarget.status.in_(
                    [DiscoveryTargetStatus.PENDING, DiscoveryTargetStatus.SCANNING]
                ),
            )
        )
        or 0
    )
    if outstanding >= 25:
        raise HTTPException(
            status_code=429,
            detail="too many pending discovery requests; wait for the discovery worker to process them",
        )
    existing = session.scalar(
        select(DiscoveryTarget).where(
            DiscoveryTarget.submitted_by_user_id == user.id,
            DiscoveryTarget.url == url,
            DiscoveryTarget.status.in_(
                [DiscoveryTargetStatus.PENDING, DiscoveryTargetStatus.SCANNING]
            ),
        )
    )
    if existing is not None:
        return existing
    target = DiscoveryTarget(
        submitted_by_user_id=user.id,
        url=url,
        company_name_hint=(payload.company_name_hint or "").strip() or None,
        auto_watch=payload.auto_watch,
        origin=DiscoveryTargetOrigin.USER,
        source_label=None,
        status=DiscoveryTargetStatus.PENDING,
    )
    session.add(target)
    session.commit()
    session.refresh(target)
    return target


@router.get("/targets", response_model=list[DiscoveryTargetRead])
def list_targets(
    include_all: bool = Query(default=False),
    user: User = Depends(current_user),
    session: Session = Depends(get_db),
) -> list[DiscoveryTarget]:
    stmt = select(DiscoveryTarget).order_by(DiscoveryTarget.created_at.desc())
    if not (include_all and user.is_admin):
        stmt = stmt.where(DiscoveryTarget.submitted_by_user_id == user.id)
    return list(session.scalars(stmt.limit(200)))


@router.post("/targets/{target_id}/retry", response_model=DiscoveryTargetRead)
def retry_target(
    target_id: uuid.UUID,
    user: User = Depends(current_user),
    session: Session = Depends(get_db),
) -> DiscoveryTarget:
    target = session.get(DiscoveryTarget, target_id)
    if target is None:
        raise HTTPException(status_code=404, detail="discovery target not found")
    if target.submitted_by_user_id != user.id and not user.is_admin:
        raise HTTPException(status_code=403, detail="not allowed to retry this discovery target")
    target.status = DiscoveryTargetStatus.PENDING
    target.error_type = None
    target.error_message = None
    session.commit()
    session.refresh(target)
    return target


@router.get("/candidates", response_model=list[SourceCandidateRead])
def list_candidates(
    _: User = Depends(admin_user), session: Session = Depends(get_db)
) -> list[SourceCandidate]:
    return list(session.scalars(select(SourceCandidate).order_by(SourceCandidate.created_at.desc()).limit(500)))


@router.post("/candidates/{candidate_id}/retry", response_model=SourceCandidateRead)
def retry_candidate(
    candidate_id: uuid.UUID,
    _: User = Depends(admin_user),
    session: Session = Depends(get_db),
) -> SourceCandidate:
    candidate = session.get(SourceCandidate, candidate_id)
    if candidate is None:
        raise HTTPException(status_code=404, detail="source candidate not found")
    candidate.status = DiscoveryCandidateStatus.DISCOVERED
    candidate.error_type = None
    candidate.error_message = None
    session.commit()
    session.refresh(candidate)
    return candidate


@router.post("/candidates/{candidate_id}/promote", response_model=SourceCandidateRead)
def promote_candidate(
    candidate_id: uuid.UUID,
    _: User = Depends(admin_user),
    settings: Settings = Depends(get_settings),
    session: Session = Depends(get_db),
) -> SourceCandidate:
    candidate = session.get(SourceCandidate, candidate_id)
    if candidate is None:
        raise HTTPException(status_code=404, detail="source candidate not found")
    if candidate.status is not DiscoveryCandidateStatus.VALID:
        raise HTTPException(status_code=409, detail="candidate must be VALID before promotion")
    service = DiscoveryService(engine=session.get_bind(), settings=settings)
    try:
        service.promote_candidate(candidate_id)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    session.expire_all()
    refreshed = session.get(SourceCandidate, candidate_id)
    assert refreshed is not None
    return refreshed


@router.post("/wide-search/refresh", response_model=WideSearchRefreshRead)
async def refresh_wide_search(
    user: User = Depends(current_user),
    settings: Settings = Depends(get_settings),
    session: Session = Depends(get_db),
) -> WideSearchRefreshRead:
    """Run the fast user-facing Phase 7C job-discovery path.

    This intentionally does not validate hundreds of ATS candidates inline. Jobs are
    stored/matched immediately; ATS resolution remains a background quality upgrade.
    """
    engine = session.get_bind()
    service = DiscoveryService(engine=engine, settings=settings)
    result = await service.ingest_hiring_signals(user_id=user.id)
    notification_ids = list(result.get("_notification_ids", []))
    connection = session.scalar(
        select(TelegramConnection).where(
            TelegramConnection.user_id == user.id,
            TelegramConnection.verified.is_(True),
        )
    )
    telegram_ready = connection is not None and bool(settings.telegram_bot_token)
    notifications_sent = 0
    if telegram_ready and notification_ids:
        notifications_sent = await deliver_pending_notifications(
            engine=engine,
            settings=settings,
            notification_ids=notification_ids,
            user_id=user.id,
        )
    return WideSearchRefreshRead(
        profiles=int(result["profiles"]),
        queries=int(result["queries"]),
        signals_seen=int(result["signals_seen"]),
        signals_relevant=int(result["signals_relevant"]),
        jobs_new=int(result["jobs_new"]),
        jobs_updated=int(result["jobs_updated"]),
        jobs_existing=int(result["jobs_existing"]),
        matches_created=int(result["matches_created"]),
        notifications_queued=int(result["notifications_queued"]),
        notifications_sent=notifications_sent,
        telegram_ready=telegram_ready,
        targets_resolved=int(result["targets_resolved"]),
        probe_candidates_staged=int(result["probe_candidates_staged"]),
        provider_failed=int(result["provider_failed"]),
        provider_warnings=list(result.get("provider_warnings", [])),
    )


@router.get("/summary", response_model=DiscoverySummaryRead)
def summary(
    _: User = Depends(admin_user), session: Session = Depends(get_db)
) -> DiscoverySummaryRead:
    return DiscoverySummaryRead(**discovery_summary(session))
