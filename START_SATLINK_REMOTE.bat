@echo off
setlocal EnableExtensions
set "ROOT=%~dp0"
cd /d "%ROOT%"
title SatLink Remote PRO 2.3.0 Neon Launcher

echo ==================================================
echo SatLink Remote PRO - PRO 2.3.0 Neon Auto Start
echo The main program starts SatLinkRelayServer itself.
echo ==================================================
echo.

if exist "%ROOT%dist-unified\SatLinkRemotePRO\SatLinkRemotePRO.exe" (
    start "SatLinkRemotePRO" /D "%ROOT%dist-unified\SatLinkRemotePRO" "%ROOT%dist-unified\SatLinkRemotePRO\SatLinkRemotePRO.exe"
    exit /b 0
)

if exist "%ROOT%SatLinkRemotePRO.exe" (
    start "SatLinkRemotePRO" /D "%ROOT%" "%ROOT%SatLinkRemotePRO.exe"
    exit /b 0
)

if exist "%ROOT%windows-agent\dist\SatLinkRemotePRO.exe" (
    start "SatLinkRemotePRO" /D "%ROOT%windows-agent\dist" "%ROOT%windows-agent\dist\SatLinkRemotePRO.exe"
    exit /b 0
)

if exist "%ROOT%windows-agent\run_py311.bat" (
    start "SatLinkRemotePRO" /D "%ROOT%windows-agent" cmd /c "call run_py311.bat"
    exit /b 0
)

echo ERROR: SatLinkRemotePRO launcher was not found.
pause
exit /b 1
