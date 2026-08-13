import asyncio

from app.core.config import get_settings
from app.notifications.telegram import TelegramClient


async def async_main() -> None:
    settings = get_settings()
    if not settings.telegram_bot_token:
        raise SystemExit("TELEGRAM_BOT_TOKEN is not configured")
    webhook_url = f"{settings.backend_url.rstrip('/')}/api/v1/telegram/webhook"
    client = TelegramClient(
        bot_token=settings.telegram_bot_token,
        timeout_seconds=settings.telegram_request_timeout_seconds,
        max_attempts=settings.telegram_max_attempts,
    )
    try:
        await client.set_webhook(url=webhook_url, secret_token=settings.telegram_webhook_secret)
    finally:
        await client.close()
    print(f"Telegram webhook configured for {webhook_url}")


def main() -> None:
    asyncio.run(async_main())


if __name__ == "__main__":
    main()
