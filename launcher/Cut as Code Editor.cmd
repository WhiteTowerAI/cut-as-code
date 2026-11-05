@echo off
setlocal
if exist "%~dp0..\runtime\hub-client.cjs" if not defined CAC_EDITOR_DATA set "CAC_EDITOR_DATA=%~dp0..\work\editor-data"
node "%~dp0launcher.cjs"
set "launcher_exit=%errorlevel%"
if not "%launcher_exit%"=="0" pause
exit /b %launcher_exit%
