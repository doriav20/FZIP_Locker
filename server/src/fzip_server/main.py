"""Application factory and lifespan wiring."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI

from .biometrics import FaceEngine
from .config import get_settings
from .db import Database
from .errors import install_exception_handlers
from .observability import configure_logging, install_request_logging
from .routers import auth, face, health
from .security import build_hasher

log = structlog.get_logger()

DESCRIPTION = """\
Authentication and face verification for FZIP Locker.

This API never receives your files or your archive password. Encryption happens
entirely on the client: archives are sealed with AES-256-GCM under a key
derived from your password via Argon2id, so the server has nothing to decrypt
even if it is fully compromised.
"""


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    configure_logging(settings.log_level, json_output=settings.is_production)

    database = Database(settings)
    await database.connect()

    app.state.settings = settings
    app.state.database = database
    app.state.hasher = build_hasher(settings)
    # Loading the ONNX models takes a second or two, so it happens once here
    # rather than per request.
    app.state.face_engine = FaceEngine(
        model_dir=settings.model_dir,
        match_threshold=settings.face_match_threshold,
    )
    log.info("startup_complete", env=settings.env)

    try:
        yield
    finally:
        await database.close()
        log.info("shutdown_complete")


def create_app() -> FastAPI:
    app = FastAPI(
        title="FZIP Locker API",
        version="2.0.0",
        description=DESCRIPTION,
        lifespan=lifespan,
        # No docs in production: the schema enumerates every endpoint and its
        # error slugs, which is reconnaissance an attacker would otherwise
        # have to do by hand.
        docs_url=None if get_settings().is_production else "/docs",
        redoc_url=None,
        openapi_url=None if get_settings().is_production else "/openapi.json",
    )

    install_request_logging(app)
    install_exception_handlers(app)

    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(face.router)
    return app


app = create_app()
