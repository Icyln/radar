from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import current_user
from app.core.config import Settings, get_settings
from app.core.rate_limit import enforce_rate_limit
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import AuthResponse, LoginRequest, RegisterRequest, UserRead
from app.services.auth import AuthServiceError, authenticate_user, issue_token, register_user

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def register(
    payload: RegisterRequest,
    request: Request,
    session: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> AuthResponse:
    enforce_rate_limit(
        request,
        bucket="auth-register",
        limit=settings.auth_register_rate_limit,
        window_seconds=settings.auth_register_rate_window_seconds,
    )
    try:
        user = register_user(session, email=payload.email, password=payload.password, settings=settings)
        token = issue_token(user, settings)
        session.commit()
    except (AuthServiceError, IntegrityError) as exc:
        session.rollback()
        raise HTTPException(status_code=409, detail="email is already registered") from exc
    return AuthResponse(access_token=token, user=UserRead.model_validate(user))


@router.post("/login", response_model=AuthResponse)
def login(
    payload: LoginRequest,
    request: Request,
    session: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> AuthResponse:
    enforce_rate_limit(
        request,
        bucket="auth-login",
        limit=settings.auth_login_rate_limit,
        window_seconds=settings.auth_login_rate_window_seconds,
    )
    try:
        user = authenticate_user(session, email=payload.email, password=payload.password)
    except AuthServiceError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    return AuthResponse(access_token=issue_token(user, settings), user=UserRead.model_validate(user))


@router.get("/me", response_model=UserRead)
def me(user: User = Depends(current_user)) -> UserRead:
    return UserRead.model_validate(user)
