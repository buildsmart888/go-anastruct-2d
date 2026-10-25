# Installation — Windows / IngeTrazo 0.5.9

## GO 2D anaStruct v0.5.5 (PREVIEW candidate)

1. Download the **complete** author-repository ZIP from the v0.5.5 feature branch and extract all files.
2. Close IngeTrazo 0.5.9 fully.
3. Double-click `setup_windows.cmd`. It delegates to `install_windows.cmd`.
4. The Windows installer checks `dist/go_anastruct_2d-v0.5.5-plugin.zip` against its `.sha256` file. A mismatched or incomplete package **stops installation**.
5. Existing plugin files are backed up under `%LOCALAPPDATA%\GO anaStruct 2D\backup\` before replacing the plugin.
6. Files are installed to `%APPDATA%\ingetrazo\plugins\go_anastruct_2d\`.
7. The installer checks for an optional prebuilt solver EXE. If no verified EXE is present, it uses the existing isolated Python runtime and can create one through Windows Python 3.10–3.13 with internet access.
8. Reopen IngeTrazo and use the **GO 2D toolbar** or the **Extensions** menu. Select `GO 2D anaStruct` > **Check Solver**.
9. Load a simply supported beam; click **Run Analysis**; then test the 3-storey portal, switching N/V/M/Deflection/Reaction.
10. Complete `docs/V055_WINDOWS_QA.md` before declaring v0.5.5 ready for users.

### Standalone worker EXE

The executable is an **optional** distribution artifact; it is **not** inside the Community extension ZIP. The maintainer build scripts are `scripts/build_windows_portable.ps1` and `tools/smoke_portable.py`. No Python-free installation is claimed until a trusted Windows EXE has been built and tested.

### Uninstall

Run `uninstall_windows.cmd`, restart IngeTrazo. Existing external Python or portable runtimes in LocalAppData may remain and can be removed separately once no longer needed.

### Diagnostics

- Missing plugin: confirm the single top-level package folder and `__init__.py`.
- Solver not ready: **Install / Repair Solver**, then **Check Solver**.
- Label clutter: enable **Auto layout**, lower **Labels/member**, toggle off load labels, zoom in, or hover a member.
- Workspace says "Not Analyzed": this is a separate host status; read **anaStruct: Analyzed (current)** in the GO panel.
- Engineering results are experimental: review equilibrium and independent reference checks.

Original Windows screenshots were of v0.5.4; v0.5.5 GUI QA is pending.
