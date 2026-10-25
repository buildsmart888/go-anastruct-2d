@echo off
setlocal
set "PLUGIN=%APPDATA%\ingetrazo\plugins\go_anastruct_2d"
set "HOME=%LOCALAPPDATA%\GO anaStruct 2D"
if exist "%PLUGIN%" rmdir /S /Q "%PLUGIN%"
if exist "%HOME%\solver-v0.4" rmdir /S /Q "%HOME%\solver-v0.4"
if exist "%HOME%\worker_config.json" del /Q "%HOME%\worker_config.json"
echo Removed GO 2D Structural - anaStruct plugin and solver runtime.
echo Restart IngeTrazo.
