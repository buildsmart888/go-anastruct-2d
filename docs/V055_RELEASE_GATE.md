# GO anaStruct v0.5.5 — Release Gate (Windows x64)

**Status: NOT RELEASE-APPROVED.** Target host: IngeTrazo v0.5.9, Windows 10 and Windows 11.

## Automated acceptance (GitHub-hosted Windows)

The draft workflow `.github/workflows/build-windows-portable-worker.yml` performs:
1. Build pinned Python 3.11 + anaStruct 1.7.0 + NumPy/PyInstaller on Windows x64 with `--onedir`.
2. Smoke-test worker binary `--check` and worker JSON protocol 1.
3. Compare the exact published **v0.5.4** plugin ZIP against the exact **v0.5.5** candidate plugin ZIP and portable EXE on four identical models: simply supported beam, portal, irregular 3-storey/3-bay portal, wind + moment frame.
4. Verify node displacements, 6-DOF reaction components, member N/V/M/deflection curves and end forces, extrema and equilibrium. The 6 m LL beam also checks Rz=+30 kN at each support and |Mmax|=45 kN-m.
5. Stage a clean %APPDATA% and %LOCALAPPDATA% plugin profile, run the official project's installer, verify the compiled runtime was selected, then confirm ZIP tampering fails closed without deleting the working solver.
6. Upload a **test artifact only** plus numerical-regression JSON; not a public Release.

The archive test verifies SHA256 but the paired checksum must be checked against an independently authenticated published value before real-world redistribution. Automated test tolerance: absolute 1e-6 and relative 1e-5 for baseline comparisons; beam analytical check has its own tolerance. Do not relax tolerances silently.

## Manual acceptance — mandatory

| Test | Windows 10 x64 | Windows 11 x64 |
| --- | --- | --- |
| Fresh local profile with no Python installed | Pending | Pending |
| Official IngeTrazo 0.5.9 install/launch | Pending | Pending |
| Extension toolbar / panel / import / Check Solver | Pending | Pending |
| Beam 6 m, q=-10 kN/m, N/V/M/D, Rz~30 kN per support | Pending | Pending |
| Portal 3 Storey 3 Bay: DL/LL/WL, SLS/ULS | Pending | Pending |
| N/V/M/D graphics + labels/hover and model updates | Pending | Pending |
| CSV and selected/all-case PDF export | Pending | Pending |
| Cancel / timeout / corrupted archive rejection | Pending | Pending |
| Upgrade / rollback / uninstall without admin access | Pending | Pending |
| Bundled dependency licenses and Windows file-signing/security review | Pending | Pending |

**Do not mark these tests passed without recorded evidence.** For each manual case attach logs, images from the actual version, OS build, IngeTrazo version, solver ZIP SHA-256 and test report. A runner's test does not prove real desktop UI performance.

### Local Windows execution (developer)

```powershell
python --version
./scripts/build_windows_portable.ps1
python tools/smoke_portable.py
python tools/numerical_regression.py --portable-exe dist/go_anastruct_worker/go_anastruct_worker.exe
python tools/clean_install_windows.py
```

Build produces `dist/go_anastruct_2d-runtime-windows-x64-v0.5.5.zip` plus paired checksum; **not** a public release. Run all commands on a controlled Windows x64 development or CI machine.

### CI limitations and blockers

Historically the Actions jobs failed with empty steps and no runner assignment. A red job in that state is **not evidence of a numerical regression**. Inspect the Actions page for billing/runner availability, repository Actions policy and workflow log errors. If GitHub-hosted runner execution is unavailable, run the commands on an authorized Windows workstation and attach test output. A standalone Windows EXE cannot be built and certified in a Linux-only environment.

## Distribution rule

Only release after both Windows versions and the numerical comparisons pass, with confirmed SHA256, file manifest, applicable GPL/source notices and trusted download origin. Keep PRs #8/#9 as drafts until all mandatory checks are verified.
