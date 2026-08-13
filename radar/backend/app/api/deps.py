import uuid

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.security import TokenError, decode_access_token
from app.db.session import get_db
from app.models.user import User

bearer = HTTPBearer(auto_error=False)


def current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    session: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> User:
    if credentials is None or credentials.scheme.casefold() != "bearer":
        raise HTTPException(status_code=401, detail="authentication required")
    try:
        user_id = uuid.UUID(decode_access_token(credentials.credentials, settings))
    except (TokenError, ValueError) as exc:
        raise HTTPException(status_code=401, detail="invalid or expired access token") from exc
    user = session.get(User, user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=401, detail="user is unavailable")
    return user


def admin_user(user: User = Depends(current_user)) -> User:
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="administrator access required")
    return user
