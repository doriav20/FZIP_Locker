"""ZIP packing and unpacking for the vault payload.

The 2022 client used ``pyminizip`` to produce a password-protected ZIP nested
inside an AES-OFB blob. That inner password used ZipCrypto, a cipher broken by
a known-plaintext attack since the 1990s. Now that the outer container is
AES-256-GCM keyed from the user's password (see :mod:`.vault`), the inner
encryption layer would add nothing -- so this module produces a plain deflate
archive and ``pyminizip`` is gone, taking its C build step with it.

Two bugs from the original are fixed here:

* Paths were assembled with hardcoded ``\\`` separators and ``os.chdir()``
  calls, so nothing worked off Windows. Everything is :mod:`pathlib` now.
* Selecting two files with the same name from different folders produced a ZIP
  with duplicate entries. Names are now deduplicated.
"""

from __future__ import annotations

import zipfile
from collections.abc import Sequence
from pathlib import Path
from typing import BinaryIO

from .errors import ArchiveError, UnsafeArchiveEntryError


def _unique_arcname(taken: set[str], candidate: str) -> str:
    """Return ``candidate``, suffixed if needed so it does not collide."""
    if candidate not in taken:
        taken.add(candidate)
        return candidate

    stem, dot, suffix = candidate.rpartition(".")
    base, ext = (stem, f".{suffix}") if dot else (candidate, "")
    counter = 2
    while f"{base} ({counter}){ext}" in taken:
        counter += 1
    resolved = f"{base} ({counter}){ext}"
    taken.add(resolved)
    return resolved


def create_archive(sources: Sequence[Path], dest: BinaryIO) -> int:
    """Write a deflate ZIP of ``sources`` into ``dest``.

    Directories are included recursively, keeping their own name as the top
    level. Returns the number of file entries written.
    """
    if not sources:
        raise ArchiveError("no files were selected")

    written = 0
    taken: set[str] = set()

    with zipfile.ZipFile(dest, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        for source in sources:
            path = Path(source)
            if not path.exists():
                raise ArchiveError(f"file not found: {path}")

            if path.is_dir():
                root = path.parent
                for member in sorted(path.rglob("*")):
                    if not member.is_file():
                        continue
                    arcname = _unique_arcname(taken, member.relative_to(root).as_posix())
                    zf.write(member, arcname=arcname)
                    written += 1
            else:
                arcname = _unique_arcname(taken, path.name)
                zf.write(path, arcname=arcname)
                written += 1

    if written == 0:
        raise ArchiveError("the selection contained no files")
    return written


def _is_within(base: Path, target: Path) -> bool:
    try:
        target.relative_to(base)
    except ValueError:
        return False
    return True


def extract_archive(src: BinaryIO, dest_dir: Path) -> int:
    """Extract a ZIP into ``dest_dir``, refusing entries that escape it.

    ``ZipFile.extractall`` does sanitise member names, but relying on that
    leaves the safety property invisible and implicit. Validating each
    resolved path against the destination makes the zip-slip defence explicit
    and testable, and also rejects absolute paths and symlink entries.
    """
    dest_dir = dest_dir.resolve()
    dest_dir.mkdir(parents=True, exist_ok=True)
    extracted = 0

    with zipfile.ZipFile(src, mode="r") as zf:
        for info in zf.infolist():
            name = info.filename

            if name.endswith("/"):
                continue  # directory entry; created implicitly below

            # Reject anything that would land outside dest_dir.
            if Path(name).is_absolute() or name.startswith(("/", "\\")):
                raise UnsafeArchiveEntryError(f"absolute path in archive: {name!r}")

            resolved = (dest_dir / name).resolve()
            if not _is_within(dest_dir, resolved):
                raise UnsafeArchiveEntryError(f"path escapes destination: {name!r}")

            # Symlink entries (Unix mode bits in the high half of external_attr)
            # can point anywhere; refuse them rather than recreate them.
            if (info.external_attr >> 16) & 0o170000 == 0o120000:
                raise UnsafeArchiveEntryError(f"symlink in archive: {name!r}")

            resolved.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(info) as member, resolved.open("wb") as out:
                while block := member.read(1024 * 1024):
                    out.write(block)
            extracted += 1

    return extracted


def unique_output_dir(base: Path) -> Path:
    """Pick a directory next to ``base`` that does not already exist.

    Mirrors the original's behaviour of appending underscores, but without the
    string surgery on ``rfind('.')`` that misfired on paths containing dots.
    """
    candidate = base.with_suffix("")
    if not candidate.exists():
        return candidate
    counter = 2
    while (numbered := candidate.with_name(f"{candidate.name} ({counter})")).exists():
        counter += 1
    return numbered
