"""Send a harmless Telegram configuration test message.

Usage:
    python -m app.scripts.test_telegram
"""

from __future__ import annotations

import httpx

from app.core.config import get_settings


def main() -> None:
    settings = get_settings()
    token = settings.telegram_bot_token
    chat_id = settings.phase1_telegram_chat_id
    if not token:
        raise SystemExit("TELEGRAM_BOT_TOKEN is empty in .env.")
    if not chat_id:
        raise SystemExit("PHASE1_TELEGRAM_CHAT_ID is empty in .env.")

    # Never print/log this URL because it contains the bot token.
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        response = httpx.post(
            url,
            json={
                "chat_id": chat_id,
                "text": "✅ Radar Telegram configuration is working.",
            },
            timeout=settings.telegram_request_timeout_seconds,
        )
        response.raise_for_status()
        body = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise SystemExit(f"Telegram test request failed: {type(exc).__name__}") from exc

    if not body.get("ok"):
        description = body.get("description") or "Telegram returned ok=false"
        raise SystemExit(f"Telegram rejected the test message: {description}")

    result = body.get("result") or {}
    print(f"Telegram test message sent successfully. message_id={result.get('message_id', 'unknown')}")


if __name__ == "__main__":
    main()
