@echo off
setlocal EnableExtensions
set "ROOT=%~dp0"
cd /d "%ROOT%"
title SatLink Remote PRO 2.2.4 Repair

echo 1. Start main program in unified mode
echo 2. Remove old separate AutoStart entries
echo 3. Build unified EXE release
echo 4. Exit
set /p "CHOICE=Choose: "
if "%CHOICE%"=="1" call "%ROOT%START_SATLINK_REMOTE.bat"
if "%CHOICE%"=="2" call "%ROOT%REMOVE_OLD_SEPARATE_AUTOSTART.bat"
if "%CHOICE%"=="3" call "%ROOT%BUILD_UNIFIED_RELEASE.bat"
exit /b 0
