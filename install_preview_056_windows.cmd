@echo off
setlocal EnableExtensions EnableDelayedExpansion
title GO 2D anaStruct v0.5.6-preview - IngeTrazo 0.5.9
set "ROOT=%~dp0"
set "PACK=%ROOT%dist\go_anastruct_2d-v0.5.6-preview-plugin.zip"
set "HASH=%PACK%.sha256"
set "DEST=%APPDATA%\ingetrazo\plugins\go_anastruct_2d"
set "BACKUP=%LOCALAPPDATA%\GO anaStruct 2D\backup-preview"
set "STAGING=%TEMP%\go_anastruct_preview_%RANDOM%_%RANDOM%"

echo ==============================================================
echo GO anaStruct 2D v0.5.6-preview / GO Factory Gable integration
echo Preview only. Close IngeTrazo 0.5.9 before continuing.
echo ==============================================================
if not exist "%PACK%" (
  echo ERROR: Preview plugin archive missing: %PACK%
  pause
  exit /b 1
)
if not exist "%HASH%" (
  echo ERROR: SHA-256 preview manifest missing: %HASH%
  pause
  exit /b 1
)
if not exist "%STAGING%" mkdir "%STAGING%"
if errorlevel 1 goto fail

echo [1/4] Checking SHA-256 and unpacking preview...
powershell.exe -NoProfile -NonInteractive -Command ^
  "$ErrorActionPreference='Stop';" ^
  "$expected=(Get-Content -Raw -LiteralPath '%HASH%').Trim().ToLowerInvariant();" ^
  "if($expected -notmatch '^[0-9a-f]{64}$'){throw 'Bad SHA-256 file'};" ^
  "$actual=(Get-FileHash -Algorithm SHA256 -LiteralPath '%PACK%').Hash.ToLowerInvariant();" ^
  "if($actual -ne $expected){throw 'Preview checksum mismatch'};" ^
  "Expand-Archive -LiteralPath '%PACK%' -DestinationPath '%STAGING%' -Force"
if errorlevel 1 goto fail
if not exist "%STAGING%\go_anastruct_2d\factory_bridge.py" goto fail
if not exist "%STAGING%\go_anastruct_2d\__init__.py" goto fail

echo [2/4] Backing up existing extension outside the plugins folder...
if exist "%DEST%\__init__.py" (
  for /f %%T in ('powershell -NoProfile -NonInteractive -Command "Get-Date -Format yyyyMMdd_HHmmss"') do set "STAMP=%%T"
  if not exist "%BACKUP%" mkdir "%BACKUP%"
  robocopy "%DEST%" "%BACKUP%\go_anastruct_2d_!STAMP!" /E /R:2 /W:1 /NFL /NDL /NJH /NJS /NP >nul
  set "RC=!ERRORLEVEL!"
  if !RC! GEQ 8 (
    echo ERROR: Original plugin backup failed; original was not changed.
    goto fail
  )
)

echo [3/4] Installing extension files...
if not exist "%DEST%" mkdir "%DEST%"
robocopy "%STAGING%\go_anastruct_2d" "%DEST%" /MIR /R:2 /W:1 /NFL /NDL /NJH /NJS /NP >nul
set "RC=%ERRORLEVEL%"
if %RC% GEQ 8 goto fail

echo [4/4] Checking solver runtime...
call "%DEST%\repair_runtime.cmd"
if errorlevel 1 (
  echo WARNING: Preview plugin installed, but solver is not ready.
  echo Open GO 2D anaStruct and click Check Solver or Install / Repair Solver.
  echo The v0.5.5 Portable EXE can be reused when installed.
)
rmdir /S /Q "%STAGING%" >nul 2>&1
echo.
echo INSTALLED PREVIEW: %DEST%
echo Restart IngeTrazo 0.5.9.
echo Create Factory 01, then choose GO anaStruct ^> Create Analysis from GO Factory.
echo Verify the section mapping, base supports and demonstration loads.
pause
exit /b 0

:fail
echo ERROR: Preview install failed. Original plugin backup (if any):
echo   %BACKUP%
rmdir /S /Q "%STAGING%" >nul 2>&1
pause
exit /b 1
