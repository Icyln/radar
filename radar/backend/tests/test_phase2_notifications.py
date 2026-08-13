from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.security import hash_password
from app.matching.service import create_matches_for_jobs
from app.models.enums import ATSProvider, NotificationStatus, WorkMode
from app.models.job import Job
from app.models.job_profile import JobProfile
from app.models.notification import Notification
from app.models.telegram_connection import TelegramConnection
from app.models.user import User
from app.notifications.telegram import TelegramSendResult
from app.schemas.job import NormalizedJob
from app.services.job_processor import process_successful_snapshot
from app.services.notifications import deliver_pending_notifications, enqueue_match_notifications


class FakeTelegramClient:
    def __init__(self) -> None:
        self.calls = 0
        self.action_flags: list[bool] = []

    async def send_job(self, *, chat_id, job, company_name, allow_actions=True):
        self.calls += 1
        self.action_flags.append(allow_actions)
        return TelegramSendResult(message_id="phase2-1")


async def test_per_user_match_notification_is_idempotent(engine, company) -> None:
    settings = Settings(database_url="sqlite://", telegram_bot_token="test-token")
    with Session(engine, expire_on_commit=False) as session:
        user = User(email="notify@example.com", password_hash=hash_password("password123"))
        session.add(user)
        session.flush()
        profile = JobProfile(
            user_id=user.id,
            name="Remote Backend",
            enabled=True,
            job_titles=["backend engineer"],
            locations=["remote"],
            work_modes=["REMOTE"],
            excluded_keywords=[],
        )
        session.add(profile)
        session.add(
            TelegramConnection(
                user_id=user.id,
                telegram_user_id=111,
                telegram_chat_id=222,
                username="notify",
                verified=True,
                connected_at=datetime.now(timezone.utc),
            )
        )
        db_company = session.get(type(company), company.id)
        result = process_successful_snapshot(
            session,
            company=db_company,
            jobs=[
                NormalizedJob(
                    company_id=company.id,
                    ats_provider=ATSProvider.GREENHOUSE,
                    external_job_id="phase2-new",
                    title="Backend Engineer",
                    location="Remote",
                    work_mode=WorkMode.REMOTE,
                    apply_url="https://example.com/phase2-new",
                    source_url="https://example.com/phase2-new",
                )
            ],
            missing_threshold=3,
        )
        match_result = create_matches_for_jobs(session, job_ids=result.new_job_ids)
        first = enqueue_match_notifications(session, match_ids=match_result.match_ids)
        second = enqueue_match_notifications(session, match_ids=match_result.match_ids)
        session.commit()
        assert len(first) == 1
        assert second == []
        assert session.scalar(select(func.count(Notification.id))) == 1

    fake = FakeTelegramClient()
    assert await deliver_pending_notifications(
        engine=engine, settings=settings, telegram_client=fake
    ) == 1
    assert await deliver_pending_notifications(
        engine=engine, settings=settings, telegram_client=fake
    ) == 0
    assert fake.calls == 1
    assert fake.action_flags == [True]
    with Session(engine) as session:
        notification = session.scalar(select(Notification))
        job = session.scalar(select(Job))
        assert notification.user_id is not None
        assert notification.status is NotificationStatus.SENT
        assert notification.job_id == job.id
