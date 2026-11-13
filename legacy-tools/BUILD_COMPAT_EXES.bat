@echo off
setlocal EnableExtensions
set "ROOT=%~dp0"
cd /d "%ROOT%"

title SatLink Remote PRO - Build Compatibility EXEs

echo ==================================================
echo SatLink Remote PRO - Build x64 / x86 if available
echo ==================================================
echo.

echo This script tries to build:
echo - Windows Agent x64 using py -3.11
echo - Server x64 using py -3.11
echo - Windows Agent x86 using py -3.11-32 if installed
echo - Server x86 using py -3.11-32 if installed
echo.

echo [1/4] Agent x64...
call "%ROOT%windows-agent\build_exe_py311_x64.bat"

echo.
echo [2/4] Server x64...
call "%ROOT%server\build_server_exe_py311_x64.bat"

echo.
echo [3/4] Agent x86...
call "%ROOT%windows-agent\build_exe_py311_x86.bat"

echo.
echo [4/4] Server x86...
call "%ROOT%server\build_server_exe_py311_x86.bat"

echo.
echo Build attempt finished.
echo Check windows-agent\dist-x64, windows-agent\dist-x86, server\dist-x64, server\dist-x86.
echo.
pause
