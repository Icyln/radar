import asyncio
from dataclasses import dataclass
from typing import Any

import httpx

from app.models.job import Job


@dataclass(slots=True)
class TelegramSendResult:
    message_id: str


class TelegramError(Exception):
    pass


def format_job_message(job: Job, company_name: str) -> str:
    posted = job.posted_at.isoformat() if job.posted_at else "Not provided by source"
    if job.source_kind == "WIDE_DISCOVERY":
        provider = (job.source_provider or job.discovery_signal_source or "Wide Search").replace("-", " ").title()
        headline = "🔎 NEW WIDE SEARCH MATCH"
        source = f"Wide discovery · {provider}"
    else:
        provider = job.ats_provider.value.title() if job.ats_provider is not None else "Direct ATS"
        headline = "🚨 NEW DIRECT ATS MATCH"
        source = f"Direct ATS · {provider}"
    return (
        f"{headline}\n\n"
        f"{job.title}\n"
        f"{company_name}\n\n"
        f"📍 {job.location or 'Location not provided'}\n"
        f"🏠 {job.work_mode.value.title()}\n"
        f"🕒 Posted: {posted}\n"
        f"📡 Detected: {job.first_seen_at.isoformat()}\n"
        f"🔗 Source: {source}\n\n"
        f"Apply:\n{job.apply_url}"
    )


class TelegramClient:
    def __init__(
        self,
        *,
        bot_token: str,
        timeout_seconds: float,
        max_attempts: int,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._token = bot_token
        self._max_attempts = max_attempts
        self._owns_client = client is None
        self._client = client or httpx.AsyncClient(timeout=timeout_seconds)

    async def close(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def _post(self, method: str, payload: dict[str, Any]) -> dict[str, Any]:
        # Never include this URL in errors/logs because it contains the bot token.
        url = f"https://api.telegram.org/bot{self._token}/{method}"
        for attempt in range(1, self._max_attempts + 1):
            try:
                response = await self._client.post(url, json=payload)
            except (httpx.TimeoutException, httpx.NetworkError) as exc:
                if attempt == self._max_attempts:
                    raise TelegramError("Telegram request failed after retries") from exc
            else:
                if response.status_code == 429 or response.status_code >= 500:
                    if attempt == self._max_attempts:
                        raise TelegramError(f"Telegram temporary HTTP failure: {response.status_code}")
                elif response.status_code >= 400:
                    raise TelegramError(f"Telegram rejected request with HTTP {response.status_code}")
                else:
                    try:
                        body = response.json()
                    except ValueError as exc:
                        raise TelegramError("Telegram returned malformed JSON") from exc
                    if not body.get("ok"):
                        raise TelegramError("Telegram API returned ok=false")
                    return body
            await asyncio.sleep(min(0.5 * (2 ** (attempt - 1)), 2.0))
        raise TelegramError("Telegram request failed")

    async def send_job(
        self,
        *,
        chat_id: str,
        job: Job,
        company_name: str,
        allow_actions: bool = True,
    ) -> TelegramSendResult:
        buttons: list[dict[str, str]] = [{"text": "Open Job", "url": job.apply_url}]
        if allow_actions:
            buttons.extend(
                [
                    {"text": "Save", "callback_data": f"save:{job.id}"},
                    {"text": "Ignore", "callback_data": f"ignore:{job.id}"},
                ]
            )
        body = await self._post(
            "sendMessage",
            {
                "chat_id": chat_id,
                "text": format_job_message(job, company_name),
                "disable_web_page_preview": False,
                "reply_markup": {"inline_keyboard": [buttons]},
            },
        )
        message_id = body.get("result", {}).get("message_id")
        if message_id is None:
            raise TelegramError("Telegram response did not contain a message id")
        return TelegramSendResult(message_id=str(message_id))

    async def send_text(self, *, chat_id: str, text: str) -> TelegramSendResult:
        body = await self._post("sendMessage", {"chat_id": chat_id, "text": text})
        message_id = body.get("result", {}).get("message_id")
        if message_id is None:
            raise TelegramError("Telegram response did not contain a message id")
        return TelegramSendResult(message_id=str(message_id))

    async def answer_callback_query(self, *, callback_query_id: str, text: str) -> None:
        await self._post(
            "answerCallbackQuery",
            {"callback_query_id": callback_query_id, "text": text, "show_alert": False},
        )

    async def set_webhook(self, *, url: str, secret_token: str | None = None) -> None:
        payload: dict[str, Any] = {"url": url, "allowed_updates": ["message", "callback_query"]}
        if secret_token:
            payload["secret_token"] = secret_token
        await self._post("setWebhook", payload)
