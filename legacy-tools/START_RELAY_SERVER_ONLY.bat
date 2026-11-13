@echo off
setlocal EnableExtensions
set "ROOT=%~dp0"
cd /d "%ROOT%server"
title Start SatLinkRelayServer Only - PRO 2.2.4
call run_server_tray_py311.bat
exit /b 0
