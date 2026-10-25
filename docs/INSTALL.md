# Installation — Windows

Target: **IngeTrazo 0.5.9 / Plugin API v2**

## Recommended installation

1. On GitHub choose **Code → Download ZIP**.
2. Extract the repository ZIP to a normal folder.
3. Close IngeTrazo completely.
4. Double-click **setup_windows.cmd** or run **install_windows.cmd**.
5. The installer rebuilds the canonical v0.5.4 plugin package from `dist/`, verifies its SHA-256, backs up any existing copy, and installs it to:
   `%APPDATA%\ingetrazo\plugins\go_anastruct_2d`
6. The installer creates an isolated anaStruct runtime under LocalAppData and installs **anaStruct 1.7.0**.
7. Restart IngeTrazo.
8. Open **GO 2D anaStruct** and click **Check Solver**.

If solver setup cannot finish because of internet/proxy/Python configuration, the extension files remain installable and you can retry from **Install / Repair Solver** in the panel.

## Uninstall

Run `uninstall_windows.cmd`, then restart IngeTrazo.
