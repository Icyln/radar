import uuid

from app.models.enums import ATSProvider
from app.services.fingerprint import build_job_fingerprint


def test_same_source_job_has_same_fingerprint() -> None:
    company_id = uuid.uuid4()
    first = build_job_fingerprint(
        provider=ATSProvider.GREENHOUSE,
        company_id=company_id,
        external_job_id="123",
        title="Backend Engineer",
        location="Remote",
        apply_url="https://example.com/123",
    )
    second = build_job_fingerprint(
        provider=ATSProvider.GREENHOUSE,
        company_id=company_id,
        external_job_id="123",
        title="Backend Software Engineer",
        location="Singapore",
        apply_url="https://example.com/changed",
    )
    assert first == second


def test_different_source_jobs_have_different_fingerprints() -> None:
    company_id = uuid.uuid4()
    first = build_job_fingerprint(
        provider=ATSProvider.GREENHOUSE,
        company_id=company_id,
        external_job_id="123",
        title="Backend Engineer",
        location="Remote",
        apply_url="https://example.com/123",
    )
    second = build_job_fingerprint(
        provider=ATSProvider.GREENHOUSE,
        company_id=company_id,
        external_job_id="124",
        title="Backend Engineer",
        location="Remote",
        apply_url="https://example.com/124",
    )
    assert first != second
