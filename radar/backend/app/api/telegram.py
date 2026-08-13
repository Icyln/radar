import logging
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import current_user
from app.core.config import Settings, get_settings
from app.db.session import get_db
from app.models.telegram_connection import TelegramConnection
from app.models.user import User
from app.models.enums import UserJobStateType
from app.notifications.telegram import TelegramClient, TelegramError
from app.schemas.telegram import TelegramConnectionRead, TelegramLinkResponse
from app.services.telegram_linking import TelegramLinkError, consume_link_token, create_link_token
from app.services.user_job_states import JobStateError, set_job_state

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/telegram", tags=["telegram"])


def _client(settings: Settings) -> TelegramClient:
    if not settings.telegram_bot_token:
        raise HTTPException(status_code=503, detail="Telegram bot is not configured")
    return TelegramClient(
        bot_token=settings.telegram_bot_token,
        timeout_seconds=settings.telegram_request_timeout_seconds,
        max_attempts=settings.telegram_max_attempts,
    )


@router.post("/link-token", response_model=TelegramLinkResponse)
def link_token(
    user: User = Depends(current_user),
    session: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> TelegramLinkResponse:
    try:
        raw, record = create_link_token(session, user_id=user.id, settings=settings)
        session.commit()
    except TelegramLinkError as exc:
        session.rollback()
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    assert settings.telegram_bot_username is not None
    return TelegramLinkResponse(
        deep_link=f"https://t.me/{settings.telegram_bot_username}?start={raw}",
        expires_at=record.expires_at,
    )


@router.get("/connection", response_model=TelegramConnectionRead | None)
def connection(
    user: User = Depends(current_user), session: Session = Depends(get_db)
) -> TelegramConnection | None:
    return session.scalar(
        select(TelegramConnection).where(TelegramConnection.user_id == user.id)
    )


@router.delete("/connection", status_code=status.HTTP_204_NO_CONTENT)
def disconnect(
    user: User = Depends(current_user), session: Session = Depends(get_db)
) -> None:
    item = session.scalar(
        select(TelegramConnection).where(TelegramConnection.user_id == user.id)
    )
    if item is not None:
        session.delete(item)
        session.commit()


@router.post("/webhook", include_in_schema=False)
async def webhook(
    request: Request,
    x_telegram_bot_api_secret_token: str | None = Header(default=None),
    session: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict[str, bool]:
    if settings.telegram_webhook_secret and (
        x_telegram_bot_api_secret_token != settings.telegram_webhook_secret
    ):
        raise HTTPException(status_code=403, detail="invalid Telegram webhook secret")
    payload: dict[str, Any] = await request.json()
    client: TelegramClient | None = None
    try:
        message = payload.get("message") or {}
        text = str(message.get("text") or "")
        if text.startswith("/start "):
            raw_token = text.split(maxsplit=1)[1].strip()
            sender = message.get("from") or {}
            chat = message.get("chat") or {}
            try:
                consume_link_token(
                    session,
                    raw_token=raw_token,
                    telegram_user_id=int(sender["id"]),
                    telegram_chat_id=int(chat["id"]),
                    username=sender.get("username"),
                )
                session.commit()
                reply = "✅ Telegram is now connected to Radar."
            except (TelegramLinkError, KeyError, TypeError, ValueError) as exc:
                session.rollback()
                reply = f"Radar could not connect this account: {exc}"
            if settings.telegram_bot_token and chat.get("id") is not None:
                client = _client(settings)
                try:
                    await client.send_text(chat_id=str(chat["id"]), text=reply)
                except TelegramError:
                    logger.warning("failed to send Telegram link confirmation", exc_info=True)
            return {"ok": True}

        callback = payload.get("callback_query") or {}
        data = str(callback.get("data") or "")
        if data.startswith("save:") or data.startswith("ignore:"):
            sender = callback.get("from") or {}
            connection = session.scalar(
                select(TelegramConnection).where(
                    TelegramConnection.telegram_user_id == int(sender.get("id", 0)),
                    TelegramConnection.verified.is_(True),
                )
            )
            answer = "Telegram is not linked to Radar."
            if connection is not None:
                import uuid

                try:
                    action, raw_job_id = data.split(":", 1)
                    state = (
                        UserJobStateType.SAVED
                        if action == "save"
                        else UserJobStateType.IGNORED
                    )
                    set_job_state(
                        session,
                        user_id=connection.user_id,
                        job_id=uuid.UUID(raw_job_id),
                        state=state,
                        require_match=True,
                    )
                    session.commit()
                    answer = "Saved in Radar." if action == "save" else "Ignored in Radar."
                except (ValueError, JobStateError):
                    session.rollback()
                    answer = "Radar could not update this job."
            callback_id = callback.get("id")
            if settings.telegram_bot_token and callback_id:
                client = _client(settings)
                try:
                    await client.answer_callback_query(
                        callback_query_id=str(callback_id), text=answer
                    )
                except TelegramError:
                    logger.warning("failed to answer Telegram callback", exc_info=True)
            return {"ok": True}
        return {"ok": True}
    finally:
        if client is not None:
            await client.close()
