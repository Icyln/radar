import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models.telegram_connection import TelegramConnection
from app.models.telegram_link_token import TelegramLinkToken


class TelegramLinkError(Exception):
    pass


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def create_link_token(
    session: Session, *, user_id: uuid.UUID, settings: Settings
) -> tuple[str, TelegramLinkToken]:
    if not settings.telegram_bot_username:
        raise TelegramLinkError("TELEGRAM_BOT_USERNAME is not configured")
    # Old unused tokens no longer need to remain valid once a new link flow starts.
    session.execute(
        delete(TelegramLinkToken).where(
            TelegramLinkToken.user_id == user_id,
            TelegramLinkToken.used_at.is_(None),
        )
    )
    raw = secrets.token_urlsafe(24)
    now = datetime.now(timezone.utc)
    record = TelegramLinkToken(
        user_id=user_id,
        token_hash=_hash_token(raw),
        expires_at=now + timedelta(minutes=settings.telegram_link_token_minutes),
    )
    session.add(record)
    session.flush()
    return raw, record


def consume_link_token(
    session: Session,
    *,
    raw_token: str,
    telegram_user_id: int,
    telegram_chat_id: int,
    username: str | None,
) -> TelegramConnection:
    now = datetime.now(timezone.utc)
    record = session.scalar(
        select(TelegramLinkToken).where(TelegramLinkToken.token_hash == _hash_token(raw_token))
    )
    if record is None or record.used_at is not None or _as_utc(record.expires_at) <= now:
        raise TelegramLinkError("link token is invalid, expired, or already used")

    claimed = session.scalar(
        select(TelegramConnection).where(
            (TelegramConnection.telegram_user_id == telegram_user_id)
            | (TelegramConnection.telegram_chat_id == telegram_chat_id)
        )
    )
    if claimed is not None and claimed.user_id != record.user_id:
        raise TelegramLinkError("this Telegram account is already linked to another Radar user")

    connection = session.scalar(
        select(TelegramConnection).where(TelegramConnection.user_id == record.user_id)
    )
    if connection is None:
        connection = TelegramConnection(
            user_id=record.user_id,
            telegram_user_id=telegram_user_id,
            telegram_chat_id=telegram_chat_id,
            username=username,
            verified=True,
            connected_at=now,
        )
        session.add(connection)
    else:
        connection.telegram_user_id = telegram_user_id
        connection.telegram_chat_id = telegram_chat_id
        connection.username = username
        connection.verified = True
        connection.connected_at = now
    record.used_at = now
    session.flush()
    return connection
