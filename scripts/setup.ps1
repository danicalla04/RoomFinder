param([string]$XamppPath='C:/xampp',[switch]$ModernDatabase)
$ErrorActionPreference='Stop'
$projectRoot=(Resolve-Path (Join-Path $PSScriptRoot '..')).Path
function Assert-Exit { if ($LASTEXITCODE -ne 0) { throw "Command failed with exit code $LASTEXITCODE" } }
$uvPath=Join-Path $projectRoot '.venv/Scripts/uv.exe'
if (-not (Test-Path -LiteralPath $uvPath)) {
    $bootstrap=Join-Path $projectRoot '.bootstrap'
    python -m venv $bootstrap
    Assert-Exit
    & (Join-Path $bootstrap 'Scripts/python.exe') -m pip install uv
    Assert-Exit
    $uvPath=Join-Path $bootstrap 'Scripts/uv.exe'
}
$neonEnvPath=Join-Path $projectRoot '.env.local'
$useNeon=(Test-Path -LiteralPath $neonEnvPath) -and [bool](Get-Content -LiteralPath $neonEnvPath | Where-Object { $_ -match '^DATABASE_URL=' } | Select-Object -First 1)
$environment=if($ModernDatabase -or $useNeon){'.venv-modern'}else{'.venv-xampp'}
$pythonPath=Join-Path $projectRoot "$environment/Scripts/python.exe"
if (-not (Test-Path -LiteralPath $pythonPath)) {
    & $uvPath venv --python 3.12 (Join-Path $projectRoot $environment)
    Assert-Exit
}
$requirements=if($ModernDatabase -or $useNeon){'requirements.txt'}else{'requirements-xampp.txt'}
& $uvPath pip install --python $pythonPath -r (Join-Path $projectRoot "backend/$requirements")
Assert-Exit
$localDirectory=Join-Path $projectRoot '.local'
New-Item -ItemType Directory -Path $localDirectory -Force | Out-Null
if (-not $useNeon -and -not (Get-NetTCPConnection -State Listen -LocalPort 3306 -ErrorAction SilentlyContinue)) {
    $mysql=Join-Path $XamppPath 'mysql/bin/mysqld.exe'
    if (-not (Test-Path -LiteralPath $mysql)) { throw "XAMPP MySQL was not found at $mysql. Install XAMPP or supply -XamppPath." }
    $mysqlConfig=Join-Path $XamppPath 'mysql/bin/my.ini'
    Start-Process -FilePath $mysql -ArgumentList "--defaults-file=$mysqlConfig",'--standalone' -WorkingDirectory (Split-Path $mysql) -WindowStyle Hidden -RedirectStandardOutput (Join-Path $localDirectory 'mysql.out.log') -RedirectStandardError (Join-Path $localDirectory 'mysql.err.log') | Out-Null
    $limit=(Get-Date).AddSeconds(20)
    while (-not (Get-NetTCPConnection -State Listen -LocalPort 3306 -ErrorAction SilentlyContinue)) {
        if ((Get-Date) -gt $limit) { throw 'MySQL did not start. Inspect .local/mysql.err.log and XAMPP logs; check port conflicts.' }
        Start-Sleep -Milliseconds 500
    }
}
if (-not $useNeon) {
    & $pythonPath -B (Join-Path $projectRoot 'scripts/initialize_database.py')
    Assert-Exit
}
Push-Location (Join-Path $projectRoot 'backend')
try {
    & $pythonPath -B manage.py migrate --noinput
    Assert-Exit
    if (-not $useNeon) {
        & $pythonPath -B manage.py seed_demo
        Assert-Exit
    }
    & $pythonPath -B manage.py check
    Assert-Exit
} finally { Pop-Location }
Push-Location (Join-Path $projectRoot 'frontend')
try { npm ci; Assert-Exit; npm run build; Assert-Exit } finally { Pop-Location }
Write-Host "Setup complete. Run ./scripts/start.ps1 -Environment $environment"
