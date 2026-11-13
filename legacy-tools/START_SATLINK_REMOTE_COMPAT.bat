@echo off
setlocal EnableExtensions EnableDelayedExpansion
set "ROOT=%~dp0"
cd /d "%ROOT%"

title SatLink Remote PRO - FINAL PRO 2.2.4 Compatibility Launcher

echo ==================================================
echo SatLink Remote PRO - FINAL PRO 2.2.4
echo Developer: Muhannad Sat Link
echo Compatibility Launcher: x64 / x86 / Python fallback
echo ==================================================
echo.

call :DETECT_ARCH
echo Windows detected: %OSARCH%
echo.

if exist "%ROOT%server\show_server_url.py" (
    echo Server URL for Android:
    pushd "%ROOT%server" >nul
    py -3.11 show_server_url.py
    popd >nul
    echo.
)

echo [1/2] Starting SatLinkRelayServer...
call :START_SERVER

echo Waiting 4 seconds for server...
timeout /t 4 /nobreak >nul

echo [2/2] Starting SatLink Remote PRO Windows Agent...
call :START_AGENT

echo.
echo Done.
echo If an EXE cannot run on this PC, this launcher will use Python source mode.
echo.
pause
exit /b 0

:DETECT_ARCH
set "OSARCH=x64"
if /i "%PROCESSOR_ARCHITECTURE%"=="x86" (
    if "%PROCESSOR_ARCHITEW6432%"=="" set "OSARCH=x86"
)
exit /b 0

:START_SERVER
if /i "%OSARCH%"=="x86" (
    if exist "%ROOT%server\dist-x86\SatLinkRelayServer_x86.exe" (
        start "SatLinkRelayServer_x86" /D "%ROOT%server\dist-x86" "%ROOT%server\dist-x86\SatLinkRelayServer_x86.exe"
        exit /b 0
    )
) else (
    if exist "%ROOT%server\dist-x64\SatLinkRelayServer_x64.exe" (
        start "SatLinkRelayServer_x64" /D "%ROOT%server\dist-x64" "%ROOT%server\dist-x64\SatLinkRelayServer_x64.exe"
        exit /b 0
    )
    if exist "%ROOT%server\dist\SatLinkRelayServer.exe" (
        start "SatLinkRelayServer" /D "%ROOT%server\dist" "%ROOT%server\dist\SatLinkRelayServer.exe"
        exit /b 0
    )
)
if exist "%ROOT%server\run_server_tray_py311.bat" (
    start "SatLinkRelayServerTray" /D "%ROOT%server" cmd /c "call run_server_tray_py311.bat"
) else if exist "%ROOT%server\run_server_py311.bat" (
    start "SatLinkRelayServer" /D "%ROOT%server" cmd /c "call run_server_py311.bat"
) else (
    echo ERROR: Server launcher is missing.
)
exit /b 0

:START_AGENT
if /i "%OSARCH%"=="x86" (
    if exist "%ROOT%windows-agent\dist-x86\SatLinkRemotePRO_x86.exe" (
        start "SatLinkRemotePRO_x86" /D "%ROOT%windows-agent\dist-x86" "%ROOT%windows-agent\dist-x86\SatLinkRemotePRO_x86.exe"
        exit /b 0
    )
) else (
    if exist "%ROOT%windows-agent\dist-x64\SatLinkRemotePRO_x64.exe" (
        start "SatLinkRemotePRO_x64" /D "%ROOT%windows-agent\dist-x64" "%ROOT%windows-agent\dist-x64\SatLinkRemotePRO_x64.exe"
        exit /b 0
    )
    if exist "%ROOT%windows-agent\dist\SatLinkRemotePRO.exe" (
        start "SatLinkRemotePRO" /D "%ROOT%windows-agent\dist" "%ROOT%windows-agent\dist\SatLinkRemotePRO.exe"
        exit /b 0
    )
)
if exist "%ROOT%windows-agent\run_py311.bat" (
    start "SatLinkRemotePRO" /D "%ROOT%windows-agent" cmd /k "call run_py311.bat"
) else (
    echo ERROR: Agent launcher is missing.
)
exit /b 0
