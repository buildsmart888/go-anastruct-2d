"""Runtime discovery, health checking and repair for the isolated anaStruct solver."""
from __future__ import annotations
import json
import os
from pathlib import Path
import subprocess

from .constants import SOLVER_VERSION

PLUGIN_ROOT = Path(__file__).resolve().parent
LOCALAPPDATA = Path(os.environ.get("LOCALAPPDATA") or (Path.home() / "AppData" / "Local"))
RUNTIME_HOME = LOCALAPPDATA / "GO anaStruct 2D"
RUNTIME_ROOT = RUNTIME_HOME / "solver-v0.4"
PLUGIN_CONFIG = PLUGIN_ROOT / "worker_config.json"
SHARED_CONFIG = RUNTIME_HOME / "worker_config.json"
DEFAULT_PYTHON = RUNTIME_ROOT / "Scripts" / "python.exe"
REPAIR_SCRIPT = PLUGIN_ROOT / "repair_runtime.cmd"


def _config_python(path: Path):
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError, TypeError):
        return None
    value = data.get("python") if isinstance(data, dict) else None
    return Path(value) if isinstance(value, str) and value.strip() else None


def candidate_pythons():
    seen = set()
    for path in (PLUGIN_CONFIG, SHARED_CONFIG):
        candidate = _config_python(path)
        if candidate is not None:
            key = str(candidate).lower()
            if key not in seen:
                seen.add(key)
                yield candidate, str(path)
    key = str(DEFAULT_PYTHON).lower()
    if key not in seen:
        yield DEFAULT_PYTHON, "standard runtime path"


def probe_python(python: Path, timeout: float = 12.0):
    if not python.is_file():
        return False, f"Python not found: {python}"
    code = (
        "import importlib.metadata as m; "
        f"assert m.version('anastruct')=='{SOLVER_VERSION}', m.version('anastruct'); "
        "from anastruct import SystemElements; "
        "print('anaStruct '+m.version('anastruct')+' OK')"
    )
    try:
        proc = subprocess.run(
            [str(python), "-I", "-X", "utf8", "-c", code],
            capture_output=True,
            text=True,
            timeout=timeout,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return False, f"Runtime probe failed: {exc}"
    if proc.returncode == 0:
        return True, (proc.stdout.strip() or f"anaStruct {SOLVER_VERSION} OK")
    detail = (proc.stderr or proc.stdout or "health check failed").strip().splitlines()
    return False, detail[-1] if detail else "health check failed"


def runtime_status(probe: bool = True):
    checked = []
    for python, source in candidate_pythons():
        exists = python.is_file()
        row = {"python": str(python), "source": source, "exists": exists}
        if exists and probe:
            healthy, message = probe_python(python)
            row.update(healthy=healthy, message=message)
            if healthy:
                return {"ready": True, "python": str(python), "source": source, "message": message, "checked": checked + [row]}
        elif exists:
            row.update(healthy=None, message="Python found; not probed")
            return {"ready": True, "python": str(python), "source": source, "message": row["message"], "checked": checked + [row]}
        checked.append(row)
    return {
        "ready": False,
        "python": None,
        "source": None,
        "message": "anaStruct solver runtime is missing or unhealthy",
        "checked": checked,
    }


def runtime_python(require_healthy: bool = False) -> str:
    status = runtime_status(probe=require_healthy)
    if status["ready"] and status.get("python"):
        return status["python"]
    paths = "\n".join(f"- {row['python']} ({row['source']})" for row in status["checked"])
    raise RuntimeError(
        "anaStruct solver runtime is not ready. Use Install / Repair Solver.\n"
        + (paths or f"Expected: {DEFAULT_PYTHON}")
    )


def diagnostic_text(status=None):
    status = status or runtime_status(probe=True)
    if status.get("ready"):
        return f"Solver ready: {status['message']}\n{status['python']}"
    lines = ["Solver NOT ready.", f"Expected anaStruct {SOLVER_VERSION}."]
    for row in status.get("checked", []):
        state = row.get("message") or ("found" if row.get("exists") else "missing")
        lines.append(f"{row['source']}: {row['python']} — {state}")
    lines.append("Use Install / Repair Solver, then Check Solver.")
    return "\n".join(lines)


def repair_runtime(timeout: float = 900.0):
    if os.name != "nt":
        raise RuntimeError("Automatic solver repair is currently supported on Windows only")
    if not REPAIR_SCRIPT.is_file():
        raise RuntimeError(f"Repair script missing: {REPAIR_SCRIPT}")
    proc = subprocess.run(
        ["cmd.exe", "/d", "/c", str(REPAIR_SCRIPT)],
        capture_output=True,
        text=True,
        timeout=timeout,
        cwd=str(PLUGIN_ROOT),
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    output = "\n".join(v.strip() for v in (proc.stdout, proc.stderr) if v and v.strip())
    if proc.returncode != 0:
        raise RuntimeError(output[-5000:] or f"Repair failed with exit code {proc.returncode}")
    status = runtime_status(probe=True)
    if not status["ready"]:
        raise RuntimeError(diagnostic_text(status))
    return status, output
