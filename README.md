# GO 2D Structural — anaStruct

**Community Preview v0.5.4** — 2D structural analysis extension for **IngeTrazo 0.5.9** using **anaStruct 1.7.0** as the analysis solver.

## Download

- **Windows installer workflow:** download the repository as ZIP, extract it, then run `setup_windows.cmd`.
- **Plugin package:** [dist/go_anastruct_2d-v0.5.4-plugin.zip](dist/go_anastruct_2d-v0.5.4-plugin.zip)
- Published package SHA-256:  
  `706f6f7654c38f84bd88bc621596f81394b26acd9063f96b52cf90d5ba52bbc6`

The published ZIP contains the same 18 source files as the verified local v0.5.4 package; CRC32 was checked file-by-file. The ZIP byte stream differs only because it was repacked with different compression metadata.

## Highlights

- 2D beam / frame / truss analytical models
- Fixed, Pin, Roller, Roller-X and Spring supports
- Load Cases and Load Combinations
- Self-weight
- Point loads, moments, uniform and varying distributed loads
- N / V / M / Deflection / Deformed Shape / Reactions
- Signed two-color force-diagram fills
- Hover internal-force readout
- Load-case colors, legend and viewport display controls
- Editable/copyable model and load tables
- CSV and PDF reports
- 10 built-in examples including irregular multi-storey portal frames and wind + moment frame

## Install on Windows

1. Click **Code → Download ZIP** on this repository.
2. Extract the downloaded repository ZIP.
3. Close IngeTrazo completely.
4. Double-click `setup_windows.cmd` or run `install_windows.cmd`.
5. The installer verifies the packaged plugin SHA-256, backs up an existing installation, and installs to:
   `%APPDATA%\ingetrazo\plugins\go_anastruct_2d`
6. Reopen **IngeTrazo 0.5.9**.
7. Open **GO 2D anaStruct**.
8. Click **Check Solver**.
9. If needed, click **Install / Repair Solver**.
10. Load an example and click **Run Analysis**.

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
