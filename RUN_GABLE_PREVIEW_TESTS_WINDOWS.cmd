@echo off
setlocal EnableExtensions DisableDelayedExpansion
title GO anaStruct 0.5.6-preview / GO Factory Gable test
set "ROOT=%~dp0"
cd /d "%ROOT%"
set "PY=%ROOT%.local-build\python311\Scripts\python.exe"
set "EXE=%ROOT%dist\go_anastruct_worker\go_anastruct_worker.exe"
set "LOG=%ROOT%.local-build\gable-preview-056-qa.log"
if not exist "%PY%" (
  echo ERROR: Missing .local-build Python 3.11 environment.
  echo Build the portable runtime on this computer first.
  pause
  exit /b 2
)
if not exist "%EXE%" (
  echo ERROR: Missing tested v0.5.5 portable solver EXE.
  pause
  exit /b 2
)
echo ==============================================================
echo GO anaStruct v0.5.6-preview / GO Factory integration acceptance
echo Reusing v0.5.5 worker without recompilation.
echo ==============================================================
echo [1/4] Compile source and validate geometry, picking, 3D frame station...
"%PY%" -m compileall -q go_anastruct_2d tools > "%LOG%" 2>&1
if errorlevel 1 goto fail
"%PY%" -m unittest discover -s tests -p "test_factory_gable_*.py" -v >> "%LOG%" 2>&1
if errorlevel 1 goto fail
echo [2/4] Run standalone and imported Gable FEM cases on Portable EXE...
"%PY%" tools\check_factory_gable_preview.py >> "%LOG%" 2>&1
if errorlevel 1 goto fail
echo [3/4] Re-run v0.5.4 vs v0.5.5 numerical regression (4 models)...
"%PY%" tools\numerical_regression.py --portable-exe "%EXE%" >> "%LOG%" 2>&1
if errorlevel 1 goto fail
echo [4/4] Build preview ZIP + matching SHA-256 manifest...
"%PY%" scripts\package_preview_056.py >> "%LOG%" 2>&1
if errorlevel 1 goto fail
"%PY%" scripts\verify_preview_056.py >> "%LOG%" 2>&1
if errorlevel 1 goto fail
echo.
echo PASS: Available automated tests and preview packaging completed.
echo Preview ZIP: "%ROOT%dist\go_anastruct_2d-v0.5.6-preview-plugin.zip"
echo SHA-256: "%ROOT%dist\go_anastruct_2d-v0.5.6-preview-plugin.zip.sha256"
echo Install by running install_preview_056_windows.cmd with IngeTrazo CLOSED.
echo Then complete manual 3D GUI verification in IngeTrazo 0.5.9.
echo Full log: "%LOG%"
pause
exit /b 0
:fail
echo.
echo FAILED: Do not distribute this preview as verified.
powershell.exe -NoProfile -NonInteractive -Command "Get-Content -LiteralPath $env:LOG -Tail 80"
echo Log: "%LOG%"
pause
exit /b 1
