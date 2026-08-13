from typing import Any

from pydantic import BaseModel, ConfigDict, ValidationError

from app.collectors.base import BaseCollector, CollectorError
from app.core.http import HttpFetchError, RetryingHttpClient
from app.models.enums import ATSProvider, WorkMode
from app.schemas.company import CompanyTarget
from app.schemas.job import NormalizedJob
from app.services.text import html_to_text, normalize_space


class _GreenhouseLocation(BaseModel):
    model_config = ConfigDict(extra="ignore")
    name: str | None = None


class _GreenhouseJob(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: int | str
    title: str
    location: _GreenhouseLocation | None = None
    absolute_url: str
    content: str | None = None


class _GreenhouseResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    jobs: list[_GreenhouseJob]


class GreenhouseCollector(BaseCollector):
    BASE_URL = "https://boards-api.greenhouse.io/v1/boards"

    def __init__(self, http_client: RetryingHttpClient) -> None:
        self.http_client = http_client

    async def close(self) -> None:
        await self.http_client.close()

    async def fetch_jobs(self, company: CompanyTarget) -> list[NormalizedJob]:
        if company.ats_provider is not ATSProvider.GREENHOUSE:
            raise CollectorError("company is not configured for Greenhouse", category="configuration")

        url = f"{self.BASE_URL}/{company.ats_identifier}/jobs"
        try:
            payload: Any = await self.http_client.get_json(url, params={"content": "true"})
            response = _GreenhouseResponse.model_validate(payload)
        except HttpFetchError as exc:
            raise CollectorError(str(exc), category=exc.category) from exc
        except ValidationError as exc:
            raise CollectorError("Greenhouse response failed schema validation", category="parsing") from exc

        normalized: list[NormalizedJob] = []
        for item in response.jobs:
            location = normalize_space(item.location.name if item.location else None) or None
            work_mode = WorkMode.REMOTE if location and "remote" in location.casefold() else WorkMode.UNKNOWN
            normalized.append(
                NormalizedJob(
                    company_id=company.id,
                    ats_provider=ATSProvider.GREENHOUSE,
                    external_job_id=str(item.id),
                    title=normalize_space(item.title),
                    description=html_to_text(item.content),
                    location=location,
                    work_mode=work_mode,
                    employment_type=None,
                    apply_url=item.absolute_url,
                    source_url=item.absolute_url,
                    # Greenhouse's list endpoint exposes updated_at, not a reliable
                    # publication timestamp for every item. Do not invent posted_at.
                    posted_at=None,
                )
            )
        return normalized
