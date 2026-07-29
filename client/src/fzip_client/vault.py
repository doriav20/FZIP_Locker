"""The `.lck` v2 container: read and write.

Layout::

    magic       b"FZIPLCK\\x02"                      8 bytes
    header_len  uint32 big-endian                    4 bytes
    header      JSON, UTF-8                          header_len bytes
    body        chunk[0] .. chunk[n-1]

    chunk[i] = AES-256-GCM(key, nonce_base || be32(i), plaintext[i]) || tag

Every chunk but the last holds exactly ``chunk_size`` plaintext bytes, so the
reader can find chunk boundaries from the header alone. The header is used
verbatim as Additional Authenticated Data, which binds the chunk count, the
KDF parameters and the owner tag to the ciphertext: change any byte of it and
decryption fails.

The 2022 format is not readable here, by design. It used a globally shared
key that is public in this repository's history, so anything it protected
should be considered already compromised rather than migrated. See
docs/SECURITY.md.
"""

from __future__ import annotations

import base64
import binascii
import json
import struct
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, BinaryIO

from . import crypto
from .errors import (
    MalformedVaultError,
    NotAVaultError,
    OwnershipError,
    UnsupportedVersionError,
)

MAGIC = b"FZIPLCK"
VERSION = 2
MAGIC_FULL = MAGIC + bytes([VERSION])

#: A header is a few hundred bytes in practice. The cap stops a hostile file
#: from claiming a multi-gigabyte header and exhausting memory on open.
MAX_HEADER_BYTES = 64 * 1024


@dataclass(frozen=True, slots=True)
class VaultHeader:
    """Parsed container header. Serialises to the exact bytes used as AAD."""

    kdf: crypto.KdfParams
    nonce_base: bytes
    chunks: int
    #: Total plaintext length. Makes the final chunk's exact size known, so
    #: appended bytes are rejected structurally rather than being absorbed
    #: into the last chunk and surfacing as a confusing decryption failure.
    size: int
    chunk_size: int = crypto.DEFAULT_CHUNK_SIZE
    owner: str = ""
    created: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    cipher: str = "AES-256-GCM"
    version: int = VERSION

    def to_bytes(self) -> bytes:
        """Serialise deterministically.

        ``sort_keys`` and a fixed separator matter: the bytes produced here are
        the AAD, and the bytes stored on disk are re-used verbatim on read, so
        the two only need to agree at write time. Determinism keeps the format
        reproducible and the tests meaningful.
        """
        payload: dict[str, Any] = {
            "v": self.version,
            "kdf": self.kdf.to_json(),
            "cipher": self.cipher,
            "chunk_size": self.chunk_size,
            "nonce_base": base64.b64encode(self.nonce_base).decode("ascii"),
            "chunks": self.chunks,
            "size": self.size,
            "owner": self.owner,
            "created": self.created,
        }
        return json.dumps(
            payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8")

    @classmethod
    def from_bytes(cls, raw: bytes) -> VaultHeader:
        try:
            payload = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise MalformedVaultError(f"header is not valid JSON: {exc}") from exc

        if not isinstance(payload, dict):
            raise MalformedVaultError("header is not a JSON object")

        version = payload.get("v")
        if version != VERSION:
            raise UnsupportedVersionError(f"unsupported container version: {version!r}")

        cipher = payload.get("cipher")
        if cipher != "AES-256-GCM":
            raise MalformedVaultError(f"unsupported cipher: {cipher!r}")

        try:
            nonce_base = base64.b64decode(payload["nonce_base"], validate=True)
            chunks = int(payload["chunks"])
            size = int(payload["size"])
            chunk_size = int(payload["chunk_size"])
            owner = str(payload.get("owner", ""))
            created = str(payload.get("created", ""))
        except (KeyError, TypeError, ValueError, binascii.Error) as exc:
            raise MalformedVaultError(f"malformed header: {exc}") from exc

        if len(nonce_base) != crypto.NONCE_BASE_SIZE:
            raise MalformedVaultError("nonce_base has the wrong length")
        if not 1 <= chunks <= crypto.MAX_CHUNKS:
            raise MalformedVaultError("chunk count out of range")
        if not 1024 <= chunk_size <= 64 * 1024 * 1024:
            raise MalformedVaultError("chunk size out of range")
        if size < 0:
            raise MalformedVaultError("negative payload size")

        # size, chunks and chunk_size must agree. Catching this here means a
        # hand-edited header is rejected before any key derivation happens.
        if chunks != max(1, -(-size // chunk_size)):
            raise MalformedVaultError("chunk count is inconsistent with payload size")

        return cls(
            kdf=crypto.KdfParams.from_json(payload.get("kdf")),
            nonce_base=nonce_base,
            chunks=chunks,
            size=size,
            chunk_size=chunk_size,
            owner=owner,
            created=created,
            cipher=cipher,
            version=version,
        )


# --------------------------------------------------------------------------
# Writing
# --------------------------------------------------------------------------
def _read_exact_chunks(src: BinaryIO, chunk_size: int) -> Iterator[bytes]:
    """Yield fixed-size plaintext chunks, always at least one (possibly empty)."""
    produced = 0
    while True:
        block = src.read(chunk_size)
        if not block:
            break
        produced += 1
        yield block
    if produced == 0:
        # An empty payload still needs one authenticated chunk, otherwise an
        # empty file would have nothing to verify and `chunks` could not be
        # >= 1 as the reader requires.
        yield b""


def write_vault(
    plaintext: BinaryIO,
    dest: BinaryIO,
    password: str,
    *,
    owner: str = "",
    chunk_size: int = crypto.DEFAULT_CHUNK_SIZE,
    plaintext_size: int | None = None,
    kdf: crypto.KdfParams | None = None,
) -> VaultHeader:
    """Encrypt ``plaintext`` into ``dest`` as a v2 container.

    ``plaintext_size`` lets the chunk count be computed up front so the header
    (and therefore the AAD) is final before any chunk is encrypted. When it is
    not supplied the payload is buffered to measure it -- fine for the modest
    archives the GUI produces, but callers with large inputs should pass the
    size.

    ``kdf`` overrides the Argon2id parameters. Production callers should leave
    it unset and take the defaults; it exists so the test suite can run with a
    cheap cost factor, and so the cost can be raised later without a format
    change (the parameters travel in the header).
    """
    if not password:
        raise ValueError("an archive password is required")

    if plaintext_size is None:
        buffered = plaintext.read()
        plaintext_size = len(buffered)
        import io

        plaintext = io.BytesIO(buffered)

    chunks = max(1, -(-plaintext_size // chunk_size))  # ceil division
    if chunks > crypto.MAX_CHUNKS:
        raise ValueError("payload too large for this container format")

    header = VaultHeader(
        kdf=kdf or crypto.KdfParams.generate(),
        nonce_base=crypto.generate_nonce_base(),
        chunks=chunks,
        size=plaintext_size,
        chunk_size=chunk_size,
        owner=owner,
    )
    header_bytes = header.to_bytes()
    if len(header_bytes) > MAX_HEADER_BYTES:
        raise ValueError("header exceeds the maximum size")

    key = crypto.derive_key(password, header.kdf)
    try:
        dest.write(MAGIC_FULL)
        dest.write(struct.pack(">I", len(header_bytes)))
        dest.write(header_bytes)

        written = 0
        for encrypted in crypto.encrypt_chunks(
            key, header.nonce_base, header_bytes, _read_exact_chunks(plaintext, chunk_size)
        ):
            dest.write(encrypted)
            written += 1

        if written != chunks:
            # Would mean the input changed size mid-write; the file on disk is
            # now inconsistent with its own authenticated header.
            raise MalformedVaultError(
                f"expected {chunks} chunks but wrote {written}; input changed while reading"
            )
    finally:
        crypto.secure_zero(key)

    return header


# --------------------------------------------------------------------------
# Reading
# --------------------------------------------------------------------------
def read_header(src: BinaryIO) -> VaultHeader:
    """Parse the header without needing the password.

    Lets the UI check ownership and show metadata before prompting.
    """
    magic = src.read(len(MAGIC_FULL))
    if len(magic) < len(MAGIC_FULL) or not magic.startswith(MAGIC):
        raise NotAVaultError("missing FZIP Locker magic bytes")
    if magic[-1] != VERSION:
        raise UnsupportedVersionError(f"unsupported container version: {magic[-1]}")

    raw_len = src.read(4)
    if len(raw_len) != 4:
        raise MalformedVaultError("truncated header length")
    (header_len,) = struct.unpack(">I", raw_len)
    if not 0 < header_len <= MAX_HEADER_BYTES:
        raise MalformedVaultError("implausible header length")

    header_bytes = src.read(header_len)
    if len(header_bytes) != header_len:
        raise MalformedVaultError("truncated header")

    return VaultHeader.from_bytes(header_bytes)


def _header_bytes_at(src: BinaryIO) -> tuple[VaultHeader, bytes]:
    """Read the header, returning both the parsed form and its exact bytes.

    The raw bytes are what get passed as AAD -- re-serialising the parsed
    header would risk a mismatch if key order or whitespace ever differed.
    """
    src.seek(0)
    magic = src.read(len(MAGIC_FULL))
    if len(magic) < len(MAGIC_FULL) or not magic.startswith(MAGIC):
        raise NotAVaultError("missing FZIP Locker magic bytes")
    if magic[-1] != VERSION:
        raise UnsupportedVersionError(f"unsupported container version: {magic[-1]}")

    raw_len = src.read(4)
    if len(raw_len) != 4:
        raise MalformedVaultError("truncated header length")
    (header_len,) = struct.unpack(">I", raw_len)
    if not 0 < header_len <= MAX_HEADER_BYTES:
        raise MalformedVaultError("implausible header length")

    header_bytes = src.read(header_len)
    if len(header_bytes) != header_len:
        raise MalformedVaultError("truncated header")

    return VaultHeader.from_bytes(header_bytes), header_bytes


def _read_body_chunks(src: BinaryIO, header: VaultHeader) -> Iterator[bytes]:
    """Yield exactly ``header.chunks`` ciphertext chunks, or raise.

    Truncation and trailing-garbage checks live here rather than in the AEAD
    layer, so a shortened file is rejected explicitly instead of silently
    decrypting to a prefix of the original.
    """
    full = header.chunk_size + crypto.GCM_TAG_SIZE

    # The header's authenticated `size` pins the final chunk's exact length,
    # so trailing bytes cannot be absorbed into it.
    last_plain = header.size - (header.chunks - 1) * header.chunk_size
    last_full = last_plain + crypto.GCM_TAG_SIZE

    for index in range(header.chunks):
        is_last = index == header.chunks - 1
        expected = last_full if is_last else full
        block = src.read(expected)
        if len(block) != expected:
            raise MalformedVaultError(f"truncated chunk {index}")
        if is_last and src.read(1):
            raise MalformedVaultError("unexpected trailing data after final chunk")
        yield block


def read_vault(
    src: BinaryIO,
    dest: BinaryIO,
    password: str,
    *,
    expected_owner: str | None = None,
) -> VaultHeader:
    """Verify and decrypt a v2 container from ``src`` into ``dest``.

    ``expected_owner`` is checked before any key derivation, purely so the UI
    can say "this belongs to another account" instead of "wrong password".
    It is advisory: the header is attacker-editable until the first tag is
    verified, so it is never a substitute for the password.
    """
    header, header_bytes = _header_bytes_at(src)

    if expected_owner is not None and header.owner and header.owner != expected_owner:
        raise OwnershipError("vault owner does not match the signed-in account")

    key = crypto.derive_key(password, header.kdf)
    try:
        for plain in crypto.decrypt_chunks(
            key, header.nonce_base, header_bytes, _read_body_chunks(src, header)
        ):
            dest.write(plain)
    finally:
        crypto.secure_zero(key)

    return header
