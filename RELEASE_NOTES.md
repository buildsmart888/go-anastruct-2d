# Release notes

## v0.5.5 — Community Preview Candidate (2026-10-25)

**Not yet a validated Windows release.** Full IngeTrazo 0.5.9 acceptance and portable EXE build are pending.

### Added
- Screen-space label placement with collision avoidance and automatic readability controls.
- New **Auto layout** checkbox and reduced default diagram labels per member.
- A dedicated GO 2D toolbar with icon, show panel, and Analyze command.
- An extension-specific analysis status indicator: Not analyzed, Analyzing, Analyzed (current), Stale, Failed/Cancelled.
- Optional portable Windows solver EXE discovery/worker invocation, with isolated Python fallback.
- Windows worker build and smoke-test scripts, editable source tree and documentation.
- Illustrated SVG examples for portal model and bending diagram.

### Changed
- Windows installer validates the v0.5.5 ZIP SHA-256, backs up previous extension, and does not override PowerShell execution policy.
- Canvas annotations are presentation-only: anaStruct 1.7.0 calculation methods and result cache are unchanged.

### Verification
- Candidate ZIP downloaded and independently re-parsed: 20 files, one package folder, correct ZIP central directory and SHA-256 `3083ae4bd759b941965afff339ba2f91e62fbfeb4671b0b5e56350042887e8ae`.
- Windows GUI screenshots correspond to v0.5.4, not v0.5.5.
- Windows CI runner did not execute any steps, so no passing runtime build or headless test can be claimed.

## v0.5.4 — Community Preview

See the verified archive `dist/go_anastruct_2d-v0.5.4-plugin.zip`. The author manually tested anaStruct 1.7.0 Solver OK and displayed N/V/M/Deflection/Reaction on IngeTrazo 0.5.9 for Windows.
