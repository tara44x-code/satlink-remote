@echo off
setlocal EnableExtensions
set "ROOT=%~dp0"
cd /d "%ROOT%"
title Build SatLinkRelayServer x86

echo [x86] Checking Python 3.11 32-bit...
py -3.11-32 --version >nul 2>&1
if errorlevel 1 goto :NO_PY

py -3.11-32 -m pip install --upgrade pip
py -3.11-32 -m pip install -r requirements.txt
py -3.11-32 -m pip install pyinstaller==6.10.0 pystray==0.19.5 pillow==10.4.0
if errorlevel 1 goto :FAIL

if exist build-x86 rmdir /s /q build-x86
if exist dist-x86 rmdir /s /q dist-x86
py -3.11-32 -m PyInstaller --noconfirm --clean --onefile --windowed --name SatLinkRelayServer_x86 --icon satlink_server_icon.ico --distpath dist-x86 --workpath build-x86 server_tray.py
if errorlevel 1 goto :FAIL
if not exist "dist-x86\SatLinkRelayServer_x86.exe" goto :FAIL

echo BUILD_OK: %ROOT%dist-x86\SatLinkRelayServer_x86.exe
exit /b 0

:NO_PY
echo ERROR: Python 3.11 32-bit was not found.
exit /b 41

:FAIL
echo ERROR: x86 relay server build failed.
exit /b 42
