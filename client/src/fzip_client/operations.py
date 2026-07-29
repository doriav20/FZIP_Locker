"""High-level vault operations: lock a selection, unlock a `.lck`.

This is the module the UI calls, replacing the 2022
``client_external_handlers.py``. Two behavioural differences worth naming:

* The old flow wrote a plaintext ZIP next to the user's chosen output path,
  encrypted it, then deleted it -- leaving recoverable plaintext in the
  destination folder if anything failed in between. The intermediate now lives
  in a private temporary directory that is removed even on failure.

* The old flow encrypted with a repository-wide static key, so "locked" files
  were readable by anyone with a copy of the source. The key is now derived
  from the archive password, which never leaves this process.
"""

from __future__ import annotations

import tempfile
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from . import archive, vault
from .errors import ArchiveError, VaultError

LOCK_SUFFIX = ".lck"


@dataclass(frozen=True, slots=True)
class LockResult:
    destination: Path
    file_count: int
    plaintext_bytes: int
    locked_bytes: int


@dataclass(frozen=True, slots=True)
class UnlockResult:
    destination: Path
    file_count: int


def normalise_destination(path: Path) -> Path:
    """Force the `.lck` suffix.

    The original did this with ``path.replace(path[path.rfind('.') + 1:], 'lck')``,
    which corrupted any path containing a dot before the extension.
    """
    return path if path.suffix.lower() == LOCK_SUFFIX else path.with_suffix(LOCK_SUFFIX)


def lock(
    sources: Sequence[Path],
    destination: Path,
    password: str,
    *,
    owner: str = "",
) -> LockResult:
    """Archive ``sources`` and seal them into ``destination``."""
    if not password:
        raise VaultError("An archive password is required.")

    destination = normalise_destination(destination)

    with tempfile.TemporaryDirectory(prefix="fzip-") as workdir:
        staged = Path(workdir) / "payload.zip"

        with staged.open("wb") as handle:
            file_count = archive.create_archive(sources, handle)

        plaintext_bytes = staged.stat().st_size

        # Write to a sibling temp file and rename on success, so an
        # interrupted lock cannot leave a truncated .lck that looks valid.
        pending = destination.with_name(destination.name + ".partial")
        try:
            with staged.open("rb") as source, pending.open("wb") as sink:
                vault.write_vault(
                    source,
                    sink,
                    password,
                    owner=owner,
                    plaintext_size=plaintext_bytes,
                )
            locked_bytes = pending.stat().st_size
            pending.replace(destination)
        except BaseException:
            pending.unlink(missing_ok=True)
            raise

    return LockResult(
        destination=destination,
        file_count=file_count,
        plaintext_bytes=plaintext_bytes,
        locked_bytes=locked_bytes,
    )


def peek(source: Path) -> vault.VaultHeader:
    """Read a vault's header without the password, for pre-flight checks."""
    with source.open("rb") as handle:
        return vault.read_header(handle)


def unlock(
    source: Path,
    password: str,
    *,
    owner: str | None = None,
    destination: Path | None = None,
) -> UnlockResult:
    """Verify, decrypt and extract ``source``.

    Extraction only begins once the whole payload has been authenticated. That
    ordering is deliberate: writing files as chunks decrypt would scatter
    attacker-controlled data across the disk before the final tag revealed the
    archive had been tampered with.
    """
    target = destination or archive.unique_output_dir(source)

    with tempfile.TemporaryDirectory(prefix="fzip-") as workdir:
        staged = Path(workdir) / "payload.zip"

        with source.open("rb") as handle, staged.open("wb") as sink:
            vault.read_vault(handle, sink, password, expected_owner=owner)

        with staged.open("rb") as handle:
            try:
                count = archive.extract_archive(handle, target)
            except ArchiveError:
                # The payload authenticated but is not a usable ZIP. Do not
                # leave a half-populated output directory behind.
                if target.is_dir() and not any(target.iterdir()):
                    target.rmdir()
                raise

    return UnlockResult(destination=target, file_count=count)
