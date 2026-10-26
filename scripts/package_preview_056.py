"""Build an IngeTrazo 0.5.9 v0.5.6-preview plugin ZIP.

This packages only extension source; the Windows anaStruct 1.7.0 portable
worker remains the independently tested v0.5.5 runtime.
"""
from __future__ import annotations

import hashlib
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "go_anastruct_2d"
DEST = ROOT / "dist/go_anastruct_2d-v0.5.6-preview-plugin.zip"
FILES = (
    "COPYING", "__init__.py", "client.py", "constants.py", "diagram_utils.py",
    "editor.py", "examples.py", "exporters.py", "factory_bridge.py",
    "label_layout.py", "load_cases.py", "load_manager.py", "model.py",
    "overlay.py", "picking.py", "repair_runtime.cmd", "runtime.py",
    "sections.py", "toolbar.py", "ui.py", "worker.py",
)


def main():
    DEST.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(DEST, "w", compression=zipfile.ZIP_DEFLATED,
                         compresslevel=9) as archive:
        for rel in FILES:
            source = PACKAGE / rel
            if not source.is_file():
                raise FileNotFoundError(source)
            entry = zipfile.ZipInfo("go_anastruct_2d/" + rel,
                                    date_time=(2026, 10, 26, 12, 0, 0))
            entry.compress_type = zipfile.ZIP_DEFLATED
            entry.create_system = 0
            entry.external_attr = 0
            archive.writestr(entry, source.read_bytes(), compress_type=zipfile.ZIP_DEFLATED,
                             compresslevel=9)
    with zipfile.ZipFile(DEST) as archive:
        assert len(archive.namelist()) == len(FILES)
        assert archive.testzip() is None
        assert all(p.startswith("go_anastruct_2d/") for p in archive.namelist())
        assert "go_anastruct_2d/factory_bridge.py" in archive.namelist()
    digest = hashlib.sha256(DEST.read_bytes()).hexdigest()
    (Path(str(DEST) + ".sha256")).write_text(digest + "\n", encoding="ascii")
    print(f"GO anaStruct v0.5.6-preview: {len(FILES)} files, SHA256 {digest}")
    return DEST


if __name__ == "__main__":
    main()
