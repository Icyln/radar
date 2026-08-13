"""Print Telegram chat IDs visible to the configured Phase-1 bot.

Usage:
    python -m app.scripts.telegram_chat_id

The bot token is read from TELEGRAM_BOT_TOKEN in Radar's .env file. The token is
never printed.
"""

from __future__ import annotations

from typing import Any

import httpx

from app.core.config import get_settings


def _chat_from_update(update: dict[str, Any]) -> dict[str, Any] | None:
    for key in (
        "message",
        "edited_message",
        "channel_post",
        "edited_channel_post",
        "my_chat_member",
        "chat_member",
        "chat_join_request",
    ):
        value = update.get(key)
        if isinstance(value, dict):
            chat = value.get("chat")
            if isinstance(chat, dict):
                return chat

    callback = update.get("callback_query")
    if isinstance(callback, dict):
        message = callback.get("message")
        if isinstance(message, dict):
            chat = message.get("chat")
            if isinstance(chat, dict):
                return chat
    return None


def _chat_label(chat: dict[str, Any]) -> str:
    display = (
        chat.get("title")
        or chat.get("username")
        or " ".join(part for part in (chat.get("first_name"), chat.get("last_name")) if part)
        or "(unnamed chat)"
    )
    return str(display)


def main() -> None:
    settings = get_settings()
    token = settings.telegram_bot_token
    if not token:
        raise SystemExit("TELEGRAM_BOT_TOKEN is empty. Add it to the project .env file first.")

    # Never print/log this URL because it contains the bot token.
    url = f"https://api.telegram.org/bot{token}/getUpdates"
    try:
        response = httpx.get(url, timeout=settings.telegram_request_timeout_seconds)
        response.raise_for_status()
        body = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise SystemExit(f"Could not read Telegram updates: {type(exc).__name__}") from exc

    if not body.get("ok"):
        description = body.get("description") or "Telegram returned ok=false"
        raise SystemExit(f"Telegram rejected getUpdates: {description}")

    unique: dict[str, dict[str, Any]] = {}
    for update in body.get("result", []):
        if not isinstance(update, dict):
            continue
        chat = _chat_from_update(update)
        if chat is None or "id" not in chat:
            continue
        unique[str(chat["id"])] = chat

    if not unique:
        print("No chats found.")
        print("1. Open your bot in Telegram.")
        print("2. Press Start or send /start (or any message).")
        print("3. Run this command again.")
        return

    print("Chats seen by this bot:")
    for chat_id, chat in unique.items():
        print(f"  chat_id={chat_id}  type={chat.get('type', 'unknown')}  name={_chat_label(chat)}")
    print("\nCopy the correct chat_id into PHASE1_TELEGRAM_CHAT_ID in .env.")


if __name__ == "__main__":
    main()
