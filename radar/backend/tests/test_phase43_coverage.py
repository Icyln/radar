import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.company import Company
from app.models.enums import (
    ATSProvider,
    JobStatus,
    MonitoringPriority,
    ProfileCoverageMode,
    WorkMode,
)
from app.models.job import Job
from app.models.job_match import JobMatch
from app.models.user import User
from app.models.user_company_watchlist import UserCompanyWatchlist
from app.services.monitor import MonitorService


def register(client, email: str) -> dict:
    response = client.post(
        "/api/v1/auth/register", json={"email": email, "password": "password123"}
    )
    assert response.status_code == 201, response.text
    return response.json()


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def add_job(session: Session, company: Company, *, suffix: str = "1", title: str = "Backend Engineer") -> Job:
    job = Job(
        company_id=company.id,
        ats_provider=company.ats_provider,
        external_job_id=f"job-{suffix}",
        title=title,
        description="Python APIs",
        location="Remote",
        work_mode=WorkMode.REMOTE,
        employment_type="FULL_TIME",
        apply_url=f"https://example.com/apply/{suffix}",
        source_url=f"https://example.com/jobs/{suffix}",
        status=JobStatus.ACTIVE,
        fingerprint=(suffix * 64)[:64],
    )
    session.add(job)
    session.flush()
    return job


def test_watchlist_profile_only_matches_watched_companies(client, engine, company) -> None:
    with Session(engine) as session:
        add_job(session, company)
        session.commit()

    user = register(client, "watchlist@example.com")
    headers = auth(user["access_token"])
    created = client.post(
        "/api/v1/job-profiles",
        headers=headers,
        json={
            "name": "Watched backend",
            "coverage_mode": "WATCHLIST",
            "job_titles": ["backend engineer"],
            "locations": [],
            "work_modes": [],
            "excluded_keywords": [],
        },
    )
    assert created.status_code == 201, created.text
    assert created.json()["coverage_mode"] == "WATCHLIST"
    assert client.get("/api/v1/jobs", headers=headers).json() == []

    added = client.put(f"/api/v1/companies/{company.id}/watchlist", headers=headers)
    assert added.status_code == 200, added.text
    assert added.json()["company_id"] == str(company.id)
    assert len(client.get("/api/v1/jobs", headers=headers).json()) == 1

    removed = client.delete(f"/api/v1/companies/{company.id}/watchlist", headers=headers)
    assert removed.status_code == 204
    assert client.get("/api/v1/jobs", headers=headers).json() == []


def test_wide_profile_is_default_and_detected_is_independent_of_matching(client, engine, company) -> None:
    with Session(engine) as session:
        add_job(session, company, suffix="2", title="Frontend Engineer")
        session.commit()

    user = register(client, "wide@example.com")
    headers = auth(user["access_token"])

    detected = client.get("/api/v1/jobs/detected?status=ACTIVE&limit=10", headers=headers)
    assert detected.status_code == 200, detected.text
    assert detected.json()["total"] == 1
    assert detected.json()["items"][0]["title"] == "Frontend Engineer"

    created = client.post(
        "/api/v1/job-profiles",
        headers=headers,
        json={
            "name": "Frontend",
            "job_titles": ["frontend engineer"],
            "locations": [],
            "work_modes": [],
            "excluded_keywords": [],
        },
    )
    assert created.status_code == 201, created.text
    assert created.json()["coverage_mode"] == "WIDE"
    assert len(client.get("/api/v1/jobs", headers=headers).json()) == 1


def test_detected_source_filters_and_pagination(client, engine, company) -> None:
    with Session(engine, expire_on_commit=False) as session:
        second = Company(
            name="Second Co",
            career_url="https://jobs.lever.co/second",
            ats_provider=ATSProvider.LEVER,
            ats_identifier="second",
            monitoring_priority=MonitoringPriority.NORMAL,
            active=True,
        )
        session.add(second)
        session.flush()
        add_job(session, company, suffix="3", title="Backend Engineer")
        add_job(session, second, suffix="4", title="Frontend Engineer")
        session.commit()

    user = register(client, "detected@example.com")
    headers = auth(user["access_token"])
    assert client.put(f"/api/v1/companies/{company.id}/watchlist", headers=headers).status_code == 200

    watched = client.get("/api/v1/jobs/detected?source=watchlist&limit=1", headers=headers).json()
    assert watched["total"] == 1
    assert watched["items"][0]["company_name"] == company.name
    assert watched["has_more"] is False

    other = client.get("/api/v1/jobs/detected?source=other&limit=1", headers=headers).json()
    assert other["total"] == 1
    assert other["items"][0]["company_name"] == "Second Co"

    all_jobs = client.get("/api/v1/jobs/detected?source=all&limit=1", headers=headers).json()
    assert all_jobs["total"] == 2
    assert all_jobs["has_more"] is True


def test_monitor_scope_selects_watchlist_and_registry_sources(engine, settings) -> None:
    with Session(engine, expire_on_commit=False) as session:
        watched_company = Company(
            name="Watched Co",
            career_url="https://boards.greenhouse.io/watched",
            ats_provider=ATSProvider.GREENHOUSE,
            ats_identifier="watched",
            monitoring_priority=MonitoringPriority.NORMAL,
            active=True,
        )
        registry_company = Company(
            name="Registry Co",
            career_url="https://boards.greenhouse.io/registry",
            ats_provider=ATSProvider.GREENHOUSE,
            ats_identifier="registry",
            monitoring_priority=MonitoringPriority.NORMAL,
            active=True,
        )
        user = User(email="scope@example.com", password_hash=hash_password("password123"))
        session.add_all([watched_company, registry_company, user])
        session.flush()
        session.add(UserCompanyWatchlist(user_id=user.id, company_id=watched_company.id))
        session.commit()

    service = MonitorService(engine=engine, settings=settings)
    assert service.eligible_company_ids(source_scope="watchlist") == [watched_company.id]
    assert service.eligible_company_ids(source_scope="registry") == [registry_company.id]
    assert set(service.eligible_company_ids(source_scope="all")) == {
        watched_company.id,
        registry_company.id,
    }


def test_switching_profile_to_watchlist_prunes_out_of_scope_matches(client, engine, company) -> None:
    with Session(engine) as session:
        add_job(session, company, suffix="5")
        session.commit()
    user = register(client, "switch@example.com")
    headers = auth(user["access_token"])
    created = client.post(
        "/api/v1/job-profiles",
        headers=headers,
        json={
            "name": "Backend",
            "coverage_mode": "WIDE",
            "job_titles": ["backend engineer"],
        },
    )
    assert len(client.get("/api/v1/jobs", headers=headers).json()) == 1
    profile_id = created.json()["id"]
    changed = client.patch(
        f"/api/v1/job-profiles/{profile_id}",
        headers=headers,
        json={"coverage_mode": "WATCHLIST"},
    )
    assert changed.status_code == 200, changed.text
    assert client.get("/api/v1/jobs", headers=headers).json() == []
    with Session(engine) as session:
        assert session.scalar(select(JobMatch.id).where(JobMatch.job_profile_id == uuid.UUID(profile_id))) is None
