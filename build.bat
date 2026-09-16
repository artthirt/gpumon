@echo off
rem Wrapper for build.ps1 - double-click or run from cmd.
rem Optional: pass a different Python, e.g.  build.bat D:\py\python.exe
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0build.ps1" %*
if errorlevel 1 (
    echo.
    echo Build FAILED - see messages above.
    pause
    exit /b 1
)
echo.
pause
