@echo off
setlocal EnableExtensions
cd /d "%~dp0"
echo Building SatLink Remote PRO Windows Agent EXE PRO 2.1.7
py -3.11 -m pip install --upgrade pip
py -3.11 -m pip install -r requirements.txt
py -3.11 -m pip install pyinstaller==6.10.0
if not exist assets mkdir assets
py -3.11 -m PyInstaller --noconfirm --clean --onefile --windowed --icon "assets\satlink_remote.ico" --name "SatLinkRemotePRO" main.py
if errorlevel 1 exit /b 1
echo Done: %cd%\dist\SatLinkRemotePRO.exe
exit /b 0
