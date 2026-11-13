@echo off
setlocal EnableExtensions
set "ROOT=%~dp0"
cd /d "%ROOT%"
title Build SatLinkRemotePRO x86

echo [x86] Checking Python 3.11 32-bit...
py -3.11-32 --version >nul 2>&1
if errorlevel 1 goto :NO_PY

py -3.11-32 -m pip install --upgrade pip
py -3.11-32 -m pip install -r requirements.txt
py -3.11-32 -m pip install pyinstaller==6.10.0
if errorlevel 1 goto :FAIL

if exist build-x86 rmdir /s /q build-x86
if exist dist-x86 rmdir /s /q dist-x86
py -3.11-32 -m PyInstaller --noconfirm --clean --onefile --windowed --name SatLinkRemotePRO_x86 --icon assets\satlink_remote.ico --distpath dist-x86 --workpath build-x86 main.py
if errorlevel 1 goto :FAIL
if not exist "dist-x86\SatLinkRemotePRO_x86.exe" goto :FAIL

echo BUILD_OK: %ROOT%dist-x86\SatLinkRemotePRO_x86.exe
exit /b 0

:NO_PY
echo ERROR: Python 3.11 32-bit was not found.
echo Install Python 3.11 x86 and enable the Python Launcher.
exit /b 21

:FAIL
echo ERROR: x86 agent build failed.
exit /b 22
