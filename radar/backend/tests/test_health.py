import os

from fastapi.testclient import TestClient

os.environ["DATABASE_URL"] = "sqlite+pysqlite:///:memory:"

from app.core.config import get_settings  # noqa: E402

get_settings.cache_clear()

from app.main import app  # noqa: E402


def test_health_and_readiness() -> None:
    client = TestClient(app)
    assert client.get("/health").json() == {"status": "ok"}
    assert client.get("/ready").json() == {"status": "ready"}
