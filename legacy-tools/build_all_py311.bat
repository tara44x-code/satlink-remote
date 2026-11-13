@echo off
setlocal EnableExtensions
set "ROOT=%~dp0"
cd /d "%ROOT%"
title SatLink Remote PRO - Build All 2.2.4

echo ==================================================
echo Building SatLink Remote PRO FINAL PRO 2.2.4
echo ==================================================
echo.

echo [1/2] Building Windows Agent EXE...
if exist "%ROOT%windows-agent\build_exe_py311.bat" (
    pushd "%ROOT%windows-agent"
    call build_exe_py311.bat
    popd
) else (
    echo Missing windows-agent\build_exe_py311.bat
)

echo.
echo [2/2] Building SatLinkRelayServer Tray EXE...
if exist "%ROOT%server\build_server_exe_py311.bat" (
    pushd "%ROOT%server"
    call build_server_exe_py311.bat
    popd
) else (
    echo Missing server\build_server_exe_py311.bat
)

echo.
echo Done.
pause
