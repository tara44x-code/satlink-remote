@echo off
setlocal EnableExtensions
set "ROOT=%~dp0"
set "OUT=%ROOT%dist-unified\SatLinkRemotePRO"
cd /d "%ROOT%"
title Build SatLink Remote PRO 2.3.0 Neon Release

echo ==================================================
echo Building SatLink Remote PRO 2.3.0 Neon Release
echo Output: dist-unified\SatLinkRemotePRO
echo ==================================================
echo.

py -3.11 --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python 3.11 was not found.
    pause
    exit /b 1
)

py -3.11 -m pip install --upgrade pip
py -3.11 -m pip install pyinstaller==6.10.0
py -3.11 -m pip install -r "%ROOT%windows-agent\requirements.txt"
py -3.11 -m pip install -r "%ROOT%server\requirements.txt"
if errorlevel 1 goto :FAIL

echo [1/2] Building SatLinkRelayServer.exe...
pushd "%ROOT%server"
py -3.11 -m PyInstaller --noconfirm --clean --onefile --windowed --icon "satlink_server_icon.ico" --name "SatLinkRelayServer" server_tray.py
if errorlevel 1 (popd & goto :FAIL)
popd

echo [2/2] Building SatLinkRemotePRO.exe...
pushd "%ROOT%windows-agent"
py -3.11 -m PyInstaller --noconfirm --clean --onefile --windowed --icon "assets\satlink_remote.ico" --name "SatLinkRemotePRO" main.py
if errorlevel 1 (popd & goto :FAIL)
popd

if exist "%OUT%" rmdir /s /q "%OUT%"
mkdir "%OUT%"
copy /y "%ROOT%windows-agent\dist\SatLinkRemotePRO.exe" "%OUT%\SatLinkRemotePRO.exe" >nul
copy /y "%ROOT%server\dist\SatLinkRelayServer.exe" "%OUT%\SatLinkRelayServer.exe" >nul
copy /y "%ROOT%server\server_config.json" "%OUT%\server_config.json" >nul
copy /y "%ROOT%server\satlink_server_icon.ico" "%OUT%\satlink_server_icon.ico" >nul
copy /y "%ROOT%UNIFIED_START_HERE_AR.txt" "%OUT%\UNIFIED_START_HERE_AR.txt" >nul
copy /y "%ROOT%README_2_3_0_NEON_AR.txt" "%OUT%\README_2_3_0_NEON_AR.txt" >nul

echo.
echo BUILD SUCCESSFUL
echo Run only: %OUT%\SatLinkRemotePRO.exe
echo SatLinkRelayServer.exe will start automatically beside it.
pause
exit /b 0

:FAIL
echo.
echo BUILD FAILED. Review the error above.
pause
exit /b 1
