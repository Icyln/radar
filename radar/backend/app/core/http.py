import asyncio
from dataclasses import dataclass
from typing import Any

import httpx


@dataclass(slots=True)
class HttpFetchError(Exception):
    message: str
    category: str
    status_code: int | None = None

    def __str__(self) -> str:
        return self.message


class RetryingHttpClient:
    def __init__(
        self,
        *,
        connect_timeout: float,
        read_timeout: float,
        max_retries: int,
        user_agent: str,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.max_retries = max_retries
        self._owns_client = client is None
        timeout = httpx.Timeout(read_timeout, connect=connect_timeout)
        self.client = client or httpx.AsyncClient(
            timeout=timeout,
            headers={"User-Agent": user_agent, "Accept": "application/json"},
            follow_redirects=True,
        )

    async def close(self) -> None:
        if self._owns_client:
            await self.client.aclose()

    async def get_json(self, url: str, *, params: dict[str, Any] | None = None) -> Any:
        attempts = self.max_retries + 1
        last_error: HttpFetchError | None = None
        for attempt in range(attempts):
            try:
                response = await self.client.get(url, params=params)
            except (httpx.TimeoutException, httpx.NetworkError) as exc:
                last_error = HttpFetchError(str(exc), "temporary")
            else:
                if response.status_code == 429 or response.status_code >= 500:
                    last_error = HttpFetchError(
                        f"upstream returned HTTP {response.status_code}",
                        "rate-limit" if response.status_code == 429 else "temporary",
                        response.status_code,
                    )
                elif 400 <= response.status_code < 500:
                    raise HttpFetchError(
                        f"upstream returned HTTP {response.status_code}",
                        "configuration" if response.status_code in {404, 410} else "permanent",
                        response.status_code,
                    )
                else:
                    try:
                        return response.json()
                    except ValueError as exc:
                        raise HttpFetchError("upstream returned malformed JSON", "parsing") from exc

            if attempt + 1 < attempts:
                await asyncio.sleep(min(0.5 * (2**attempt), 2.0))

        assert last_error is not None
        raise last_error
