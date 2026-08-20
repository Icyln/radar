from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Protocol
from urllib.parse import urlparse

from app.core.config import Settings
from app.core.http import RetryingHttpClient
from app.discovery.detector import DetectedSource, detect_ats_source
from app.models.enums import ATSProvider

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class HiringSignal:
    """A fresh public indication that a company is hiring for a specific role."""

    source: str
    external_id: str
    url: str
    company_name: str | None
    title: str
    location: str | None
    posted_at: datetime | None
    remote: bool | None = None
    company_slug: str | None = None
    ats_sources: tuple[DetectedSource, ...] = ()
    provider_hints: tuple[ATSProvider, ...] = ()
    description: str | None = None
    employment_type: str | None = None


class HiringSignalProvider(Protocol):
    async def fetch(self, *, search_terms: list[str]) -> list[HiringSignal]: ...

    async def close(self) -> None: ...


def _timestamp(value: object) -> datetime | None:
    if isinstance(value, datetime):
        result = value
    elif isinstance(value, (int, float)):
        try:
            numeric = float(value)
            if abs(numeric) >= 100_000_000_000:
                numeric /= 1000.0
            result = datetime.fromtimestamp(numeric, tz=timezone.utc)
        except (OverflowError, OSError, ValueError):
            return None
    elif isinstance(value, str) and value.strip():
        clean = value.strip()
        if clean.isdigit():
            try:
                numeric = float(clean)
                if abs(numeric) >= 100_000_000_000:
                    numeric /= 1000.0
                result = datetime.fromtimestamp(numeric, tz=timezone.utc)
            except (OverflowError, OSError, ValueError):
                return None
        else:
            try:
                result = datetime.fromisoformat(clean.replace("Z", "+00:00"))
            except ValueError:
                return None
    else:
        return None

    if result.tzinfo is None:
        return result.replace(tzinfo=timezone.utc)
    return result.astimezone(timezone.utc)


def _text(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    clean = value.strip()
    return clean or None


_URL_RE = re.compile(r"https?://[^\s\"'<>]+", re.IGNORECASE)


def _direct_ats_sources(value: object) -> tuple[DetectedSource, ...]:
    if not isinstance(value, str) or not value:
        return ()
    sources: dict[tuple[ATSProvider, str], DetectedSource] = {}
    for raw in _URL_RE.findall(value.replace("&amp;", "&")):
        detected = detect_ats_source(raw.rstrip(".,);]"))
        if detected is not None:
            sources[(detected.provider, detected.identifier)] = detected
    return tuple(sources.values())


def _provider_hints(value: object) -> tuple[ATSProvider, ...]:
    if not isinstance(value, str) or not value:
        return ()
    lowered = value.casefold()
    hints: list[ATSProvider] = []
    if "greenhouse.io" in lowered:
        hints.append(ATSProvider.GREENHOUSE)
    if "lever.co" in lowered:
        hints.append(ATSProvider.LEVER)
    if "ashbyhq.com" in lowered:
        hints.append(ATSProvider.ASHBY)
    return tuple(hints)


def _company_slug_from_arbeitnow_url(url: str) -> str | None:
    parts = [part for part in urlparse(url).path.split("/") if part]
    try:
        index = parts.index("companies")
    except ValueError:
        return None
    if index + 1 >= len(parts):
        return None
    return _text(parts[index + 1])


class PublicHiringSignalProvider:
    """Bounded no-key discovery with per-source failure isolation and deeper pagination."""

    ARBEITNOW_DE = "https://www.arbeitnow.com/api/job-board-api"
    ARBEITNOW_UK = "https://www.arbeitnow.co.uk/api/job-board-api"
    HIMALAYAS_SEARCH = "https://himalayas.app/jobs/api/search"

    def __init__(
        self,
        *,
        settings: Settings,
        client: RetryingHttpClient | None = None,
    ) -> None:
        self.settings = settings
        self._owns_client = client is None
        self.failed_sources: list[str] = []
        self.failed_provider_names: set[str] = set()
        self.successful_sources: set[str] = set()
        self.source_counts: dict[str, int] = {}
        self.pages_fetched: dict[str, int] = {}
        self.client = client or RetryingHttpClient(
            connect_timeout=settings.monitor_http_connect_timeout_seconds,
            read_timeout=settings.monitor_http_read_timeout_seconds,
            max_retries=settings.monitor_http_max_retries,
            user_agent=settings.discovery_user_agent,
        )

    async def close(self) -> None:
        if self._owns_client:
            await self.client.close()

    def _record_failure(self, source: str, exc: Exception, *, context: str | None = None) -> None:
        self.failed_provider_names.add(source)
        detail = f"{exc.__class__.__name__}: {str(exc) or repr(exc)}"
        message = f"{source}{f' {context}' if context else ''}: {detail}"[:500]
        if message not in self.failed_sources and len(self.failed_sources) < 25:
            self.failed_sources.append(message)
        logger.warning("hiring signal source unavailable: %s", message)

    def _mark_success(self, source: str, *, count: int, pages: int) -> None:
        self.successful_sources.add(source)
        self.source_counts[source] = self.source_counts.get(source, 0) + count
        self.pages_fetched[source] = self.pages_fetched.get(source, 0) + pages

    async def _get_json_bounded(
        self, url: str, *, params: dict[str, Any] | None = None
    ) -> Any:
        return await asyncio.wait_for(
            self.client.get_json(url, params=params),
            timeout=self.settings.discovery_hiring_request_total_timeout_seconds,
        )

    @staticmethod
    def _arbeitnow_signal(item: object, *, source: str) -> HiringSignal | None:
        if not isinstance(item, dict):
            return None
        url = _text(item.get("url"))
        title = _text(item.get("title"))
        if not url or not title:
            return None
        slug = _text(item.get("slug")) or url
        description = item.get("description")
        return HiringSignal(
            source=source,
            external_id=slug[:500],
            url=url,
            company_name=_text(item.get("company_name")),
            title=title,
            location=_text(item.get("location")),
            posted_at=_timestamp(item.get("created_at")),
            remote=item.get("remote") if isinstance(item.get("remote"), bool) else None,
            company_slug=_company_slug_from_arbeitnow_url(url),
            ats_sources=_direct_ats_sources(description),
            provider_hints=_provider_hints(description),
            description=_text(description),
            employment_type=_text(item.get("job_types")) or _text(item.get("job_type")),
        )

    async def _fetch_arbeitnow_endpoint(
        self, *, endpoint: str, source: str
    ) -> list[HiringSignal]:
        results: list[HiringSignal] = []
        pages = 0
        for page in range(1, self.settings.discovery_hiring_arbeitnow_pages + 1):
            try:
                payload = await self._get_json_bounded(endpoint, params={"page": page})
            except Exception as exc:
                self._record_failure(source, exc, context=f"page {page}")
                break
            if not isinstance(payload, dict):
                break
            data = payload.get("data")
            if not isinstance(data, list):
                break
            pages += 1
            for item in data:
                signal = self._arbeitnow_signal(item, source=source)
                if signal is not None:
                    results.append(signal)
            links = payload.get("links")
            if not isinstance(links, dict) or not links.get("next"):
                break
        if pages:
            self._mark_success(source, count=len(results), pages=pages)
        return results

    @staticmethod
    def _himalayas_signal(item: object) -> HiringSignal | None:
        if not isinstance(item, dict):
            return None
        title = _text(item.get("title"))
        url = _text(item.get("applicationLink")) or _text(item.get("url"))
        if not title or not url:
            return None
        external_id = _text(item.get("guid")) or url
        locations = item.get("locationRestrictions")
        location: str | None = None
        if isinstance(locations, list):
            names: list[str] = []
            for value in locations:
                if isinstance(value, dict):
                    name = _text(value.get("name")) or _text(value.get("alpha2"))
                else:
                    name = _text(value)
                if name:
                    names.append(name)
            location = ", ".join(names) or None
        elif isinstance(locations, str):
            location = _text(locations)
        description = item.get("description")
        return HiringSignal(
            source="himalayas",
            external_id=external_id[:500],
            url=url,
            company_name=_text(item.get("companyName")),
            title=title,
            location=location,
            posted_at=_timestamp(item.get("pubDate")),
            remote=True,
            company_slug=_text(item.get("companySlug")),
            ats_sources=_direct_ats_sources(description),
            provider_hints=_provider_hints(description),
            description=_text(description),
            employment_type=_text(item.get("employmentType")) or _text(item.get("type")),
        )

    async def _fetch_himalayas(self, search_terms: list[str]) -> list[HiringSignal]:
        results: list[HiringSignal] = []
        pages = 0
        for term in search_terms[: self.settings.discovery_hiring_max_queries]:
            for page in range(1, self.settings.discovery_hiring_himalayas_pages + 1):
                try:
                    payload: Any = await self._get_json_bounded(
                        self.HIMALAYAS_SEARCH,
                        params={"q": term, "sort": "recent", "page": page},
                    )
                except Exception as exc:
                    self._record_failure("himalayas", exc, context=f"{term!r} page {page}")
                    break
                jobs: object
                if isinstance(payload, dict):
                    jobs = payload.get("jobs") or payload.get("data") or payload.get("results") or []
                else:
                    jobs = payload
                if not isinstance(jobs, list):
                    break
                pages += 1
                if not jobs:
                    break
                for item in jobs:
                    signal = self._himalayas_signal(item)
                    if signal is not None:
                        results.append(signal)
        if pages:
            self._mark_success("himalayas", count=len(results), pages=pages)
        return results

    async def fetch(self, *, search_terms: list[str]) -> list[HiringSignal]:
        if not search_terms:
            return []

        results: list[HiringSignal] = []
        if self.settings.discovery_hiring_arbeitnow_enabled:
            for endpoint, source in (
                (self.ARBEITNOW_DE, "arbeitnow-eu"),
                (self.ARBEITNOW_UK, "arbeitnow-uk"),
            ):
                results.extend(await self._fetch_arbeitnow_endpoint(endpoint=endpoint, source=source))

        if self.settings.discovery_hiring_himalayas_enabled:
            results.extend(await self._fetch_himalayas(search_terms))

        deduped: dict[tuple[str, str], HiringSignal] = {}
        for signal in results:
            deduped[(signal.source, signal.external_id)] = signal
        return list(deduped.values())


__all__ = ["HiringSignal", "HiringSignalProvider", "PublicHiringSignalProvider"]
