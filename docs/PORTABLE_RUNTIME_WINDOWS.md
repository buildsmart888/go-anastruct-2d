# Optional offline Windows portable solver (v0.5.5 candidate)

**Status: installer integration candidate; NOT a released Python-free distribution.**

For IngeTrazo 0.5.9 on Windows 10/11 x64, the portable solver is a separate
build artifact, not included in the small Community extension ZIP. The solver
still uses Python internally; it is **bundled**, so end users do not need to
install system Python when the verified binary distribution is present.

## Build on a trusted Windows x64 machine

1. Use pinned Python 3.11 and the repository build script
   `scripts/build_windows_portable.ps1`.
2. Run `tools/smoke_portable.py` and verify test output for the protocol and
   sample equilibrium checks.
3. Inspect and license-review the compiled distribution, including bundled
   anaStruct / NumPy dependencies, before shipping it.
4. Place BOTH generated files beside the installer under `dist/`:
   - `go_anastruct_2d-runtime-windows-x64-v0.5.5.zip`
   - `go_anastruct_2d-runtime-windows-x64-v0.5.5.zip.sha256`
5. Publish the trusted SHA-256 independently of the downloaded files. A checksum
   stored beside a ZIP checks consistency, **not publisher authenticity**.

## Install on Windows x64 without a system Python installation

1. Download a complete, trusted distribution containing the two runtime files,
   the v0.5.5 plugin ZIP and its manifest, and the installer scripts.
2. Close IngeTrazo.
3. Run `setup_windows.cmd` from the distribution root.
4. The installer validates the plugin and optional runtime ZIPs, unpacks the
   runtime to a staging directory, executes `go_anastruct_worker.exe --check`,
   moves any previous runtime aside and promotes the staged runtime. If the
   upgrade fails, it attempts to restore the previous runtime.
5. Reopen IngeTrazo 0.5.9, select **Check Solver**, and run beam/portal examples.
   Confirm N/V/M/deflection, reactions, CSV and PDF exports.

The offline runtime path does not require administrative privileges,
PowerShell execution-policy overrides, Defender exclusions or network calls.

## Missing files / fallback

If the runtime ZIP is absent, the existing installer continues with its isolated
Python virtual-environment fallback, which may require a system Python
installation and network access. If the portable ZIP is present but its manifest
is missing, or its checksum fails, the installer **stops** instead of silently
downgrading to an unverified runtime.

**Do not advertise a Python-free release until a real clean Windows installation
with the compiled runtime and IngeTrazo 0.5.9 has passed QA.**
