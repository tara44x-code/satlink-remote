@echo off
setlocal EnableExtensions
cd /d "%~dp0"
echo =============================================
echo Building SatLink Remote PRO Windows Agent EXE
echo Version: PRO 2.1.7
echo =============================================
py -3.11 -m pip install --upgrade pip
py -3.11 -m pip install -r requirements.txt
py -3.11 -m pip install pyinstaller==6.10.0
if not exist assets mkdir assets
py -3.11 -m PyInstaller --noconfirm --clean --onefile --windowed --icon "assets\satlink_remote.ico" --name "SatLinkRemotePRO" main.py
if errorlevel 1 (
    echo.
    echo Build failed. Check the error above.
    pause
    exit /b 1
)
echo.
echo Done. EXE location:
echo %cd%\dist\SatLinkRemotePRO.exe
pause
