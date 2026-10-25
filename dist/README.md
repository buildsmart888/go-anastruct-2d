# v0.5.4 distribution package

## Canonical plugin ZIP

Use:

`go_anastruct_2d-v0.5.4-plugin.zip`

Verified publication:

- Size: **64,432 bytes**
- SHA-256: `096ad236fa737b66d4a77ae79ed6690a452da168e6c8757b08f0d707d2f6056f`
- ZIP integrity: verified with `unzip -t`
- Python source syntax: verified with `python -m compileall`

## Recovery chunks

The exact same ZIP can be reconstructed from the 22 files under:

`canonical_parts4k/part_00.b64` … `part_21.b64`

Parts 00–20 contain 4,000 Base64 characters each; part 21 contains the final 1,912 characters.

Users normally do **not** need these files. `install_windows.cmd` prefers the direct ZIP and only uses the chunks if the ZIP is missing. In both paths it checks the canonical SHA-256 before extraction.

Legacy/repacked package parts from the failed publication were removed as part of Issue #2.
