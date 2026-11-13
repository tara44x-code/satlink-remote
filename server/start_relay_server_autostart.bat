@echo off
setlocal EnableExtensions
set "SERVER_DIR=%~dp0"
set "LOG_DIR=%SERVER_DIR%logs"
set "LOG_FILE=%LOG_DIR%autostart.log"
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%" >nul 2>&1

echo [%DATE% %TIME%] SatLinkRelayServer AutoStart begin >> "%LOG_FILE%"
cd /d "%SERVER_DIR%" >> "%LOG_FILE%" 2>&1

if exist "%SERVER_DIR%dist\SatLinkRelayServer.exe" (
    echo Starting EXE dist\SatLinkRelayServer.exe >> "%LOG_FILE%"
    start "" /D "%SERVER_DIR%dist" "%SERVER_DIR%dist\SatLinkRelayServer.exe" --minimized --autostart
    exit /b 0
)

if exist "%SERVER_DIR%dist-x64\SatLinkRelayServer_x64.exe" (
    echo Starting EXE dist-x64\SatLinkRelayServer_x64.exe >> "%LOG_FILE%"
    start "" /D "%SERVER_DIR%dist-x64" "%SERVER_DIR%dist-x64\SatLinkRelayServer_x64.exe" --minimized --autostart
    exit /b 0
)

if exist "%SERVER_DIR%dist-x86\SatLinkRelayServer_x86.exe" (
    echo Starting EXE dist-x86\SatLinkRelayServer_x86.exe >> "%LOG_FILE%"
    start "" /D "%SERVER_DIR%dist-x86" "%SERVER_DIR%dist-x86\SatLinkRelayServer_x86.exe" --minimized --autostart
    exit /b 0
)

echo Starting Python source mode >> "%LOG_FILE%"
where pyw >nul 2>&1
if errorlevel 1 (
    start "" py -3.11 "%SERVER_DIR%server_tray.py" --minimized --autostart
) else (
    start "" pyw -3.11 "%SERVER_DIR%server_tray.py" --minimized --autostart
)
exit /b 0
