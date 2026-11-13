@echo off
setlocal EnableExtensions
set "ROOT=%~dp0"
set "OUT=%ROOT%dist-dual\SatLinkRemotePRO_DUAL"
cd /d "%ROOT%"
title Build SatLink Remote PRO 2.2.4 x64 and x86

echo =====================================================
echo SatLink Remote PRO 2.2.4 Dual Architecture Builder
echo Builds separate Windows x64 and Windows x86 folders.
echo =====================================================
echo.

call "%ROOT%windows-agent\build_exe_py311_x64.bat"
if errorlevel 1 goto :FAIL_X64_AGENT
call "%ROOT%server\build_server_exe_py311_x64.bat"
if errorlevel 1 goto :FAIL_X64_SERVER

call "%ROOT%windows-agent\build_exe_py311_x86.bat"
if errorlevel 1 goto :FAIL_X86_AGENT
call "%ROOT%server\build_server_exe_py311_x86.bat"
if errorlevel 1 goto :FAIL_X86_SERVER

if exist "%OUT%" rmdir /s /q "%OUT%"
mkdir "%OUT%\Windows-x64"
mkdir "%OUT%\Windows-x86"
mkdir "%OUT%\Android"

copy /y "%ROOT%windows-agent\dist-x64\SatLinkRemotePRO_x64.exe" "%OUT%\Windows-x64\SatLinkRemotePRO.exe" >nul
copy /y "%ROOT%server\dist-x64\SatLinkRelayServer_x64.exe" "%OUT%\Windows-x64\SatLinkRelayServer.exe" >nul
copy /y "%ROOT%server\server_config.json" "%OUT%\Windows-x64\server_config.json" >nul

copy /y "%ROOT%windows-agent\dist-x86\SatLinkRemotePRO_x86.exe" "%OUT%\Windows-x86\SatLinkRemotePRO.exe" >nul
copy /y "%ROOT%server\dist-x86\SatLinkRelayServer_x86.exe" "%OUT%\Windows-x86\SatLinkRelayServer.exe" >nul
copy /y "%ROOT%server\server_config.json" "%OUT%\Windows-x86\server_config.json" >nul

copy /y "%ROOT%START_CORRECT_WINDOWS_VERSION.bat" "%OUT%\START_CORRECT_WINDOWS_VERSION.bat" >nul
copy /y "%ROOT%README_DUAL_ARCH_AR.txt" "%OUT%\README_DUAL_ARCH_AR.txt" >nul
copy /y "%ROOT%CHECK_WINDOWS_ARCHITECTURE.bat" "%OUT%\CHECK_WINDOWS_ARCHITECTURE.bat" >nul
copy /y "%ROOT%android-app\BUILD_APK_AR.txt" "%OUT%\Android\BUILD_APK_AR.txt" >nul

if not exist "%OUT%\Windows-x64\SatLinkRemotePRO.exe" goto :COPY_FAIL
if not exist "%OUT%\Windows-x64\SatLinkRelayServer.exe" goto :COPY_FAIL
if not exist "%OUT%\Windows-x86\SatLinkRemotePRO.exe" goto :COPY_FAIL
if not exist "%OUT%\Windows-x86\SatLinkRelayServer.exe" goto :COPY_FAIL

echo.
echo BUILD SUCCESSFUL
echo Output: %OUT%
echo Use START_CORRECT_WINDOWS_VERSION.bat on the target PC.
pause
exit /b 0

:FAIL_X64_AGENT
echo ERROR: Failed to build the x64 main program.
goto :FAIL
:FAIL_X64_SERVER
echo ERROR: Failed to build the x64 relay server.
goto :FAIL
:FAIL_X86_AGENT
echo ERROR: Failed to build the x86 main program.
echo Python 3.11 32-bit must be installed on the build PC.
goto :FAIL
:FAIL_X86_SERVER
echo ERROR: Failed to build the x86 relay server.
goto :FAIL
:COPY_FAIL
echo ERROR: A required EXE was not copied to the release folder.
:FAIL
pause
exit /b 1
