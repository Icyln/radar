from typing import Any

from pydantic import BaseModel, ConfigDict, ValidationError

from app.collectors.base import BaseCollector, CollectorError
from app.core.http import HttpFetchError, RetryingHttpClient
from app.models.enums import ATSProvider, WorkMode
from app.schemas.company import CompanyTarget
from app.schemas.job import NormalizedJob
from app.services.text import html_to_text, normalize_space


class _LeverCategories(BaseModel):
    model_config = ConfigDict(extra="ignore")
    location: str | None = None
    commitment: str | None = None


class _LeverJob(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    text: str
    categories: _LeverCategories | None = None
    description: str | None = None
    descriptionPlain: str | None = None
    hostedUrl: str
    applyUrl: str
    workplaceType: str | None = None


def _work_mode(value: str | None, location: str | None) -> WorkMode:
    normalized = (value or "").strip().casefold()
    if normalized == "remote":
        return WorkMode.REMOTE
    if normalized == "hybrid":
        return WorkMode.HYBRID
    if normalized in {"on-site", "onsite", "on site"}:
        return WorkMode.ONSITE
    if location and "remote" in location.casefold():
        return WorkMode.REMOTE
    return WorkMode.UNKNOWN


class LeverCollector(BaseCollector):
    BASE_URL = "https://api.lever.co/v0/postings"
    EU_BASE_URL = "https://api.eu.lever.co/v0/postings"

    def __init__(self, http_client: RetryingHttpClient) -> None:
        self.http_client = http_client

    async def close(self) -> None:
        await self.http_client.close()

    async def fetch_jobs(self, company: CompanyTarget) -> list[NormalizedJob]:
        if company.ats_provider is not ATSProvider.LEVER:
            raise CollectorError("company is not configured for Lever", category="configuration")

        base_url = (
            self.EU_BASE_URL
            if "jobs.eu.lever.co" in company.career_url.casefold()
            else self.BASE_URL
        )
        url = f"{base_url}/{company.ats_identifier}"
        try:
            payload: Any = await self.http_client.get_json(url, params={"mode": "json"})
            items = [_LeverJob.model_validate(item) for item in payload]
        except HttpFetchError as exc:
            raise CollectorError(str(exc), category=exc.category) from exc
        except (ValidationError, TypeError) as exc:
            raise CollectorError("Lever response failed schema validation", category="parsing") from exc

        normalized: list[NormalizedJob] = []
        for item in items:
            location = normalize_space(item.categories.location if item.categories else None) or None
            description = normalize_space(item.descriptionPlain) or html_to_text(item.description)
            normalized.append(
                NormalizedJob(
                    company_id=company.id,
                    ats_provider=ATSProvider.LEVER,
                    external_job_id=item.id,
                    title=normalize_space(item.text),
                    description=description,
                    location=location,
                    work_mode=_work_mode(item.workplaceType, location),
                    employment_type=normalize_space(
                        item.categories.commitment if item.categories else None
                    )
                    or None,
                    apply_url=item.applyUrl,
                    source_url=item.hostedUrl,
                    # The public Postings API does not document a publication timestamp.
                    posted_at=None,
                )
            )
        return normalized
