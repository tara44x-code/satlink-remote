@echo off
cd /d "%~dp0"
title SatLink Remote PRO - Python 3.12
py -3.12 --version
py -3.12 -m pip install --upgrade pip
py -3.12 -m pip install -r requirements.txt
py -3.12 main.py
pause
