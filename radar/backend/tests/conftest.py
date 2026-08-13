import os
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")

from app import models as _models  # noqa: E402,F401
from app.core.config import Settings, get_settings  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.db.session import get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models.company import Company  # noqa: E402
from app.models.enums import ATSProvider, MonitoringPriority  # noqa: E402


@pytest.fixture
def engine() -> Generator[Engine, None, None]:
    db_engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(db_engine)
    try:
        yield db_engine
    finally:
        Base.metadata.drop_all(db_engine)
        db_engine.dispose()


@pytest.fixture
def settings() -> Settings:
    return Settings(
        database_url="sqlite+pysqlite:///:memory:",
        jwt_secret="test-secret-for-radar-tests-32-bytes-minimum",
        telegram_bot_token="test-token",
        telegram_bot_username="radar_test_bot",
        telegram_webhook_secret="webhook-secret",
        admin_emails="admin@example.com",
    )


@pytest.fixture
def client(engine: Engine, settings: Settings) -> Generator[TestClient, None, None]:
    def override_db() -> Generator[Session, None, None]:
        with Session(engine, expire_on_commit=False) as session:
            yield session

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_settings] = lambda: settings
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()


@pytest.fixture
def company(engine: Engine) -> Company:
    with Session(engine, expire_on_commit=False) as session:
        item = Company(
            name="Example Co",
            website="https://example.com",
            career_url="https://boards.greenhouse.io/example",
            ats_provider=ATSProvider.GREENHOUSE,
            ats_identifier="example",
            monitoring_priority=MonitoringPriority.NORMAL,
            active=True,
        )
        session.add(item)
        session.commit()
        return item
