# GO 2D Structural — anaStruct

**Community Preview v0.5.4** — 2D structural analysis extension for **IngeTrazo 0.5.9** using **anaStruct 1.7.0** as the analysis solver.

## Highlights

- 2D beam / frame / truss analytical models
- Fixed, Pin, Roller, Roller-X and Spring supports
- Load Cases and Load Combinations
- Self-weight
- Point loads, moments, uniform and varying distributed loads
- N / V / M / Deflection / Deformed Shape / Reactions
- Signed two-color force-diagram fills
- Hover internal-force readout
- Load-case colors and viewport display controls
- CSV and PDF reports
- Built-in examples including irregular multi-storey portal frames

## Install on Windows

1. Download the repository or the Windows package.
2. Close IngeTrazo completely.
3. Run `install_windows.cmd`.
4. Reopen IngeTrazo 0.5.9.
5. Open **GO 2D anaStruct**.
6. Click **Check Solver**.
7. If needed, click **Install / Repair Solver**.
8. Load an example and click **Run Analysis**.

The plugin is installed to:

```text
%APPDATA%\ingetrazo\plugins\go_anastruct_2d
```

## Documentation

- [Installation](docs/INSTALL.md)
- [User guide](docs/USER_GUIDE.md)
- [Troubleshooting](docs/TROUBLESHOOTING.md)
- [Acceptance checklist](docs/ACCEPTANCE.md)
- [Release notes](RELEASE_NOTES.md)
- [Third-party notices](THIRD_PARTY_NOTICES.md)

## Engineering status

This is a **preview/testing release**. Results must be independently checked before professional design use.

## License

Distributed as **GPL-3.0-or-later** for this preview repository. anaStruct 1.7.0 and IngeTrazo are GPL-licensed projects. See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

## Author

GO Engineering / [buildsmart888](https://github.com/buildsmart888)
