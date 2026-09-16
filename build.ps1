# Builds a standalone Windows app from main.py with Nuitka.
#
# Usage:
#   .\build.ps1                  # build with the default Python
#   .\build.ps1 -Python D:\py\python.exe
#
# Result: dist\gpu_monitor\gpu_monitor.exe  (runnable on a clean machine,
# no Python installation needed).

[CmdletBinding()]
param(
    [string]$Python = "d:\devs\Python314\python.exe",
    [string]$AppName = "gpu_monitor"
)

$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

Write-Host "Using Python: $Python" -ForegroundColor Cyan
& $Python --version
if ($LASTEXITCODE -ne 0) { throw "Python not found at $Python" }

# ---------------------------------------------------------------- prereqs
Write-Host "Checking build dependencies (nuitka)..." -ForegroundColor Cyan
& $Python -c "import nuitka" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Installing nuitka..." -ForegroundColor Yellow
    & $Python -m pip install nuitka
    if ($LASTEXITCODE -ne 0) { throw "pip install failed" }
}

# ---------------------------------------------------------------- build
$buildDir = Join-Path $PSScriptRoot "build"
$distDir  = Join-Path $PSScriptRoot "dist"

Write-Host "Building standalone with Nuitka (this takes a few minutes)..." -ForegroundColor Cyan

& $Python -m nuitka `
    --standalone `
    --output-filename="$AppName.exe" `
    --output-dir="$distDir" `
    --include-package=gpu_monitor `
    --windows-console-mode=disable `
    --remove-output `
    --jobs=0 `
    main.py

if ($LASTEXITCODE -ne 0) { throw "Nuitka build failed (exit $LASTEXITCODE)" }

# Nuitka writes <distDir>\<module>\<exe>; surface it clearly
$exe = Get-ChildItem -Path $distDir -Recurse -Filter "$AppName.exe" |
    Select-Object -First 1
if (-not $exe) { throw "Build finished but $AppName.exe was not found in $distDir" }

Write-Host ""
Write-Host "Build OK:" -ForegroundColor Green
Write-Host "  $($exe.FullName)"
Write-Host "  (the whole folder must be distributed together with the exe)"
