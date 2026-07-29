"""MongoDB access and index management.

Indexes are created at startup rather than assumed. The 2022 server caught
``DuplicateKeyError`` to detect a taken email address, but never created the
unique index that would raise it -- so duplicate accounts were silently
possible and the error branch was dead code.

TTL indexes do the expiry work for challenges, refresh tokens and rate-limit
counters, so nothing needs a cleanup job and stale rows cannot accumulate.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import structlog
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo import ASCENDING, IndexModel
from pymongo.errors import PyMongoError

from .config import Settings
from .errors import ServiceUnavailableError

log = structlog.get_logger()

USERS = "users"
REFRESH_TOKENS = "refresh_tokens"
FACE_CHALLENGES = "face_challenges"
RATE_LIMITS = "rate_limits"


class Database:
    def __init__(self, settings: Settings) -> None:
        self._client: AsyncIOMotorClient[dict[str, Any]] = AsyncIOMotorClient(
            settings.mongo_uri,
            serverSelectionTimeoutMS=5_000,
            uuidRepresentation="standard",
        )
        self.db: AsyncIOMotorDatabase[dict[str, Any]] = self._client[settings.mongo_db]

    async def connect(self) -> None:
        try:
            await self._client.admin.command("ping")
        except PyMongoError as exc:
            raise ServiceUnavailableError("Database is unreachable.") from exc
        await self.ensure_indexes()
        log.info("database_connected")

    async def close(self) -> None:
        self._client.close()

    async def healthy(self) -> bool:
        try:
            await self._client.admin.command("ping")
        except PyMongoError:
            return False
        return True

    async def ensure_indexes(self) -> None:
        await self.db[USERS].create_indexes(
            [
                # Unique, and case-insensitive via a collation-free approach:
                # emails are normalised to lowercase before insert, so a plain
                # unique index is sufficient and avoids collation surprises.
                IndexModel([("email", ASCENDING)], unique=True, name="uniq_email"),
            ]
        )
        await self.db[REFRESH_TOKENS].create_indexes(
            [
                IndexModel(
                    [("token_hash", ASCENDING)], unique=True, name="uniq_token_hash"
                ),
                IndexModel([("user_id", ASCENDING)], name="by_user"),
                IndexModel([("family_id", ASCENDING)], name="by_family"),
                # Mongo removes expired rows on its own; no cleanup job needed.
                IndexModel(
                    [("expires_at", ASCENDING)], expireAfterSeconds=0, name="ttl_expiry"
                ),
            ]
        )
        await self.db[FACE_CHALLENGES].create_indexes(
            [
                IndexModel([("nonce", ASCENDING)], unique=True, name="uniq_nonce"),
                IndexModel(
                    [("expires_at", ASCENDING)], expireAfterSeconds=0, name="ttl_expiry"
                ),
            ]
        )
        await self.db[RATE_LIMITS].create_indexes(
            [
                IndexModel([("key", ASCENDING)], unique=True, name="uniq_key"),
                IndexModel(
                    [("expires_at", ASCENDING)], expireAfterSeconds=0, name="ttl_expiry"
                ),
            ]
        )
        log.info("indexes_ensured")


# --------------------------------------------------------------------------
# Rate limiting
# --------------------------------------------------------------------------
async def register_failure(
    db: AsyncIOMotorDatabase[dict[str, Any]], key: str, window_seconds: int
) -> int:
    """Record a failed attempt against ``key``, returning the running count.

    The window is fixed rather than sliding: the first failure sets the expiry
    and subsequent ones increment within it. Simple, and adequate for slowing
    an online guessing attack -- which is all a lockout can ever do.
    """
    now = datetime.now(UTC)
    result = await db[RATE_LIMITS].find_one_and_update(
        {"key": key},
        {
            "$inc": {"count": 1},
            "$setOnInsert": {"expires_at": now + timedelta(seconds=window_seconds)},
        },
        upsert=True,
        return_document=True,
    )
    return int(result.get("count", 1)) if result else 1


async def failure_count(db: AsyncIOMotorDatabase[dict[str, Any]], key: str) -> int:
    row = await db[RATE_LIMITS].find_one({"key": key})
    if not row:
        return 0
    expires_at = row.get("expires_at")
    # Mongo's TTL monitor only sweeps once a minute, so an expired row can
    # still be present. Treat it as gone rather than trusting the sweep.
    if isinstance(expires_at, datetime):
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)
        if expires_at <= datetime.now(UTC):
            return 0
    return int(row.get("count", 0))


async def clear_failures(db: AsyncIOMotorDatabase[dict[str, Any]], key: str) -> None:
    await db[RATE_LIMITS].delete_one({"key": key})
