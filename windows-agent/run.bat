@echo off
setlocal EnableExtensions
cd /d "%~dp0"

title SatLink Remote PRO - Windows Agent

echo ============================================
echo SatLink Remote PRO - Windows Agent
echo Developer: Muhannad Sat Link
echo Version: PRO 2.2.4
echo ============================================
echo.

set "PY="

py -3.12 --version >nul 2>&1
if not errorlevel 1 set "PY=py -3.12"

if not defined PY (
    py -3.11 --version >nul 2>&1
    if not errorlevel 1 set "PY=py -3.11"
)

if not defined PY (
    echo ERROR: Python 3.12 or Python 3.11 was not found.
    echo.
    echo Please install Python 3.11 or 3.12 and enable: Add python.exe to PATH
    echo Do not use Python 3.14 for this project.
    echo.
    pause
    exit /b 1
)

echo Using Python:
%PY% --version

echo.
echo Upgrading pip...
%PY% -m pip install --upgrade pip
if errorlevel 1 goto install_error

echo.
echo Installing requirements...
%PY% -m pip install -r requirements.txt
if errorlevel 1 goto install_error

echo.
echo Starting SatLink Remote PRO...
%PY% main.py
pause
exit /b 0

:install_error
echo.
echo Install failed.
echo Make sure you installed Python 3.11/3.12 64-bit and checked Add python.exe to PATH.
echo.
pause
exit /b 1
