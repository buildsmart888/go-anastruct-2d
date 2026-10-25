@echo off
setlocal EnableExtensions EnableDelayedExpansion
title GO 2D Structural - anaStruct v0.5.5 Installer

set "ROOT=%~dp0"
set "PACK=%ROOT%dist\go_anastruct_2d-v0.5.5-plugin.zip"
set "HASH=%PACK%.sha256"
set "DEST=%APPDATA%\ingetrazo\plugins\go_anastruct_2d"
set "BACKUPROOT=%LOCALAPPDATA%\GO anaStruct 2D\backup"
set "TMP=%TEMP%\go_anastruct_2d_v055_%RANDOM%_%RANDOM%"
set "EXTRACT=%TMP%\extract"

echo ===================================================
echo GO 2D Structural - anaStruct v0.5.5
echo For IngeTrazo 0.5.9 on Windows x64
echo ===================================================
echo.
if not exist "%PACK%" (
  echo ERROR: Plugin package missing: %PACK%
  pause
  exit /b 1
)
if not exist "%HASH%" (
  echo ERROR: SHA-256 manifest missing: %HASH%
  pause
  exit /b 1
)
mkdir "%EXTRACT%" >nul 2>&1
if errorlevel 1 (
  echo ERROR: Cannot create temporary extraction folder.
  pause
  exit /b 1
)

echo [1/5] Verifying SHA-256 and extracting package...
powershell.exe -NoProfile -NonInteractive -Command ^
 "$ErrorActionPreference='Stop';" ^
 "$expected=(Get-Content -Raw -LiteralPath '%HASH%').Trim().ToLowerInvariant();" ^
 "if($expected -notmatch '^[0-9a-f]{64}$'){throw 'Invalid SHA-256 manifest'};" ^
 "$actual=(Get-FileHash -Algorithm SHA256 -LiteralPath '%PACK%').Hash.ToLowerInvariant();" ^
 "if($actual -ne $expected){throw ('Package SHA-256 mismatch: '+$actual)};" ^
 "Expand-Archive -LiteralPath '%PACK%' -DestinationPath '%EXTRACT%' -Force"
if errorlevel 1 goto fail

set "SRC=%EXTRACT%\go_anastruct_2d"
if not exist "%SRC%\__init__.py" (
  echo ERROR: Verified ZIP is missing go_anastruct_2d\__init__.py.
  goto fail
)
if not exist "%SRC%\label_layout.py" (
  echo ERROR: Verified ZIP is missing v0.5.5 label layout module.
  goto fail
)
if not exist "%SRC%\toolbar.py" (
  echo ERROR: Verified ZIP is missing v0.5.5 toolbar module.
  goto fail
)

echo [2/5] Backing up existing extension...
if exist "%DEST%\__init__.py" (
  for /f %%T in ('powershell -NoProfile -NonInteractive -Command "Get-Date -Format yyyyMMdd_HHmmss"') do set "STAMP=%%T"
  if not exist "%BACKUPROOT%" mkdir "%BACKUPROOT%"
  xcopy "%DEST%" "%BACKUPROOT%\go_anastruct_2d_!STAMP!\" /E /I /H /Y >nul
  if errorlevel 1 (
    echo ERROR: Backup failed; original plugin was NOT overwritten.
    goto fail
  )
)

echo [3/5] Installing extension...
if not exist "%DEST%" mkdir "%DEST%"
robocopy "%SRC%" "%DEST%" /MIR /R:2 /W:1 /NFL /NDL /NJH /NJS /NP >nul
set "RC=%ERRORLEVEL%"
if %RC% GEQ 8 (
  echo ERROR: Plugin copy failed, Robocopy exit code %RC%.
  goto fail
)

echo [4/5] Checking bundled / portable / Python solver...
if exist "%ROOT%dist\go_anastruct_2d-runtime-windows-x64-v0.5.5.zip" (
  call "%ROOT%install_portable_runtime.cmd"
  if errorlevel 1 goto fail
)
call "%DEST%\repair_runtime.cmd"
if errorlevel 1 (
  echo WARNING: Extension installed, but solver runtime is not ready.
  echo The extension can use either a verified portable Windows worker,
  echo or the existing isolated Python/anaStruct 1.7.0 runtime.
  echo Open the plugin and click Check Solver / Install - Repair Solver.
  rmdir /S /Q "%TMP%" >nul 2>&1
  pause
  exit /b 1
)

echo [5/5] Finished.
rmdir /S /Q "%TMP%" >nul 2>&1
echo.
echo SUCCESS: GO anaStruct v0.5.5 installed to:
echo %DEST%
echo Reopen IngeTrazo 0.5.9 and open GO 2D anaStruct.
pause
exit /b 0

:fail
rmdir /S /Q "%TMP%" >nul 2>&1
pause
exit /b 1
