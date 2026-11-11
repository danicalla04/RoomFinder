param([ValidateSet('.venv-xampp','.venv-modern')][string]$Environment='.venv-xampp',[switch]$Browser)
$ErrorActionPreference='Stop'
$projectRoot=(Resolve-Path (Join-Path $PSScriptRoot '..')).Path
& (Join-Path $projectRoot "$Environment/Scripts/python.exe") -B (Join-Path $projectRoot 'backend/manage.py') test accounts bookings hotels rooms --noinput
if($LASTEXITCODE -ne 0){throw 'Database tests failed.'}
Push-Location (Join-Path $projectRoot 'frontend')
try {
    npm run build
    if($LASTEXITCODE -ne 0){throw 'Frontend build failed.'}
    if($Browser){npm run test:e2e;if($LASTEXITCODE -ne 0){throw 'Browser tests failed.'}}
} finally { Pop-Location }
