# GO anaStruct 2D — self-contained Windows runtime (v0.5.5 candidate)

**Target:** Windows 10/11 x64 with IngeTrazo 0.5.9.

## Architecture
The GUI continues to use the existing isolated JSON worker protocol.
When available, `go_anastruct_worker.exe` includes Python, NumPy, anaStruct
1.7.0 and its compiled dependencies. The end user does **not** need
to install a system Python to run this EXE. The program still uses Python
internally; this is not a Rust/native anaStruct rewrite.

## Windows build (maintainer/CI only)

From this repository on Windows x64, with Python 3.11 installed:

```powershell
./scripts/build_windows_portable.ps1
python tools/smoke_portable.py
```

The build produces `dist/go_anastruct_2d-runtime-windows-x64-v0.5.5.zip`
and its SHA-256 file. The CI workflow must pass before a runtime is
distributed to end users. An unsigned test EXE may trigger SmartScreen;
do not suppress Microsoft Defender or bypass safety controls.

## Install a **verified** runtime archive on Windows

1. Obtain the built archive **from the project release or a trusted CI artifact**,
   with its matching published SHA-256.
2. Verify the hash against the exact ZIP before extracting it.
3. Close IngeTrazo. Extract the contents of the ZIP directly to:

   `%LOCALAPPDATA%\GO anaStruct 2D\portable-v0.5.5\`

4. The path must contain `go_anastruct_worker.exe` and its `_internal`
   runtime directory; do not copy the EXE alone.
5. Restart IngeTrazo 0.5.9, open GO anaStruct, and click `Check Solver`.
   It should show a ready **portable Windows worker**, not a venv Python path.
6. Load the simple beam and portal examples. Verify results and exported reports.

If no verified portable worker is installed, GO anaStruct continues using
the existing isolated Python 3.10-3.13 virtual environment fallback.

## Security and release policy

- Do not claim a Python-free download until the portable ZIP has been built
  and tested on a clean Windows PC.
- No arbitrary downloaded script execution or ExecutionPolicy Bypass.
- Publish the runtime archive and SHA-256 together, with dependency/source
  notices. The code and bundled dependencies remain subject to upstream
  license obligations (including GPL).
- The IngeTrazo **Community extension ZIP** includes Python plugin code only.
  The large portable solver runtime is a separate release asset.
- Verify numerical results independently for professional engineering use.

## Acceptance criteria

- EXE `--check` returns anaStruct 1.7.0 OK
- JSON worker protocol 1 solves beam and portal with equilibrium checks
- N/V/M/Deflection/Reaction and case-combination results match v0.5.4 within tolerance
- No system Python needed when the portable EXE is installed
- Package installs, uninstalls and repairs without elevated permissions
- Report CSV/PDF generation and recovery from timeout/cancel checked in GUI
- Source/code notices and executable binary hashes published
