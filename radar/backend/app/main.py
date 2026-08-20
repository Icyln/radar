from contextlib import asynccontextmanager
import re
import uuid

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware

from app.api.auth import router as auth_router
from app.api.companies import router as companies_router
from app.api.dashboard import router as dashboard_router
from app.api.discovery import router as discovery_router
from app.api.health import router as health_router
from app.api.job_profiles import router as job_profiles_router
from app.api.jobs import router as jobs_router
from app.api.telegram import router as telegram_router
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.core.rate_limit import reset_rate_limits
from app.version import __version__

settings = get_settings()
configure_logging(settings.log_level)

_REQUEST_ID = re.compile(r"^[A-Za-z0-9._:-]{1,100}$")


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Initialize process-local application state for each API process."""
    reset_rate_limits()
    yield


async def request_safety_middleware(request: Request, call_next):
    content_length = request.headers.get("content-length")
    if content_length:
        try:
            too_large = int(content_length) > settings.api_max_request_bytes
        except ValueError:
            too_large = True
        if too_large:
            return JSONResponse(status_code=413, content={"detail": "request body is too large"})

    incoming_id = request.headers.get("x-request-id", "")
    request_id = incoming_id if _REQUEST_ID.fullmatch(incoming_id) else uuid.uuid4().hex
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Cache-Control"] = (
        "no-store"
        if request.url.path.startswith("/api/")
        else response.headers.get("Cache-Control", "")
    )
    return response


middleware = [
    Middleware(
        CORSMiddleware,
        allow_origins=[settings.frontend_url],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
        expose_headers=["X-Request-ID"],
    ),
    Middleware(BaseHTTPMiddleware, dispatch=request_safety_middleware),
]

app = FastAPI(
    title="Radar API",
    version=__version__,
    docs_url="/docs" if settings.environment != "production" else None,
    redoc_url=None if settings.environment == "production" else "/redoc",
    lifespan=lifespan,
    middleware=middleware,
)

app.include_router(health_router)
app.include_router(auth_router)
app.include_router(job_profiles_router)
app.include_router(jobs_router)
app.include_router(companies_router)
app.include_router(telegram_router)
app.include_router(dashboard_router)
app.include_router(discovery_router)
