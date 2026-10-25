# v0.5.5 Windows 0.5.9 QA checklist

**Status: release candidate — not yet certified.**

## Issues addressed by code

- #5: screen-space collision-aware label drawing, new Auto layout toggle,
  configurable samples/member; hover and solver result arrays unchanged.
- #7: extension-owned `anaStruct: Analyzed / Stale / Running` status,
  explicitly distinct from the host GO Structural Workspace status badge.
- #6: optional portable Windows solver EXE support, build script and workflow.
  **Portable artifact is pending successful Windows CI/clean-machine testing.**

## Manual acceptance to check before merging/releasing

- [ ] Clean install from v0.5.5 ZIP on IngeTrazo 0.5.9 Windows x64
- [ ] GO 2D toolbar icon appears; Show/Analyze actions work and no duplicate toolbar after restart
- [ ] Re-run sample 8: Portal 3 Storey 3 Bay, DL and SLS; compare N/V/M/D and reactions to v0.5.4
- [ ] Auto layout makes values readable in Model, N, V, M, Deflection, Reaction
- [ ] Toggling auto layout off still shows raw labels when deliberately requested
- [ ] Hover retains full unrounded force results despite suppressed display labels
- [ ] Changing loads/geometry marks anaStruct results stale; cancelled analysis never says analyzed
- [ ] Host workspace badge remains clearly independent unless officially integrated
- [ ] CSV and selected/all-case PDF export verified
- [ ] Self-contained worker runtime `--check` and numerical protocol pass without system Python
- [ ] Installer backup/rollback and SHA failure cases verified
- [ ] GPL notices and distribution obligations reviewed
- [ ] Exact community ZIP verified: one top-level package, `__init__.py`, sha256

## Screenshot provenance

Images supplied by the project author on 2026-10-25, from Windows/IngeTrazo
0.5.9, represent **v0.5.4 before label layout changes**. They are
before-improvement reference examples, not proof that v0.5.5 has been tested.

## Screenshot gallery status

A compact composite of four authentic v0.5.4 screenshots is committed to
`screenshots/windows_059_v054_portal_gallery.jpg` for the source project;
`screenshots/go_anastruct_2d.jpg` is used as a preview in the catalog fork.
The nine full-resolution originals are not yet committed individually.
These images are baseline references only and do not substitute for a new
v0.5.5 GUI acceptance capture.
