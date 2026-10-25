"""Validate packaged GO 2D anaStruct plugin without invoking the solver.

Checks SHA256, ZIP integrity, exact source-file parity and Python syntax.
Run before publishing a community metadata checksum.
"""
from __future__ import annotations

import hashlib
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "go_anastruct_2d"
ZIP = ROOT / "dist" / "go_anastruct_2d-v0.5.5-plugin.zip"
MANIFEST = ZIP.with_suffix(ZIP.suffix + ".sha256")


def verify() -> None:
    assert ZIP.is_file(), ZIP
    assert MANIFEST.is_file(), MANIFEST
    expected = MANIFEST.read_text(encoding="ascii").strip().lower()
    assert len(expected) == 64 and all(c in "0123456789abcdef" for c in expected)
    actual = hashlib.sha256(ZIP.read_bytes()).hexdigest()
    assert actual == expected, f"SHA-256 mismatch: {actual} vs {expected}"

    with zipfile.ZipFile(ZIP) as archive:
        assert archive.testzip() is None, "ZIP CRC validation failed"
        names = archive.namelist()
        assert len(names) == len(set(names)), "duplicate archive paths"
        assert names and all(
            path.startswith("go_anastruct_2d/") and not path.endswith("/")
            for path in names
        ), "expected exactly one plugin folder"
        assert "go_anastruct_2d/__init__.py" in names
        for filename in names:
            rel = filename.split("/", 1)[1]
            source = PACKAGE / rel
            assert source.is_file(), f"missing source: {source}"
            data = archive.read(filename)
            assert data == source.read_bytes(), f"source differs: {rel}"
            if filename.endswith(".py"):
                compile(data, filename, "exec")

    print(f"GO anaStruct plugin package verified: {len(names)} files, SHA256 {actual}")


if __name__ == "__main__":
    try:
        verify()
    except (AssertionError, OSError, SyntaxError, zipfile.BadZipFile) as exc:
        print(f"FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
