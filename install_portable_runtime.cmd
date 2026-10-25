@echo off
setlocal EnableExtensions DisableDelayedExpansion

rem Offline portable runtime installer for GO anaStruct v0.5.5 / Windows x64.
rem No network calls, administrator privileges, execution-policy bypass or Defender changes.
set "ROOT=%~dp0"
set "ARCHIVE=%ROOT%dist\go_anastruct_2d-runtime-windows-x64-v0.5.5.zip"
set "DIGEST=%ARCHIVE%.sha256"
set "RUNTIME_HOME=%LOCALAPPDATA%\GO anaStruct 2D"
set "RUNTIME_TARGET=%RUNTIME_HOME%\portable-v0.5.5"
set "RUNTIME_STAGE=%RUNTIME_HOME%\.portable_stage_%RANDOM%_%RANDOM%"
set "RUNTIME_BACKUP=%RUNTIME_HOME%\.portable_previous_%RANDOM%_%RANDOM%"

if not exist "%ARCHIVE%" (
  echo INFO: Optional portable runtime was not supplied. Python fallback may be required.
  exit /b 2
)
if not exist "%DIGEST%" (
  echo ERROR: Portable runtime archive exists without its SHA-256 manifest.
  exit /b 1
)

set "GOA_ARCHIVE=%ARCHIVE%"
set "GOA_DIGEST=%DIGEST%"
set "GOA_RUNTIME_HOME=%RUNTIME_HOME%"
set "GOA_RUNTIME_TARGET=%RUNTIME_TARGET%"
set "GOA_RUNTIME_STAGE=%RUNTIME_STAGE%"
set "GOA_RUNTIME_BACKUP=%RUNTIME_BACKUP%"

echo Verifying the optional offline Windows x64 runtime and preparing rollback...
powershell.exe -NoProfile -NonInteractive -Command ^
  "$ErrorActionPreference = 'Stop';" ^
  "$stage = $env:GOA_RUNTIME_STAGE; $target = $env:GOA_RUNTIME_TARGET; $backup = $env:GOA_RUNTIME_BACKUP;" ^
  "try {" ^
  "  if (-not (($env:PROCESSOR_ARCHITECTURE -eq 'AMD64') -or ($env:PROCESSOR_ARCHITEW6432 -eq 'AMD64'))) {throw 'Requires Windows x64 (AMD64)'};" ^
  "  $expected = (Get-Content -Raw -LiteralPath $env:GOA_DIGEST).Trim().ToLowerInvariant();" ^
  "  if ($expected -notmatch '^[0-9a-f]{64}$') {throw 'Invalid SHA-256 manifest'};" ^
  "  $actual = (Get-FileHash -Algorithm SHA256 -LiteralPath $env:GOA_ARCHIVE).Hash.ToLowerInvariant();" ^
  "  if ($actual -ne $expected) {throw ('Runtime checksum mismatch: ' + $actual)};" ^
  "  New-Item -ItemType Directory -Path $env:GOA_RUNTIME_HOME -Force | Out-Null;" ^
  "  if (Test-Path -LiteralPath $stage) {throw 'Temporary installation path already exists'};" ^
  "  New-Item -ItemType Directory -Path $stage | Out-Null;" ^
  "  Expand-Archive -LiteralPath $env:GOA_ARCHIVE -DestinationPath $stage -Force;" ^
  "  $exe = Join-Path $stage 'go_anastruct_worker.exe';" ^
  "  if (-not (Test-Path -LiteralPath $exe -PathType Leaf)) {throw 'Runtime EXE missing from ZIP'};" ^
  "  $check = (& $exe --check | Out-String);" ^
  "  if ($LASTEXITCODE -ne 0 -or $check -notmatch 'anaStruct 1[.]7[.]0 OK') {throw 'Portable solver failed --check'};" ^
  "  if (Test-Path -LiteralPath $backup) {throw 'Backup staging path already exists'};" ^
  "  if (Test-Path -LiteralPath $target) {Move-Item -LiteralPath $target -Destination $backup};" ^
  "  Move-Item -LiteralPath $stage -Destination $target;" ^
  "  if (Test-Path -LiteralPath $backup) {Remove-Item -LiteralPath $backup -Recurse -Force};" ^
  "  Write-Host ('PASS: Portable anaStruct worker installed at ' + $target);" ^
  "} catch {" ^
  "  [Console]::Error.WriteLine(('Portable installation failed: ' + $_));" ^
  "  if (Test-Path -LiteralPath $backup) {" ^
  "    if (Test-Path -LiteralPath $target) {Remove-Item -LiteralPath $target -Recurse -Force -ErrorAction SilentlyContinue};" ^
  "    if (-not (Test-Path -LiteralPath $target)) {Move-Item -LiteralPath $backup -Destination $target};" ^
  "  };" ^
  "  if (Test-Path -LiteralPath $stage) {Remove-Item -LiteralPath $stage -Recurse -Force -ErrorAction SilentlyContinue};" ^
  "  exit 1;" ^
  "}"
if errorlevel 1 (
  echo ERROR: Portable runtime install failed. Any previous runtime was preserved if possible.
  exit /b 1
)
exit /b 0
