@echo off
setlocal EnableExtensions
set "ROOT=%~dp0"
set "SRC=%ROOT%go_anastruct_2d"
set "PLUGIN=%APPDATA%\ingetrazo\plugins\go_anastruct_2d"
set "BACKUPROOT=%LOCALAPPDATA%\GO anaStruct 2D\backup"

if not exist "%SRC%\__init__.py" (
  echo ERROR: go_anastruct_2d package must be beside install_windows.cmd
  exit /b 1
)

if exist "%PLUGIN%\__init__.py" (
  for /f %%T in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd_HHmmss"') do set "STAMP=%%T"
  if not exist "%BACKUPROOT%" mkdir "%BACKUPROOT%"
  xcopy "%PLUGIN%" "%BACKUPROOT%\go_anastruct_2d_%STAMP%\" /E /I /H /Y >nul
)

if not exist "%PLUGIN%" mkdir "%PLUGIN%"
robocopy "%SRC%" "%PLUGIN%" /MIR /NFL /NDL /NJH /NJS /NP >nul
if errorlevel 8 (
  echo ERROR: Failed to copy extension package.
  exit /b 1
)

call "%PLUGIN%\repair_runtime.cmd"
if errorlevel 1 (
  echo.
  echo ERROR: Extension files were copied but solver installation failed.
  echo You can retry later from the GO 2D anaStruct panel: Install / Repair Solver.
  exit /b 1
)

echo.
echo Installed GO 2D Structural - anaStruct v0.5.4
echo Plugin: %PLUGIN%
echo Fully restart IngeTrazo, then open Extensions ^> GO 2D Structural - anaStruct.
exit /b 0
