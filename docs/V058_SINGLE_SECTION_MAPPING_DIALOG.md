# GO anaStruct 2D v0.5.8-preview — Single Steel Section Review

**Target:** IngeTrazo 0.5.9 / GO Factory v0.3.2-preview.
**Source branch:** feat/v058-section-mapping-one-dialog. **Not released.**

## Why the popup changed

v0.5.7-preview displayed one selection and a second Yes/No confirmation for
*each* factory section. Rejecting one section canceled the complete import.
This was functional but confusing and repetitive for H/WF column + rafter.

The new dialog shows all required factory steel section IDs in **one table**:

- Factory section
- Analysis mapping + STRONG / WEAK axis
- Preview section A (m2)
- Preview in-plane Iz (m4)
- Explicit NOMINAL/UNVERIFIED or MANUAL SUBSTITUTE status

A single checkbox confirms that results are preliminary/nominal; press
**Apply Sections & Continue** once. Cancel changes neither Factory geometry
nor the currently loaded anaStruct model, loads, releases or results.

Existing saved acknowledged mappings are reused on subsequent frame changes
without reopening the dialog. Unsupported sections (C/Z/L, etc.) do not offer
a fabricated nominal FEM formula; manual substitutions are limited to existing
Steel example profiles and are labeled physically non-equivalent.

The solver, 3D overlay Y-plane, Factory import schema, restraints, load
combinations and release mechanics are unchanged.

## Windows acceptance (pending)

1. Download branch source as a complete ZIP and extract.
2. Run RUN_SECTION_MAPPING_058_TESTS_WINDOWS.cmd to compile, test pure
   section mapping policy and Core integration and generate a new plugin ZIP.
3. Close IngeTrazo 0.5.9, run install_preview_058_windows.cmd, restart.
4. Generate Factory 01 with GO Factory v0.3.2-preview.
5. Import Gable frame at Y=0: **one** table dialog with H-300x300x10x15
   and WF-300x150, then **one** consent checkbox/action.
6. Try Cancel and no consent: old model must be unchanged.
7. Select strong/weak axis, verify displayed A/Iz and no RC fallback.
8. Run solver and verify pinned base My≈0; switch Y=12 (no repeated dialog)
   and check loads/release/combo edits preserved.
9. Save/reopen, inspect N/V/M/Deflection/Reaction and PDF/CSV.

**Automated test code exists, but host GUI tests remain unverified.**
Use preview for development only; nominal 2D stiffness is not independently
manufacturer-verified and not automatically transferable to 3D J/Iy/Iz.
