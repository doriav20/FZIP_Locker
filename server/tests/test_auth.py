"""Auth route tests.

Several of these encode fixes for specific 2022 defects and are labelled as
such, so a future refactor that reintroduces the flaw fails loudly.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient

from fzip_server.db import REFRESH_TOKENS, USERS
from fzip_server.security import hash_refresh_token

from .conftest import (
    FakeFaceEngine,
    auth_header,
    enrolment_files,
    frame,
    problem_slug,
    register_user,
)


# --------------------------------------------------------------------------
# Registration
# --------------------------------------------------------------------------
async def test_register_returns_tokens(client: AsyncClient, credentials):
    body = await register_user(client, credentials)
    assert body["token_type"] == "Bearer"
    assert body["access_token"] and body["refresh_token"]
    assert body["user_id"]


async def test_register_stores_hash_not_password(
    client: AsyncClient, credentials, database
):
    """The 2022 server stored passwords reversibly. Nothing recoverable now."""
    await register_user(client, credentials)
    user = await database.db[USERS].find_one({"email": credentials["email"]})

    assert user["password_hash"].startswith("$argon2id$")
    assert credentials["password"] not in str(user)
    assert "password" not in user  # only password_hash


async def test_register_encrypts_embeddings(client: AsyncClient, credentials, database):
    await register_user(client, credentials)
    user = await database.db[USERS].find_one({"email": credentials["email"]})

    assert len(user["embeddings"]) == 3
    for record in user["embeddings"]:
        assert set(record) == {"ciphertext", "nonce", "key_version", "dim"}
        assert record["dim"] == 128


async def test_duplicate_email_is_rejected(client: AsyncClient, credentials):
    """The old code caught DuplicateKeyError for an index it never created."""
    await register_user(client, credentials)
    response = await client.post(
        "/api/v1/auth/register", data=credentials, files=enrolment_files()
    )
    assert response.status_code == 409
    assert problem_slug(response) == "email-already-registered"


async def test_email_case_is_normalised(client: AsyncClient, credentials):
    await register_user(client, credentials)
    shouting = dict(credentials, email=credentials["email"].upper())
    response = await client.post(
        "/api/v1/auth/register", data=shouting, files=enrolment_files()
    )
    assert response.status_code == 409


async def test_short_password_is_rejected(client: AsyncClient, credentials):
    response = await client.post(
        "/api/v1/auth/register",
        data=dict(credentials, password="short"),
        files=enrolment_files(),
    )
    assert response.status_code == 422


async def test_register_requires_exactly_three_frames(client: AsyncClient, credentials):
    response = await client.post(
        "/api/v1/auth/register",
        data=credentials,
        files=[("frames", ("a.jpg", frame(), "image/jpeg"))],
    )
    assert response.status_code == 401
    assert problem_slug(response) == "face-mismatch"


async def test_mismatched_enrolment_frames_are_rejected(
    client: AsyncClient, credentials
):
    """Three photos of three different people must not enrol as one account."""
    response = await client.post(
        "/api/v1/auth/register",
        data=credentials,
        files=[
            ("frames", ("a.jpg", frame("alice"), "image/jpeg")),
            ("frames", ("b.jpg", frame("bob"), "image/jpeg")),
            ("frames", ("c.jpg", frame("carol"), "image/jpeg")),
        ],
    )
    assert response.status_code == 401
    assert problem_slug(response) == "face-mismatch"


async def test_failed_enrolment_creates_no_account(
    client: AsyncClient, credentials, database
):
    """The old flow inserted the user first, stranding faceless accounts."""
    await client.post(
        "/api/v1/auth/register",
        data=credentials,
        files=[
            ("frames", (f"f{i}.jpg", frame("alice") + b";NOFACE", "image/jpeg"))
            for i in range(3)
        ],
    )
    assert await database.db[USERS].count_documents({"email": credentials["email"]}) == 0


# --------------------------------------------------------------------------
# Login
# --------------------------------------------------------------------------
async def test_login_succeeds(client: AsyncClient, credentials):
    await register_user(client, credentials)
    response = await client.post("/api/v1/auth/login", json=credentials)
    assert response.status_code == 200
    assert response.json()["access_token"]


async def test_wrong_password_is_rejected(client: AsyncClient, credentials):
    await register_user(client, credentials)
    response = await client.post(
        "/api/v1/auth/login", json=dict(credentials, password="wrong-but-long-enough")
    )
    assert response.status_code == 401
    assert problem_slug(response) == "invalid-credentials"


async def test_unknown_and_known_accounts_are_indistinguishable(
    client: AsyncClient, credentials
):
    """No account-existence oracle: identical status, slug and detail text."""
    await register_user(client, credentials)

    known = await client.post(
        "/api/v1/auth/login", json=dict(credentials, password="wrong-but-long-enough")
    )
    unknown = await client.post(
        "/api/v1/auth/login",
        json={"email": "nobody@example.com", "password": "wrong-but-long-enough"},
    )

    assert known.status_code == unknown.status_code == 401
    assert known.json()["type"] == unknown.json()["type"]
    assert known.json()["detail"] == unknown.json()["detail"]


async def test_lockout_after_repeated_failures(client: AsyncClient, credentials):
    await register_user(client, credentials)
    wrong = dict(credentials, password="wrong-but-long-enough")

    statuses = []
    for _ in range(8):
        response = await client.post("/api/v1/auth/login", json=wrong)
        statuses.append(response.status_code)

    assert 429 in statuses, statuses
    # Correct credentials are refused too while locked - otherwise the lockout
    # would only slow attackers who guess wrong forever.
    assert (await client.post("/api/v1/auth/login", json=credentials)).status_code == 429


async def test_successful_login_clears_the_failure_counter(
    client: AsyncClient, credentials
):
    await register_user(client, credentials)
    wrong = dict(credentials, password="wrong-but-long-enough")

    for _ in range(3):
        await client.post("/api/v1/auth/login", json=wrong)
    assert (await client.post("/api/v1/auth/login", json=credentials)).status_code == 200

    for _ in range(3):
        await client.post("/api/v1/auth/login", json=wrong)
    # Counter was reset, so three more failures must not trip the limit.
    assert (await client.post("/api/v1/auth/login", json=credentials)).status_code == 200


async def test_unknown_fields_are_rejected(client: AsyncClient, credentials):
    response = await client.post(
        "/api/v1/auth/login", json=dict(credentials, is_admin=True)
    )
    assert response.status_code == 422


# --------------------------------------------------------------------------
# Refresh rotation
# --------------------------------------------------------------------------
async def test_refresh_rotates_the_token(client: AsyncClient, credentials):
    tokens = await register_user(client, credentials)
    response = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )
    assert response.status_code == 200
    assert response.json()["refresh_token"] != tokens["refresh_token"]


async def test_refresh_token_reuse_revokes_the_family(
    client: AsyncClient, credentials, database
):
    """Presenting a spent token means it was captured: kill the whole chain."""
    tokens = await register_user(client, credentials)
    first = tokens["refresh_token"]

    rotated = (
        await client.post("/api/v1/auth/refresh", json={"refresh_token": first})
    ).json()

    replay = await client.post("/api/v1/auth/refresh", json={"refresh_token": first})
    assert replay.status_code == 401
    assert problem_slug(replay) == "token-reused"

    # The token issued from the compromised chain is dead too.
    followup = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": rotated["refresh_token"]}
    )
    assert followup.status_code == 401
    assert await database.db[REFRESH_TOKENS].count_documents({}) == 0


async def test_unknown_refresh_token_is_rejected(client: AsyncClient):
    response = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": "x" * 43}
    )
    assert response.status_code == 401


async def test_expired_refresh_token_is_rejected(
    client: AsyncClient, credentials, database
):
    tokens = await register_user(client, credentials)
    await database.db[REFRESH_TOKENS].update_one(
        {"token_hash": hash_refresh_token(tokens["refresh_token"])},
        {"$set": {"expires_at": datetime.now(UTC) - timedelta(seconds=1)}},
    )
    response = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )
    assert response.status_code == 401
    assert problem_slug(response) == "token-expired"


async def test_refresh_tokens_are_stored_hashed(
    client: AsyncClient, credentials, database
):
    tokens = await register_user(client, credentials)
    record = await database.db[REFRESH_TOKENS].find_one({})
    assert record["token_hash"] != tokens["refresh_token"]
    assert record["token_hash"] == hash_refresh_token(tokens["refresh_token"])


# --------------------------------------------------------------------------
# Logout
# --------------------------------------------------------------------------
async def test_logout_revokes_the_family(client: AsyncClient, credentials, database):
    tokens = await register_user(client, credentials)
    response = await client.post(
        "/api/v1/auth/logout", json={"refresh_token": tokens["refresh_token"]}
    )
    assert response.status_code == 204
    assert await database.db[REFRESH_TOKENS].count_documents({}) == 0


async def test_logout_with_unknown_token_is_a_noop(client: AsyncClient):
    response = await client.post(
        "/api/v1/auth/logout", json={"refresh_token": "y" * 43}
    )
    assert response.status_code == 204


# --------------------------------------------------------------------------
# /me
# --------------------------------------------------------------------------
async def test_me_returns_the_account(client: AsyncClient, credentials):
    tokens = await register_user(client, credentials)
    response = await client.get("/api/v1/auth/me", headers=auth_header(tokens))
    assert response.status_code == 200
    body = response.json()
    assert body["email"] == credentials["email"]
    assert body["has_enrolled_face"] is True


@pytest.mark.parametrize(
    "header",
    [
        pytest.param({}, id="missing"),
        pytest.param({"Authorization": "Bearer nonsense"}, id="garbage"),
        pytest.param({"Authorization": "Basic abc"}, id="wrong-scheme"),
        pytest.param({"Authorization": "Bearer"}, id="no-token"),
    ],
)
async def test_me_requires_a_valid_bearer_token(client: AsyncClient, header):
    response = await client.get("/api/v1/auth/me", headers=header)
    assert response.status_code == 401


async def test_face_token_cannot_be_used_as_an_access_token(
    client: AsyncClient, credentials, settings, face_engine: FakeFaceEngine
):
    """The `typ` claim keeps the two token kinds from being interchangeable."""
    from fzip_server.security import create_token

    tokens = await register_user(client, credentials)
    face_token = create_token(settings, tokens["user_id"], "face", 60)

    response = await client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {face_token}"}
    )
    assert response.status_code == 401


async def test_problem_responses_use_the_rfc_media_type(client: AsyncClient):
    response = await client.get("/api/v1/auth/me")
    assert response.headers["content-type"].startswith("application/problem+json")
    body = response.json()
    assert {"type", "title", "status", "detail"} <= set(body)
