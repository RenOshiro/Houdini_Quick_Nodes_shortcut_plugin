@echo off
rem Network Shortcuts installer for Windows. Double-click to install; no Python needed.
rem Extra arguments are passed to install.py, e.g.  install.bat --uninstall   or   install.bat --list
setlocal EnableDelayedExpansion
cd /d "%~dp0"

set "RUNNER="
rem 1) Houdini's own Python (hython) - newest installed version
for /f "delims=" %%D in ('dir /b /ad /o-n "%ProgramFiles%\Side Effects Software\Houdini *" 2^>nul') do (
    if not defined RUNNER if exist "%ProgramFiles%\Side Effects Software\%%D\bin\hython.exe" (
        set "RUNNER=%ProgramFiles%\Side Effects Software\%%D\bin\hython.exe"
    )
)
rem 2) HFS from a Houdini command prompt
if not defined RUNNER if defined HFS if exist "%HFS%\bin\hython.exe" set "RUNNER=%HFS%\bin\hython.exe"
rem 3) any Python 3 on PATH
if not defined RUNNER (
    where python >nul 2>nul && set "RUNNER=python"
)
if not defined RUNNER (
    echo Could not find Houdini ^(hython^) or Python 3.
    echo Install Python 3, or run:  "C:\Program Files\Side Effects Software\Houdini XX.X.XXX\bin\hython.exe" install.py
    if not defined NS_NO_PAUSE pause
    exit /b 1
)

echo Using: !RUNNER!
"!RUNNER!" install.py %*
set "RC=%ERRORLEVEL%"
echo.
if not defined NS_NO_PAUSE pause
exit /b %RC%
