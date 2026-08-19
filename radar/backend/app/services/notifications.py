import logging
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import Select, and_, or_, select, update
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models.company import Company
from app.models.crawler_log import CrawlerLog
from app.models.enums import NotificationChannel, NotificationStatus, UserJobStateType
from app.models.job import Job
from app.models.job_match import JobMatch
from app.models.notification import Notification
from app.models.telegram_connection import TelegramConnection
from app.models.user_job_state import UserJobState
from app.notifications.telegram import TelegramClient, TelegramError
from app.services.text import normalize_for_match

logger = logging.getLogger(__name__)


def _eligible_title(job: Job, settings: Settings) -> bool:
    if settings.phase1_notify_all_new_jobs:
        return True
    keywords = settings.phase1_keywords
    if not keywords:
        return False
    normalized_title = normalize_for_match(job.title)
    return any(keyword in normalized_title for keyword in keywords)


def enqueue_phase1_notifications(
    session: Session,
    *,
    company: Company,
    new_job_ids: list[uuid.UUID],
    settings: Settings,
    initial_sync: bool,
    crawler_log_id: uuid.UUID | None = None,
) -> list[uuid.UUID]:
    del company  # retained in the signature for Phase-1 compatibility
    recipient = settings.phase1_telegram_chat_id
    if not recipient or not settings.telegram_bot_token:
        return []
    if initial_sync and not settings.phase1_notify_on_initial_sync:
        return []

    queued: list[uuid.UUID] = []
    jobs = list(session.scalars(select(Job).where(Job.id.in_(new_job_ids)))) if new_job_ids else []
    for job in jobs:
        if not _eligible_title(job, settings):
            continue
        notification = Notification(
            user_id=None,
            job_id=job.id,
            channel=NotificationChannel.TELEGRAM,
            recipient=recipient,
            crawler_log_id=crawler_log_id,
            status=NotificationStatus.PENDING,
        )
        try:
            with session.begin_nested():
                session.add(notification)
                session.flush()
            queued.append(notification.id)
        except IntegrityError:
            continue
    return queued


def enqueue_match_notifications(
    session: Session,
    *,
    match_ids: list[uuid.UUID],
    crawler_log_id: uuid.UUID | None = None,
) -> list[uuid.UUID]:
    if not match_ids:
        return []
    matches = list(session.scalars(select(JobMatch).where(JobMatch.id.in_(match_ids))))
    queued: list[uuid.UUID] = []
    seen: set[tuple[uuid.UUID, uuid.UUID]] = set()
    for match in matches:
        key = (match.user_id, match.job_id)
        if key in seen:
            continue
        seen.add(key)
        connection = session.scalar(
            select(TelegramConnection).where(
                TelegramConnection.user_id == match.user_id,
                TelegramConnection.verified.is_(True),
            )
        )
        if connection is None:
            continue
        ignored = session.scalar(
            select(UserJobState.id).where(
                UserJobState.user_id == match.user_id,
                UserJobState.job_id == match.job_id,
                UserJobState.state == UserJobStateType.IGNORED,
            )
        )
        if ignored is not None:
            continue
        notification = Notification(
            user_id=match.user_id,
            job_id=match.job_id,
            channel=NotificationChannel.TELEGRAM,
            recipient=str(connection.telegram_chat_id),
            crawler_log_id=crawler_log_id,
            status=NotificationStatus.PENDING,
        )
        try:
            with session.begin_nested():
                session.add(notification)
                session.flush()
            queued.append(notification.id)
        except IntegrityError:
            continue
    return queued


def _claimable_status(settings: Settings, *, now: datetime):
    stale_before = now - timedelta(minutes=settings.telegram_sending_stale_minutes)
    return or_(
        Notification.status.in_([NotificationStatus.PENDING, NotificationStatus.FAILED]),
        and_(
            Notification.status == NotificationStatus.SENDING,
            Notification.last_attempt_at.is_not(None),
            Notification.last_attempt_at < stale_before,
        ),
    )


def _claimable_query(
    settings: Settings,
    *,
    now: datetime,
    notification_ids: list[uuid.UUID] | None = None,
    user_id: uuid.UUID | None = None,
) -> Select[tuple[Notification]]:
    statement = select(Notification).where(
        Notification.channel == NotificationChannel.TELEGRAM,
        _claimable_status(settings, now=now),
        Notification.attempt_count < settings.telegram_max_attempts,
    )
    if notification_ids is not None:
        if not notification_ids:
            return statement.where(Notification.id.is_(None))
        statement = statement.where(Notification.id.in_(notification_ids))
    if user_id is not None:
        statement = statement.where(Notification.user_id == user_id)
    return (
        statement
        .order_by(Notification.created_at.asc())
        .limit(settings.phase1_max_notifications_per_run)
    )


async def deliver_pending_notifications(
    *,
    engine: Engine,
    settings: Settings,
    telegram_client: TelegramClient | None = None,
    notification_ids: list[uuid.UUID] | None = None,
    user_id: uuid.UUID | None = None,
) -> int:
    if not settings.telegram_bot_token:
        return 0

    owns_client = telegram_client is None
    client = telegram_client or TelegramClient(
        bot_token=settings.telegram_bot_token,
        timeout_seconds=settings.telegram_request_timeout_seconds,
        max_attempts=settings.telegram_max_attempts,
    )
    sent = 0
    try:
        with Session(engine, expire_on_commit=False) as session:
            claim_now = datetime.now(timezone.utc)
            candidate_ids = [
                item.id
                for item in session.scalars(
                    _claimable_query(
                        settings,
                        now=claim_now,
                        notification_ids=notification_ids,
                        user_id=user_id,
                    )
                )
            ]

        for notification_id in candidate_ids:
            now = datetime.now(timezone.utc)
            with Session(engine, expire_on_commit=False) as session:
                claimed = session.execute(
                    update(Notification)
                    .where(
                        Notification.id == notification_id,
                        _claimable_status(settings, now=now),
                        Notification.attempt_count < settings.telegram_max_attempts,
                    )
                    .values(
                        status=NotificationStatus.SENDING,
                        attempt_count=Notification.attempt_count + 1,
                        last_attempt_at=now,
                        error_message=None,
                    )
                )
                if claimed.rowcount != 1:
                    session.rollback()
                    continue
                session.commit()

                notification = session.get(Notification, notification_id)
                if notification is None:
                    continue
                job = session.get(Job, notification.job_id)
                if job is None:
                    notification.status = NotificationStatus.FAILED
                    notification.error_message = "job no longer exists"
                    session.commit()
                    continue
                company = session.get(Company, job.company_id) if job.company_id is not None else None
                company_name = (company.name if company is not None else job.source_company_name) or "Unknown company"
                recipient = notification.recipient
                allow_actions = notification.user_id is not None

            try:
                result = await client.send_job(
                    chat_id=recipient,
                    job=job,
                    company_name=company_name,
                    allow_actions=allow_actions,
                )
            except TelegramError as exc:
                with Session(engine) as session:
                    notification = session.get(Notification, notification_id)
                    if notification is not None:
                        notification.status = NotificationStatus.FAILED
                        notification.error_message = str(exc)[:1000]
                        session.commit()
                logger.warning(
                    "telegram notification failed", extra={"notification_id": str(notification_id)}
                )
                continue

            with Session(engine) as session:
                notification = session.get(Notification, notification_id)
                if notification is not None:
                    notification.status = NotificationStatus.SENT
                    notification.sent_at = datetime.now(timezone.utc)
                    notification.telegram_message_id = result.message_id
                    notification.error_message = None
                    if notification.crawler_log_id is not None:
                        crawler_log = session.get(CrawlerLog, notification.crawler_log_id)
                        if crawler_log is not None:
                            crawler_log.notifications_sent += 1
                    session.commit()
            sent += 1
    finally:
        if owns_client:
            await client.close()
    return sent
