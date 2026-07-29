"""Biometric envelope encryption tests.

The cross-user case is the one that matters most: without binding each sealed
template to its owner, an attacker with write access to Mongo could copy one
user's encrypted embedding into another user's document and authenticate with
the wrong face -- never having broken the encryption at all.
"""

from __future__ import annotations

import base64
import secrets

import numpy as np
import pytest

from fzip_server.crypto import (
    CURRENT_KEY_VERSION,
    open_embedding,
    seal_embedding,
)


@pytest.fixture
def key() -> bytes:
    return secrets.token_bytes(32)


@pytest.fixture
def vector() -> np.ndarray:
    rng = np.random.default_rng(1234)
    raw = rng.standard_normal(128).astype(np.float32)
    return raw / np.linalg.norm(raw)


def test_round_trip(key, vector):
    sealed = seal_embedding(key, "user-1", vector)
    restored = open_embedding(key, "user-1", sealed)
    np.testing.assert_allclose(restored, vector, rtol=0, atol=0)


def test_sealed_record_has_the_expected_shape(key, vector):
    sealed = seal_embedding(key, "user-1", vector)
    assert set(sealed) == {"ciphertext", "nonce", "key_version", "dim"}
    assert sealed["dim"] == 128
    assert sealed["key_version"] == CURRENT_KEY_VERSION


def test_ciphertext_does_not_contain_the_plaintext(key, vector):
    sealed = seal_embedding(key, "user-1", vector)
    assert vector.tobytes() not in base64.b64decode(sealed["ciphertext"])


def test_nonce_is_fresh_each_time(key, vector):
    nonces = {seal_embedding(key, "user-1", vector)["nonce"] for _ in range(50)}
    assert len(nonces) == 50


def test_wrong_key_fails(key, vector):
    sealed = seal_embedding(key, "user-1", vector)
    with pytest.raises(ValueError, match="authentication"):
        open_embedding(secrets.token_bytes(32), "user-1", sealed)


def test_record_cannot_be_moved_between_users(key, vector):
    """Alice's sealed template must not open under Bob's identity."""
    sealed = seal_embedding(key, "alice", vector)
    with pytest.raises(ValueError, match="authentication"):
        open_embedding(key, "bob", sealed)


def test_tampered_ciphertext_fails(key, vector):
    sealed = seal_embedding(key, "user-1", vector)
    raw = bytearray(base64.b64decode(sealed["ciphertext"]))
    raw[0] ^= 0x01
    sealed["ciphertext"] = base64.b64encode(bytes(raw)).decode()

    with pytest.raises(ValueError, match="authentication"):
        open_embedding(key, "user-1", sealed)


def test_tampered_key_version_fails(key, vector):
    """key_version is inside the AAD, so it cannot be rewritten silently."""
    sealed = seal_embedding(key, "user-1", vector)
    sealed["key_version"] = CURRENT_KEY_VERSION + 1

    with pytest.raises(ValueError, match="authentication"):
        open_embedding(key, "user-1", sealed)


def test_declared_dimension_must_match(key, vector):
    sealed = seal_embedding(key, "user-1", vector)
    sealed["dim"] = 64
    with pytest.raises(ValueError, match="dimension mismatch"):
        open_embedding(key, "user-1", sealed)


@pytest.mark.parametrize(
    "record",
    [
        pytest.param({}, id="empty"),
        pytest.param({"ciphertext": "AAAA"}, id="missing-fields"),
        pytest.param(
            {"ciphertext": "!!not base64!!", "nonce": "AAAA", "key_version": 1, "dim": 1},
            id="bad-base64",
        ),
        pytest.param(None, id="none"),
    ],
)
def test_malformed_records_are_rejected(key, record):
    with pytest.raises(ValueError, match=r"malformed embedding record|authentication"):
        open_embedding(key, "user-1", record)


def test_two_dimensional_input_is_refused(key):
    with pytest.raises(ValueError, match="1-D"):
        seal_embedding(key, "user-1", np.zeros((4, 4), dtype=np.float32))
