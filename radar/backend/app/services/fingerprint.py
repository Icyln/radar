import hashlib
import uuid

from app.models.enums import ATSProvider


def build_job_fingerprint(
    *,
    provider: ATSProvider,
    company_id: uuid.UUID,
    external_job_id: str | None,
    title: str,
    location: str | None,
    apply_url: str,
) -> str:
    """Build stable source identity.

    Provider job IDs are preferred. When the public ATS feed does not expose one
    (notably Ashby's unauthenticated feed), the application URL is the most stable
    provider-controlled identity available. Title/location are intentionally not
    included in that fallback because legitimate edits must update the existing row
    rather than create a duplicate.
    """
    del title, location
    if external_job_id:
        identity = f"external:{external_job_id.strip()}"
    else:
        identity = f"url:{apply_url.strip()}"
    raw = f"{provider.value}|{company_id}|{identity}".encode()
    return hashlib.sha256(raw).hexdigest()
