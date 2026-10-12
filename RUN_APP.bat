@echo off
chcp 65001 >nul
title Stock Advisor - SET Risk Profile
cd /d "%~dp0"
echo ============================================
echo   Stock Advisor  -  SET Risk Profile
echo ============================================
echo.

set "PY="
call :try py -3
if not defined PY call :try python
if not defined PY call :try python3
if not defined PY call :trypath "%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
if not defined PY call :trypath "%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
if not defined PY call :trypath "%LOCALAPPDATA%\Programs\Python\Python310\python.exe"
if not defined PY call :trypath "%USERPROFILE%\miniforge3\python.exe"
if not defined PY call :trypath "%USERPROFILE%\miniconda3\python.exe"
if not defined PY call :trypath "%USERPROFILE%\anaconda3\python.exe"
if not defined PY goto nopython

echo [1/3] Found Python:
%PY% --version
echo.

if exist ".venv\Scripts\python.exe" goto haveenv
echo [2/3] Creating virtual environment ... first run only
%PY% -m venv .venv
if errorlevel 1 goto failed
echo       Installing streamlit, pandas, plotly ... 2-3 minutes
".venv\Scripts\python.exe" -m pip install --upgrade pip --quiet
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto failed
goto runapp

:haveenv
echo [2/3] Environment already set up.

:runapp
echo.
echo [3/3] Starting the app ...
echo       Browser opens at  http://localhost:8501
echo       KEEP THIS WINDOW OPEN while presenting.
echo       Press Ctrl+C here to stop.
echo.
".venv\Scripts\python.exe" -m streamlit run app.py
goto end

:try
%* -c "import sys;print(sys.version)" >nul 2>&1
if not errorlevel 1 set "PY=%*"
goto :eof

:trypath
if not exist %1 goto :eof
%1 -c "import sys" >nul 2>&1
if not errorlevel 1 set "PY=%~1"
goto :eof

:nopython
echo.
echo   ###  PYTHON IS NOT INSTALLED ON THIS COMPUTER  ###
echo.
echo   The "python" command found in WindowsApps is only a
echo   Microsoft Store shortcut, not a real Python installation.
echo.
echo   Install it one of these two ways, then run this file again:
echo.
echo   [A] Microsoft Store  - search "Python 3.12" and click Get
echo   [B] python.org       - https://www.python.org/downloads/
echo       IMPORTANT: tick "Add python.exe to PATH" in the installer
echo.
pause
exit /b 1

:failed
echo.
echo   Setup failed. Check your internet connection and try again.
pause
exit /b 1

:end
pause
