"""Face verification: challenge issuance and verification.

The 2022 flow was a single request carrying a pickled numpy array. Capturing
one such request gave an attacker a payload that authenticated forever, and
unpickling it gave them code execution. Here verification is a two-step
challenge-response over multipart images:

1. ``POST /challenge`` returns a single-use nonce and a randomly chosen head
   movement, valid for 60 seconds.
2. ``POST /verify`` submits several frames plus that nonce. The nonce is spent
   atomically on first use, the frames must show the requested movement, and
   the best-matching frame must clear the similarity threshold.
"""

from __future__ import annotations

import secrets
from datetime import UTC, datetime, timedelta
from typing import Annotated

import structlog
from fastapi import APIRouter, File, Form, UploadFile

from ..biometrics import TurnDirection, check_head_turn
from ..crypto import open_embedding
from ..db import FACE_CHALLENGES, USERS, failure_count, register_failure
from ..deps import AppSettings, ClientIp, CurrentUser, Db, Faces
from ..errors import (
    AccountLockedError,
    ChallengeInvalidError,
    FaceMismatchError,
    LivenessFailedError,
    NoEnrolledFaceError,
)
from ..models import ChallengeResponse, FaceVerifyResponse
from ..security import create_token

log = structlog.get_logger()
router = APIRouter(prefix="/api/v1/face", tags=["face"])

#: Cap on frames accepted per verification. Without it, a caller could submit
#: thousands of images and have the server embed every one.
MAX_FRAMES = 12


@router.post("/challenge", response_model=ChallengeResponse)
async def create_challenge(user: CurrentUser, db: Db, settings: AppSettings) -> ChallengeResponse:
    if not user.get("embeddings"):
        raise NoEnrolledFaceError

    nonce = secrets.token_urlsafe(24)
    direction = secrets.choice(list(TurnDirection))
    now = datetime.now(UTC)

    await db[FACE_CHALLENGES].insert_one(
        {
            "nonce": nonce,
            "user_id": user["_id"],
            "direction": direction.value,
            "created_at": now,
            "expires_at": now + timedelta(seconds=settings.face_challenge_ttl_seconds),
            "consumed_at": None,
        }
    )

    return ChallengeResponse(
        nonce=nonce,
        direction=direction,
        frames_required=settings.face_liveness_frames,
        expires_in=settings.face_challenge_ttl_seconds,
    )


@router.post("/verify", response_model=FaceVerifyResponse)
async def verify(
    user: CurrentUser,
    db: Db,
    settings: AppSettings,
    engine: Faces,
    ip: ClientIp,
    nonce: Annotated[str, Form()],
    frames: Annotated[list[UploadFile], File()],
) -> FaceVerifyResponse:
    rate_key = f"face:{user['_id']}"
    if await failure_count(db, rate_key) >= settings.login_max_attempts:
        raise AccountLockedError

    if not settings.face_liveness_frames <= len(frames) <= MAX_FRAMES:
        raise LivenessFailedError(
            f"Send between {settings.face_liveness_frames} and {MAX_FRAMES} frames."
        )

    # Spend the nonce atomically. find_one_and_update means two concurrent
    # requests carrying the same nonce cannot both succeed - a plain
    # find-then-update would leave that race open.
    challenge = await db[FACE_CHALLENGES].find_one_and_update(
        {
            "nonce": nonce,
            "user_id": user["_id"],
            "consumed_at": None,
            "expires_at": {"$gt": datetime.now(UTC)},
        },
        {"$set": {"consumed_at": datetime.now(UTC)}},
    )
    if challenge is None:
        raise ChallengeInvalidError

    sealed = user.get("embeddings") or []
    if not sealed:
        raise NoEnrolledFaceError

    # Decode every frame first; detection failures are reported before any
    # matching happens.
    detections = []
    probes = []
    for upload in frames:
        vector, face = engine.embed_bytes(await upload.read())
        detections.append(face)
        probes.append(vector)

    direction = TurnDirection(challenge["direction"])
    passed, diagnostics = check_head_turn(detections, direction)
    if not passed:
        await register_failure(db, rate_key, settings.login_lockout_seconds)
        # Diagnostics are logged, never returned: telling the caller exactly
        # how far short they fell would make the check easier to game.
        log.info("liveness_failed", user_id=user["_id"], **diagnostics)
        raise LivenessFailedError

    enrolled = [
        open_embedding(settings.biometric_key_bytes, user["_id"], record) for record in sealed
    ]

    best_score = 0.0
    matched = False
    for probe in probes:
        ok, score = engine.best_match(probe, enrolled)
        best_score = max(best_score, score)
        matched = matched or ok

    if not matched:
        await register_failure(db, rate_key, settings.login_lockout_seconds)
        log.info("face_mismatch", user_id=user["_id"], best_score=round(best_score, 4))
        raise FaceMismatchError

    await db[USERS].update_one(
        {"_id": user["_id"]}, {"$set": {"last_face_verified_at": datetime.now(UTC)}}
    )
    log.info("face_verified", user_id=user["_id"], best_score=round(best_score, 4))

    return FaceVerifyResponse(
        face_token=create_token(settings, user["_id"], "face", settings.face_token_ttl_seconds),
        expires_in=settings.face_token_ttl_seconds,
        # Rounded to two places so repeated attempts cannot be used to
        # hill-climb toward the threshold.
        similarity=round(best_score, 2),
    )
