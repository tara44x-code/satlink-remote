@echo off
setlocal EnableExtensions
set "STARTUP=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"

echo Removing old separate server startup entries...
del /q "%STARTUP%\SatLinkRelayServer_AutoStart.vbs" >nul 2>&1
del /q "%STARTUP%\SatLinkRemotePRO_Agent_AutoStart.bat" >nul 2>&1
del /q "%STARTUP%\SatLinkRemotePRO_Compat.lnk" >nul 2>&1
schtasks /Delete /TN "SatLinkRelayServer" /F >nul 2>&1

echo Done. Use the main program button: Run with Windows.
pause
