@echo off
setlocal
for %%I in ("%~dp0.") do set "PROJECT=%%~fI"
set "PYCHARM=C:\pyc\PyCharm 2026.2.1\bin\pycharm64.exe"
if not exist "%PYCHARM%" set "PYCHARM=%ProgramFiles%\JetBrains\PyCharm 2026.2.1\bin\pycharm64.exe"
if not exist "%PYCHARM%" set "PYCHARM=%LOCALAPPDATA%\Programs\PyCharm\bin\pycharm64.exe"
if not exist "%PYCHARM%" (
  echo PyCharm not found. Please open this folder with your IDE manually.
  pause
  exit /b 1
)
start "" "%PYCHARM%" "%PROJECT%"
