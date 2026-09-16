@echo off
REM ============================================================
REM  GPU Monitor - build a standalone one-file EXE with Nuitka
REM
REM  Produces:  build\gpumon.exe
REM  Recipe is the same as the checked-working video-downloader
REM  build (standalone + onefile + pyside6 plugin, no console).
REM  Requires: Visual Studio 2022 with the C++ build tools.
REM ============================================================
setlocal

set "PYTHON=d:\devs\Python314\python.exe"
set "APP=main.py"
set "OUT=build"

echo === [1/3] Importing MSVC x64 environment (vcvars64) ===
set "VS_PATH="
for /f "usebackq tokens=*" %%i in (`"C:\Program Files (x86)\Microsoft Visual Studio\Installer\vswhere.exe" -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath`) do set "VS_PATH=%%i"
if not defined VS_PATH (
    echo FAILED: Visual Studio 2022 with C++ tools not found
    exit /b 1
)
echo Found: %VS_PATH%
call "%VS_PATH%\VC\Auxiliary\Build\vcvars64.bat" >nul
if not defined INCLUDE (
    echo FAILED: vcvars64 did not set up the environment
    exit /b 1
)

echo === [2/3] Installing/updating Nuitka build dependencies ===
%PYTHON% -m pip install --quiet nuitka ordered-set zstandard
if errorlevel 1 (
    echo FAILED: pip install of Nuitka dependencies
    exit /b 1
)

echo === [3/3] Building standalone one-file EXE (takes several minutes) ===
%PYTHON% -m nuitka ^
    --standalone ^
    --onefile ^
    --enable-plugin=pyside6 ^
    --windows-disable-console ^
    --include-windows-runtime-dlls=yes ^
    --remove-output ^
    --output-filename=gpumon.exe ^
    --output-dir=%OUT% ^
    %APP%

if errorlevel 1 (
    echo.
    echo FAILED: Nuitka build exited with an error
    exit /b 1
)

echo.
echo === Done: %OUT%\gpumon.exe ===
echo Run it directly or copy the EXE anywhere (no Python needed).
endlocal
