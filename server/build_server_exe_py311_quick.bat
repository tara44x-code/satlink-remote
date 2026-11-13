@echo off
setlocal EnableExtensions
cd /d "%~dp0"
echo Building SatLink Relay Server EXE PRO 2.1.7
py -3.11 -m pip install --upgrade pip
py -3.11 -m pip install -r requirements.txt
py -3.11 -m pip install pyinstaller==6.10.0
py -3.11 -m PyInstaller --noconfirm --clean --onefile --icon "satlink_server_icon.ico" --name "SatLinkRelayServer" relay_server.py
if errorlevel 1 exit /b 1
echo Done: %cd%\dist\SatLinkRelayServer.exe
exit /b 0
