"""FastAPI dependencies.

Expensive objects (the Mongo client, the Argon2 hasher, the ONNX models) are
built once during startup and read from ``app.state``. Loading the face models
per request would add seconds of latency.
"""

from __future__ import annotations

from typing import Annotated, Any

from argon2 import PasswordHasher
from fastapi import Depends, Request
from motor.motor_asyncio import AsyncIOMotorDatabase

from .biometrics import FaceEngine
from .config import Settings, get_settings
from .db import USERS, Database
from .errors import AuthenticationRequiredError
from .security import decode_token


def get_app_settings() -> Settings:
    return get_settings()


def get_database(request: Request) -> Database:
    database: Database = request.app.state.database
    return database


def get_db(request: Request) -> AsyncIOMotorDatabase[dict[str, Any]]:
    database: Database = request.app.state.database
    return database.db


def get_hasher(request: Request) -> PasswordHasher:
    hasher: PasswordHasher = request.app.state.hasher
    return hasher


def get_face_engine(request: Request) -> FaceEngine:
    engine: FaceEngine = request.app.state.face_engine
    return engine


def client_ip(request: Request) -> str:
    """Best-effort client address for rate-limit keys.

    ``X-Forwarded-For`` is trusted here because the only ingress is the Caddy
    container on a private Compose network. Exposing this service directly to
    the internet without a proxy that overwrites the header would let a caller
    forge it and sidestep per-IP limits.
    """
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _bearer_token(request: Request) -> str:
    header = request.headers.get("authorization", "")
    scheme, _, token = header.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise AuthenticationRequiredError
    return token


async def current_user(
    request: Request,
    db: Annotated[AsyncIOMotorDatabase[dict[str, Any]], Depends(get_db)],
    settings: Annotated[Settings, Depends(get_app_settings)],
) -> dict[str, Any]:
    payload = decode_token(settings, _bearer_token(request), expected_type="access")
    user = await db[USERS].find_one({"_id": payload["sub"]})
    if user is None:
        # The token verified but the account is gone. Treat as unauthenticated
        # rather than 404: the caller should not learn that a valid-looking
        # token maps to a deleted account.
        raise AuthenticationRequiredError
    return user


CurrentUser = Annotated[dict[str, Any], Depends(current_user)]
Db = Annotated[AsyncIOMotorDatabase[dict[str, Any]], Depends(get_db)]
AppSettings = Annotated[Settings, Depends(get_app_settings)]
Hasher = Annotated[PasswordHasher, Depends(get_hasher)]
Faces = Annotated[FaceEngine, Depends(get_face_engine)]
ClientIp = Annotated[str, Depends(client_ip)]
