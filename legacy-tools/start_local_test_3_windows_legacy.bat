@echo off
setlocal EnableExtensions
set "ROOT=%~dp0"
cd /d "%ROOT%"

title SatLink Remote PRO - Legacy 3 Window Test

echo =============================================
echo SatLink Remote PRO - Legacy 3 Window Test
echo Version: PRO 2.1.7 BAT Clean Fix
echo =============================================
echo.
echo This launcher opens 3 windows:
echo 1. Relay Server
echo 2. Windows Agent
echo 3. Standalone Relay Client
echo.
echo Use this only if the one-click Relay inside the Windows Agent has a problem.
echo.
pause

start "SatLinkRelayServer" /D "%ROOT%server" cmd /k "call run_server_py311.bat"
timeout /t 2 /nobreak >nul
start "SatLinkRemotePRO" /D "%ROOT%windows-agent" cmd /k "call run_py311.bat"
timeout /t 4 /nobreak >nul
start "SatLinkRelayClient Legacy" /D "%ROOT%windows-agent" cmd /k "call run_relay_client_py311.bat"
