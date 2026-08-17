import re
from collections import deque
from dataclasses import dataclass
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse

import httpx

from app.discovery.detector import DetectedSource, detect_ats_source
from app.discovery.security import UnsafeDiscoveryUrl, ensure_public_url

_ATS_URL_PATTERN = re.compile(
    r"https?://(?:boards\.greenhouse\.io|job-boards\.greenhouse\.io|boards-api\.greenhouse\.io|"
    r"jobs\.lever\.co|jobs\.eu\.lever\.co|api\.lever\.co|api\.eu\.lever\.co|"
    r"jobs\.ashbyhq\.com|api\.ashbyhq\.com)/[^\"'<>\\s]+",
    re.IGNORECASE,
)
_CAREER_HINTS = ("career", "jobs", "join", "vacan", "opening", "work-with", "work_with")


class _HtmlLinks(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.links: list[str] = []
        self._in_title = False
        self.title_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.casefold() == "title":
            self._in_title = True
        if tag.casefold() != "a":
            return
        for key, value in attrs:
            if key.casefold() == "href" and value:
                self.links.append(value)

    def handle_endtag(self, tag: str) -> None:
        if tag.casefold() == "title":
            self._in_title = False

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self.title_parts.append(data)

    @property
    def title(self) -> str | None:
        value = " ".join(part.strip() for part in self.title_parts if part.strip()).strip()
        return value or None


@dataclass(slots=True)
class FetchedPage:
    url: str
    text: str
    title: str | None
    links: list[str]


@dataclass(slots=True)
class DiscoveryScanResult:
    sources: list[DetectedSource]
    pages_scanned: int
    title_hint: str | None


class SafeHtmlFetcher:
    def __init__(
        self,
        *,
        connect_timeout: float,
        read_timeout: float,
        user_agent: str,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._owns_client = client is None
        timeout = httpx.Timeout(read_timeout, connect=connect_timeout)
        self.client = client or httpx.AsyncClient(
            timeout=timeout,
            headers={
                "User-Agent": user_agent,
                "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.1",
            },
            follow_redirects=False,
        )

    async def close(self) -> None:
        if self._owns_client:
            await self.client.aclose()

    async def fetch(self, url: str, *, max_redirects: int = 4) -> FetchedPage:
        current = await ensure_public_url(url)
        for _ in range(max_redirects + 1):
            response = await self.client.get(current)
            if response.status_code in {301, 302, 303, 307, 308}:
                location = response.headers.get("location")
                if not location:
                    raise RuntimeError("discovery page redirected without a Location header")
                current = await ensure_public_url(urljoin(current, location))
                continue
            if response.status_code >= 400:
                raise RuntimeError(f"discovery page returned HTTP {response.status_code}")
            content_type = response.headers.get("content-type", "").casefold()
            if "html" not in content_type and "text" not in content_type:
                raise RuntimeError("discovery target did not return HTML")
            text = response.text
            parser = _HtmlLinks()
            parser.feed(text)
            return FetchedPage(current, text, parser.title, parser.links)
        raise RuntimeError("discovery page redirected too many times")


class TargetCrawler:
    def __init__(self, fetcher: SafeHtmlFetcher) -> None:
        self.fetcher = fetcher

    async def scan(self, url: str, *, max_pages: int = 6) -> DiscoveryScanResult:
        direct = detect_ats_source(url)
        if direct is not None:
            return DiscoveryScanResult([direct], 0, None)

        start = await ensure_public_url(url)
        start_host = (urlparse(start).hostname or "").casefold()
        queue: deque[str] = deque([start])
        visited: set[str] = set()
        sources: dict[tuple[str, str], DetectedSource] = {}
        title_hint: str | None = None

        while queue and len(visited) < max_pages:
            current = queue.popleft()
            if current in visited:
                continue
            page = await self.fetcher.fetch(current)
            visited.add(current)
            if title_hint is None:
                title_hint = page.title

            final_direct = detect_ats_source(page.url)
            if final_direct is not None:
                sources[(final_direct.provider.value, final_direct.identifier)] = final_direct

            raw_urls = _ATS_URL_PATTERN.findall(page.text)
            for href in [*page.links, *raw_urls]:
                absolute = urljoin(page.url, href)
                detected = detect_ats_source(absolute)
                if detected is not None:
                    sources[(detected.provider.value, detected.identifier)] = detected
                    continue

                parsed = urlparse(absolute)
                host = (parsed.hostname or "").casefold()
                if host != start_host or parsed.scheme not in {"http", "https"}:
                    continue
                path = (parsed.path or "/").casefold()
                if any(hint in path for hint in _CAREER_HINTS):
                    clean = parsed._replace(fragment="").geturl()
                    if clean not in visited and clean not in queue:
                        queue.append(clean)

        return DiscoveryScanResult(list(sources.values()), len(visited), title_hint)


__all__ = [
    "DiscoveryScanResult",
    "SafeHtmlFetcher",
    "TargetCrawler",
    "UnsafeDiscoveryUrl",
]
