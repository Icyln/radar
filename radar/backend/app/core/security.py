from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError

from app.core.config import Settings

_hasher = PasswordHasher()
_ALGORITHM = "HS256"


class TokenError(Exception):
    pass


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except (VerifyMismatchError, InvalidHashError):
        return False


def create_access_token(*, subject: str, settings: Settings, now: datetime | None = None) -> str:
    issued_at = now or datetime.now(timezone.utc)
    expires_at = issued_at + timedelta(minutes=settings.jwt_access_token_minutes)
    payload: dict[str, Any] = {
        "sub": subject,
        "iat": int(issued_at.timestamp()),
        "exp": int(expires_at.timestamp()),
        "type": "access",
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=_ALGORITHM)


def decode_access_token(token: str, settings: Settings) -> str:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[_ALGORITHM])
    except jwt.PyJWTError as exc:
        raise TokenError("invalid or expired access token") from exc
    if payload.get("type") != "access" or not payload.get("sub"):
        raise TokenError("invalid access token")
    return str(payload["sub"])
