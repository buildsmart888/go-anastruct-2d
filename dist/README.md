# v0.5.4 distribution package

## Direct package

Canonical GitHub distribution artifact:

- `go_anastruct_2d-v0.5.4-plugin.zip`
- Size: **62,923 bytes**
- SHA-256: `706f6f7654c38f84bd88bc621596f81394b26acd9063f96b52cf90d5ba52bbc6`

This GitHub-repacked ZIP contains the same 18 uncompressed source files as the locally verified v0.5.4 plugin package. File size + CRC32 were compared for every archive entry; the ZIP stream differs only because of compression/archive metadata.

## Reproducible fallback

The same GitHub artifact can be reconstructed from:

- `plugin_v0.5.4.part01.b64`
- `plugin_v0.5.4.part02.b64`
- `plugin_v0.5.4.part03.b64`
- `plugin_v0.5.4.part04.b64`
- `plugin_v0.5.4.part05.b64`
- `plugin_v0.5.4.part06.b64`
- `plugin_v0.5.4.part07.b64`
- `plugin_v0.5.4.part08.b64`

Users do **not** need to reconstruct it manually. Run `install_windows.cmd` from the repository root; it prefers the direct ZIP and verifies SHA-256 before installation.
