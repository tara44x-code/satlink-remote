@echo off
setlocal EnableExtensions
set "ROOT=%~dp0"
cd /d "%ROOT%"
title Build SatLinkRelayServer x64

echo [x64] Checking Python 3.11 64-bit...
py -3.11-64 --version >nul 2>&1
if errorlevel 1 goto :NO_PY

py -3.11-64 -m pip install --upgrade pip
py -3.11-64 -m pip install -r requirements.txt
py -3.11-64 -m pip install pyinstaller==6.10.0 pystray==0.19.5 pillow==10.4.0
if errorlevel 1 goto :FAIL

if exist build-x64 rmdir /s /q build-x64
if exist dist-x64 rmdir /s /q dist-x64
py -3.11-64 -m PyInstaller --noconfirm --clean --onefile --windowed --name SatLinkRelayServer_x64 --icon satlink_server_icon.ico --distpath dist-x64 --workpath build-x64 server_tray.py
if errorlevel 1 goto :FAIL
if not exist "dist-x64\SatLinkRelayServer_x64.exe" goto :FAIL

echo BUILD_OK: %ROOT%dist-x64\SatLinkRelayServer_x64.exe
exit /b 0

:NO_PY
echo ERROR: Python 3.11 64-bit was not found.
exit /b 31

:FAIL
echo ERROR: x64 relay server build failed.
exit /b 32
