# Troubleshooting

## Solver not ready

Click **Install / Repair Solver**, then **Check Solver**. The required solver version is anaStruct 1.7.0.

## Extension does not appear

Confirm the installed folder is:
`%APPDATA%\ingetrazo\plugins\go_anastruct_2d`

and contains `__init__.py`. Fully restart IngeTrazo.

## Results are stale

Geometry, loads, properties, cases or combinations changed after the last run. Run Analysis again.

## Analysis error

Record:
- IngeTrazo version
- extension version
- selected example/model
- load case/combination
- full error text
- screenshot

Open a GitHub issue with those details. Do not hide equilibrium or solver errors when reporting a problem.

## Installer SHA mismatch

Download the repository ZIP again. The installer deliberately stops if the reconstructed v0.5.4 package differs from the published SHA-256.
