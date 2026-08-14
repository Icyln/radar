import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.collectors.base import BaseCollector, CollectorError
from app.core.config import Settings
from app.models.company import Company
from app.models.crawler_log import CrawlerLog
from app.models.enums import ATSProvider, CrawlerStatus, MonitoringPriority, WorkMode
from app.models.monitor_run import MonitorRun
from app.schemas.job import NormalizedJob
from app.services.monitor import MonitorService


class MixedCollector(BaseCollector):
    async def fetch_jobs(self, company):
        if company.ats_identifier == "broken":
            raise CollectorError("temporary outage", category="temporary")
        return [
            NormalizedJob(
                company_id=company.id,
                ats_provider=company.ats_provider,
                external_job_id=f"job-{company.ats_identifier}",
                title="Backend Engineer",
                location="Remote",
                work_mode=WorkMode.REMOTE,
                apply_url=f"https://example.com/{company.ats_identifier}/apply",
                source_url=f"https://example.com/{company.ats_identifier}/job",
            )
        ]


def mixed_factory(provider, settings):
    return MixedCollector()


def add_company(
    session: Session,
    *,
    identifier: str,
    company_id: uuid.UUID | None = None,
    last_checked_at: datetime | None = None,
) -> Company:
    item = Company(
        id=company_id or uuid.uuid4(),
        name=identifier.title(),
        career_url=f"https://boards.greenhouse.io/{identifier}",
        ats_provider=ATSProvider.GREENHOUSE,
        ats_identifier=identifier,
        monitoring_priority=MonitoringPriority.NORMAL,
        active=True,
        last_checked_at=last_checked_at,
    )
    session.add(item)
    session.flush()
    return item


def test_due_selection_batching_and_stable_sharding(engine) -> None:
    now = datetime.now(timezone.utc)
    with Session(engine, expire_on_commit=False) as session:
        never = add_company(session, identifier="never", company_id=uuid.UUID(int=2))
        old = add_company(
            session,
            identifier="old",
            company_id=uuid.UUID(int=3),
            last_checked_at=now - timedelta(hours=2),
        )
        add_company(
            session,
            identifier="recent",
            company_id=uuid.UUID(int=4),
            last_checked_at=now - timedelta(minutes=5),
        )
        session.commit()

    settings = Settings(database_url="sqlite://", telegram_bot_token=None)
    service = MonitorService(engine=engine, settings=settings)
    due = service.eligible_company_ids(min_age_minutes=60, batch_size=2)
    assert due == [never.id, old.id]

    shard_zero = service.eligible_company_ids(shard_index=0, shard_count=2)
    shard_one = service.eligible_company_ids(shard_index=1, shard_count=2)
    assert set(shard_zero).isdisjoint(shard_one)
    assert set(shard_zero) | set(shard_one) == {
        uuid.UUID(int=2),
        uuid.UUID(int=3),
        uuid.UUID(int=4),
    }


async def test_monitor_run_groups_crawler_logs_and_records_partial_status(engine) -> None:
    with Session(engine, expire_on_commit=False) as session:
        healthy = add_company(session, identifier="healthy")
        broken = add_company(session, identifier="broken")
        session.commit()

    settings = Settings(database_url="sqlite://", telegram_bot_token=None)
    service = MonitorService(engine=engine, settings=settings, collector_factory=mixed_factory)
    summary = await service.run(max_concurrency=2)

    assert summary["companies"] == 2
    assert summary["success"] == 1
    assert summary["failed"] == 1
    run_id = uuid.UUID(str(summary["monitor_run_id"]))

    with Session(engine) as session:
        run = session.get(MonitorRun, run_id)
        assert run is not None
        assert run.status is CrawlerStatus.PARTIAL
        assert run.companies_selected == 2
        assert run.companies_succeeded == 1
        assert run.companies_failed == 1
        logs = list(session.scalars(select(CrawlerLog).where(CrawlerLog.monitor_run_id == run_id)))
        assert len(logs) == 2
        assert {item.company_id for item in logs} == {healthy.id, broken.id}


async def test_monitor_run_records_skipped_when_nothing_is_due(engine) -> None:
    with Session(engine) as session:
        add_company(
            session,
            identifier="recent",
            last_checked_at=datetime.now(timezone.utc),
        )
        session.commit()

    settings = Settings(database_url="sqlite://", telegram_bot_token=None)
    service = MonitorService(engine=engine, settings=settings, collector_factory=mixed_factory)
    summary = await service.run(min_age_minutes=60)
    run_id = uuid.UUID(str(summary["monitor_run_id"]))
    assert summary["companies"] == 0

    with Session(engine) as session:
        run = session.get(MonitorRun, run_id)
        assert run is not None
        assert run.status is CrawlerStatus.SKIPPED


def test_phase5_workflow_is_bounded_and_secret_driven() -> None:
    workflow = Path(__file__).parents[2] / ".github" / "workflows" / "scheduled_monitor.yml"
    text = workflow.read_text(encoding="utf-8")
    assert 'cron: "7,37 * * * *"' in text
    assert "secrets.DATABASE_URL" in text
    assert "secrets.TELEGRAM_BOT_TOKEN" in text
    assert "--scope watchlist" in text
    assert "--scope registry" in text
    assert "--batch-size" in text
    assert "--min-age-minutes" in text
    assert "cancel-in-progress: false" in text


def exploding_factory(provider, settings):
    raise RuntimeError("unexpected collector construction failure")


async def test_unexpected_company_failure_finishes_crawler_log(engine) -> None:
    with Session(engine, expire_on_commit=False) as session:
        company = add_company(session, identifier="explode")
        session.commit()

    settings = Settings(database_url="sqlite://", telegram_bot_token=None)
    service = MonitorService(engine=engine, settings=settings, collector_factory=exploding_factory)
    summary = await service.run()

    assert summary["failed"] == 1
    with Session(engine) as session:
        crawler_log = session.scalar(
            select(CrawlerLog).where(CrawlerLog.company_id == company.id)
        )
        assert crawler_log is not None
        assert crawler_log.status is CrawlerStatus.FAILED
        assert crawler_log.completed_at is not None
        assert crawler_log.error_type == "RuntimeError"
        assert "collector construction" in (crawler_log.error_message or "")
