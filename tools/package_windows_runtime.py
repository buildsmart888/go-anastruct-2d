"""Package a Windows PyInstaller --onedir worker as the expected offline ZIP.

Run only after worker.exe --check and the JSON protocol smoke test succeed.
Does not compile Windows code; that must happen on Windows x64.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "dist" / "go_anastruct_worker"
TARGET = ROOT / "dist" / "go_anastruct_2d-runtime-windows-x64-v0.5.5.zip"


def main() -> int:
    exe = SOURCE / "go_anastruct_worker.exe"
    inner = SOURCE / "_internal"
    if not exe.is_file() or not inner.is_dir():
        raise RuntimeError(
            "Missing full PyInstaller --onedir output: "
            "both go_anastruct_worker.exe and _internal/ must exist."
        )
    files = sorted((p for p in SOURCE.rglob("*") if p.is_file()), key=lambda p: p.as_posix())
    if len(files) < 3:
        raise RuntimeError("Portable runtime appears incomplete")
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(TARGET, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for file in files:
            rel = file.relative_to(SOURCE).as_posix()
            if ".." in Path(rel).parts or rel.startswith("/"):
                raise RuntimeError(f"Unsafe worker path {rel}")
            archive.write(file, arcname=rel)
    with zipfile.ZipFile(TARGET) as archive:
        if archive.testzip() is not None:
            raise RuntimeError("Portable ZIP failed CRC validation")
        if "go_anastruct_worker.exe" not in archive.namelist():
            raise RuntimeError("Portable ZIP is missing its executable")
    sha = hashlib.sha256(TARGET.read_bytes()).hexdigest()
    Path(str(TARGET) + ".sha256").write_text(sha + "\n", encoding="ascii")
    print(f"PACKAGE OK: {TARGET.name}")
    print(f"FILES: {len(files)}")
    print(f"SHA256: {sha}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, zipfile.BadZipFile) as exc:
        print(f"BUILD PACKAGE FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
