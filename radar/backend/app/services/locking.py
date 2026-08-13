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
    return bool(
        connection.execute(
            text("SELECT pg_try_advisory_lock(:key)"), {"key": _advisory_key(company_id)}
        ).scalar_one()
    )


def release_company_lock(connection: Connection, company_id: uuid.UUID) -> None:
    if connection.dialect.name != "postgresql":
        return
    connection.execute(
        text("SELECT pg_advisory_unlock(:key)"), {"key": _advisory_key(company_id)}
    )
