from sqlalchemy import select
from sqlalchemy.orm import Session

from app.collectors.base import BaseCollector
from app.core.config import Settings
from app.models.crawler_log import CrawlerLog
from app.models.enums import ATSProvider, CrawlerStatus, JobStatus, WorkMode
from app.models.job import Job
from app.schemas.job import NormalizedJob
from app.services.monitor import MonitorService


class SuccessfulCollector(BaseCollector):
    async def fetch_jobs(self, company):
        return [
            NormalizedJob(
                company_id=company.id,
                ats_provider=ATSProvider.GREENHOUSE,
                external_job_id="persist-me",
                title="Frontend Engineer",
                location="Remote",
                work_mode=WorkMode.REMOTE,
                apply_url="https://example.com/apply",
                source_url="https://example.com/job",
            )
        ]


def successful_factory(provider, settings):
    return SuccessfulCollector()


async def test_successful_monitor_persists_job_and_crawler_log(engine, company) -> None:
    settings = Settings(database_url="sqlite://", telegram_bot_token=None)
    service = MonitorService(engine=engine, settings=settings, collector_factory=successful_factory)

    status = await service.run_company(company.id)
    assert status == "success"

    with Session(engine) as session:
        job = session.scalar(select(Job))
        assert job is not None
        assert job.external_job_id == "persist-me"
        assert job.status is JobStatus.ACTIVE

        log = session.scalar(select(CrawlerLog).order_by(CrawlerLog.started_at.desc()))
        assert log is not None
        assert log.status is CrawlerStatus.SUCCESS
        assert log.jobs_received == 1
        assert log.jobs_new == 1
