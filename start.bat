@echo off
setlocal enabledelayedexpansion
set "SCRIPT_DIR=%~dp0"
set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"

echo.
echo ============================================
echo   LIPS IDE
echo ============================================

:: ── Python 3.11+ ─────────────────────────────────────────────────────────────
set "SYS_PYTHON="
for %%c in (python3 python) do (
  if "!SYS_PYTHON!"=="" (
    %%c --version >nul 2>&1 && (
      for /f %%v in ('%%c -c "import sys; print(1 if sys.version_info >= (3,11) else 0)" 2^>nul') do (
        if "%%v"=="1" set "SYS_PYTHON=%%c"
      )
    )
  )
)
if "!SYS_PYTHON!"=="" (
  echo  [ERROR] Python 3.11+ required - https://python.org
  goto :fail
)
for /f "tokens=*" %%v in ('!SYS_PYTHON! --version 2^>^&1') do echo  [OK] %%v

:: ── Node 18+ ─────────────────────────────────────────────────────────────────
node --version >nul 2>&1 || (
  echo  [ERROR] Node.js 18+ required - https://nodejs.org
  goto :fail
)
for /f %%v in ('node -e "process.stdout.write(process.version.slice(1).split(^'.^')[0])"') do set "NODE_MAJOR=%%v"
if !NODE_MAJOR! LSS 18 (
  echo  [ERROR] Node.js 18+ required
  goto :fail
)
for /f "tokens=*" %%v in ('node --version') do echo  [OK] Node.js %%v

npm --version >nul 2>&1 || (
  echo  [ERROR] npm required (ships with Node.js)
  goto :fail
)
for /f "tokens=*" %%v in ('npm --version') do echo  [OK] npm %%v

:: ── Virtual environment ───────────────────────────────────────────────────────
echo.
echo ── Setting up virtual environment

set "VENV=%SCRIPT_DIR%\.venv"
set "PYTHON=%VENV%\Scripts\python.exe"

if not exist "!PYTHON!" (
  !SYS_PYTHON! -m venv "!VENV!"
  echo  [OK] Created virtual environment at .venv\
) else (
  echo  [OK] Using existing virtual environment at .venv\
)

:: ── Port checks ──────────────────────────────────────────────────────────────
echo.
echo ── Checking ports

"!PYTHON!" -c "import socket; s=socket.socket(); s.settimeout(1); r=s.connect_ex(('127.0.0.1',8000)); s.close(); exit(0 if r==0 else 1)" >nul 2>&1
if !errorlevel!==0 (
  echo  [ERROR] Port 8000 is already in use.
  echo          Find the process: netstat -ano ^| findstr :8000
  echo          Stop it with:     taskkill /F /PID ^<pid^>
  goto :fail
)
echo  [OK] Port 8000 is free

"!PYTHON!" -c "import socket; s=socket.socket(); s.settimeout(1); r=s.connect_ex(('127.0.0.1',5173)); s.close(); exit(0 if r==0 else 1)" >nul 2>&1
if !errorlevel!==0 (
  echo  [ERROR] Port 5173 is already in use.
  echo          Find the process: netstat -ano ^| findstr :5173
  echo          Stop it with:     taskkill /F /PID ^<pid^>
  goto :fail
)
echo  [OK] Port 5173 is free

:: ── Backend ───────────────────────────────────────────────────────────────────
echo.
echo ── Starting backend

"!PYTHON!" -m pip install -e "%SCRIPT_DIR%\lips" -r "%SCRIPT_DIR%\backend\requirements.txt" -q --disable-pip-version-check
echo  [OK] Python dependencies ready (lips installed as editable package)

cd /d "%SCRIPT_DIR%\backend"
start /b "!PYTHON!" -m uvicorn main:app --reload --port 8000 --log-level warning
echo  [OK] FastAPI server started

:: Poll until backend responds (up to 15 s)
echo  Waiting for backend...
set "READY=0"
for /l %%i in (1,1,30) do (
  if "!READY!"=="0" (
    "!PYTHON!" -c "import urllib.request,sys; urllib.request.urlopen('http://localhost:8000/api/templates',timeout=1); sys.exit(0)" >nul 2>&1
    if !errorlevel!==0 (
      set "READY=1"
    ) else (
      timeout /t 1 /nobreak >nul
    )
  )
)
if "!READY!"=="1" (
  echo  [OK] Backend ready
) else (
  echo  [WARN] Backend health-check timed out (may still be starting)
)

:: ── Frontend ─────────────────────────────────────────────────────────────────
echo.
echo ── Starting frontend
cd /d "%SCRIPT_DIR%\frontend"

call npm install --silent
echo  [OK] Node dependencies ready

start /b npm run dev
echo  [OK] Vite dev server started

:: ── Ready ─────────────────────────────────────────────────────────────────────
echo.
echo ============================================
echo   Frontend -^> http://localhost:5173  ^<- open this
echo   Backend  -^> http://localhost:8000
echo ============================================
echo   Both servers are running in the background.
echo   Close this window or press Ctrl+C to stop.
echo.

:: Keep window open
pause >nul
goto :eof

:fail
echo.
pause
exit /b 1
