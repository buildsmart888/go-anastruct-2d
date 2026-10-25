# Windows installer hardening (review candidate)

This patch updates only the repository-level Windows installer, not the published v0.5.4 plugin ZIP, numerical solver, Python runtime installation routine, or extension source.

## Changes
- Remove the PowerShell `-ExecutionPolicy Bypass` argument from the package reconstruction/hash/extraction commands. These are inline `-Command` invocations and do not require changing execution policy.
- Stop installation if copying the published ZIP fails.
- Stop installation before replacing the extension if backing up an existing installation fails.

## Known limits
- The extension still uses a separate isolated Python runtime and still invokes `repair_runtime.cmd` from the packaged plugin.
- The bundled runtime script has not been audited or modified as part of this patch.
- This patch does **not** provide a Python-free installation, a vendored solver, or a new Windows executable.
- PowerShell and a batch file are still needed for manual repository installs. Windows SmartScreen/Defender behavior is not guaranteed.
- This change does not update the canonical plugin ZIP or its SHA-256.

## Windows acceptance test (required before merge)
1. Download the complete repository ZIP from this branch and extract it.
2. With IngeTrazo closed, run `setup_windows.cmd` on a Windows 10/11 machine.
3. Confirm the v0.5.4 SHA-256 check succeeds and the plugin installs.
4. Reinstall with an existing plugin to confirm a backup is created.
5. Simulate inability to back up and confirm installation stops before plugin overwrite.
6. Simulate a corrupt ZIP and confirm the hash check fails.
7. Open IngeTrazo 0.5.9, run `Check Solver`, then solve the simply supported beam and portal frame presets, checking reactions and N/V/M/deflection against the v0.5.4 baseline.

## Future packaging work
Evaluate a self-contained signed Windows runtime with pinned dependencies and a verified SBOM, while keeping the solver process interface and regression checks stable. Review upstream anaStruct licensing before redistribution.
