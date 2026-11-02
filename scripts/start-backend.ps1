$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$pythonPath = Join-Path $projectRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $pythonPath)) { throw 'Run scripts/setup.ps1 first.' }
Push-Location $projectRoot
try {
    $env:PYTHONUTF8 = '1'
    & $pythonPath backend/manage.py runserver 127.0.0.1:8000 --noreload
    if ($LASTEXITCODE -ne 0) { throw "Backend stopped with exit code $LASTEXITCODE" }
} finally { Pop-Location }
