@echo off
setlocal EnableExtensions
set "ROOT=%~dp0"
set "OUT=%ROOT%dist-final\SatLinkRemotePRO_FINAL_PRO_2_1_7"

if not exist "%ROOT%windows-agent\dist\SatLinkRemotePRO.exe" (
    echo Missing Windows Agent EXE. Run windows-agent\build_exe_py311.bat first.
    exit /b 1
)
if not exist "%ROOT%server\dist\SatLinkRelayServer.exe" (
    echo Missing Relay Server EXE. Run server\build_server_exe_py311.bat first.
    exit /b 1
)

if exist "%OUT%" rmdir /s /q "%OUT%"
mkdir "%OUT%"
mkdir "%OUT%\Windows-Agent"
mkdir "%OUT%\Relay-Server"
mkdir "%OUT%\Android-APK"
mkdir "%OUT%\Docs"

copy /y "%ROOT%windows-agent\dist\SatLinkRemotePRO.exe" "%OUT%\Windows-Agent" >nul
copy /y "%ROOT%server\dist\SatLinkRelayServer.exe" "%OUT%\Relay-Server" >nul
copy /y "%ROOT%START_SATLINK_REMOTE.bat" "%OUT%" >nul
copy /y "%ROOT%REPAIR_START.bat" "%OUT%" >nul

if exist "%ROOT%START_HERE_AR.txt" copy /y "%ROOT%START_HERE_AR.txt" "%OUT%\Docs" >nul
if exist "%ROOT%FINAL_USAGE_AR.txt" copy /y "%ROOT%FINAL_USAGE_AR.txt" "%OUT%\Docs" >nul
if exist "%ROOT%IMPORTANT_SECURITY_AR.txt" copy /y "%ROOT%IMPORTANT_SECURITY_AR.txt" "%OUT%\Docs" >nul

if exist "%ROOT%android-app\app\build\outputs\apk\debug\app-debug.apk" (
    copy /y "%ROOT%android-app\app\build\outputs\apk\debug\app-debug.apk" "%OUT%\Android-APK\SatLinkRemotePRO_DEBUG.apk" >nul
)
if exist "%ROOT%android-app\app\build\outputs\apk\release\app-release.apk" (
    copy /y "%ROOT%android-app\app\build\outputs\apk\release\app-release.apk" "%OUT%\Android-APK\SatLinkRemotePRO_RELEASE.apk" >nul
)

echo Final portable folder created:
echo %OUT%
exit /b 0
