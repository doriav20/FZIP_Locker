"""Liveness and readiness probes for container healthchecks."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Response, status

from ..db import Database
from ..deps import get_database

router = APIRouter(tags=["health"])

Db = Annotated[Database, Depends(get_database)]


@router.get("/healthz")
async def healthz() -> dict[str, str]:
    """Liveness: the process is up and serving.

    Deliberately does not touch the database. A liveness probe that fails on a
    transient database blip would have the orchestrator restart a perfectly
    healthy process, which usually makes an outage worse.
    """
    return {"status": "ok"}


@router.get("/readyz")
async def readyz(response: Response, database: Db) -> dict[str, Any]:
    """Readiness: dependencies are reachable, so traffic can be routed here."""
    db_ok = await database.healthy()
    if not db_ok:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return {"status": "ok" if db_ok else "degraded", "database": db_ok}
