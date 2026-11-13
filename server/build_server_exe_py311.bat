@echo off
setlocal EnableExtensions
cd /d "%~dp0"
echo =============================================
echo Building SatLinkRelayServer Tray EXE
echo Version: PRO 2.2.4
echo =============================================
py -3.11 -m pip install --upgrade pip
py -3.11 -m pip install -r requirements.txt
py -3.11 -m pip install pyinstaller==6.10.0
py -3.11 -m PyInstaller --noconfirm --clean --onefile --windowed --icon "satlink_server_icon.ico" --name "SatLinkRelayServer" server_tray.py
if errorlevel 1 (
    echo Build failed. Check the error above.
    pause
    exit /b 1
)
echo.
echo Done. EXE location:
echo %cd%\dist\SatLinkRelayServer.exe
echo.
echo This EXE runs in tray mode. Press X to hide it near the clock.
pause
