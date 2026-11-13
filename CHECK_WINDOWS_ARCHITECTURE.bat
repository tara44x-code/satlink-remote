@echo off
setlocal EnableExtensions
set "ARCH=%PROCESSOR_ARCHITECTURE%"
if defined PROCESSOR_ARCHITEW6432 set "ARCH=%PROCESSOR_ARCHITEW6432%"

echo Windows architecture: %ARCH%
if /I "%ARCH%"=="x86" (
  echo Recommended folder: Windows-x86
) else if /I "%ARCH%"=="AMD64" (
  echo Recommended folder: Windows-x64
) else if /I "%ARCH%"=="ARM64" (
  echo Recommended folder: Windows-x64 ^(Windows ARM emulation may be required^)
) else (
  echo Unknown architecture. Check Settings ^> System ^> About ^> System type.
)
pause
