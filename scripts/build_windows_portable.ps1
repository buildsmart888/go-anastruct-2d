# Build on Windows 10/11 x64 using Python 3.11 (release maintainer task).
# Creates a standalone anaStruct binary; never runs on an end user's PC.
$ErrorActionPreference = 'Stop'
$Root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
Set-Location $Root
python -m pip install --disable-pip-version-check 'numpy==2.2.6' 'anastruct==1.7.0' 'pyinstaller==6.16.0'
if ($LASTEXITCODE -ne 0) { throw 'Pinned build dependencies could not be installed' }
python -m PyInstaller --noconfirm --clean --onedir --console --name go_anastruct_worker --paths $Root --collect-all anastruct --collect-all numpy --copy-metadata anastruct --copy-metadata numpy tools/worker_entry.py
if ($LASTEXITCODE -ne 0) { throw 'PyInstaller failed' }
$Exe = Join-Path $Root 'dist/go_anastruct_worker/go_anastruct_worker.exe'
if (-not (Test-Path $Exe)) { throw 'Worker executable missing' }
& $Exe --check
if ($LASTEXITCODE -ne 0) { throw 'Standalone worker check failed' }
$Target = Join-Path $Root 'dist/go_anastruct_2d-runtime-windows-x64-v0.5.5.zip'
if (Test-Path $Target) { Remove-Item -LiteralPath $Target -Force }
Compress-Archive -Path (Join-Path $Root 'dist/go_anastruct_worker/*') -DestinationPath $Target
(Get-FileHash -Algorithm SHA256 -LiteralPath $Target).Hash.ToLowerInvariant() |
    Set-Content -LiteralPath "$Target.sha256" -NoNewline -Encoding ascii
Write-Host "Built portable Windows runtime: $Target"
Write-Host "SHA256: $((Get-FileHash -Algorithm SHA256 -LiteralPath $Target).Hash.ToLowerInvariant())"
