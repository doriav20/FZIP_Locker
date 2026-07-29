"""Envelope encryption for biometric templates at rest.

Face embeddings are the one piece of genuinely irrevocable data this service
holds: a user can change a leaked password, but not their face. So they are
never stored in the clear. The 2022 server wrote the trained LBPH model into
the user document as a blob that could be lifted straight out of a dump and
replayed.

The wrapping key lives in the environment (``FZIP_BIOMETRIC_KEY``), not in the
database, so a dump of Mongo alone yields nothing usable.
"""

from __future__ import annotations

import base64
import secrets
from typing import Any, TypedDict

import numpy as np
from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

NONCE_SIZE = 12
EMBEDDING_DTYPE = np.float32

#: Bumped when the wrapping key is rotated. Each record carries the version it
#: was sealed under, so a rewrap can run incrementally instead of requiring
#: every user to re-enrol.
CURRENT_KEY_VERSION = 1


class SealedEmbedding(TypedDict):
    ciphertext: str
    nonce: str
    key_version: int
    dim: int


def _aad(user_id: str, key_version: int) -> bytes:
    """Bind each sealed template to its owner.

    Without this, an attacker with write access to Mongo could copy user A's
    encrypted embedding into user B's document and then authenticate as B
    using A's face -- without ever breaking the encryption.
    """
    return f"fzip-embedding:{user_id}:{key_version}".encode()


def seal_embedding(key: bytes, user_id: str, vector: np.ndarray) -> SealedEmbedding:
    if vector.ndim != 1:
        raise ValueError("embedding must be a 1-D vector")

    flat = np.ascontiguousarray(vector, dtype=EMBEDDING_DTYPE)
    nonce = secrets.token_bytes(NONCE_SIZE)
    ciphertext = AESGCM(key).encrypt(nonce, flat.tobytes(), _aad(user_id, CURRENT_KEY_VERSION))

    return SealedEmbedding(
        ciphertext=base64.b64encode(ciphertext).decode("ascii"),
        nonce=base64.b64encode(nonce).decode("ascii"),
        key_version=CURRENT_KEY_VERSION,
        dim=int(flat.shape[0]),
    )


def open_embedding(key: bytes, user_id: str, record: Any) -> np.ndarray:
    """Decrypt a sealed embedding.

    Raises :class:`ValueError` on tag failure, which means either the wrapping
    key is wrong or the record was moved between users.
    """
    try:
        ciphertext = base64.b64decode(record["ciphertext"])
        nonce = base64.b64decode(record["nonce"])
        key_version = int(record["key_version"])
        dim = int(record["dim"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(f"malformed embedding record: {exc}") from exc

    try:
        plaintext = AESGCM(key).decrypt(nonce, ciphertext, _aad(user_id, key_version))
    except InvalidTag as exc:
        raise ValueError("embedding failed authentication") from exc

    vector = np.frombuffer(plaintext, dtype=EMBEDDING_DTYPE)
    if vector.shape[0] != dim:
        raise ValueError("embedding dimension mismatch")
    return vector
