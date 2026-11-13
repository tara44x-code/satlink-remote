@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title SatLinkRelayServer - PRO 2.1.7

echo =============================================
echo SatLinkRelayServer - PRO 2.1.7
echo Developer: Muhannad Sat Link
echo Port: 7777
echo =============================================
echo.
echo Server URL for Android:
py -3.11 show_server_url.py
echo.
echo If Windows Firewall appears, choose Allow access for Private networks.
echo Keep this window open while testing Relay.
echo.
py -3.11 -m pip install --upgrade pip
py -3.11 -m pip install -r requirements.txt
py -3.11 relay_server.py
pause
