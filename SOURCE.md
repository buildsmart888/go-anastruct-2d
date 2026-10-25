# Source code and version history

GO 2D Structural — anaStruct v0.5.5 source is now directly editable in:

`go_anastruct_2d/`

The package can be reviewed without extracting the distribution ZIP. The v0.5.4 release source remains inside the verified legacy ZIP:

`dist/go_anastruct_2d-v0.5.4-plugin.zip`

**v0.5.5 preview ZIP** (`dist/go_anastruct_2d-v0.5.5-plugin.zip`) has the checksum:

`3083ae4bd759b941965afff339ba2f91e62fbfeb4671b0b5e56350042887e8ae`

Archive status: ZIP format and file layout verified, Windows execution/GUI acceptance pending.

Build tools:

- `scripts/package_plugin.py` — create a distributable plugin ZIP and compute its SHA-256 for a new revision. After any rebuild, re-check the final bytes and update the catalog TOML before release.
- `scripts/build_windows_portable.ps1` — optional maintainer-only build of self-contained Windows solver executable.
- `tools/smoke_portable.py` — solver protocol and numerical smoke check on Windows.

Upstream solver: anaStruct 1.7.0; IngeTrazo target: 0.5.9 / API v2.

License: GPL-3.0-or-later. See `THIRD_PARTY_NOTICES.md`.
