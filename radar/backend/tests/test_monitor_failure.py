from sqlalchemy import select
from sqlalchemy.orm import Session

from app.collectors.base import BaseCollector, CollectorError
from app.core.config import Settings
from app.models.crawler_log import CrawlerLog
from app.models.enums import ATSProvider, CrawlerStatus, JobStatus, WorkMode
from app.models.job import Job
from app.schemas.job import NormalizedJob
from app.services.job_processor import process_successful_snapshot
from app.services.monitor import MonitorService


class FailingCollector(BaseCollector):
    async def fetch_jobs(self, company):
        raise CollectorError("temporary source outage", category="temporary")


def failing_factory(provider, settings):
    return FailingCollector()


async def test_failed_collector_does_not_increment_missing_count(engine, company) -> None:
    with Session(engine) as session:
        db_company = session.get(type(company), company.id)
        process_successful_snapshot(
            session,
            company=db_company,
            jobs=[
                NormalizedJob(
                    company_id=company.id,
                    ats_provider=ATSProvider.GREENHOUSE,
                    external_job_id="1",
                    title="Backend Engineer",
                    location="Remote",
                    work_mode=WorkMode.REMOTE,
                    apply_url="https://example.com/1",
                    source_url="https://example.com/1",
                )
            ],
            missing_threshold=2,
        )
        session.commit()

    settings = Settings(database_url="sqlite://", telegram_bot_token=None)
    service = MonitorService(engine=engine, settings=settings, collector_factory=failing_factory)
    status = await service.run_company(company.id)
    assert status == "failed"

    with Session(engine) as session:
        job = session.scalar(select(Job))
        assert job.status is JobStatus.ACTIVE
        assert job.missing_count == 0
        log = session.scalar(select(CrawlerLog).order_by(CrawlerLog.started_at.desc()))
        assert log.status is CrawlerStatus.FAILED
        assert log.error_type == "temporary"
