from dataclasses import dataclass
from urllib.parse import parse_qs, unquote, urlparse

from app.models.enums import ATSProvider


@dataclass(frozen=True, slots=True)
class DetectedSource:
    provider: ATSProvider
    identifier: str
    career_url: str
    source_url: str


def _parsed(url: str):
    parsed = urlparse(url)
    parts = [unquote(part) for part in parsed.path.split("/") if part]
    return parsed, (parsed.hostname or "").casefold(), parts


def detect_ats_source(url: str) -> DetectedSource | None:
    parsed, host, parts = _parsed(url)

    if host in {"boards.greenhouse.io", "job-boards.greenhouse.io"}:
        query = parse_qs(parsed.query)
        embedded_identifier = (query.get("for") or [None])[0]
        identifier = embedded_identifier or (parts[0] if parts and parts[0] != "embed" else None)
        if identifier:
            identifier = unquote(identifier)
            return DetectedSource(
                ATSProvider.GREENHOUSE,
                identifier,
                f"https://boards.greenhouse.io/{identifier}",
                url,
            )
    if host == "boards-api.greenhouse.io" and len(parts) >= 4:
        if parts[0] == "v1" and parts[1] == "boards" and parts[3] == "jobs":
            identifier = parts[2]
            return DetectedSource(
                ATSProvider.GREENHOUSE,
                identifier,
                f"https://boards.greenhouse.io/{identifier}",
                url,
            )

    if host in {"jobs.lever.co", "jobs.eu.lever.co"} and parts:
        identifier = parts[0]
        return DetectedSource(
            ATSProvider.LEVER,
            identifier,
            f"https://{host}/{identifier}",
            url,
        )
    if host in {"api.lever.co", "api.eu.lever.co"} and len(parts) >= 3:
        if parts[0] == "v0" and parts[1] == "postings":
            identifier = parts[2]
            jobs_host = "jobs.eu.lever.co" if host == "api.eu.lever.co" else "jobs.lever.co"
            return DetectedSource(
                ATSProvider.LEVER,
                identifier,
                f"https://{jobs_host}/{identifier}",
                url,
            )

    if host == "jobs.ashbyhq.com" and parts:
        identifier = parts[0]
        return DetectedSource(
            ATSProvider.ASHBY,
            identifier,
            f"https://jobs.ashbyhq.com/{identifier}",
            url,
        )
    if host == "api.ashbyhq.com" and len(parts) >= 3:
        if parts[0] == "posting-api" and parts[1] == "job-board":
            identifier = parts[2]
            return DetectedSource(
                ATSProvider.ASHBY,
                identifier,
                f"https://jobs.ashbyhq.com/{identifier}",
                url,
            )

    return None
