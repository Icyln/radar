from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, ValidationError

from app.collectors.base import BaseCollector, CollectorError
from app.core.http import HttpFetchError, RetryingHttpClient
from app.models.enums import ATSProvider, WorkMode
from app.schemas.company import CompanyTarget
from app.schemas.job import NormalizedJob
from app.services.text import html_to_text, normalize_space


class _AshbyJob(BaseModel):
    model_config = ConfigDict(extra="ignore")
    title: str
    location: str | None = None
    isRemote: bool | None = None
    workplaceType: str | None = None
    descriptionHtml: str | None = None
    descriptionPlain: str | None = None
    publishedAt: datetime | None = None
    employmentType: str | None = None
    jobUrl: str
    applyUrl: str
    isListed: bool = True


class _AshbyResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    jobs: list[_AshbyJob]


def _work_mode(item: _AshbyJob) -> WorkMode:
    normalized = (item.workplaceType or "").strip().casefold()
    if normalized == "remote" or item.isRemote is True:
        return WorkMode.REMOTE
    if normalized == "hybrid":
        return WorkMode.HYBRID
    if normalized in {"onsite", "on-site", "on site"}:
        return WorkMode.ONSITE
    return WorkMode.UNKNOWN


class AshbyCollector(BaseCollector):
    BASE_URL = "https://api.ashbyhq.com/posting-api/job-board"

    def __init__(self, http_client: RetryingHttpClient) -> None:
        self.http_client = http_client

    async def close(self) -> None:
        await self.http_client.close()

    async def fetch_jobs(self, company: CompanyTarget) -> list[NormalizedJob]:
        if company.ats_provider is not ATSProvider.ASHBY:
            raise CollectorError("company is not configured for Ashby", category="configuration")

        url = f"{self.BASE_URL}/{company.ats_identifier}"
        try:
            payload: Any = await self.http_client.get_json(
                url, params={"includeCompensation": "false"}
            )
            response = _AshbyResponse.model_validate(payload)
        except HttpFetchError as exc:
            raise CollectorError(str(exc), category=exc.category) from exc
        except ValidationError as exc:
            raise CollectorError("Ashby response failed schema validation", category="parsing") from exc

        normalized: list[NormalizedJob] = []
        for item in response.jobs:
            # Respect Ashby's isListed flag: false means direct-link-only, not job-board discovery.
            if not item.isListed:
                continue
            description = normalize_space(item.descriptionPlain) or html_to_text(item.descriptionHtml)
            normalized.append(
                NormalizedJob(
                    company_id=company.id,
                    ats_provider=ATSProvider.ASHBY,
                    # Ashby's unauthenticated public feed does not expose a separate job ID;
                    # downstream fingerprinting uses the stable URLs as fallback identity.
                    external_job_id=None,
                    title=normalize_space(item.title),
                    description=description,
                    location=normalize_space(item.location) or None,
                    work_mode=_work_mode(item),
                    employment_type=normalize_space(item.employmentType) or None,
                    apply_url=item.applyUrl,
                    source_url=item.jobUrl,
                    posted_at=item.publishedAt,
                )
            )
        return normalized
