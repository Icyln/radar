import uuid

import httpx
import pytest

from app.collectors.ashby import AshbyCollector
from app.collectors.lever import LeverCollector
from app.core.http import RetryingHttpClient
from app.models.enums import ATSProvider, WorkMode
from app.schemas.company import CompanyTarget


def make_http(handler) -> tuple[RetryingHttpClient, httpx.AsyncClient]:
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return (
        RetryingHttpClient(
            connect_timeout=1,
            read_timeout=1,
            max_retries=0,
            user_agent="RadarTest",
            client=client,
        ),
        client,
    )


@pytest.mark.asyncio
async def test_lever_collector_normalizes_payload() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["mode"] == "json"
        return httpx.Response(
            200,
            json=[
                {
                    "id": "abc-123",
                    "text": "Backend Software Engineer",
                    "categories": {"location": "Singapore", "commitment": "Full-time"},
                    "descriptionPlain": "Build APIs",
                    "hostedUrl": "https://jobs.lever.co/example/abc-123",
                    "applyUrl": "https://jobs.lever.co/example/abc-123/apply",
                    "workplaceType": "hybrid",
                }
            ],
        )

    http, client = make_http(handler)
    collector = LeverCollector(http)
    target = CompanyTarget(
        id=uuid.uuid4(),
        name="Example",
        ats_provider=ATSProvider.LEVER,
        ats_identifier="example",
        career_url="https://jobs.lever.co/example",
    )
    jobs = await collector.fetch_jobs(target)
    await client.aclose()
    assert len(jobs) == 1
    assert jobs[0].external_job_id == "abc-123"
    assert jobs[0].work_mode is WorkMode.HYBRID
    assert jobs[0].location == "Singapore"
    assert jobs[0].employment_type == "Full-time"


@pytest.mark.asyncio
async def test_ashby_collector_normalizes_and_skips_unlisted() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["includeCompensation"] == "false"
        return httpx.Response(
            200,
            json={
                "apiVersion": "1",
                "jobs": [
                    {
                        "title": "Python Engineer",
                        "location": "Remote",
                        "isRemote": True,
                        "workplaceType": "Remote",
                        "descriptionPlain": "Build reliable systems",
                        "publishedAt": "2026-08-13T00:00:00+00:00",
                        "employmentType": "FullTime",
                        "jobUrl": "https://jobs.ashbyhq.com/example/one",
                        "applyUrl": "https://jobs.ashbyhq.com/example/one/application",
                        "isListed": True,
                    },
                    {
                        "title": "Unlisted",
                        "jobUrl": "https://jobs.ashbyhq.com/example/two",
                        "applyUrl": "https://jobs.ashbyhq.com/example/two/application",
                        "isListed": False,
                    },
                ],
            },
        )

    http, client = make_http(handler)
    collector = AshbyCollector(http)
    target = CompanyTarget(
        id=uuid.uuid4(),
        name="Example",
        ats_provider=ATSProvider.ASHBY,
        ats_identifier="example",
        career_url="https://jobs.ashbyhq.com/example",
    )
    jobs = await collector.fetch_jobs(target)
    await client.aclose()
    assert len(jobs) == 1
    assert jobs[0].external_job_id is None
    assert jobs[0].work_mode is WorkMode.REMOTE
    assert jobs[0].posted_at is not None
