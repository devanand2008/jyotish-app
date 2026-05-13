@echo off
setlocal EnableDelayedExpansion
title Jyotish App 3.0 - Tamil Vedic Astrology Platform
cls

echo.
echo  +====================================================+
echo  ^|  JYOTISH ASTROLOGY 3.0  --  Tamil Vedic Platform  ^|
echo  ^|  Python FastAPI  +  Ephem Engine  +  Frontend     ^|
echo  +====================================================+
echo.

:: ---- PATHS --------------------------------------------------
set "ROOT=%~dp0"
if "%ROOT:~-1%"=="\" set "ROOT=%ROOT:~0,-1%"

set "BACKEND=%ROOT%\backend"
set "VENV_PY=%BACKEND%\venv\Scripts\python.exe"
set "VENV_PKGS=%BACKEND%\venv\Lib\site-packages"
set "LAN_IP="
for /f "tokens=2 delims=:" %%I in ('ipconfig ^| findstr /C:"IPv4 Address"') do if not defined LAN_IP set "LAN_IP=%%I"
if defined LAN_IP set "LAN_IP=%LAN_IP: =%"

echo  Project Root  : %ROOT%
echo  Backend Path  : %BACKEND%
echo  Python (venv) : %VENV_PY%
if defined LAN_IP echo  Phone URL     : http://%LAN_IP%:8080/login.html
if defined LAN_IP echo  Note          : Google mobile login needs Render HTTPS or an HTTPS tunnel.
echo.

:: ---- STEP 1: Locate Python ----------------------------------
echo  [1/4] Locating Python...

if exist "%VENV_PY%" (
    set "PY=%VENV_PY%"
    echo        [OK] venv Python found.
) else (
    echo        [WARN] venv not found. Checking system Python...
    where python >nul 2>&1
    if !errorlevel! == 0 (
        set "PY=python"
        echo        [OK] Using system Python.
    ) else (
        echo.
        echo  [ERROR] Python not found!
        echo          To fix, open CMD and run:
        echo          cd "%BACKEND%"
        echo          python -m venv venv
        pause
        exit /b 1
    )
)

:: ---- STEP 2: Check packages by import -----------------------
echo.
echo  [2/4] Checking core dependencies...
"%PY%" -c "import os, platform; platform.machine=(lambda: 'AMD64') if os.name=='nt' else platform.machine; import fastapi, uvicorn, ephem, sqlalchemy, google.oauth2.id_token, jose, openpyxl" >nul 2>&1
if !errorlevel! == 0 (
    echo        [OK] All dependencies already installed.
) else (
    echo        [INFO] Some packages missing. Installing now - one time setup...
    echo        This may take a few minutes on first run...
    "%PY%" -m pip install -q fastapi "uvicorn[standard]" pydantic python-multipart "ephem>=4.1" sqlalchemy google-auth requests "python-jose[cryptography]" "passlib[bcrypt]" openpyxl
    if !errorlevel! == 0 (
        echo        [OK] Dependencies installed successfully.
    ) else (
        echo        [WARN] Install had issues -- trying to start anyway.
    )
)

:: ---- STEP 3: Free port 8080 ---------------------------------
echo.
echo  [3/4] Checking port 8080...
for /f "tokens=5" %%P in ('netstat -aon 2^>nul ^| findstr ":8080 " ^| findstr "LISTENING"') do (
    echo        Freeing PID %%P on port 8080...
    taskkill /f /pid %%P >nul 2>&1
)
ping -n 2 127.0.0.1 >nul
echo        [OK] Port 8080 clear.

:: ---- STEP 4: Start FastAPI backend --------------------------
echo.
echo  [4/4] Starting FastAPI Backend on port 8080...
echo        Working dir: %BACKEND%
echo.

start "Jyotish-Backend" cmd /k "cd /d "%BACKEND%" && "%PY%" -m uvicorn main:app --reload --host 0.0.0.0 --port 8080"

echo  [4.5/4] Starting Video Signaling Server on port 5000...
start "Jyotish-Video-Server" cmd /k "cd /d "%ROOT%\backend-video" && npm install cors express socket.io && node server.js"

:: ---- Wait for backend to boot --------------------------------
echo  Waiting for backend to start (6 sec)...
ping -n 7 127.0.0.1 >nul

:: ---- Open browser -------------------------------------------
echo.
echo  Opening frontend from FastAPI server...
start "" "http://localhost:8080/login.html"

:: ---- Status banner ------------------------------------------
echo.
echo  +====================================================+
echo  ^|        JYOTISH APP 3.0 IS RUNNING!               ^|
echo  ^|                                                   ^|
echo  ^|  App URL       :  http://localhost:8080           ^|
if defined LAN_IP echo  ^|  Phone URL     :  http://%LAN_IP%:8080/login.html ^|
echo  ^|  Mobile Google :  Use Render HTTPS, not private IP     ^|
echo  ^|  API Docs      :  http://localhost:8080/docs      ^|
echo  ^|  Health Check  :  http://localhost:8080/health    ^|
echo  ^|                                                   ^|  
echo  ^|  Press any key to STOP all services...           ^|
echo  +====================================================+
echo.
pause >nul

:: ---- Shutdown -----------------------------------------------
color 0C
echo.
echo  Stopping Jyotish backend...
taskkill /f /fi "WINDOWTITLE eq Jyotish-Backend*" >nul 2>&1
for /f "tokens=5" %%P in ('netstat -aon 2^>nul ^| findstr ":8080 " ^| findstr "LISTENING"') do (
    taskkill /f /pid %%P >nul 2>&1
)
echo  [DONE] All services stopped. Goodbye!
ping -n 3 127.0.0.1 >nul
exit /b 0
