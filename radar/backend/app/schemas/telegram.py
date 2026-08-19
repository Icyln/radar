import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class TelegramLinkResponse(BaseModel):
    deep_link: str
    expires_at: datetime


class TelegramConnectionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    telegram_user_id: int
    telegram_chat_id: int
    username: str | None
    verified: bool
    connected_at: datetime


class TelegramTestResponse(BaseModel):
    ok: bool
    message: str
    telegram_message_id: str


class TelegramDeliveryStatus(BaseModel):
    sent_today: int
    pending: int
    failed: int
