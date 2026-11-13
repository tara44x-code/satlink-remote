@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title SatLinkRelayServer AutoStart - PRO 2.2.4

REM Do not print Arabic text here to avoid Windows BAT encoding problems.
REM This starts SatLinkRelayServer in system tray mode only.

where pyw >nul 2>&1
if errorlevel 1 (
    start "" py -3.11 "%~dp0server_tray.py" --minimized --autostart
) else (
    start "" pyw -3.11 "%~dp0server_tray.py" --minimized --autostart
)
exit /b 0
