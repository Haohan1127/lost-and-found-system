@echo off
setlocal
set "ROOT=%~dp0"
if not exist "%ROOT%.venv\Scripts\python.exe" (
  echo [ERROR] Python venv not found: %ROOT%.venv
  echo Run scripts\setup.ps1 first.
  pause
  exit /b 1
)
if not exist "%ROOT%frontend\node_modules" (
  echo [ERROR] frontend dependencies not found.
  echo Run scripts\setup.ps1 first.
  pause
  exit /b 1
)
echo Starting backend  : http://127.0.0.1:8000
start "LostFound Backend" /d "%ROOT%" cmd /k "set PYTHONUTF8=1&& .venv\Scripts\python.exe backend\manage.py runserver 127.0.0.1:8000 --noreload"
echo Starting frontend : http://127.0.0.1:5173
start "LostFound Frontend" /d "%ROOT%frontend" cmd /k "npm.cmd run dev -- --host 127.0.0.1 --port 5173"
echo Waiting for services to become ready ...
timeout /t 9 /nobreak >nul
start "" "http://127.0.0.1:5173"
echo.
echo App URL: http://127.0.0.1:5173
echo Demo accounts / one-time binding codes: see README.md
echo To stop the servers: run Stop-LostFound.bat (Chinese name: 停止失物招领.bat)
echo You can close this window now.
timeout /t 6 /nobreak >nul
