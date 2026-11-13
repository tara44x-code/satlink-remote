@echo off
cd /d "%~dp0"
py -3.11 -m pip install requests
py -3.11 relay_client.py
pause
