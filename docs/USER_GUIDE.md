# User Guide

## Quick start

1. Open **GO 2D anaStruct**.
2. Click **Check Solver**.
3. Choose one of the built-in examples.
4. Click **Run Analysis**.
5. Choose a Load Case or Load Combination.
6. Switch the viewport diagram between Model, N, V, M, Deflection, Reaction and Deformed.

## Model data

The model editor contains editable tables for Nodes, Members, Materials, Sections, Point Loads and Distributed Loads. Rows can be added, duplicated, copied, pasted and deleted.

Internal solver units are normalized to **m + kN**.

## Load Cases / Combinations

Use **Load Cases / Combinations…** to define DL, LL, WL and custom cases, select the self-weight case, and enter combination factors in a spreadsheet-style table.

## Results

- N: axial force
- V: shear force
- M: bending moment
- Deflection: member transverse deflection
- Deformed: complete global displaced shape / frame sway
- Reaction: support reactions

Hover a member after analysis to read cached N/V/M/deflection values at that location.

## Display

The panel can show/hide point/moment loads, distributed loads, self-weight, load labels, diagram labels, IDs and Min/Max values. Load arrows are color-coded by case/type.

## Export

Current results can be exported to CSV and PDF. Full PDF export includes all solved cases/combinations. Treat preview outputs as engineering aids and independently verify critical design decisions.
