"""Face challenge and verification route tests.

The replay and liveness cases are the point of this file: the 2022 protocol
accepted a single pickled ndarray with no nonce, so one captured request
authenticated forever.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient

from fzip_server.db import FACE_CHALLENGES

from .conftest import (
    auth_header,
    frame,
    get_challenge,
    problem_slug,
    register_user,
    verification_files,
)


# --------------------------------------------------------------------------
# Challenge issuance
# --------------------------------------------------------------------------
async def test_challenge_requires_authentication(client: AsyncClient):
    response = await client.post("/api/v1/face/challenge")
    assert response.status_code == 401


async def test_challenge_returns_nonce_and_direction(client: AsyncClient, credentials):
    tokens = await register_user(client, credentials)
    challenge = await get_challenge(client, tokens)

    assert challenge["nonce"]
    assert challenge["direction"] in {"left", "right"}
    assert challenge["frames_required"] >= 2


async def test_each_challenge_is_unique(client: AsyncClient, credentials):
    tokens = await register_user(client, credentials)
    nonces = {(await get_challenge(client, tokens))["nonce"] for _ in range(5)}
    assert len(nonces) == 5


# --------------------------------------------------------------------------
# Verification
# --------------------------------------------------------------------------
async def test_verification_succeeds_with_a_live_turn(client: AsyncClient, credentials):
    tokens = await register_user(client, credentials)
    challenge = await get_challenge(client, tokens)

    response = await client.post(
        "/api/v1/face/verify",
        headers=auth_header(tokens),
        data={"nonce": challenge["nonce"]},
        files=verification_files(
            "alice", challenge["direction"], challenge["frames_required"]
        ),
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["face_token"]
    assert body["similarity"] >= 0.363


async def test_nonce_cannot_be_replayed(client: AsyncClient, credentials):
    """The single-use nonce is what makes a captured payload worthless."""
    tokens = await register_user(client, credentials)
    challenge = await get_challenge(client, tokens)
    payload = {
        "data": {"nonce": challenge["nonce"]},
        "files": verification_files(
            "alice", challenge["direction"], challenge["frames_required"]
        ),
    }

    first = await client.post(
        "/api/v1/face/verify", headers=auth_header(tokens), **payload
    )
    assert first.status_code == 200

    replay = await client.post(
        "/api/v1/face/verify", headers=auth_header(tokens), **payload
    )
    assert replay.status_code == 400
    assert problem_slug(replay) == "challenge-invalid"


async def test_unknown_nonce_is_rejected(client: AsyncClient, credentials):
    tokens = await register_user(client, credentials)
    response = await client.post(
        "/api/v1/face/verify",
        headers=auth_header(tokens),
        data={"nonce": "never-issued"},
        files=verification_files(),
    )
    assert response.status_code == 400
    assert problem_slug(response) == "challenge-invalid"


async def test_expired_challenge_is_rejected(
    client: AsyncClient, credentials, database
):
    tokens = await register_user(client, credentials)
    challenge = await get_challenge(client, tokens)

    await database.db[FACE_CHALLENGES].update_one(
        {"nonce": challenge["nonce"]},
        {"$set": {"expires_at": datetime.now(UTC) - timedelta(seconds=1)}},
    )

    response = await client.post(
        "/api/v1/face/verify",
        headers=auth_header(tokens),
        data={"nonce": challenge["nonce"]},
        files=verification_files("alice", challenge["direction"]),
    )
    assert response.status_code == 400


async def test_another_users_challenge_is_rejected(client: AsyncClient, credentials):
    """A nonce is bound to the account it was issued for."""
    alice = await register_user(client, credentials)
    bob = await register_user(
        client, {"email": "bob@example.com", "password": "another-long-password"}, "bob"
    )

    challenge = await get_challenge(client, alice)
    response = await client.post(
        "/api/v1/face/verify",
        headers=auth_header(bob),
        data={"nonce": challenge["nonce"]},
        files=verification_files("bob", challenge["direction"]),
    )
    assert response.status_code == 400
    assert problem_slug(response) == "challenge-invalid"


async def test_still_frames_fail_liveness(client: AsyncClient, credentials):
    """The exact 2022 attack: the same frame repeated must not authenticate."""
    tokens = await register_user(client, credentials)
    challenge = await get_challenge(client, tokens)

    response = await client.post(
        "/api/v1/face/verify",
        headers=auth_header(tokens),
        data={"nonce": challenge["nonce"]},
        files=[
            ("frames", (f"v{i}.jpg", frame("alice", 0.0), "image/jpeg"))
            for i in range(challenge["frames_required"])
        ],
    )
    assert response.status_code == 401
    assert problem_slug(response) == "liveness-failed"


async def test_turning_the_wrong_way_fails(client: AsyncClient, credentials):
    tokens = await register_user(client, credentials)
    challenge = await get_challenge(client, tokens)
    wrong = "right" if challenge["direction"] == "left" else "left"

    response = await client.post(
        "/api/v1/face/verify",
        headers=auth_header(tokens),
        data={"nonce": challenge["nonce"]},
        files=verification_files("alice", wrong, challenge["frames_required"]),
    )
    assert response.status_code == 401
    assert problem_slug(response) == "liveness-failed"


async def test_liveness_diagnostics_are_not_leaked(client: AsyncClient, credentials):
    """Telling the caller how far short they fell would help them tune an attack."""
    tokens = await register_user(client, credentials)
    challenge = await get_challenge(client, tokens)

    response = await client.post(
        "/api/v1/face/verify",
        headers=auth_header(tokens),
        data={"nonce": challenge["nonce"]},
        files=[
            ("frames", (f"v{i}.jpg", frame("alice", 0.0), "image/jpeg"))
            for i in range(challenge["frames_required"])
        ],
    )
    body = response.text.lower()
    for leaked in ("ratio", "baseline", "achieved", "0.18"):
        assert leaked not in body


async def test_wrong_face_is_rejected(client: AsyncClient, credentials):
    tokens = await register_user(client, credentials, identity="alice")
    challenge = await get_challenge(client, tokens)

    response = await client.post(
        "/api/v1/face/verify",
        headers=auth_header(tokens),
        data={"nonce": challenge["nonce"]},
        files=verification_files(
            "mallory", challenge["direction"], challenge["frames_required"]
        ),
    )
    assert response.status_code == 401
    assert problem_slug(response) == "face-mismatch"


async def test_too_few_frames_is_rejected(client: AsyncClient, credentials):
    tokens = await register_user(client, credentials)
    challenge = await get_challenge(client, tokens)

    response = await client.post(
        "/api/v1/face/verify",
        headers=auth_header(tokens),
        data={"nonce": challenge["nonce"]},
        files=[("frames", ("v0.jpg", frame("alice", 0.0), "image/jpeg"))],
    )
    assert response.status_code == 401
    assert problem_slug(response) == "liveness-failed"


async def test_too_many_frames_is_rejected(client: AsyncClient, credentials):
    """Bounded so a caller cannot make the server embed a thousand images."""
    tokens = await register_user(client, credentials)
    challenge = await get_challenge(client, tokens)

    response = await client.post(
        "/api/v1/face/verify",
        headers=auth_header(tokens),
        data={"nonce": challenge["nonce"]},
        files=[
            ("frames", (f"v{i}.jpg", frame("alice", 0.0), "image/jpeg"))
            for i in range(50)
        ],
    )
    assert response.status_code == 401


async def test_undetectable_frame_is_reported_clearly(client: AsyncClient, credentials):
    tokens = await register_user(client, credentials)
    challenge = await get_challenge(client, tokens)

    response = await client.post(
        "/api/v1/face/verify",
        headers=auth_header(tokens),
        data={"nonce": challenge["nonce"]},
        files=[
            ("frames", (f"v{i}.jpg", b"NOFACE", "image/jpeg"))
            for i in range(challenge["frames_required"])
        ],
    )
    assert response.status_code == 422
    assert problem_slug(response) == "no-face-detected"


async def test_repeated_failures_lock_face_verification(
    client: AsyncClient, credentials
):
    tokens = await register_user(client, credentials)

    statuses = []
    for _ in range(8):
        challenge = await get_challenge(client, tokens)
        response = await client.post(
            "/api/v1/face/verify",
            headers=auth_header(tokens),
            data={"nonce": challenge["nonce"]},
            files=verification_files(
                "mallory", challenge["direction"], challenge["frames_required"]
            ),
        )
        statuses.append(response.status_code)

    assert 429 in statuses, statuses


@pytest.mark.parametrize("path", ["/api/v1/face/challenge", "/api/v1/face/verify"])
async def test_face_endpoints_require_auth(client: AsyncClient, path):
    response = await client.post(path)
    assert response.status_code == 401
