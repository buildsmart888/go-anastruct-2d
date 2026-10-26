@echo off
setlocal EnableExtensions
title GO anaStruct v0.5.8-preview - Single Popup QA
set "ROOT=%~dp0"
cd /d "%ROOT%"
set "PY=py -3.11"
set "LOG=%ROOT%section-mapping-058-test.log"
echo =============================================================
echo GO anaStruct v0.5.8-preview: Steel Section Mapping QA
echo =============================================================
echo [1/4] Python source compile...
%PY% -m compileall -q go_anastruct_2d > "%LOG%" 2>&1
if errorlevel 1 goto fail
echo [2/4] Qt-free mapping policy and core geometry tests...
%PY% -m unittest discover -s tests -p "test_section_mapping_policy.py" -v >> "%LOG%" 2>&1
if errorlevel 1 goto fail
%PY% -m unittest discover -s tests -p "test_engineering_core.py" -v >> "%LOG%" 2>&1
if errorlevel 1 goto fail
%PY% -m unittest discover -s tests -p "test_core_factory_integration.py" -v >> "%LOG%" 2>&1
if errorlevel 1 goto fail
echo [3/4] Package plugin and verify SHA256...
%PY% scripts\package_preview_058.py >> "%LOG%" 2>&1
if errorlevel 1 goto fail
echo [4/4] Verify SHA256 and complete plugin ZIP...
powershell.exe -NoProfile -NonInteractive -Command ^
  "$p='dist\go_anastruct_2d-v0.5.8-preview-plugin.zip';" ^
  "$a=(Get-FileHash -Algorithm SHA256 -LiteralPath $p).Hash.ToLowerInvariant();" ^
  "$b=(Get-Content -Raw -LiteralPath ($p+'.sha256')).Trim().ToLowerInvariant();" ^
  "if($a -ne $b){throw 'ZIP SHA mismatch'}; Write-Host 'ZIP SHA256 OK'">> "%LOG%" 2>&1
if errorlevel 1 goto fail
echo.
echo PASS: Available source, policy, Core and packaging checks.
echo Preview: dist\go_anastruct_2d-v0.5.8-preview-plugin.zip
echo Installer: install_preview_058_windows.cmd
echo WARNING: GUI section dialog in IngeTrazo 0.5.9 must still be tested manually.
pause
exit /b 0
:fail
echo FAILED. Do not install this candidate as a verified extension.
powershell.exe -NoProfile -NonInteractive -Command "Get-Content -LiteralPath $env:LOG -Tail 90"
echo Log: "%LOG%"
pause
exit /b 1
