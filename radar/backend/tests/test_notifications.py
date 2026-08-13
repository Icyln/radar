from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models.crawler_log import CrawlerLog
from app.models.enums import ATSProvider, CrawlerStatus, NotificationStatus, WorkMode
from app.models.job import Job
from app.models.notification import Notification
from app.notifications.telegram import TelegramSendResult
from app.schemas.job import NormalizedJob
from app.services.job_processor import process_successful_snapshot
from app.services.notifications import deliver_pending_notifications, enqueue_phase1_notifications


class FakeTelegramClient:
    def __init__(self) -> None:
        self.calls = 0

    async def send_job(self, *, chat_id, job, company_name, allow_actions=True):
        self.calls += 1
        return TelegramSendResult(message_id="99")


async def test_notification_enqueue_and_delivery_are_idempotent(engine, company) -> None:
    settings = Settings(
        database_url="sqlite://",
        telegram_bot_token="test-token",
        phase1_telegram_chat_id="12345",
        phase1_notify_all_new_jobs=True,
        phase1_notify_on_initial_sync=True,
    )

    with Session(engine, expire_on_commit=False) as session:
        db_company = session.get(type(company), company.id)
        log = CrawlerLog(
            company_id=company.id,
            ats_provider=ATSProvider.GREENHOUSE,
            started_at=db_company.created_at,
            status=CrawlerStatus.SUCCESS,
        )
        session.add(log)
        session.flush()
        result = process_successful_snapshot(
            session,
            company=db_company,
            jobs=[
                NormalizedJob(
                    company_id=company.id,
                    ats_provider=ATSProvider.GREENHOUSE,
                    external_job_id="new-1",
                    title="Backend Engineer",
                    location="Remote",
                    work_mode=WorkMode.REMOTE,
                    apply_url="https://example.com/new-1",
                    source_url="https://example.com/new-1",
                )
            ],
            missing_threshold=3,
        )
        first = enqueue_phase1_notifications(
            session,
            company=db_company,
            new_job_ids=result.new_job_ids,
            settings=settings,
            initial_sync=False,
            crawler_log_id=log.id,
        )
        session.commit()
        assert len(first) == 1

    with Session(engine, expire_on_commit=False) as session:
        db_company = session.get(type(company), company.id)
        job_id = session.scalar(select(Job.id))
        second = enqueue_phase1_notifications(
            session,
            company=db_company,
            new_job_ids=[job_id],
            settings=settings,
            initial_sync=False,
        )
        session.commit()
        assert second == []
        assert session.scalar(select(func.count(Notification.id))) == 1

    fake = FakeTelegramClient()
    sent = await deliver_pending_notifications(engine=engine, settings=settings, telegram_client=fake)
    sent_again = await deliver_pending_notifications(engine=engine, settings=settings, telegram_client=fake)
    assert sent == 1
    assert sent_again == 0
    assert fake.calls == 1

    with Session(engine) as session:
        notification = session.scalar(select(Notification))
        assert notification.status is NotificationStatus.SENT
        assert notification.telegram_message_id == "99"
        log = session.scalar(select(CrawlerLog))
        assert log.notifications_sent == 1
