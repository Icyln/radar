import httpx
import pytest

from app.collectors.base import CollectorError
from app.collectors.greenhouse import GreenhouseCollector
from app.core.http import RetryingHttpClient
from app.models.enums import WorkMode
from app.schemas.company import CompanyTarget


@pytest.mark.asyncio
async def test_greenhouse_collector_normalizes_payload(company) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["content"] == "true"
        return httpx.Response(
            200,
            json={
                "jobs": [
                    {
                        "id": 127817,
                        "title": " Backend Engineer ",
                        "updated_at": "2026-08-13T00:00:00Z",
                        "location": {"name": "Remote - APAC"},
                        "absolute_url": "https://boards.greenhouse.io/example/jobs/127817",
                        "content": "&lt;p&gt;Build &amp;amp; ship APIs&lt;/p&gt;",
                    }
                ]
            },
        )

    async_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    http = RetryingHttpClient(
        connect_timeout=1,
        read_timeout=1,
        max_retries=0,
        user_agent="RadarTest",
        client=async_client,
    )
    collector = GreenhouseCollector(http)
    jobs = await collector.fetch_jobs(CompanyTarget.model_validate(company))
    await async_client.aclose()

    assert len(jobs) == 1
    job = jobs[0]
    assert job.external_job_id == "127817"
    assert job.title == "Backend Engineer"
    assert job.location == "Remote - APAC"
    assert job.work_mode is WorkMode.REMOTE
    assert job.description == "Build & ship APIs"
    assert job.posted_at is None


@pytest.mark.asyncio
async def test_greenhouse_failure_is_not_an_empty_snapshot(company) -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, json={"error": "down"})

    async_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    http = RetryingHttpClient(
        connect_timeout=1,
        read_timeout=1,
        max_retries=0,
        user_agent="RadarTest",
        client=async_client,
    )
    collector = GreenhouseCollector(http)
    with pytest.raises(CollectorError) as exc_info:
        await collector.fetch_jobs(CompanyTarget.model_validate(company))
    await async_client.aclose()

    assert exc_info.value.category == "temporary"
