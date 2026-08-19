from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api import telegram as telegram_api
from app.core.security import hash_password
from app.discovery.hiring import HiringSignal
from app.models.enums import NotificationStatus, ProfileCoverageMode
from app.models.job_profile import JobProfile
from app.models.notification import Notification
from app.models.telegram_connection import TelegramConnection
from app.models.user import User
from app.notifications.telegram import TelegramSendResult, format_job_message
from app.services.discovery import DiscoveryService
from app.services.notifications import deliver_pending_notifications


class FakeTelegramClient:
    def __init__(self) -> None:
        self.jobs: list[tuple[str, str, str]] = []
        self.texts: list[tuple[str, str]] = []
        self.closed = False

    async def send_job(self, *, chat_id, job, company_name, allow_actions=True):
        self.jobs.append((chat_id, company_name, format_job_message(job, company_name)))
        return TelegramSendResult(message_id=f"job-{len(self.jobs)}")

    async def send_text(self, *, chat_id, text):
        self.texts.append((chat_id, text))
        return TelegramSendResult(message_id="test-1")

    async def close(self):
        self.closed = True


def _signal() -> HiringSignal:
    return HiringSignal(
        source="himalayas",
        external_id="phase7d-wide-role",
        url="https://himalayas.app/companies/phase7d/jobs/frontend-engineer",
        company_name="Phase 7D Co",
        company_slug="phase7d",
        title="Frontend Engineer",
        location="Remote",
        posted_at=datetime.now(timezone.utc) - timedelta(hours=1),
        remote=True,
        description="Build a web app.",
        employment_type="Full time",
    )


async def test_wide_job_is_delivered_immediately_and_refresh_is_idempotent(engine, settings) -> None:
    with Session(engine, expire_on_commit=False) as session:
        user = User(email="phase7d@example.com", password_hash=hash_password("password123"))
        session.add(user)
        session.flush()
        profile = JobProfile(
            user_id=user.id,
            name="Web Development",
            enabled=True,
            coverage_mode=ProfileCoverageMode.WIDE,
            job_titles=["Frontend Engineer"],
            locations=[],
            work_modes=[],
            excluded_keywords=[],
            max_job_age_days=30,
            include_unknown_posted_at=False,
        )
        session.add(profile)
        session.add(
            TelegramConnection(
                user_id=user.id,
                telegram_user_id=7101,
                telegram_chat_id=7201,
                username="phase7d",
                verified=True,
                connected_at=datetime.now(timezone.utc),
            )
        )
        session.commit()
        profile_id = profile.id
        user_id = user.id

    service = DiscoveryService(engine=engine, settings=settings)
    with Session(engine) as session:
        profile = session.get(JobProfile, profile_id)
        first = service.ingest_hiring_signal_jobs([_signal()], profiles=[profile])
        second = service.ingest_hiring_signal_jobs([_signal()], profiles=[profile])

    notification_ids = list(first["_notification_ids"])
    assert first["jobs_new"] == 1
    assert first["matches_created"] == 1
    assert first["notifications_queued"] == 1
    assert second["jobs_new"] == 0
    assert second["notifications_queued"] == 0

    fake = FakeTelegramClient()
    sent = await deliver_pending_notifications(
        engine=engine,
        settings=settings,
        telegram_client=fake,
        notification_ids=notification_ids,
        user_id=user_id,
    )
    assert sent == 1
    assert len(fake.jobs) == 1
    _, company_name, message = fake.jobs[0]
    assert company_name == "Phase 7D Co"
    assert "NEW WIDE SEARCH MATCH" in message
    assert "Wide discovery · Himalayas" in message

    assert await deliver_pending_notifications(
        engine=engine,
        settings=settings,
        telegram_client=fake,
        notification_ids=notification_ids,
        user_id=user_id,
    ) == 0
    with Session(engine) as session:
        notification = session.scalar(select(Notification))
        assert notification is not None
        assert notification.status is NotificationStatus.SENT


def test_telegram_settings_expose_delivery_status_and_test_button(client, engine, monkeypatch) -> None:
    registered = client.post(
        "/api/v1/auth/register",
        json={"email": "telegram-ui@example.com", "password": "password123"},
    )
    assert registered.status_code == 201
    token = registered.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    with Session(engine) as session:
        user = session.scalar(select(User).where(User.email == "telegram-ui@example.com"))
        assert user is not None
        session.add(
            TelegramConnection(
                user_id=user.id,
                telegram_user_id=7301,
                telegram_chat_id=7401,
                username="telegram_ui",
                verified=True,
                connected_at=datetime.now(timezone.utc),
            )
        )
        session.commit()

    fake = FakeTelegramClient()
    monkeypatch.setattr(telegram_api, "_client", lambda settings: fake)
    response = client.post("/api/v1/telegram/test", headers=headers)
    assert response.status_code == 200
    assert response.json()["ok"] is True
    assert fake.texts == [
        (
            "7401",
            "✅ Radar Telegram test\n\nYour Telegram connection is working. New matching Direct ATS and Wide Search jobs can be delivered to this chat.",
        )
    ]
    assert fake.closed is True

    status = client.get("/api/v1/telegram/delivery-status", headers=headers)
    assert status.status_code == 200
    assert status.json() == {"sent_today": 0, "pending": 0, "failed": 0}


def test_wide_refresh_reports_immediate_telegram_delivery(client, engine, monkeypatch) -> None:
    from app.api import discovery as discovery_api

    registered = client.post(
        "/api/v1/auth/register",
        json={"email": "wide-delivery@example.com", "password": "password123"},
    )
    assert registered.status_code == 201
    token = registered.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    with Session(engine) as session:
        user = session.scalar(select(User).where(User.email == "wide-delivery@example.com"))
        assert user is not None
        session.add(
            TelegramConnection(
                user_id=user.id,
                telegram_user_id=7501,
                telegram_chat_id=7601,
                username="wide_delivery",
                verified=True,
                connected_at=datetime.now(timezone.utc),
            )
        )
        session.commit()
        user_id = user.id

    notification_id = __import__("uuid").uuid4()

    async def fake_ingest(self, *, user_id=None):
        assert user_id is not None
        return {
            "profiles": 1,
            "queries": 2,
            "signals_seen": 20,
            "signals_relevant": 4,
            "jobs_new": 3,
            "jobs_updated": 0,
            "jobs_existing": 1,
            "matches_created": 3,
            "notifications_queued": 1,
            "targets_queued": 0,
            "targets_existing": 4,
            "targets_resolved": 4,
            "probe_candidates_staged": 6,
            "probe_candidates_existing": 0,
            "provider_failed": 0,
            "provider_warnings": [],
            "_notification_ids": [notification_id],
        }

    calls = {}

    async def fake_deliver(*, engine, settings, notification_ids=None, user_id=None, **kwargs):
        calls["notification_ids"] = notification_ids
        calls["user_id"] = user_id
        return 1

    monkeypatch.setattr(DiscoveryService, "ingest_hiring_signals", fake_ingest)
    monkeypatch.setattr(discovery_api, "deliver_pending_notifications", fake_deliver)

    response = client.post("/api/v1/discovery/wide-search/refresh", headers=headers)
    assert response.status_code == 200
    payload = response.json()
    assert payload["jobs_new"] == 3
    assert payload["notifications_queued"] == 1
    assert payload["notifications_sent"] == 1
    assert payload["telegram_ready"] is True
    assert calls == {"notification_ids": [notification_id], "user_id": user_id}
