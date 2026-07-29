"""Registration, login, refresh and logout."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Annotated, Any

import structlog
from fastapi import APIRouter, BackgroundTasks, File, Form, UploadFile, status
from pymongo.errors import DuplicateKeyError

from ..crypto import seal_embedding
from ..db import (
    REFRESH_TOKENS,
    USERS,
    clear_failures,
    failure_count,
    register_failure,
)
from ..deps import AppSettings, ClientIp, CurrentUser, Db, Faces, Hasher
from ..errors import (
    AccountLockedError,
    EmailAlreadyRegisteredError,
    FaceMismatchError,
    InvalidCredentialsError,
    TokenExpiredError,
    TokenReusedError,
)
from ..mailer import send_welcome_email
from ..models import (
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from ..security import (
    burn_password_time,
    create_token,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)

log = structlog.get_logger()
router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

#: Enrolment images must plausibly show the same person. Below this cosine
#: similarity the three captures are too dissimilar to be one face, which
#: catches both accidental bystanders and a deliberate attempt to enrol
#: several people against one account.
ENROLMENT_CONSISTENCY_THRESHOLD = 0.30


async def _issue_tokens(
    db: Any, settings: Any, user_id: str, family_id: str | None = None
) -> TokenResponse:
    access = create_token(settings, user_id, "access", settings.access_token_ttl_seconds)
    refresh = generate_refresh_token()
    now = datetime.now(UTC)

    await db[REFRESH_TOKENS].insert_one(
        {
            "token_hash": hash_refresh_token(refresh),
            "user_id": user_id,
            # A family groups every token descended from one login, so reuse
            # can revoke the whole chain rather than a single link.
            "family_id": family_id or str(uuid.uuid4()),
            "created_at": now,
            "expires_at": now + timedelta(seconds=settings.refresh_token_ttl_seconds),
            "used_at": None,
        }
    )
    return TokenResponse(
        access_token=access,
        refresh_token=refresh,
        expires_in=settings.access_token_ttl_seconds,
        user_id=user_id,
    )


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    db: Db,
    settings: AppSettings,
    hasher: Hasher,
    engine: Faces,
    background: BackgroundTasks,
    email: Annotated[str, Form()],
    password: Annotated[str, Form()],
    frames: Annotated[list[UploadFile], File()],
) -> TokenResponse:
    """Create an account and enrol three face templates in one step."""
    payload = RegisterRequest(email=email, password=password)

    if len(frames) != 3:
        raise FaceMismatchError("Exactly three enrolment images are required.")

    # Embed before writing anything, so a face failure does not leave a
    # half-created account behind. The 2022 flow inserted the user first and
    # returned an error afterwards, stranding accounts with no enrolled face.
    embeddings = []
    for upload in frames:
        vector, _ = engine.embed_bytes(await upload.read())
        embeddings.append(vector)

    for index in range(1, len(embeddings)):
        score = engine.similarity(embeddings[0], embeddings[index])
        if score < ENROLMENT_CONSISTENCY_THRESHOLD:
            raise FaceMismatchError("The enrolment images do not all show the same person.")

    user_id = str(uuid.uuid4())
    try:
        await db[USERS].insert_one(
            {
                "_id": user_id,
                "email": payload.email,
                "password_hash": hash_password(hasher, payload.password),
                "created_at": datetime.now(UTC),
                "embeddings": [
                    seal_embedding(settings.biometric_key_bytes, user_id, vector)
                    for vector in embeddings
                ],
            }
        )
    except DuplicateKeyError as exc:
        raise EmailAlreadyRegisteredError from exc

    background.add_task(send_welcome_email, settings, payload.email)
    log.info("user_registered", user_id=user_id)
    return await _issue_tokens(db, settings, user_id)


@router.post("/login", response_model=TokenResponse)
async def login(
    body: LoginRequest,
    db: Db,
    settings: AppSettings,
    hasher: Hasher,
    ip: ClientIp,
) -> TokenResponse:
    ip_key = f"login:ip:{ip}"
    account_key = f"login:email:{body.email}"

    # Limit by account and by source address. Account-only limiting lets one
    # attacker lock every user out; IP-only limiting is trivially bypassed
    # with a botnet. Neither alone is enough.
    for key in (ip_key, account_key):
        if await failure_count(db, key) >= settings.login_max_attempts:
            raise AccountLockedError

    user = await db[USERS].find_one({"email": body.email})
    if user is None:
        # Spend the same CPU time as a real verification, so response latency
        # does not reveal whether the account exists.
        burn_password_time(hasher)
        await register_failure(db, ip_key, settings.login_lockout_seconds)
        raise InvalidCredentialsError

    ok, upgraded = verify_password(hasher, user["password_hash"], body.password)
    if not ok:
        await register_failure(db, ip_key, settings.login_lockout_seconds)
        await register_failure(db, account_key, settings.login_lockout_seconds)
        raise InvalidCredentialsError

    if upgraded:
        # Argon2 parameters were raised since this password was last set.
        await db[USERS].update_one({"_id": user["_id"]}, {"$set": {"password_hash": upgraded}})
        log.info("password_hash_upgraded", user_id=user["_id"])

    await clear_failures(db, ip_key)
    await clear_failures(db, account_key)
    log.info("user_logged_in", user_id=user["_id"])
    return await _issue_tokens(db, settings, user["_id"])


@router.post("/refresh", response_model=TokenResponse)
async def refresh(body: RefreshRequest, db: Db, settings: AppSettings) -> TokenResponse:
    """Exchange a refresh token for a new pair, rotating it.

    Every refresh token is single-use. Presenting a spent one means it was
    captured, so the entire family is revoked -- logging out the real user too.
    That is the correct direction to fail: an inconvenient re-login beats an
    attacker holding a valid session.
    """
    token_hash = hash_refresh_token(body.refresh_token)
    record = await db[REFRESH_TOKENS].find_one({"token_hash": token_hash})

    if record is None:
        raise TokenExpiredError

    if record.get("used_at") is not None:
        await db[REFRESH_TOKENS].delete_many({"family_id": record["family_id"]})
        log.warning(
            "refresh_token_reuse_detected",
            user_id=record["user_id"],
            family_id=record["family_id"],
        )
        raise TokenReusedError

    expires_at = record["expires_at"]
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    if expires_at <= datetime.now(UTC):
        raise TokenExpiredError

    await db[REFRESH_TOKENS].update_one(
        {"_id": record["_id"]}, {"$set": {"used_at": datetime.now(UTC)}}
    )
    return await _issue_tokens(db, settings, record["user_id"], record["family_id"])


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(body: LogoutRequest, db: Db) -> None:
    """Revoke the presented token's whole family.

    Logging out should end the session everywhere it could be resumed, not
    just invalidate the one string the caller happened to send.
    """
    record = await db[REFRESH_TOKENS].find_one(
        {"token_hash": hash_refresh_token(body.refresh_token)}
    )
    if record is not None:
        await db[REFRESH_TOKENS].delete_many({"family_id": record["family_id"]})


@router.get("/me", response_model=UserResponse)
async def me(user: CurrentUser) -> UserResponse:
    return UserResponse(
        user_id=user["_id"],
        email=user["email"],
        created_at=user["created_at"],
        has_enrolled_face=bool(user.get("embeddings")),
    )
