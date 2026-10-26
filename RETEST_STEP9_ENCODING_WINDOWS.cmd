@echo off
setlocal EnableExtensions DisableDelayedExpansion
title GO anaStruct v0.5.5 - Re-test Windows clean install (no EXE rebuild)
set "ROOT=%~dp0"
cd /d "%ROOT%"
set "PY=%ROOT%.local-build\python311\Scripts\python.exe"
set "EXE=%ROOT%dist\go_anastruct_worker\go_anastruct_worker.exe"
set "RUNTIME_ZIP=%ROOT%dist\go_anastruct_2d-runtime-windows-x64-v0.5.5.zip"
set "PLUGIN_ZIP=%ROOT%dist\go_anastruct_2d-v0.5.5-plugin.zip"
set "LOG=%ROOT%.local-build\retest-stage9-encoding.log"
set "RUNTIME_SOURCE=%ROOT%go_anastruct_2d\runtime.py"
echo ===============================================================
echo GO anaStruct v0.5.5 - RE-TEST STAGE 9 / WINDOWS ENCODING FIX
echo Reuses your compiled EXE. No PyInstaller rebuild is necessary.
echo ===============================================================
if not exist "%PY%" goto missing
if not exist "%EXE%" goto missing
if not exist "%RUNTIME_ZIP%" goto missing
if not exist "%RUNTIME_ZIP%.sha256" goto missing
if not exist "%RUNTIME_SOURCE%" goto missing

findstr /C:"def _worker_output_text(" "%RUNTIME_SOURCE%" >nul
if errorlevel 1 (
  echo ERROR: Runtime.py has not been patched to support CP1252 / UTF-8 worker output.
  echo Download the updated go_anastruct_2d/runtime.py from the project QA branch.
  pause
  exit /b 2
)

echo [A] Rebuilding only the PLUGIN ZIP and SHA256 from patched Python source...
"%PY%" "%ROOT%scripts\package_plugin.py" > "%LOG%" 2>&1
if errorlevel 1 goto fail
"%PY%" "%ROOT%scripts\verify_release.py" >> "%LOG%" 2>&1
if errorlevel 1 goto fail

echo [B] Comparing published v0.5.4, patched v0.5.5 and EXISTING EXE...
"%PY%" "%ROOT%tools\numerical_regression.py" --portable-exe "%EXE%" >> "%LOG%" 2>&1
if errorlevel 1 goto fail

echo [C] Isolated Windows clean install plus corrupted archive rejection...
"%PY%" "%ROOT%tools\clean_install_windows.py" >> "%LOG%" 2>&1
if errorlevel 1 goto fail

echo ===============================================================
echo PASS: Numerical regression + Windows clean-profile install tests.
echo Plugin ZIP: "%PLUGIN_ZIP%"
echo Portable EXE/ZIP reused without recompilation.
echo Report: "%ROOT%dist\numerical-regression-v055.json"
echo IMPORTANT: IngeTrazo 0.5.9 desktop GUI testing is still required.
echo ===============================================================
pause
exit /b 0

:missing
echo ERROR: Existing build environment, runtime source or Portable EXE/ZIP is missing.
echo Reuse your original project directory containing .local-build and dist.
pause
exit /b 2

:fail
echo FAILED. Existing Portable EXE has NOT been rebuilt.
echo Last 80 log lines:
powershell.exe -NoProfile -NonInteractive -Command "Get-Content -LiteralPath $env:LOG -Tail 80"
echo Log file: "%LOG%"
pause
exit /b 1
