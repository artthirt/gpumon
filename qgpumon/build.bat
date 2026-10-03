@echo off
rem Configure + build qgpumon (MSVC 2026 + Ninja + Qt 6.12)
setlocal
call "C:\Program Files\Microsoft Visual Studio\18\Professional\VC\Auxiliary\Build\vcvars64.bat" >nul
set PATH=%PATH%;D:\devs\Python314\Scripts
cd /d %~dp0
if not exist build (
    cmake -S . -B build -G Ninja -DCMAKE_BUILD_TYPE=Release -DCMAKE_PREFIX_PATH=D:/devs/Qt/6.12.0/msvc2022_64 || exit /b 1
)
cmake --build build --target qgpumon || exit /b 1
endlocal
