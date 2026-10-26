# GO anaStruct 2D v0.5.6-preview — GO Factory Gable Integration

**Preview only. Not engineering design approval or a public Release.**

Host: IngeTrazo 0.5.9 / Extension API v2. Solver stays anaStruct 1.7.0 in the existing separately tested v0.5.5 Portable EXE.

## Reference GO Factory scene

Generate Factory 01 using GO Factory Generator v0.3.1:

- Factory width X=18 m; factory length Y=36 m
- Gable / Portal Frame; eave Z=6 m; roof rise 2.5 m; ridge Z=8.5 m
- Six bays of 6 m, creating frames at Y=0, 6, 12, 18, 24, 30 and 36 m
- Standard columns, rafters, purlins, girts and bracing as needed

GO Factory stores project, category, mark, section and world-space
start/end endpoints under the group.ext metadata namespace
named go_factory_generator. The adapter reads Columns and Rafters;
it does not edit the 3D steel model.

## What to test

1. Use example selector: **11 — Gable Frame from GO Factory**.
2. Without GO Factory installed, Load example works standalone with DEMO loads.
3. With Factory 01 in the scene, click **Create Analysis from GO Factory**.
4. Section names in GO Factory are NOT authoritative analytical A/Iz.
   Select an explicit sample analysis section in the mapping dialogs.
   Verify steel properties and support conditions independently before any
   engineering design use.
5. Use the station selector Y=0 and Y=12 to move centerlines, supports,
   DL/LL/WL arrows, reaction, N/V/M, deflection and deformed shape to
   the matching factory frame.
6. Changing only the frame display station does not rerun analysis when
   geometric model and loads are identical. Geometry/section changes
   invalidate existing FEM results.
7. Toggle Show analytical overlay and GO Factory alignment markers;
   verify picking, hover, orbit, zoom, save/reopen and PDF/CSV.

## Known constraints

- Only a planar portal frame with **exactly two columns and two rafters**.
  Center-column frames, trusses, hip/cross-gable and segmented roofs are
  intentionally rejected with an explanation.
- GO Factory metadata is the authoritative centerline source. Moving steel
  independently after generation can leave metadata stale.
- The supplied loads, selected analytical starter sections, E/A/Iz and
  restraint choices are DEMO assumptions, not a verified design.
- This is a 2D transverse solver, not 3D analysis of purlins/bracing.
- No real IngeTrazo 0.5.9 GUI run has been performed in this authoring
  environment; Windows acceptance is explicitly PENDING.

## Windows test and preview package

From the downloaded source branch folder, using the Python 3.11
environment and built worker from the accepted v0.5.5 development
folder, run RUN_GABLE_PREVIEW_TESTS_WINDOWS.cmd.

That checks source compilation, unit tests for geometry and picking,
standalone/imported Gable FEM using the existing worker, legacy
v0.5.4-v0.5.5 regression and then generates:

- dist/go_anastruct_2d-v0.5.6-preview-plugin.zip
- dist/go_anastruct_2d-v0.5.6-preview-plugin.zip.sha256

Close IngeTrazo and run install_preview_056_windows.cmd from the
same folder to back up and install the Preview ZIP.

If the branch ZIP has been extracted to a new folder rather than the
original development folder, copy the previously verified
dist/go_anastruct_worker directory into this new project's dist and
the original .local-build/python311 environment may need to be reused
from its existing folder because venv paths are not always relocatable.
Alternatively build the runtime on the new folder first.

## Mandatory manual acceptance (all pending)

| Check | Win10 | Win11 |
|---|---|---|
| Preview extension discovered in IngeTrazo 0.5.9 | Pending | Pending |
| GO Factory 0.3.1 generates Factory 01 | Pending | Pending |
| Standalone Example 11 analyzes and overlays at Y=0 | Pending | Pending |
| Metadata import at Y=0 matches physical steel endpoints | Pending | Pending |
| Frame switch to Y=12 remains aligned | Pending | Pending |
| N/V/M/Deflection/Reaction, supports, loads and ID labels | Pending | Pending |
| Picking/hover, orbit/zoom, save/reopen, CSV/PDF | Pending | Pending |
| Missing/incompatible metadata and section warnings | Pending | Pending |

Do not merge, distribute as verified, or publish to the Community catalog
until these checks and the third-party license review have passed.
