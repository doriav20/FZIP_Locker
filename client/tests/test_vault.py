"""Container format tests.

The round-trip cases prove it works. The tamper cases are the ones that
matter: they are what the 2022 AES-OFB implementation would have failed,
since it had no authentication tag to check.
"""

from __future__ import annotations

import io
import json
import struct

import pytest

from fzip_client import crypto, vault
from fzip_client.errors import (
    DecryptionError,
    MalformedVaultError,
    NotAVaultError,
    OwnershipError,
    UnsupportedVersionError,
)


def seal(payload: bytes, password: str, kdf: crypto.KdfParams, **kwargs) -> bytes:
    dest = io.BytesIO()
    vault.write_vault(io.BytesIO(payload), dest, password, kdf=kdf, **kwargs)
    return dest.getvalue()


def unseal(blob: bytes, password: str, **kwargs) -> bytes:
    out = io.BytesIO()
    vault.read_vault(io.BytesIO(blob), out, password, **kwargs)
    return out.getvalue()


# --------------------------------------------------------------------------
# Round trips
# --------------------------------------------------------------------------
@pytest.mark.parametrize(
    "payload",
    [
        pytest.param(b"", id="empty"),
        pytest.param(b"x", id="single-byte"),
        pytest.param(b"hello world", id="small"),
        pytest.param(b"\x00" * 4096, id="all-zeros"),
        pytest.param(bytes(range(256)) * 64, id="binary"),
    ],
)
def test_round_trip(payload, password, cheap_kdf):
    assert unseal(seal(payload, password, cheap_kdf), password) == payload


def test_round_trip_spans_many_chunks(password, cheap_kdf):
    # 4 KiB chunks over ~10 KiB of data: 3 chunks, last one partial.
    payload = bytes(range(256)) * 40
    blob = seal(payload, password, cheap_kdf, chunk_size=4096)

    header = vault.read_header(io.BytesIO(blob))
    assert header.chunks == 3
    assert unseal(blob, password) == payload


def test_exact_chunk_multiple_has_no_empty_trailing_chunk(password, cheap_kdf):
    payload = b"A" * 8192
    blob = seal(payload, password, cheap_kdf, chunk_size=4096)
    assert vault.read_header(io.BytesIO(blob)).chunks == 2
    assert unseal(blob, password) == payload


def test_ciphertext_does_not_contain_plaintext(password, cheap_kdf):
    payload = b"TOP SECRET MARKER STRING"
    assert payload not in seal(payload, password, cheap_kdf)


def test_identical_inputs_produce_different_ciphertext(password, cheap_kdf):
    """A fresh nonce per file means identical inputs never produce identical output.

    Holding the salt (and therefore the key) fixed isolates the nonce as the
    source of the difference. Under a fixed nonce this would leak that two
    archives share a plaintext -- and under GCM specifically, reusing a nonce
    with the same key would leak the authentication subkey outright.
    """
    first = seal(b"same", password, cheap_kdf)
    second = seal(b"same", password, cheap_kdf)
    assert first != second
    assert unseal(first, password) == unseal(second, password) == b"same"


# --------------------------------------------------------------------------
# Authentication failures
# --------------------------------------------------------------------------
def test_wrong_password_is_rejected(password, cheap_kdf):
    blob = seal(b"secret data", password, cheap_kdf)
    with pytest.raises(DecryptionError):
        unseal(blob, "not the password")


@pytest.mark.parametrize("bit", [0, 1, 7])
def test_single_bit_flip_in_body_is_detected(bit, password, cheap_kdf):
    """The property AES-OFB could not provide: any modification fails closed."""
    blob = bytearray(seal(b"payload that matters", password, cheap_kdf))
    blob[-8] ^= 1 << bit
    with pytest.raises(DecryptionError):
        unseal(bytes(blob), password)


def test_every_body_byte_is_authenticated(password, cheap_kdf):
    """Flip each byte of the body in turn; none may decrypt successfully."""
    payload = b"0123456789abcdef"
    blob = seal(payload, password, cheap_kdf)
    body_start = len(blob) - (len(payload) + crypto.GCM_TAG_SIZE)

    for offset in range(body_start, len(blob)):
        mutated = bytearray(blob)
        mutated[offset] ^= 0xFF
        with pytest.raises(DecryptionError):
            unseal(bytes(mutated), password)


def test_truncated_body_is_rejected(password, cheap_kdf):
    blob = seal(b"A" * 10000, password, cheap_kdf, chunk_size=4096)
    with pytest.raises((MalformedVaultError, DecryptionError)):
        unseal(blob[:-100], password)


def test_dropping_a_whole_final_chunk_is_rejected(password, cheap_kdf):
    """Truncation attack: remove a chunk and the authenticated count catches it."""
    blob = seal(b"A" * 12288, password, cheap_kdf, chunk_size=4096)
    assert vault.read_header(io.BytesIO(blob)).chunks == 3

    without_last = blob[: -(4096 + crypto.GCM_TAG_SIZE)]
    with pytest.raises((MalformedVaultError, DecryptionError)):
        unseal(without_last, password)


def test_trailing_data_is_rejected(password, cheap_kdf):
    blob = seal(b"data", password, cheap_kdf)
    with pytest.raises(MalformedVaultError):
        unseal(blob + b"extra", password)


def test_chunks_cannot_be_reordered(password, cheap_kdf):
    """Per-chunk nonces include the index, so swapping chunks fails."""
    blob = seal(b"A" * 4096 + b"B" * 4096, password, cheap_kdf, chunk_size=4096)
    header_end = len(blob) - 2 * (4096 + crypto.GCM_TAG_SIZE)
    size = 4096 + crypto.GCM_TAG_SIZE

    head = blob[:header_end]
    first = blob[header_end : header_end + size]
    second = blob[header_end + size :]

    with pytest.raises(DecryptionError):
        unseal(head + second + first, password)


# --------------------------------------------------------------------------
# Header binding (AAD)
# --------------------------------------------------------------------------
def _split(blob: bytes) -> tuple[bytes, dict, bytes]:
    (header_len,) = struct.unpack(">I", blob[8:12])
    header = json.loads(blob[12 : 12 + header_len])
    return blob[:8], header, blob[12 + header_len :]


def _reassemble(magic: bytes, header: dict, body: bytes) -> bytes:
    raw = json.dumps(header, sort_keys=True, separators=(",", ":")).encode()
    return magic + struct.pack(">I", len(raw)) + raw + body


def test_editing_the_owner_field_breaks_decryption(password, cheap_kdf):
    """The owner tag is inside the AAD, so it cannot be swapped silently."""
    blob = seal(b"mine", password, cheap_kdf, owner="user-a")
    magic, header, body = _split(blob)
    header["owner"] = "user-b"

    with pytest.raises(DecryptionError):
        unseal(_reassemble(magic, header, body), password)


def test_lowering_the_chunk_count_breaks_decryption(password, cheap_kdf):
    blob = seal(b"A" * 12288, password, cheap_kdf, chunk_size=4096)
    magic, header, body = _split(blob)
    header["chunks"] = 1

    with pytest.raises((DecryptionError, MalformedVaultError)):
        unseal(_reassemble(magic, header, body), password)


def test_inconsistent_size_and_chunk_count_is_rejected(password, cheap_kdf):
    """size, chunks and chunk_size must agree, checked before key derivation."""
    blob = seal(b"A" * 12288, password, cheap_kdf, chunk_size=4096)
    magic, header, body = _split(blob)
    header["size"] = 999999  # would imply many more chunks

    with pytest.raises(MalformedVaultError, match="inconsistent"):
        unseal(_reassemble(magic, header, body), password)


def test_editing_the_size_field_breaks_decryption(password, cheap_kdf):
    """A size edit that stays internally consistent still fails the AAD check."""
    payload = b"A" * 4096
    blob = seal(payload, password, cheap_kdf, chunk_size=4096)
    magic, header, body = _split(blob)
    header["size"] = 4095  # still 1 chunk, so the consistency check passes

    with pytest.raises(MalformedVaultError):
        unseal(_reassemble(magic, header, body), password)


def test_editing_the_created_timestamp_breaks_decryption(password, cheap_kdf):
    """Even a field nothing reads is authenticated -- the whole header is AAD."""
    blob = seal(b"data", password, cheap_kdf)
    magic, header, body = _split(blob)
    header["created"] = "1999-01-01T00:00:00+00:00"

    with pytest.raises(DecryptionError):
        unseal(_reassemble(magic, header, body), password)


# --------------------------------------------------------------------------
# Structural validation
# --------------------------------------------------------------------------
def test_non_vault_file_is_rejected(password):
    with pytest.raises(NotAVaultError):
        unseal(b"PK\x03\x04 this is a plain zip", password)


def test_empty_file_is_rejected(password):
    with pytest.raises(NotAVaultError):
        unseal(b"", password)


def test_future_version_is_rejected(password, cheap_kdf):
    blob = bytearray(seal(b"data", password, cheap_kdf))
    blob[7] = 99
    with pytest.raises(UnsupportedVersionError):
        unseal(bytes(blob), password)


def test_absurd_header_length_is_rejected(password):
    blob = vault.MAGIC_FULL + struct.pack(">I", 0xFFFFFFFF) + b"{}"
    with pytest.raises(MalformedVaultError):
        unseal(blob, password)


def test_hostile_kdf_memory_cost_is_rejected(password, cheap_kdf):
    """A malicious file must not be able to request 1 TiB of RAM on open."""
    blob = seal(b"data", password, cheap_kdf)
    magic, header, body = _split(blob)
    header["kdf"]["m"] = 1024 * 1024 * 1024  # 1 TiB in KiB

    with pytest.raises(MalformedVaultError):
        unseal(_reassemble(magic, header, body), password)


def test_unknown_kdf_algorithm_is_rejected(password, cheap_kdf):
    blob = seal(b"data", password, cheap_kdf)
    magic, header, body = _split(blob)
    header["kdf"]["alg"] = "md5"

    with pytest.raises(MalformedVaultError):
        unseal(_reassemble(magic, header, body), password)


# --------------------------------------------------------------------------
# Ownership (advisory)
# --------------------------------------------------------------------------
def test_ownership_mismatch_reports_clearly(password, cheap_kdf):
    blob = seal(b"mine", password, cheap_kdf, owner="user-a")
    with pytest.raises(OwnershipError):
        unseal(blob, password, expected_owner="user-b")


def test_matching_owner_decrypts(password, cheap_kdf):
    blob = seal(b"mine", password, cheap_kdf, owner="user-a")
    assert unseal(blob, password, expected_owner="user-a") == b"mine"


def test_header_is_readable_without_the_password(password, cheap_kdf):
    blob = seal(b"mine", password, cheap_kdf, owner="user-a")
    header = vault.read_header(io.BytesIO(blob))
    assert header.owner == "user-a"
    assert header.version == vault.VERSION


def test_empty_password_is_refused(cheap_kdf):
    with pytest.raises(ValueError, match="password is required"):
        seal(b"data", "", cheap_kdf)
