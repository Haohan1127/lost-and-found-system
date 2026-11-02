$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Push-Location (Join-Path $projectRoot 'frontend')
try {
    & npm.cmd run dev
    if ($LASTEXITCODE -ne 0) { throw "Frontend stopped with exit code $LASTEXITCODE" }
} finally { Pop-Location }
