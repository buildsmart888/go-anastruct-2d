"""Build and verify a complete Core-integrated IngeTrazo preview plugin ZIP."""
from __future__ import annotations
import hashlib
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "go_anastruct_2d"
OUTPUT = ROOT / "dist/go_anastruct_2d-v0.5.8-preview-plugin.zip"
EXTS = {".py", ".json", ".cmd", ".txt"}
ALLOWED_FILES = {"COPYING"}


def source_files():
    files = [
        p for p in SOURCE.rglob("*")
        if p.is_file() and "__pycache__" not in p.parts
        and (p.suffix in EXTS or p.name in ALLOWED_FILES)
    ]
    names = [p.relative_to(SOURCE).as_posix() for p in files]
    if len(names) != len(set(names)):
        raise AssertionError("Duplicate source paths")
    for required in ("__init__.py", "engineering_core.py", "steel_sections_v1.json"):
        if required not in names:
            raise AssertionError(f"Required Core source missing: {required}")
    return sorted(files, key=lambda p: p.relative_to(SOURCE).as_posix())


def main():
    files = source_files()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(OUTPUT, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for f in files:
            path = "go_anastruct_2d/" + f.relative_to(SOURCE).as_posix()
            entry = zipfile.ZipInfo(path, date_time=(2026, 10, 26, 12, 0, 0))
            entry.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(entry, f.read_bytes(), compress_type=zipfile.ZIP_DEFLATED,
                       compresslevel=9)
    with zipfile.ZipFile(OUTPUT) as z:
        if z.testzip() is not None:
            raise AssertionError("Preview ZIP CRC verification failed")
        for f in files:
            assert z.read("go_anastruct_2d/" + f.relative_to(SOURCE).as_posix()) == f.read_bytes()
    digest = hashlib.sha256(OUTPUT.read_bytes()).hexdigest()
    Path(str(OUTPUT) + ".sha256").write_text(digest + "\n", encoding="ascii")
    print(f"PASS: go_anastruct_2d v0.5.8-preview preview ZIP, {len(files)} files, SHA-256 {digest}")
    return OUTPUT


if __name__ == "__main__":
    main()
