import uuid
from types import SimpleNamespace

from app.services.locking import release_company_lock, try_company_lock


class _ScalarResult:
    def __init__(self, value: bool) -> None:
        self.value = value

    def scalar_one(self) -> bool:
        return self.value


class _FakePostgresConnection:
    def __init__(self, acquired: bool = True) -> None:
        self.dialect = SimpleNamespace(name="postgresql")
        self.acquired = acquired
        self.commits = 0
        self.statements: list[str] = []

    def execute(self, statement, params=None):
        self.statements.append(str(statement))
        if "pg_try_advisory_lock" in str(statement):
            return _ScalarResult(self.acquired)
        return _ScalarResult(True)

    def commit(self) -> None:
        self.commits += 1


def test_postgres_advisory_lock_closes_autobegun_transaction() -> None:
    connection = _FakePostgresConnection(acquired=True)
    assert try_company_lock(connection, uuid.uuid4()) is True
    assert connection.commits == 1


def test_postgres_advisory_unlock_closes_autobegun_transaction() -> None:
    connection = _FakePostgresConnection(acquired=True)
    release_company_lock(connection, uuid.uuid4())
    assert connection.commits == 1
