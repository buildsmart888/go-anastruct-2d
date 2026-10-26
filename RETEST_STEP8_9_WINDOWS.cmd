@echo off
setlocal EnableExtensions DisableDelayedExpansion
title GO anaStruct v0.5.5 - Re-test Numerical Regression (No EXE Rebuild)
set "ROOT=%~dp0"
set "PY=%ROOT%.local-build\python311\Scripts\python.exe"
set "EXE=%ROOT%dist\go_anastruct_worker\go_anastruct_worker.exe"
set "ZIP=%ROOT%dist\go_anastruct_2d-runtime-windows-x64-v0.5.5.zip"
set "LOG=%ROOT%.local-build\regression-only-v055.log"
cd /d "%ROOT%"

echo ============================================================
echo GO anaStruct v0.5.5 - RETEST STEPS 8 AND 9 ONLY
echo Reuses the already-built Windows x64 Portable EXE and ZIP.
echo No Python installation, dependency download or PyInstaller rebuild.
echo ============================================================
echo.

if not exist "%PY%" (
  echo ERROR: Existing Python build environment is missing: "%PY%"
  pause
  exit /b 2
)
if not exist "%EXE%" (
  echo ERROR: Existing portable worker EXE not found: "%EXE%"
  pause
  exit /b 2
)
if not exist "%ZIP%" (
  echo ERROR: Existing portable ZIP not found: "%ZIP%"
  pause
  exit /b 2
)
if not exist "%ZIP%.sha256" (
  echo ERROR: Existing portable ZIP SHA-256 file not found.
  pause
  exit /b 2
)

echo Checking the example-1 vs example-10 test fixture guard...
"%PY%" -m unittest discover -s tests -p "test_numeric_regression_fixture.py" -v > "%LOG%" 2>&1
if errorlevel 1 goto numerical_fail
echo [8/9] Comparing v0.5.4 / v0.5.5 / portable worker.
echo Running numerical analysis and recording the first mismatch...
"%PY%" "%ROOT%tools\numerical_regression.py" --portable-exe "%EXE%" > "%LOG%" 2>&1
if errorlevel 1 goto numerical_fail
echo PASS: Numerical regression.
echo.

echo [9/9] Clean-profile install and corrupted-archive rejection...
"%PY%" "%ROOT%tools\clean_install_windows.py" >> "%LOG%" 2>&1
if errorlevel 1 goto installation_fail
echo PASS: Clean-profile installation.
echo.
echo ============================================================
echo PASS: Steps 8 and 9 completed.
echo Numerical report: "%ROOT%dist\numerical-regression-v055.json"
echo Log: "%LOG%"
echo IMPORTANT: Real Windows 10/11 IngeTrazo UI acceptance is still pending.
echo ============================================================
pause
exit /b 0

:numerical_fail
echo.
echo FAILED: Step 8 numerical regression (EXE remains built).
goto print_log

:installation_fail
echo.
echo FAILED: Step 9 clean-profile install (EXE remains built).
goto print_log

:print_log
echo ------------------------------------------------------------
echo ERROR DETAIL FROM TEST LOG:
echo ------------------------------------------------------------
type "%LOG%"
echo ------------------------------------------------------------
echo Report this output before changing numerical tolerances or publishing.
echo Saved log: "%LOG%"
pause
exit /b 1
