@echo off
setlocal
echo Stopping services on ports 8000 (backend) and 5173 (frontend) ...
for %%P in (8000 5173) do (
  for /f "tokens=5" %%A in ('netstat -ano ^| findstr ":%%P" ^| findstr "LISTENING"') do (
    echo   port %%P : PID %%A
    taskkill /PID %%A /F >nul 2>&1
  )
)
taskkill /FI "WINDOWTITLE eq LostFound Backend" /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq LostFound Frontend" /F >nul 2>&1
echo Done.
timeout /t 3 /nobreak >nul
