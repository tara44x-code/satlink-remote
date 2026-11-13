@echo off
cd /d "%~dp0"
title SatLink Remote PRO - Python 3.11
py -3.11 --version
py -3.11 -m pip install --upgrade pip
py -3.11 -m pip install -r requirements.txt
py -3.11 main.py
pause
