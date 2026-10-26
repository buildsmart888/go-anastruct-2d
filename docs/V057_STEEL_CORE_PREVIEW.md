# GO anaStruct v0.5.7-preview — Shared Steel Core integration

**Draft for IngeTrazo 0.5.9 Windows testing. Not design-approved.**

Depends on the v0.5.6-preview Gable overlay introduced in PR #10 and the
previously validated anaStruct 1.7.0 solver/worker. No worker protocol or
numerical solver changes were made in this branch.

## What's added

- Identical GO Engineering Core v0.1 JSON snapshot and pure-Python nominal
  section property calculator as in GO Factory v0.3.2-preview.
- On **Create Analysis from GO Factory**, H/WF and supported tube profiles
  offer an explicit STRONG/WEAK in-plane axis selection and a second
  acknowledgement before generating numerical A and Iz. No automatic RC
  substitution for steel members. The properties are **unverified nominal**
  values until checked by a qualified engineer.
- GO Factory catalog version/SHA-256 consistency is checked when present
  in the member metadata; legacy untagged Factory models can still import
  but carry a source warning.
- Buttons directly in the Factory dock for Sections / Materials, Point / Line
  Loads, Member Releases and Load Combinations, backed by the existing
  ModelEditor and LoadCaseCombinationDialog.
- End release_i/release_j now use an actual checkbox: checked means a
  rotational hinge (zero end moment), unchecked means continuous connection.
  The existing numerical worker honors these booleans unchanged.
- Changing base support **Fixed ↔ Pin** updates stored FEM model and marks
  previous results stale; the UI is synchronized from saved nodes.
- Same-topology/equivalent-geometry Factory re-import and station changes
  preserve manually edited loads, combinations, materials, sections, and
  end releases. Different geometry requires confirmation before replacing
  those edits.

## What is still NOT complete

- Source catalog H/RHS/PIPE properties use idealized nominal dimensions
  with NO radii/tolerances/manufacturer validation. Treat as DEMO only.
- C/Z channels, angles and other families remain for 3D/BOQ identification
  but cannot be converted into a reliable FEM section without additional
  verified data.
- Global buckling, local buckling, bending resistance, 3D torsion, design
  codes/strength checks and certified section capacity are NOT implemented.
- Factory metadata centerline alignment does not prove manually edited
  3D solids still coincide; verify visually.
- PDF/CSV existing report generators remain, but manufacturer property
  citations are NOT automatically generated.
- Shared source is currently vendored in two plugin repositories and needs
  a single separately managed library/repository before broader expansion.

## Windows test procedure

1. Close IngeTrazo 0.5.9.
2. Download complete GO Factory branch `feat/go-core-v01-steel-catalog`, extract
   the repository and run `install_preview_032_windows.cmd` beside its ZIP.
3. Download complete GO anaStruct branch `feat/v057-go-steel-catalog`, extract
   the repository and run `install_preview_057_windows.cmd`.
   The existing v0.5.5 worker/venv can be reused. Do NOT run the v0.5.5
   installer afterwards because that would downgrade the plugin.
4. Restart IngeTrazo. Build Factory 01, 18×36 m / Gable / Portal / eave 6 m /
   rise 2.5 m / bays 6.
5. In GO anaStruct, click Create Analysis from GO Factory; explicitly choose
   H-300x300x10x15 and WF-300x150 strong/weak axis and acknowledge preview.
6. Open Sections and confirm A/Iz carry a GOCORE section ID, family Steel,
   nominal/unverified status, and match the selected bending axis.
7. Compare Pin vs Fixed: after switching, old results MUST be stale and
   Pin support should not return a genuine rotational restraint moment.
8. Edit one distributed load, one point load, an ULS combination factor and
   member release_i/release_j; reanalyze and verify balance.
9. Switch from Y=0 to Y=12 with equivalent member geometry: verify edited
   loads, releases and combinations were not reset and result freshness
   remains valid if FEM inputs did not change.
10. Save/reopen .igz; check the entire model, section mappings, results,
    viewport labels, 3D overlay, and CSV/PDF exports.

Build QA: run `RUN_GO_CORE_057_TESTS_WINDOWS.cmd` from the feature branch
folder. If its optional previously compiled worker is absent, the script
reports that numerical worker tests remain pending, even if it packages
a ZIP.

**Do not merge PRs, publish a GitHub Release, or use structural output to
approve a real project until numerical and UI checks pass on Windows.**
