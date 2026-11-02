param([switch]$ResetDemoPasswords)
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
    if (-not (Test-Path -LiteralPath $pythonPath)) {
        Invoke-Checked 'python' @('-m', 'venv', '.venv')
    }
    # Use the Tsinghua PyPI mirror by default to avoid timeouts; override with PIP_INDEX_URL.
    $pipIndex = if ($env:PIP_INDEX_URL) { $env:PIP_INDEX_URL } else { 'https://pypi.tuna.tsinghua.edu.cn/simple' }
    Invoke-Checked $pythonPath @('-m', 'pip', 'install', '-i', $pipIndex, '-r', 'backend/requirements.txt')
    Push-Location (Join-Path $projectRoot 'frontend')
    try { Invoke-Checked 'npm.cmd' @('ci', '--no-audit', '--no-fund') }
    finally { Pop-Location }
    Invoke-Checked $pythonPath @('backend/manage.py', 'migrate', '--noinput')
    $seedArguments = @('backend/manage.py', 'seed_demo')
    if ($ResetDemoPasswords) { $seedArguments += '--reset-passwords' }
    Invoke-Checked $pythonPath $seedArguments
    Invoke-Checked $pythonPath @('backend/manage.py', 'seed_demo_users')
    Write-Host 'Ready. Start backend and frontend in two separate terminals.'
} finally { Pop-Location }
