@echo off
setlocal EnableExtensions
set "PLUGIN=%~dp0"
set "RUNTIME=%LOCALAPPDATA%\GO anaStruct 2D\solver-v0.4"
set "HOME=%LOCALAPPDATA%\GO anaStruct 2D"
set "VENV_PY=%RUNTIME%\Scripts\python.exe"

if not exist "%HOME%" mkdir "%HOME%"

if not exist "%VENV_PY%" (
  echo [1/4] Creating isolated Python runtime...
  set "CREATED="
  where py >nul 2>nul
  if not errorlevel 1 (
    py -3.12 -m venv "%RUNTIME%" >nul 2>&1
    if not errorlevel 1 set "CREATED=1"
    if not defined CREATED (
      py -3 -m venv "%RUNTIME%" >nul 2>&1
      if not errorlevel 1 set "CREATED=1"
    )
  )
  if not defined CREATED (
    where python >nul 2>nul
    if not errorlevel 1 (
      python -m venv "%RUNTIME%" >nul 2>&1
      if not errorlevel 1 set "CREATED=1"
    )
  )
  if not defined CREATED (
    echo ERROR: Could not create a Python virtual environment. Install Python 3.10-3.13 or Python Launcher ^(py.exe^).
    exit /b 1
  )
)

if not exist "%VENV_PY%" (
  echo ERROR: Solver Python was not created: %VENV_PY%
  exit /b 1
)

echo [2/4] Installing NumPy and anaStruct 1.7.0...
"%VENV_PY%" -m pip install --disable-pip-version-check --upgrade "numpy>=1.23.5,<3" "anastruct==1.7.0"
if errorlevel 1 (
  echo ERROR: pip could not install anaStruct 1.7.0. Check internet/proxy access and try again.
  exit /b 1
)

echo [3/4] Checking solver...
"%VENV_PY%" -I -X utf8 -c "import importlib.metadata as m; assert m.version('anastruct')=='1.7.0'; from anastruct import SystemElements; import numpy; print('anaStruct',m.version('anastruct'),'NumPy',numpy.__version__,'OK')"
if errorlevel 1 (
  echo ERROR: anaStruct runtime health check failed.
  exit /b 1
)

echo [4/4] Writing runtime configuration...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$p='%VENV_PY%'; $d=@{python=$p;protocol=1;solver='anastruct';version='1.7.0'} | ConvertTo-Json; $d | Set-Content -LiteralPath '%PLUGIN%worker_config.json' -Encoding UTF8; $d | Set-Content -LiteralPath '%HOME%\worker_config.json' -Encoding UTF8"
if errorlevel 1 (
  echo ERROR: Could not write worker_config.json.
  exit /b 1
)

echo GO 2D Structural anaStruct solver is READY.
echo Runtime: %VENV_PY%
exit /b 0
