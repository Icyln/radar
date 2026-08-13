from app.collectors.ashby import AshbyCollector
from app.collectors.base import BaseCollector, CollectorError
from app.collectors.greenhouse import GreenhouseCollector
from app.collectors.lever import LeverCollector
from app.core.config import Settings
from app.core.http import RetryingHttpClient
from app.models.enums import ATSProvider


def build_collector(provider: ATSProvider, settings: Settings) -> BaseCollector:
    http_client = RetryingHttpClient(
        connect_timeout=settings.monitor_http_connect_timeout_seconds,
        read_timeout=settings.monitor_http_read_timeout_seconds,
        max_retries=settings.monitor_http_max_retries,
        user_agent=settings.monitor_user_agent,
    )
    if provider is ATSProvider.GREENHOUSE:
        return GreenhouseCollector(http_client)
    if provider is ATSProvider.LEVER:
        return LeverCollector(http_client)
    if provider is ATSProvider.ASHBY:
        return AshbyCollector(http_client)
    raise CollectorError(f"unsupported ATS provider: {provider.value}", category="configuration")
