from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import User


class AuthServiceError(Exception):
    pass


def register_user(session: Session, *, email: str, password: str, settings: Settings) -> User:
    normalized = email.strip().casefold()
    if session.scalar(select(User.id).where(User.email == normalized)) is not None:
        raise AuthServiceError("email is already registered")
    user = User(
        email=normalized,
        password_hash=hash_password(password),
        is_active=True,
        is_admin=normalized in settings.admin_email_set,
    )
    session.add(user)
    session.flush()
    return user


def authenticate_user(session: Session, *, email: str, password: str) -> User:
    normalized = email.strip().casefold()
    user = session.scalar(select(User).where(User.email == normalized))
    if user is None or not user.is_active or not verify_password(password, user.password_hash):
        raise AuthServiceError("invalid email or password")
    return user


def issue_token(user: User, settings: Settings) -> str:
    return create_access_token(subject=str(user.id), settings=settings)
