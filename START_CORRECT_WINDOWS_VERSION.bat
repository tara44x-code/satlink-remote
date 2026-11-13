@echo off
setlocal EnableExtensions
set "ROOT=%~dp0"
set "ARCH=%PROCESSOR_ARCHITECTURE%"
if defined PROCESSOR_ARCHITEW6432 set "ARCH=%PROCESSOR_ARCHITEW6432%"

if /I "%ARCH%"=="x86" goto :X86
if /I "%ARCH%"=="AMD64" goto :X64
if /I "%ARCH%"=="ARM64" goto :X64

echo ERROR: Unsupported or unknown Windows architecture: %ARCH%
pause
exit /b 1

:X64
if not exist "%ROOT%Windows-x64\SatLinkRemotePRO.exe" goto :MISSING
start "SatLinkRemotePRO x64" /D "%ROOT%Windows-x64" "%ROOT%Windows-x64\SatLinkRemotePRO.exe"
exit /b 0

:X86
if not exist "%ROOT%Windows-x86\SatLinkRemotePRO.exe" goto :MISSING
start "SatLinkRemotePRO x86" /D "%ROOT%Windows-x86" "%ROOT%Windows-x86\SatLinkRemotePRO.exe"
exit /b 0

:MISSING
echo ERROR: The required program file was not found.
echo Run BUILD_DUAL_ARCH_RELEASE.bat first on the build PC.
pause
exit /b 2
