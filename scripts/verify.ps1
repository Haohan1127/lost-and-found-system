param([switch]$Browser)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$pythonPath = Join-Path $projectRoot '.venv\Scripts\python.exe'
function Invoke-Checked {
    param([string]$Program, [string[]]$CommandArguments)
    & $Program @CommandArguments
    if ($LASTEXITCODE -ne 0) { throw "Command failed ($LASTEXITCODE): $Program" }
}
Push-Location $projectRoot
try {
    $env:PYTHONUTF8 = '1'
    Invoke-Checked $pythonPath @('backend/manage.py', 'check')
    Invoke-Checked $pythonPath @('backend/manage.py', 'makemigrations', '--check', '--dry-run')
    Invoke-Checked $pythonPath @('backend/manage.py', 'test', 'tests', 'users.tests', '--noinput')
    Push-Location (Join-Path $projectRoot 'frontend')
    try {
        Invoke-Checked 'npm.cmd' @('test')
        Invoke-Checked 'npm.cmd' @('run', 'build')
        if ($Browser) { Invoke-Checked 'npm.cmd' @('run', 'test:e2e') }
    } finally { Pop-Location }
} finally { Pop-Location }
