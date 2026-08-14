import hashlib
import uuid

from sqlalchemy import Connection, text


def _advisory_key(company_id: uuid.UUID) -> int:
    digest = hashlib.blake2b(company_id.bytes, digest_size=8).digest()
    unsigned = int.from_bytes(digest, "big", signed=False)
    return unsigned - 2**64 if unsigned >= 2**63 else unsigned


def try_company_lock(connection: Connection, company_id: uuid.UUID) -> bool:
    if connection.dialect.name != "postgresql":
        return True
    acquired = bool(
        connection.execute(
            text("SELECT pg_try_advisory_lock(:key)"), {"key": _advisory_key(company_id)}
        ).scalar_one()
    )
    # SQLAlchemy 2.x autobegins a transaction for execute().  The advisory
    # lock is session-level, so committing here closes that otherwise-idle
    # transaction without releasing the lock.
    connection.commit()
    return acquired


def release_company_lock(connection: Connection, company_id: uuid.UUID) -> None:
    if connection.dialect.name != "postgresql":
        return
    connection.execute(
        text("SELECT pg_advisory_unlock(:key)"), {"key": _advisory_key(company_id)}
    )
    connection.commit()
