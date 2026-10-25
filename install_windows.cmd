@echo off
setlocal EnableExtensions EnableDelayedExpansion
title GO 2D Structural - anaStruct v0.5.4 Installer

set "ROOT=%~dp0"
set "DIST=%ROOT%dist"
set "PLUGIN=%APPDATA%\ingetrazo\plugins\go_anastruct_2d"
set "BACKUPROOT=%LOCALAPPDATA%\GO anaStruct 2D\backup"
set "TMP=%TEMP%\go_anastruct_2d_v054_%RANDOM%"
set "ZIP=%TMP%\go_anastruct_2d-v0.5.4-plugin.zip"
set "EXTRACT=%TMP%\extract"
set "EXPECTED_SHA=096ad236fa737b66d4a77ae79ed6690a452da168e6c8757b08f0d707d2f6056f"

echo ==============================================
echo   GO 2D Structural - anaStruct v0.5.4
echo   IngeTrazo 0.5.9 Community Preview
echo ==============================================
echo.

if not exist "%DIST%\plugin_v0.5.4.part01.b64" (
  echo ERROR: Distribution parts were not found under:
  echo   %DIST%
  echo.
  echo Download the complete repository ZIP from GitHub and extract it first.
  pause
  exit /b 1
)

mkdir "%TMP%" >nul 2>&1
mkdir "%EXTRACT%" >nul 2>&1

echo [1/5] Rebuilding verified plugin package...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$ErrorActionPreference='Stop';" ^
  "$parts=Get-ChildItem -LiteralPath '%DIST%' -Filter 'plugin_v0.5.4.part*.b64' | Sort-Object Name;" ^
  "if($parts.Count -ne 8){throw ('Expected 8 package parts, found '+$parts.Count)};" ^
  "$b64=($parts | ForEach-Object {(Get-Content -Raw -LiteralPath $_.FullName).Trim()}) -join '';" ^
  "[IO.File]::WriteAllBytes('%ZIP%',[Convert]::FromBase64String($b64));" ^
  "$hash=(Get-FileHash -Algorithm SHA256 -LiteralPath '%ZIP%').Hash.ToLowerInvariant();" ^
  "if($hash -ne '%EXPECTED_SHA%'){throw ('SHA-256 mismatch: '+$hash)};" ^
  "Expand-Archive -LiteralPath '%ZIP%' -DestinationPath '%EXTRACT%' -Force"
if errorlevel 1 (
  echo.
  echo ERROR: Could not rebuild or verify the plugin package.
  rmdir /S /Q "%TMP%" >nul 2>&1
  pause
  exit /b 1
)

set "SRC=%EXTRACT%\go_anastruct_2d"
if not exist "%SRC%\__init__.py" (
  echo ERROR: Verified ZIP did not contain go_anastruct_2d\__init__.py
  rmdir /S /Q "%TMP%" >nul 2>&1
  pause
  exit /b 1
)

echo [2/5] Backing up existing installation...
if exist "%PLUGIN%\__init__.py" (
  for /f %%T in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd_HHmmss"') do set "STAMP=%%T"
  if not exist "%BACKUPROOT%" mkdir "%BACKUPROOT%"
  xcopy "%PLUGIN%" "%BACKUPROOT%\go_anastruct_2d_!STAMP!\" /E /I /H /Y >nul
)

echo [3/5] Installing extension...
if not exist "%PLUGIN%" mkdir "%PLUGIN%"
robocopy "%SRC%" "%PLUGIN%" /MIR /R:2 /W:1 /NFL /NDL /NJH /NJS /NP >nul
set "RC=%ERRORLEVEL%"
if %RC% GEQ 8 (
  echo ERROR: Failed to copy extension. Robocopy exit code: %RC%
  rmdir /S /Q "%TMP%" >nul 2>&1
  pause
  exit /b %RC%
)

echo [4/5] Installing / checking anaStruct 1.7.0 solver...
call "%PLUGIN%\repair_runtime.cmd"
if errorlevel 1 (
  echo.
  echo WARNING: Extension installed, but solver runtime setup failed.
  echo Open IngeTrazo and use: GO 2D anaStruct ^> Install / Repair Solver
  rmdir /S /Q "%TMP%" >nul 2>&1
  pause
  exit /b 1
)

echo [5/5] Finalizing...
rmdir /S /Q "%TMP%" >nul 2>&1

echo.
echo SUCCESS
echo Installed:
echo   %PLUGIN%
echo.
echo Next:
echo   1. Close IngeTrazo completely if it is open.
echo   2. Reopen IngeTrazo 0.5.9.
echo   3. Open the GO 2D anaStruct panel.
echo   4. Click Check Solver.
echo   5. Load an example and Run Analysis.
echo.
pause
exit /b 0
