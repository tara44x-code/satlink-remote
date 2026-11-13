@echo off
setlocal EnableExtensions

echo ==================================================
echo SatLink Remote PRO - Windows Compatibility Check
echo ==================================================
echo.
echo Processor architecture variables:
echo PROCESSOR_ARCHITECTURE=%PROCESSOR_ARCHITECTURE%
echo PROCESSOR_ARCHITEW6432=%PROCESSOR_ARCHITEW6432%
echo.

if /i "%PROCESSOR_ARCHITECTURE%"=="x86" (
    if "%PROCESSOR_ARCHITEW6432%"=="" (
        echo Result: Windows 32-bit / x86
        echo Use x86 EXE or source Python mode.
    ) else (
        echo Result: Windows 64-bit running 32-bit shell
        echo Use x64 EXE.
    )
) else (
    echo Result: Windows 64-bit / x64
    echo Use x64 EXE.
)

echo.
echo Optional detailed Windows info:
wmic os get osarchitecture 2>nul

echo.
pause
