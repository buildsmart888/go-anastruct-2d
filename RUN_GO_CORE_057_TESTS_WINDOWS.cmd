@echo off
setlocal EnableExtensions
title GO anaStruct v0.5.7-preview - Core FEM integration tests
set "ROOT=%~dp0"
cd /d "%ROOT%"
set "PY=%ROOT%.local-build\python311\Scripts\python.exe"
set "LOG=%ROOT%go-core-v01-qa.log"
set "EXE=%ROOT%dist\go_anastruct_worker\go_anastruct_worker.exe"
if not exist "%PY%" (
  echo Build venv absent; using installed Python 3.11 launcher.
  set "PY=py -3.11"
)
echo GO anaStruct v0.5.7-preview / Section Catalog and FEM bridge
%PY% -m compileall -q go_anastruct_2d > "%LOG%" 2>&1
if errorlevel 1 goto fail
%PY% -m unittest discover -s tests -p "test_engineering_core.py" -v >> "%LOG%" 2>&1
if errorlevel 1 goto fail
%PY% -m unittest discover -s tests -p "test_core_factory_integration.py" -v >> "%LOG%" 2>&1
if errorlevel 1 goto fail
%PY% -m unittest discover -s tests -p "test_factory_gable_bridge.py" -v >> "%LOG%" 2>&1
if errorlevel 1 goto fail
if exist "%EXE%" (
  echo Running FEM smoke using the previously tested anaStruct 1.7.0 worker...
  %PY% tools\check_factory_gable_preview.py >> "%LOG%" 2>&1
  if errorlevel 1 goto fail
  %PY% tools\numerical_regression.py --portable-exe "%EXE%" >> "%LOG%" 2>&1
  if errorlevel 1 goto fail
) else (
  echo WARNING: Portable EXE absent. Numerical worker tests are NOT passed.>> "%LOG%"
  echo WARNING: Portable EXE absent. FEM smoke/regression remain PENDING.
)
%PY% scripts\package_preview_057.py >> "%LOG%" 2>&1
if errorlevel 1 goto fail
echo.
echo PASS: Available Core tests and preview package; see log for optional solver-test status.
echo ZIP: dist\go_anastruct_2d-v0.5.7-preview-plugin.zip
echo SHA: dist\go_anastruct_2d-v0.5.7-preview-plugin.zip.sha256
echo GUI acceptance on IngeTrazo 0.5.9 is still required.
pause
exit /b 0
:fail
echo FAILED: do NOT use this candidate for design.
powershell.exe -NoProfile -NonInteractive -Command "Get-Content -LiteralPath $env:LOG -Tail 90"
echo Log: "%LOG%"
pause
exit /b 1
