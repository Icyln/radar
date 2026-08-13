from urllib.parse import parse_qs, urlparse

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.main import app
from app.models.company import Company
from app.models.enums import ATSProvider, JobStatus, MonitoringPriority, WorkMode
from app.models.job import Job
from app.models.telegram_connection import TelegramConnection


def register(client, email="user@example.com", password="password123"):
    response = client.post("/api/v1/auth/register", json={"email": email, "password": password})
    assert response.status_code == 201, response.text
    return response.json()


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def seed_active_job(engine) -> None:
    with Session(engine) as session:
        company = Company(
            name="Seed Co",
            career_url="https://boards.greenhouse.io/seed",
            ats_provider=ATSProvider.GREENHOUSE,
            ats_identifier="seed",
            monitoring_priority=MonitoringPriority.NORMAL,
            active=True,
        )
        session.add(company)
        session.flush()
        session.add(
            Job(
                company_id=company.id,
                ats_provider=ATSProvider.GREENHOUSE,
                external_job_id="seed-job",
                title="Backend Software Engineer",
                description="Python backend APIs",
                location="Remote",
                work_mode=WorkMode.REMOTE,
                apply_url="https://example.com/apply",
                source_url="https://example.com/job",
                status=JobStatus.ACTIVE,
                fingerprint="b" * 64,
            )
        )
        session.commit()


def test_auth_profile_jobs_state_and_ownership(client, engine) -> None:
    seed_active_job(engine)
    first = register(client, "first@example.com")
    second = register(client, "second@example.com")
    first_headers = auth(first["access_token"])
    second_headers = auth(second["access_token"])

    created = client.post(
        "/api/v1/job-profiles",
        headers=first_headers,
        json={
            "name": "Remote Backend",
            "job_titles": ["backend engineer"],
            "locations": ["remote"],
            "work_modes": ["REMOTE"],
            "excluded_keywords": [],
        },
    )
    assert created.status_code == 201, created.text
    profile_id = created.json()["id"]
    assert client.get(f"/api/v1/job-profiles/{profile_id}", headers=second_headers).status_code == 404

    jobs = client.get("/api/v1/jobs", headers=first_headers)
    assert jobs.status_code == 200
    assert len(jobs.json()) == 1
    job_id = jobs.json()[0]["id"]

    saved = client.put(
        f"/api/v1/jobs/{job_id}/state", headers=first_headers, json={"state": "SAVED"}
    )
    assert saved.status_code == 200
    assert saved.json()["user_state"] == "SAVED"
    ignored = client.put(
        f"/api/v1/jobs/{job_id}/state", headers=first_headers, json={"state": "IGNORED"}
    )
    assert ignored.status_code == 200
    assert ignored.json()["user_state"] == "IGNORED"
    assert client.get("/api/v1/jobs?view=saved", headers=first_headers).json() == []
    assert len(client.get("/api/v1/jobs?view=ignored", headers=first_headers).json()) == 1
    assert client.put(
        f"/api/v1/jobs/{job_id}/state", headers=second_headers, json={"state": "SAVED"}
    ).status_code == 404


def test_admin_company_api(client) -> None:
    regular = register(client, "regular@example.com")
    admin = register(client, "admin@example.com")
    payload = {
        "name": "Lever Example",
        "career_url": "https://jobs.lever.co/example",
        "ats_provider": "LEVER",
        "ats_identifier": "example",
        "monitoring_priority": "HIGH",
        "active": True,
    }
    assert client.post(
        "/api/v1/companies", headers=auth(regular["access_token"]), json=payload
    ).status_code == 403
    response = client.post(
        "/api/v1/companies", headers=auth(admin["access_token"]), json=payload
    )
    assert response.status_code == 201, response.text
    assert response.json()["ats_provider"] == "LEVER"


def test_telegram_link_token_is_single_use(client, engine, settings) -> None:
    user = register(client, "telegram@example.com")
    headers = auth(user["access_token"])
    no_network_settings = Settings(
        database_url="sqlite+pysqlite:///:memory:",
        jwt_secret=settings.jwt_secret,
        telegram_bot_token=None,
        telegram_bot_username="radar_test_bot",
        telegram_webhook_secret="webhook-secret",
    )
    app.dependency_overrides[get_settings] = lambda: no_network_settings
    link = client.post("/api/v1/telegram/link-token", headers=headers)
    assert link.status_code == 200, link.text
    raw = parse_qs(urlparse(link.json()["deep_link"]).query)["start"][0]
    update = {
        "update_id": 1,
        "message": {
            "message_id": 1,
            "text": f"/start {raw}",
            "from": {"id": 123456, "username": "radar_user"},
            "chat": {"id": 123456, "type": "private"},
        },
    }
    webhook_headers = {"X-Telegram-Bot-Api-Secret-Token": "webhook-secret"}
    assert client.post("/api/v1/telegram/webhook", headers=webhook_headers, json=update).status_code == 200
    assert client.post("/api/v1/telegram/webhook", headers=webhook_headers, json=update).status_code == 200
    with Session(engine) as session:
        connections = list(session.scalars(select(TelegramConnection)))
        assert len(connections) == 1
        assert connections[0].telegram_user_id == 123456
