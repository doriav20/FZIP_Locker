"""End-to-end lock/unlock tests, without the GUI.

These exercise the whole client-side path a user actually triggers: archive,
seal, then verify, decrypt and extract. No Qt, no network.
"""

from __future__ import annotations

import pytest

from fzip_client import crypto, operations, vault
from fzip_client.errors import (
    ArchiveError,
    DecryptionError,
    NotAVaultError,
    OwnershipError,
    VaultError,
)

CHEAP = {"time_cost": 1, "memory_kib": 8192, "parallelism": 1}
PASSWORD = "a-sufficiently-long-archive-password"


@pytest.fixture(autouse=True)
def _cheap_kdf(monkeypatch):
    """Use a cheap KDF everywhere in this module.

    operations.lock() intentionally does not expose a KDF override - production
    callers should not be able to weaken it by accident - so the default is
    patched at the source instead.
    """
    original = crypto.KdfParams.generate

    @classmethod
    def cheap(cls):  # type: ignore[misc]
        import secrets

        return cls(salt=secrets.token_bytes(crypto.SALT_SIZE), **CHEAP)

    monkeypatch.setattr(crypto.KdfParams, "generate", cheap)
    yield
    monkeypatch.setattr(crypto.KdfParams, "generate", original)


def _tree(root):
    (root / "docs").mkdir(parents=True)
    (root / "docs" / "notes.txt").write_bytes(b"notes content")
    (root / "docs" / "deep").mkdir()
    (root / "docs" / "deep" / "buried.bin").write_bytes(bytes(range(256)))
    (root / "top.txt").write_bytes(b"top level")
    return root


def test_lock_then_unlock_round_trips(tmp_path):
    source = _tree(tmp_path / "input")
    locked = tmp_path / "archive.lck"

    result = operations.lock([source], locked, PASSWORD, owner="user-1")
    assert result.destination == locked
    assert result.file_count == 3
    assert locked.is_file()

    out = operations.unlock(locked, PASSWORD, owner="user-1", destination=tmp_path / "out")
    assert out.file_count == 3
    assert (out.destination / "input" / "top.txt").read_bytes() == b"top level"
    assert (out.destination / "input" / "docs" / "deep" / "buried.bin").read_bytes() == bytes(
        range(256)
    )


def test_locked_file_reveals_nothing(tmp_path):
    secret = tmp_path / "secret.txt"
    secret.write_bytes(b"UNIQUE-MARKER-STRING-12345")
    locked = tmp_path / "out.lck"

    operations.lock([secret], locked, PASSWORD)
    blob = locked.read_bytes()

    assert b"UNIQUE-MARKER-STRING-12345" not in blob
    # Nor the filename, since the ZIP directory is inside the encrypted payload.
    assert b"secret.txt" not in blob


def test_suffix_is_normalised(tmp_path):
    source = tmp_path / "a.txt"
    source.write_bytes(b"x")

    result = operations.lock([source], tmp_path / "archive.zip", PASSWORD)
    assert result.destination.suffix == ".lck"


def test_dotted_destination_is_not_mangled(tmp_path):
    """The original's rfind('.') surgery broke names like this."""
    source = tmp_path / "a.txt"
    source.write_bytes(b"x")

    result = operations.lock([source], tmp_path / "my.backup.2026.lck", PASSWORD)
    assert result.destination.name == "my.backup.2026.lck"


def test_wrong_password_is_rejected(tmp_path):
    source = tmp_path / "a.txt"
    source.write_bytes(b"payload")
    locked = tmp_path / "out.lck"
    operations.lock([source], locked, PASSWORD)

    with pytest.raises(DecryptionError):
        operations.unlock(locked, "the-wrong-password-entirely")


def test_foreign_archive_is_refused(tmp_path):
    source = tmp_path / "a.txt"
    source.write_bytes(b"payload")
    locked = tmp_path / "out.lck"
    operations.lock([source], locked, PASSWORD, owner="alice")

    with pytest.raises(OwnershipError):
        operations.unlock(locked, PASSWORD, owner="bob")


def test_tampered_archive_is_refused(tmp_path):
    source = tmp_path / "a.txt"
    source.write_bytes(b"payload")
    locked = tmp_path / "out.lck"
    operations.lock([source], locked, PASSWORD)

    blob = bytearray(locked.read_bytes())
    blob[-1] ^= 0xFF
    locked.write_bytes(bytes(blob))

    with pytest.raises(DecryptionError):
        operations.unlock(locked, PASSWORD)


def test_non_vault_file_is_refused(tmp_path):
    fake = tmp_path / "not-a-vault.lck"
    fake.write_bytes(b"PK\x03\x04 plain zip")

    with pytest.raises(NotAVaultError):
        operations.unlock(fake, PASSWORD)


def test_peek_reads_metadata_without_the_password(tmp_path):
    source = tmp_path / "a.txt"
    source.write_bytes(b"payload")
    locked = tmp_path / "out.lck"
    operations.lock([source], locked, PASSWORD, owner="alice")

    header = operations.peek(locked)
    assert header.owner == "alice"
    assert header.version == vault.VERSION
    assert header.size > 0


def test_failed_lock_leaves_no_partial_file(tmp_path):
    """An interrupted lock must not leave something that looks like a vault."""
    locked = tmp_path / "out.lck"
    with pytest.raises(ArchiveError, match="not found"):
        operations.lock([tmp_path / "does-not-exist"], locked, PASSWORD)

    assert not locked.exists()
    assert not locked.with_name(locked.name + ".partial").exists()


def test_no_plaintext_intermediate_survives(tmp_path):
    """The 2022 flow left a plaintext .zip next to the output on failure."""
    source = tmp_path / "a.txt"
    source.write_bytes(b"payload")
    locked = tmp_path / "out.lck"

    operations.lock([source], locked, PASSWORD)

    leftovers = [p.name for p in tmp_path.iterdir() if p.suffix in {".zip", ".partial"}]
    assert leftovers == []


def test_unlock_picks_a_free_output_directory(tmp_path):
    source = tmp_path / "a.txt"
    source.write_bytes(b"payload")
    locked = tmp_path / "archive.lck"
    operations.lock([source], locked, PASSWORD)

    first = operations.unlock(locked, PASSWORD)
    assert first.destination == tmp_path / "archive"

    second = operations.unlock(locked, PASSWORD)
    assert second.destination == tmp_path / "archive (2)"


def test_empty_password_is_refused(tmp_path):
    source = tmp_path / "a.txt"
    source.write_bytes(b"x")
    with pytest.raises(VaultError, match="password"):
        operations.lock([source], tmp_path / "out.lck", "")


def test_multi_chunk_archive_round_trips(tmp_path):
    """Crosses the chunk boundary so the streaming path is really exercised.

    The payload must be incompressible: it is the *deflated* ZIP that gets
    chunked, so a repeating pattern would collapse to a single chunk and this
    test would silently stop covering the streaming path.
    """
    import os

    payload = os.urandom(3 * 1024 * 1024)
    big = tmp_path / "big.bin"
    big.write_bytes(payload)
    locked = tmp_path / "big.lck"

    operations.lock([big], locked, PASSWORD)

    header = operations.peek(locked)
    assert header.chunks >= 3, f"expected multiple chunks, got {header.chunks}"

    out = operations.unlock(locked, PASSWORD, destination=tmp_path / "out")
    assert (out.destination / "big.bin").read_bytes() == payload


def test_compressible_payload_shrinks(tmp_path):
    """Sanity check on the deflate layer, and a companion to the test above."""
    source = tmp_path / "repetitive.bin"
    source.write_bytes(b"A" * (2 * 1024 * 1024))
    locked = tmp_path / "out.lck"

    result = operations.lock([source], locked, PASSWORD)
    assert result.plaintext_bytes < 100_000  # 2 MiB of 'A' deflates hard
    assert operations.unlock(locked, PASSWORD, destination=tmp_path / "out")
