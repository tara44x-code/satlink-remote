@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title SatLinkRelayServer Tray Launcher - PRO 2.2.4

echo =============================================
echo SatLinkRelayServer Tray - PRO 2.2.4
echo Developer: Muhannad Sat Link
echo Mode: X button hides to system tray
echo =============================================

echo Installing server requirements if needed...
py -3.11 -m pip install --upgrade pip
py -3.11 -m pip install -r requirements.txt

echo Starting SatLinkRelayServer tray app...
where pyw >nul 2>&1
if errorlevel 1 (
    start "" py -3.11 "%~dp0server_tray.py"
) else (
    start "" pyw -3.11 "%~dp0server_tray.py"
)
exit /b 0
