"""Clean-profile installer acceptance on Windows x64, using an already built worker.

Uses a fresh APPDATA/LOCALAPPDATA under RUNNER_TEMP and does not alter a
real user's plugin installation. A proper IngeTrazo GUI test is still manual.
"""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
ZIP = ROOT / "dist/go_anastruct_2d-runtime-windows-x64-v0.5.5.zip"
SHA = Path(str(ZIP) + ".sha256")
INSTALLER = ROOT / "install_windows.cmd"
PACKAGE = "go_anastruct_2d"


def run(argv, env, timeout=240):
    result = subprocess.run(argv, cwd=ROOT, env=env, capture_output=True,
                            text=True, errors="replace", timeout=timeout)
    if result.returncode:
        raise RuntimeError(f"EXIT={result.returncode}\n{result.stdout[-5000:]}\n{result.stderr[-5000:]}")
    return result


def main():
    if os.name != "nt":
        raise RuntimeError("Clean-profile installer test requires Windows")
    if not ZIP.is_file() or not SHA.is_file():
        raise FileNotFoundError("Missing portable worker ZIP/manifest")
    digest = hashlib.sha256(ZIP.read_bytes()).hexdigest()
    if digest != SHA.read_text(encoding="ascii").strip().lower():
        raise AssertionError("Portable ZIP hash mismatch")
    with tempfile.TemporaryDirectory(prefix="go-v055-clean-install-") as td:
        root = Path(td)
        env = dict(os.environ)
        env["APPDATA"] = str(root / "Roaming")
        env["LOCALAPPDATA"] = str(root / "Local")
        env["TEMP"] = str(root / "Temp")
        env["TMP"] = env["TEMP"]
        for name in ("APPDATA", "LOCALAPPDATA", "TEMP"):
            Path(env[name]).mkdir(parents=True)
        # setup/install CMD has a pause at the end. Feed an enter for its final prompt.
        proc = subprocess.run(["cmd.exe", "/d", "/c", str(INSTALLER)],
                              input="\n", cwd=ROOT, env=env,
                              capture_output=True, text=True,
                              errors="replace", timeout=360)
        if proc.returncode:
            raise RuntimeError(f"Clean install failed {proc.returncode}\n{proc.stdout[-5000:]}\n{proc.stderr[-5000:]}")
        plugin = Path(env["APPDATA"]) / "ingetrazo/plugins" / PACKAGE
        exe = Path(env["LOCALAPPDATA"]) / "GO anaStruct 2D/portable-v0.5.5/go_anastruct_worker.exe"
        if not (plugin / "__init__.py").is_file():
            raise AssertionError("Plugin was not installed")
        if not exe.is_file():
            raise AssertionError("Self-contained worker was not installed")
        check = run([str(exe), "--check"], env=env, timeout=60)
        if "anaStruct 1.7.0 OK" not in check.stdout:
            raise AssertionError("Solver health check did not pass")
        plugin_home = str(plugin.parent)
        bootstrap = (
            "import sys,json;"
            "sys.path.insert(0,sys.argv[1]);"
            "from go_anastruct_2d.runtime import runtime_status;"
            "s=runtime_status(probe=True);"
            "assert s['ready'] and s.get('worker_exe'),s;"
            "print(json.dumps(s))"
        )
        status = run([sys.executable, "-I", "-X", "utf8", "-c", bootstrap,
                      plugin_home], env=env)
        print("PASS: isolated clean install, plugin, portable runtime selected")
        print(status.stdout[-1000:])
        # Corruption rejection: a modified runtime artifact MUST not overwrite an
        # already verified installation.
        original = ZIP.read_bytes()
        try:
            ZIP.write_bytes(original + b"integrity-test-tamper")
            bad = subprocess.run(["cmd.exe", "/d", "/c", str(ROOT / "install_portable_runtime.cmd")],
                                 cwd=ROOT, env=env, capture_output=True,
                                 text=True, errors="replace", timeout=120)
            if bad.returncode == 0:
                raise AssertionError("Installer accepted corrupted ZIP")
            if not exe.is_file():
                raise AssertionError("Previously installed worker was lost after tamper rejection")
            run([str(exe), "--check"], env=env, timeout=60)
        finally:
            ZIP.write_bytes(original)
        print("PASS: corrupted archive rejected; existing worker preserved")


if __name__ == "__main__":
    main()
