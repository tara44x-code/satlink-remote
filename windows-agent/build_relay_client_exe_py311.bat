@echo off
setlocal
cd /d "%~dp0"
echo Building optional standalone Relay Client EXE...
py -3.11 -m pip install --upgrade pip
py -3.11 -m pip install -r requirements.txt
py -3.11 -m pip install pyinstaller==6.10.0
py -3.11 -m PyInstaller --noconfirm --clean --onefile --name "SatLinkRelayClient" relay_client.py
if errorlevel 1 (
    echo Build failed.
    pause
    exit /b 1
)
echo Done: %cd%\dist\SatLinkRelayClient.exe
pause
