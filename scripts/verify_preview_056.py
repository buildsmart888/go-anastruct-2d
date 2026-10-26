"""Verify preview package bytes, source parity, SHA-256 and Python syntax."""
from __future__ import annotations

import hashlib
from pathlib import Path
import sys
import zipfile

from package_preview_056 import DEST, FILES, PACKAGE


def main():
    digest_path = Path(str(DEST) + ".sha256")
    if not DEST.is_file() or not digest_path.is_file():
        raise FileNotFoundError("Preview ZIP / SHA-256 manifest is missing")
    digest = hashlib.sha256(DEST.read_bytes()).hexdigest()
    expected = digest_path.read_text(encoding="ascii").strip().lower()
    if digest != expected or len(expected) != 64:
        raise AssertionError(f"SHA-256 mismatch: {digest}, manifest={expected}")
    with zipfile.ZipFile(DEST) as archive:
        if archive.testzip() is not None:
            raise AssertionError("ZIP CRC validation failed")
        names = archive.namelist()
        expected_names = ["go_anastruct_2d/" + x for x in FILES]
        if len(names) != len(set(names)) or set(names) != set(expected_names):
            raise AssertionError("Preview ZIP contains missing, extra or duplicate package files")
        for rel in FILES:
            data = archive.read("go_anastruct_2d/" + rel)
            if data != (PACKAGE / rel).read_bytes():
                raise AssertionError("Preview ZIP source parity mismatch: " + rel)
            if rel.endswith(".py"):
                compile(data, "go_anastruct_2d/" + rel, "exec")
    print(f"PASS: {DEST.name}; {len(FILES)} source files; SHA-256 {digest}")


if __name__ == "__main__":
    try:
        main()
    except (AssertionError, OSError, SyntaxError, zipfile.BadZipFile) as exc:
        print("FAIL: Preview verification:", exc, file=sys.stderr)
        raise SystemExit(1)
