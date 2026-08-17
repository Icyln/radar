from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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

settings = get_settings()
configure_logging(settings.log_level)

app = FastAPI(
    title="Radar API",
    version="0.6.0",
    docs_url="/docs" if settings.environment != "production" else None,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)
app.include_router(health_router)
app.include_router(auth_router)
app.include_router(job_profiles_router)
app.include_router(jobs_router)
app.include_router(companies_router)
app.include_router(telegram_router)
app.include_router(dashboard_router)
app.include_router(discovery_router)
