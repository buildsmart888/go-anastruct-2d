"""Run anaStruct in an isolated Python worker; never import it in the IngeTrazo GUI."""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time

from .runtime import runtime_python


class SolverCancelled(RuntimeError):
    pass


def analyze(model: dict, timeout: float = 180.0, cancel=None) -> dict:
    root = Path(__file__).parent
    worker = root / "worker.py"
    python = runtime_python(require_healthy=True)
    source_hash = hashlib.sha256(worker.read_bytes()).hexdigest()
    payload = json.dumps({"protocol": 1, "model": model}, allow_nan=False).encode("utf-8")
    env = os.environ.copy()
    for key in (
        "PYTHONHOME", "PYTHONPATH", "__PYVENV_LAUNCHER__", "_MEIPASS2",
        "_PYI_APPLICATION_HOME_DIR", "_PYI_ARCHIVE_FILE", "_PYI_PARENT_PROCESS_LEVEL",
    ):
        env.pop(key, None)
    if cancel is not None and cancel.is_set():
        raise SolverCancelled("Analysis cancelled")
    with tempfile.TemporaryFile() as inp, tempfile.TemporaryFile() as out, tempfile.TemporaryFile() as err:
        inp.write(payload)
        inp.seek(0)
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        # Run the worker as a package module. With -I Python intentionally
        # omits the current directory, so add only the plugin parent explicitly.
        # This preserves relative imports such as ``from .constants import ...``.
        package_parent = str(root.parent)
        bootstrap = (
            "import runpy,sys;"
            f"sys.path.insert(0,{package_parent!r});"
            "runpy.run_module('go_anastruct_2d.worker',run_name='__main__')"
        )
        proc = subprocess.Popen(
            [python, "-I", "-X", "utf8", "-c", bootstrap],
            stdin=inp, stdout=out, stderr=err, env=env, creationflags=flags,
        )
        started = time.monotonic()
        try:
            while proc.poll() is None:
                if cancel is not None and cancel.is_set():
                    proc.kill()
                    raise SolverCancelled("Analysis cancelled")
                if time.monotonic() - started > timeout:
                    proc.kill()
                    raise RuntimeError(f"anaStruct solver timeout after {timeout:.0f}s")
                time.sleep(0.02)
        finally:
            try:
                proc.wait(timeout=5)
            except Exception:
                pass
        out.seek(0)
        stdout = out.read(64 * 1024 * 1024).decode("utf-8", "replace")
        err.seek(0)
        stderr = err.read(8192).decode("utf-8", "replace")
    try:
        reply = json.loads(stdout)
    except ValueError as exc:
        raise RuntimeError("Invalid anaStruct worker JSON: " + stderr[-2000:]) from exc
    if reply.get("protocol") != 1:
        raise RuntimeError("anaStruct worker protocol mismatch")
    if not reply.get("ok"):
        message = str((reply.get("error") or {}).get("message", "anaStruct solver failed"))
        if "No module named 'anastruct'" in message or "anastruct" in stderr.lower() and "module" in stderr.lower():
            message += "\nSolver dependency is missing. Use Install / Repair Solver."
        raise RuntimeError(message)
    if hashlib.sha256(worker.read_bytes()).hexdigest() != source_hash:
        raise RuntimeError("anaStruct worker changed during analysis; result discarded")
    result = reply["result"]
    result["worker_sha256"] = source_hash
    result["worker_path"] = str(worker)
    result["worker_runtime_path"] = python
    return result
