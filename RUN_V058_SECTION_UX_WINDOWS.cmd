@echo off
setlocal EnableExtensions
title GO anaStruct 0.5.8-preview - section dialog QA
set "ROOT=%~dp0"
cd /d "%ROOT%"
set "PY=%ROOT%.local-build\python311\Scripts\python.exe"
if not exist "%PY%" set "PY=py -3.11"
set "LOG=%ROOT%v058-section-ux-qa.log"
echo [1/3] Verifying plugin syntax...
%PY% -m compileall -q go_anastruct_2d > "%LOG%" 2>&1
if errorlevel 1 goto fail
echo [2/3] GO Core bridge/re-import regression tests...
%PY% -m unittest discover -s tests -p "test_core_factory_integration.py" -v >> "%LOG%" 2>&1
if errorlevel 1 goto fail
%PY% -m unittest discover -s tests -p "test_engineering_core.py" -v >> "%LOG%" 2>&1
if errorlevel 1 goto fail
echo [3/3] Building v0.5.8-preview plugin ZIP + checksum...
%PY% scripts\package_preview_058.py >> "%LOG%" 2>&1
if errorlevel 1 goto fail
echo PASS: source/automated tests and preview packaging.
echo Preview: dist\go_anastruct_2d-v0.5.8-preview-plugin.zip
echo SHA256 : dist\go_anastruct_2d-v0.5.8-preview-plugin.zip.sha256
echo Close IngeTrazo; run install_preview_058_windows.cmd; restart.
echo Manual GUI tests remain pending: sections choice, single summary, No silent cancel.
pause
exit /b 0
:fail
echo FAILED. Do not install as verified.
powershell.exe -NoProfile -NonInteractive -Command "Get-Content -LiteralPath $env:LOG -Tail 70"
pause
exit /b 1
