from __future__ import annotations

import csv
import io
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import httpx

from app.discovery.security import ensure_public_url


@dataclass(frozen=True, slots=True)
class DiscoveryFeedEntry:
    url: str
    company_name: str | None = None


def _clean_entry(url: object, company_name: object = None) -> DiscoveryFeedEntry | None:
    if not isinstance(url, str):
        return None
    clean_url = url.strip()
    if not clean_url:
        return None
    clean_name = company_name.strip() if isinstance(company_name, str) and company_name.strip() else None
    return DiscoveryFeedEntry(url=clean_url, company_name=clean_name)


def parse_feed_text(text: str, *, content_type: str = "") -> list[DiscoveryFeedEntry]:
    stripped = text.lstrip()
    entries: list[DiscoveryFeedEntry] = []
    if "json" in content_type.casefold() or stripped.startswith("[") or stripped.startswith("{"):
        payload: Any = json.loads(text)
        if isinstance(payload, dict):
            payload = payload.get("targets") or payload.get("companies") or payload.get("entries") or []
        if not isinstance(payload, list):
            raise ValueError("discovery JSON feed must contain a list")
        for item in payload:
            if isinstance(item, str):
                entry = _clean_entry(item)
            elif isinstance(item, dict):
                entry = _clean_entry(
                    item.get("url") or item.get("career_url") or item.get("careers_url"),
                    item.get("company_name") or item.get("name"),
                )
            else:
                entry = None
            if entry is not None:
                entries.append(entry)
        return entries

    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames and any(
        name in {field.strip().casefold() for field in reader.fieldnames if field}
        for name in {"url", "career_url", "careers_url"}
    ):
        for row in reader:
            normalized = {str(key).strip().casefold(): value for key, value in row.items() if key}
            entry = _clean_entry(
                normalized.get("url")
                or normalized.get("career_url")
                or normalized.get("careers_url"),
                normalized.get("company_name") or normalized.get("name"),
            )
            if entry is not None:
                entries.append(entry)
        return entries

    # Headerless fallback: URL[, company name]
    plain_reader = csv.reader(io.StringIO(text))
    for row in plain_reader:
        if not row:
            continue
        entry = _clean_entry(row[0], row[1] if len(row) > 1 else None)
        if entry is not None:
            entries.append(entry)
    return entries


def load_bundled_feed(path: Path | None = None) -> list[DiscoveryFeedEntry]:
    catalog = path or Path(__file__).with_name("catalogs") / "starter.csv"
    return parse_feed_text(catalog.read_text(encoding="utf-8"), content_type="text/csv")


class RemoteDiscoveryFeedFetcher:
    def __init__(
        self,
        *,
        connect_timeout: float,
        read_timeout: float,
        user_agent: str,
        max_bytes: int,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.max_bytes = max_bytes
        self._owns_client = client is None
        timeout = httpx.Timeout(read_timeout, connect=connect_timeout)
        self.client = client or httpx.AsyncClient(
            timeout=timeout,
            headers={"User-Agent": user_agent, "Accept": "text/csv,application/json,text/plain;q=0.8"},
            follow_redirects=False,
        )

    async def close(self) -> None:
        if self._owns_client:
            await self.client.aclose()

    async def fetch(self, url: str, *, max_redirects: int = 4) -> list[DiscoveryFeedEntry]:
        current = await ensure_public_url(url)
        for _ in range(max_redirects + 1):
            async with self.client.stream("GET", current) as response:
                if response.status_code in {301, 302, 303, 307, 308}:
                    location = response.headers.get("location")
                    if not location:
                        raise RuntimeError("discovery feed redirected without a Location header")
                    current = await ensure_public_url(urljoin(current, location))
                    continue
                if response.status_code >= 400:
                    raise RuntimeError(f"discovery feed returned HTTP {response.status_code}")
                chunks: list[bytes] = []
                size = 0
                async for chunk in response.aiter_bytes():
                    size += len(chunk)
                    if size > self.max_bytes:
                        raise RuntimeError("discovery feed exceeded configured size limit")
                    chunks.append(chunk)
                body = b"".join(chunks).decode(response.encoding or "utf-8", errors="replace")
                return parse_feed_text(body, content_type=response.headers.get("content-type", ""))
        raise RuntimeError("discovery feed redirected too many times")


__all__ = [
    "DiscoveryFeedEntry",
    "RemoteDiscoveryFeedFetcher",
    "load_bundled_feed",
    "parse_feed_text",
]
