@echo off
setlocal EnableExtensions DisableDelayedExpansion
title GO anaStruct v0.5.5 - Build and Test Portable EXE on this PC
set "ROOT=%~dp0"
cd /d "%ROOT%"
set "LOCALBUILD=%ROOT%.local-build"
set "VENV=%LOCALBUILD%\python311"
set "PY=%VENV%\Scripts\python.exe"
set "LOG=%LOCALBUILD%\build-and-test-v055.log"
set "EXE=%ROOT%dist\go_anastruct_worker\go_anastruct_worker.exe"
set "PORTABLE=%ROOT%dist\go_anastruct_2d-runtime-windows-x64-v0.5.5.zip"

echo ============================================================
echo GO anaStruct v0.5.5 - Portable Windows x64 LOCAL TEST BUILD
echo This builds on your Windows PC without using GitHub Actions.
echo It uses an isolated Python 3.11 build environment, not admin.
echo ============================================================
echo.

if /I "%PROCESSOR_ARCHITECTURE%"=="AMD64" goto arch_ok
if /I "%PROCESSOR_ARCHITEW6432%"=="AMD64" goto arch_ok
echo ERROR: This script requires Windows 10/11 x64.
pause
exit /b 1
:arch_ok

if not exist "%LOCALBUILD%" mkdir "%LOCALBUILD%"
if errorlevel 1 goto fail
echo Starting local build > "%LOG%"
echo ROOT: %ROOT% >> "%LOG%"
echo.

rem The build computer needs Python 3.11; end users of the EXE do not.
set "BOOT="
where py >nul 2>&1
if errorlevel 1 goto check_python
py -3.11 -c "import sys,struct;sys.exit(0 if sys.version_info[:2]==(3,11) and struct.calcsize('P')==8 else 1)" >nul 2>&1
if not errorlevel 1 set "BOOT=py -3.11"
:check_python
if defined BOOT goto boot_ok
where python >nul 2>&1
if errorlevel 1 goto no_python
python -c "import sys,struct;sys.exit(0 if sys.version_info[:2]==(3,11) and struct.calcsize('P')==8 else 1)" >nul 2>&1
if not errorlevel 1 set "BOOT=python"
if not defined BOOT goto no_python
:boot_ok

set "STAGE=1/9 - Create Python virtual environment"
echo [1/9] Creating isolated Python 3.11 build environment...
if not exist "%PY%" (
  %BOOT% -m venv "%VENV%" >> "%LOG%" 2>&1
  if errorlevel 1 goto fail
)
if not exist "%PY%" goto fail

set "STAGE=2/9 - Install pinned dependencies"
echo [2/9] Installing PINNED build dependencies (internet required)...
"%PY%" -m pip install --disable-pip-version-check --upgrade "pip==25.2" "numpy==2.2.6" "anastruct==1.7.0" "pyinstaller==6.16.0" >> "%LOG%" 2>&1
if errorlevel 1 goto fail

set "STAGE=3/9 - Verify plugin package"
echo [3/9] Repackaging candidate plugin from checked source and verifying ZIP...
"%PY%" "%ROOT%scripts\package_plugin.py" >> "%LOG%" 2>&1
if errorlevel 1 goto fail
"%PY%" "%ROOT%scripts\verify_release.py" >> "%LOG%" 2>&1
if errorlevel 1 goto fail

set "STAGE=4/9 - Build PyInstaller Windows worker EXE"
echo [4/9] Building standalone Windows worker EXE...
"%PY%" -m PyInstaller --noconfirm --clean --onedir --console --name go_anastruct_worker --distpath "%ROOT%dist" --workpath "%LOCALBUILD%\pyinstaller" --specpath "%LOCALBUILD%" --paths "%ROOT%." --collect-all anastruct --collect-all numpy --copy-metadata anastruct --copy-metadata numpy "%ROOT%tools\worker_entry.py" >> "%LOG%" 2>&1
if errorlevel 1 goto fail
if not exist "%EXE%" (
  echo ERROR: PyInstaller exited successfully but EXE not found at %EXE% >> "%LOG%"
  goto fail
)

set "STAGE=5/9 - Check built worker EXE"
echo [5/9] Checking worker EXE / NumPy / anaStruct...
"%EXE%" --check >> "%LOG%" 2>&1
if errorlevel 1 goto fail

set "STAGE=6/9 - Test worker JSON and equilibrium"
echo [6/9] Checking JSON protocol and FEM equilibrium...
"%PY%" "%ROOT%tools\smoke_portable.py" >> "%LOG%" 2>&1
if errorlevel 1 goto fail

set "STAGE=7/9 - Package ZIP and SHA-256"
echo [7/9] Packaging portable Windows ZIP + SHA-256...
"%PY%" "%ROOT%tools\package_windows_runtime.py" >> "%LOG%" 2>&1
if errorlevel 1 goto fail
if not exist "%PORTABLE%" goto fail
if not exist "%PORTABLE%.sha256" goto fail

set "STAGE=8/9 - Numerical regression (beam and portals)"
echo [8/9] Comparing v0.5.4 vs v0.5.5 vs EXE: beam and portals...
"%PY%" -m unittest discover -s tests -p "test_numeric_regression_fixture.py" -v >> "%LOG%" 2>&1
if errorlevel 1 goto fail
"%PY%" "%ROOT%tools\numerical_regression.py" --portable-exe "%EXE%" >> "%LOG%" 2>&1
if errorlevel 1 goto fail

set "STAGE=9/9 - Clean profile installation test"
echo [9/9] Clean-profile install, fallback selection and tamper rejection...
"%PY%" "%ROOT%tools\clean_install_windows.py" >> "%LOG%" 2>&1
if errorlevel 1 goto fail

echo.
echo ============================================================
echo PASS: All LOCAL build and automatic tests completed.
echo Your portable ZIP is:
echo   %PORTABLE%
echo SHA-256:
echo   %PORTABLE%.sha256
echo Numerical test report:
echo   %ROOT%dist\numerical-regression-v055.json
echo Log:
echo   %LOG%
echo ============================================================
echo.
echo The GUI of IngeTrazo 0.5.9 STILL requires manual Windows testing.
echo Copy the two portable files to the distribution dist folder
echo and run setup_windows.cmd if testing installation on your own account.
pause
exit /b 0

:no_python
echo ERROR: Python 3.11 x64 is needed ONLY on this build computer.
echo Install Python 3.11 x64 from python.org, then run this file again.
echo You can still test the v0.5.5 PLUGIN using setup_windows.cmd
echo with its existing Python runtime fallback.
pause
exit /b 2

:fail
echo.
echo BUILD OR TEST FAILED at stage %STAGE%. No release was published.
echo Full diagnostics:
echo   %LOG%
echo.
echo -------- Last 60 log lines / actual error --------
powershell.exe -NoProfile -NonInteractive -Command "if(Test-Path -LiteralPath $env:LOG){ Get-Content -LiteralPath $env:LOG -Tail 60 } else { Write-Host 'Log file not found' }"
echo -------- End of log --------
echo.
echo Please copy the lines above when reporting a failure.
pause
exit /b 1
