from __future__ import annotations

import io
import zipfile

import pytest

from fzip_client.archive import (
    create_archive,
    extract_archive,
    unique_output_dir,
)
from fzip_client.errors import ArchiveError, UnsafeArchiveEntryError


def _zip_of(**entries: bytes) -> io.BytesIO:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, data in entries.items():
            zf.writestr(name, data)
    buf.seek(0)
    return buf


def test_round_trip_files(tmp_path):
    (tmp_path / "a.txt").write_bytes(b"alpha")
    (tmp_path / "b.txt").write_bytes(b"beta")

    buf = io.BytesIO()
    assert create_archive([tmp_path / "a.txt", tmp_path / "b.txt"], buf) == 2

    out = tmp_path / "out"
    buf.seek(0)
    assert extract_archive(buf, out) == 2
    assert (out / "a.txt").read_bytes() == b"alpha"
    assert (out / "b.txt").read_bytes() == b"beta"


def test_directories_are_included_recursively(tmp_path):
    root = tmp_path / "project"
    (root / "nested" / "deep").mkdir(parents=True)
    (root / "top.txt").write_bytes(b"top")
    (root / "nested" / "mid.txt").write_bytes(b"mid")
    (root / "nested" / "deep" / "low.txt").write_bytes(b"low")

    buf = io.BytesIO()
    assert create_archive([root], buf) == 3

    out = tmp_path / "out"
    buf.seek(0)
    extract_archive(buf, out)
    assert (out / "project" / "nested" / "deep" / "low.txt").read_bytes() == b"low"


def test_duplicate_basenames_are_deduplicated(tmp_path):
    """The 2022 client produced a ZIP with duplicate entries here."""
    for folder in ("one", "two"):
        (tmp_path / folder).mkdir()
        (tmp_path / folder / "notes.txt").write_bytes(folder.encode())

    buf = io.BytesIO()
    create_archive([tmp_path / "one" / "notes.txt", tmp_path / "two" / "notes.txt"], buf)

    buf.seek(0)
    with zipfile.ZipFile(buf) as zf:
        names = zf.namelist()
    assert len(names) == len(set(names)) == 2


def test_empty_selection_is_refused():
    with pytest.raises(ArchiveError, match="no files"):
        create_archive([], io.BytesIO())


def test_missing_file_is_reported(tmp_path):
    with pytest.raises(ArchiveError, match="not found"):
        create_archive([tmp_path / "ghost.txt"], io.BytesIO())


# --------------------------------------------------------------------------
# Zip-slip
# --------------------------------------------------------------------------
@pytest.mark.parametrize(
    "hostile_name",
    [
        pytest.param("../escaped.txt", id="parent-traversal"),
        pytest.param("../../../../etc/passwd", id="deep-traversal"),
        pytest.param("nested/../../escaped.txt", id="traversal-mid-path"),
    ],
)
def test_path_traversal_entries_are_refused(hostile_name, tmp_path):
    buf = _zip_of(**{hostile_name: b"owned"})
    with pytest.raises(UnsafeArchiveEntryError):
        extract_archive(buf, tmp_path / "out")

    assert not (tmp_path / "escaped.txt").exists()


def test_absolute_path_entry_is_refused(tmp_path):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("/tmp/owned.txt", b"owned")
    buf.seek(0)

    with pytest.raises(UnsafeArchiveEntryError):
        extract_archive(buf, tmp_path / "out")


def test_symlink_entry_is_refused(tmp_path):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        info = zipfile.ZipInfo("link")
        info.external_attr = 0o120777 << 16  # S_IFLNK | 0777
        zf.writestr(info, "/etc/passwd")
    buf.seek(0)

    with pytest.raises(UnsafeArchiveEntryError):
        extract_archive(buf, tmp_path / "out")


# --------------------------------------------------------------------------
# Output naming
# --------------------------------------------------------------------------
def test_unique_output_dir_avoids_collisions(tmp_path):
    base = tmp_path / "archive.lck"
    assert unique_output_dir(base) == tmp_path / "archive"

    (tmp_path / "archive").mkdir()
    assert unique_output_dir(base) == tmp_path / "archive (2)"

    (tmp_path / "archive (2)").mkdir()
    assert unique_output_dir(base) == tmp_path / "archive (3)"


def test_dotted_names_survive(tmp_path):
    """The old rfind('.') logic mangled paths like `my.backup.2024.lck`."""
    base = tmp_path / "my.backup.2024.lck"
    assert unique_output_dir(base) == tmp_path / "my.backup.2024"
