# Windows installer hardening — Windows 0.5.9 manual smoke evidence

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

## Windows acceptance and regression checks
1. Download the complete repository ZIP from this branch and extract it.
2. With IngeTrazo closed, run `setup_windows.cmd` on a Windows 10/11 machine.
3. Confirm the v0.5.4 SHA-256 check succeeds and the plugin installs.
4. Reinstall with an existing plugin to confirm a backup is created.
5. Simulate inability to back up and confirm installation stops before plugin overwrite.
6. Simulate a corrupt ZIP and confirm the hash check fails.
7. Open IngeTrazo 0.5.9, run `Check Solver`, then solve the simply supported beam and portal frame presets, checking reactions and N/V/M/deflection against the v0.5.4 baseline.

## Future packaging work
Evaluate a self-contained signed Windows runtime with pinned dependencies and a verified SBOM, while keeping the solver process interface and regression checks stable. Review upstream anaStruct licensing before redistribution.

## Manual Windows evidence (2026-10-25)

The project author ran GO 2D Structural — anaStruct v0.5.4 within IngeTrazo 0.5.9 on Windows and reported a successful trial. Two screenshots show:

- The `GO 2D anaStruct` panel loaded in IngeTrazo 0.5.9, displaying `Solver ready: anaStruct 1.7.0 OK` and a LocalAppData isolated `python.exe`.
- Preset `10 — Portal Wind + Moment Frame`, load case `DL` and self-weight enabled.
- Rendered member **Deflection** plots with numerical values.
- Rendered **M** bending moment diagram with fills and numerical values.

These are user-provided manual smoke-test results, **not** a machine-verified full numerical acceptance or a clean install audit. Still unconfirmed: package corruption failure, backup failure rollback, CSV/PDF export, full results comparison, UI behavior on a fresh Windows account, and standalone runtime portability.

## CI status

The first GitHub Actions Windows workflow run (https://github.com/buildsmart888/go-anastruct-2d/actions/runs/40209409552) failed before any job steps began (no runner details or usable job logs were available). This is **not** a passing CI test and the exact runner-side cause has not been confirmed. Manual evidence is reported separately from CI.

## Observed UX follow-up

Both screenshots show dense overlapping result and load labels. Tracking separately as a viewport label deconfliction / adaptive density task; no solver change is needed for this cosmetic issue.
