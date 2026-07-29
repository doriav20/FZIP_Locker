"""Cryptographic primitives for the `.lck` v2 container.

Design notes, and why this replaced the 2022 implementation wholesale:

* **Argon2id, not a static key.** The old client loaded a 32-byte AES key from
  ``key.key`` -- a file committed to the repository, identical for every user.
  Anyone who cloned the repo could decrypt anyone's archive. Here the key is
  derived from the archive password the user types, with a random per-file
  salt, and it is never stored or transmitted anywhere.

* **AES-256-GCM, not AES-OFB.** OFB is a confidentiality-only mode with no
  integrity protection: an attacker who cannot read a file can still flip
  arbitrary plaintext bits by flipping ciphertext bits. GCM is an AEAD -- any
  modification is detected and decryption fails closed.

* **Chunked, not whole-file.** The container encrypts in fixed-size chunks so
  multi-gigabyte archives stream through constant memory. Each chunk gets a
  distinct nonce derived from a random per-file base plus the chunk index, so
  chunks cannot be reordered, duplicated, or spliced between files.

* **Header as AAD.** The container's JSON header (which carries the chunk
  count, the KDF parameters and the owner tag) is passed as Additional
  Authenticated Data on every chunk. Editing any of it -- including truncating
  the file and lowering the chunk count -- fails tag verification.
"""

from __future__ import annotations

import secrets
import struct
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from typing import Any

from argon2.low_level import Type as Argon2Type
from argon2.low_level import hash_secret_raw
from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from .errors import DecryptionError, MalformedVaultError

# --------------------------------------------------------------------------
# Sizes, in bytes
# --------------------------------------------------------------------------
KEY_SIZE = 32  # AES-256
SALT_SIZE = 16
NONCE_BASE_SIZE = 8  # + 4-byte chunk counter = 12-byte GCM nonce
NONCE_SIZE = 12
GCM_TAG_SIZE = 16

#: Plaintext bytes per chunk. 1 MiB balances memory use against per-chunk
#: tag overhead (16 bytes per chunk, i.e. ~0.0015% expansion).
DEFAULT_CHUNK_SIZE = 1024 * 1024

#: The 4-byte counter caps a single file at 2^32 chunks (~4 PiB at 1 MiB).
MAX_CHUNKS = 2**32 - 1

# --------------------------------------------------------------------------
# Argon2id defaults
#
# OWASP's current floor for Argon2id is t=2, m=19 MiB, p=1. We sit
# deliberately above it: 64 MiB of memory makes GPU and ASIC cracking far
# more expensive, and ~0.1s on a typical desktop is imperceptible when you
# are already picking a file in a dialog.
#
# These values are written into each file's header, so they can be raised
# later without making existing archives unreadable.
# --------------------------------------------------------------------------
DEFAULT_TIME_COST = 3
DEFAULT_MEMORY_KIB = 65536  # 64 MiB
DEFAULT_PARALLELISM = 4


@dataclass(frozen=True, slots=True)
class KdfParams:
    """Argon2id parameters, serialised into the container header."""

    salt: bytes
    time_cost: int = DEFAULT_TIME_COST
    memory_kib: int = DEFAULT_MEMORY_KIB
    parallelism: int = DEFAULT_PARALLELISM
    alg: str = "argon2id"

    @classmethod
    def generate(cls) -> KdfParams:
        """Fresh parameters with a cryptographically random salt."""
        return cls(salt=secrets.token_bytes(SALT_SIZE))

    def to_json(self) -> dict[str, Any]:
        import base64

        return {
            "alg": self.alg,
            "salt": base64.b64encode(self.salt).decode("ascii"),
            "t": self.time_cost,
            "m": self.memory_kib,
            "p": self.parallelism,
        }

    @classmethod
    def from_json(cls, raw: Any) -> KdfParams:
        import base64
        import binascii

        if not isinstance(raw, dict):
            raise MalformedVaultError("kdf section is not an object")

        alg = raw.get("alg")
        if alg != "argon2id":
            raise MalformedVaultError(f"unsupported KDF algorithm: {alg!r}")

        try:
            salt = base64.b64decode(raw["salt"], validate=True)
            time_cost = int(raw["t"])
            memory_kib = int(raw["m"])
            parallelism = int(raw["p"])
        except (KeyError, TypeError, ValueError, binascii.Error) as exc:
            raise MalformedVaultError(f"malformed kdf section: {exc}") from exc

        # Reject absurd values before handing them to Argon2. A hostile file
        # could otherwise request terabytes of memory and take the process
        # down -- a denial of service triggered purely by opening a file.
        if not SALT_SIZE <= len(salt) <= 64:
            raise MalformedVaultError("kdf salt has an implausible length")
        if not 1 <= time_cost <= 16:
            raise MalformedVaultError("kdf time cost out of range")
        if not 8192 <= memory_kib <= 1024 * 1024:  # 8 MiB .. 1 GiB
            raise MalformedVaultError("kdf memory cost out of range")
        if not 1 <= parallelism <= 16:
            raise MalformedVaultError("kdf parallelism out of range")

        return cls(
            salt=salt,
            time_cost=time_cost,
            memory_kib=memory_kib,
            parallelism=parallelism,
            alg=alg,
        )


def derive_key(password: str, params: KdfParams) -> bytearray:
    """Derive a 32-byte AES key from ``password`` using Argon2id.

    Returns a ``bytearray`` rather than ``bytes`` so the caller can overwrite
    it with :func:`secure_zero` once finished. See that function's docstring
    for the honest caveats.
    """
    raw = hash_secret_raw(
        secret=password.encode("utf-8"),
        salt=params.salt,
        time_cost=params.time_cost,
        memory_cost=params.memory_kib,
        parallelism=params.parallelism,
        hash_len=KEY_SIZE,
        type=Argon2Type.ID,
    )
    return bytearray(raw)


def secure_zero(buf: bytearray) -> None:
    """Overwrite a mutable buffer in place.

    This is defence in depth, not a guarantee. CPython may already have copied
    the material during allocation, garbage collection, or string interning,
    and we cannot reach those copies. It costs nothing and shortens the window
    in which the key sits in a page that might be swapped or core-dumped.
    """
    for i in range(len(buf)):
        buf[i] = 0


def _nonce(nonce_base: bytes, index: int) -> bytes:
    """GCM nonce for chunk ``index``: 8 random bytes + a 4-byte counter.

    Uniqueness matters more than secrecy for a GCM nonce: reusing one under
    the same key is catastrophic, leaking the authentication subkey. The base
    is random per file, and each file has its own key (its own salt), so the
    counter only needs to be unique within one file.
    """
    return nonce_base + struct.pack(">I", index)


def encrypt_chunks(
    key: bytes | bytearray,
    nonce_base: bytes,
    aad: bytes,
    plaintext_chunks: Iterable[bytes],
) -> Iterator[bytes]:
    """Encrypt an iterable of plaintext chunks, yielding ciphertext+tag each.

    ``aad`` is the serialised container header, bound into every chunk.
    """
    aesgcm = AESGCM(bytes(key))
    for index, chunk in enumerate(plaintext_chunks):
        if index > MAX_CHUNKS:
            raise ValueError("input exceeds the maximum supported chunk count")
        yield aesgcm.encrypt(_nonce(nonce_base, index), chunk, aad)


def decrypt_chunks(
    key: bytes | bytearray,
    nonce_base: bytes,
    aad: bytes,
    ciphertext_chunks: Iterable[bytes],
) -> Iterator[bytes]:
    """Decrypt and verify chunks in order.

    Raises :class:`DecryptionError` on the first tag mismatch -- wrong
    password, corruption, or tampering. The caller must not treat any yielded
    plaintext as trustworthy until the iterator has run to completion, since
    a truncation would only surface at the end.
    """
    aesgcm = AESGCM(bytes(key))
    for index, chunk in enumerate(ciphertext_chunks):
        try:
            yield aesgcm.decrypt(_nonce(nonce_base, index), chunk, aad)
        except InvalidTag as exc:
            raise DecryptionError(f"authentication failed on chunk {index}") from exc


def generate_nonce_base() -> bytes:
    return secrets.token_bytes(NONCE_BASE_SIZE)
