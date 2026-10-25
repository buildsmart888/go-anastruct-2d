"""Windows smoke test for portable anaStruct worker -- no system Python subprocess."""
import json
import subprocess
from pathlib import Path

from go_anastruct_2d.examples import EXAMPLES


def main():
    exe = Path("dist/go_anastruct_worker/go_anastruct_worker.exe")
    assert exe.is_file(), str(exe)
    check = subprocess.run([str(exe), "--check"], capture_output=True, text=True, timeout=30)
    assert check.returncode == 0, check.stderr
    assert "anaStruct 1.7.0 OK" in check.stdout
    name = next(iter(EXAMPLES))
    model = EXAMPLES[name]()
    request = json.dumps({"protocol": 1, "model": model}, allow_nan=False)
    proc = subprocess.run(
        [str(exe)], input=request, capture_output=True, text=True, timeout=180
    )
    assert proc.returncode == 0, proc.stderr[-2500:]
    reply = json.loads(proc.stdout)
    assert reply.get("ok") is True, reply
    cases = reply["result"]["cases"]
    assert cases, "No load cases solved"
    for case, data in cases.items():
        if not data.get("empty_load_case"):
            assert data["equilibrium"]["passed"], case
            assert data["equilibrium"]["load_mapping_passed"], case
    print(f"Windows portable anaStruct smoke PASS: {name}, cases={list(cases)}")


if __name__ == "__main__":
    main()
