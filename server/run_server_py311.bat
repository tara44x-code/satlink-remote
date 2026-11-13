@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title SatLinkRelayServer - PRO 2.2.4

echo =============================================
echo SatLinkRelayServer - PRO 2.2.4
echo Developer: Muhannad Sat Link
echo Port: 7777
echo =============================================
echo.
echo This is the console mode. For tray mode use run_server_tray_py311.bat
echo Server URL for Android:
py -3.11 show_server_url.py
echo.
py -3.11 -m pip install --upgrade pip
py -3.11 -m pip install -r requirements.txt
py -3.11 relay_server.py
pause
