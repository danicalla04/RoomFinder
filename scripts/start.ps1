param([ValidateSet('.venv-xampp','.venv-modern')][string]$Environment='.venv-xampp')
$ErrorActionPreference='Stop'
$projectRoot=(Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$localDirectory=Join-Path $projectRoot '.local'
New-Item -ItemType Directory -Path $localDirectory -Force | Out-Null
$pythonPath=Join-Path $projectRoot "$Environment/Scripts/python.exe"
if (-not (Test-Path -LiteralPath $pythonPath)) { throw 'Run scripts/setup.ps1 first.' }
$databaseUrlLine=$env:DATABASE_URL
foreach($envFile in @('.env.local','.env','backend/.env')) {
    $envPath=Join-Path $projectRoot $envFile
    if (-not $databaseUrlLine -and (Test-Path -LiteralPath $envPath)) {
        $databaseUrlLine=Get-Content -LiteralPath $envPath | Where-Object { $_ -match '^DATABASE_URL=' } | Select-Object -First 1
    }
}
if (-not $databaseUrlLine -and -not (Get-NetTCPConnection -LocalPort 3306 -State Listen -ErrorAction SilentlyContinue)) { throw 'Start MySQL in XAMPP before starting RoomFinder.' }
$stateFile=Join-Path $localDirectory 'servers.json'
$owned=@()
if (Test-Path -LiteralPath $stateFile) { $parsed=ConvertFrom-Json -InputObject (Get-Content -LiteralPath $stateFile -Raw); foreach($record in $parsed){$owned+=@($record)} }
function Wait-Endpoint([string]$Uri) {
    $limit=(Get-Date).AddSeconds(30)
    do {
        try { $response=Invoke-WebRequest -Uri $Uri -UseBasicParsing -TimeoutSec 3; if($response.StatusCode -eq 200){return} } catch {}
        Start-Sleep -Milliseconds 500
    } while ((Get-Date) -lt $limit)
    throw "Server did not become ready: $Uri. Inspect .local logs."
}
if (-not (Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue)) {
    $managePath=Join-Path $projectRoot 'backend/manage.py'
    $process=Start-Process -FilePath $pythonPath -ArgumentList '-B',('"'+$managePath+'"'),'runserver','127.0.0.1:8000','--noreload' -WorkingDirectory (Join-Path $projectRoot 'backend') -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $localDirectory 'backend.out.log') -RedirectStandardError (Join-Path $localDirectory 'backend.err.log')
    $owned+=@{id=$process.Id;service='backend'}
    ConvertTo-Json -InputObject $owned | Set-Content -LiteralPath $stateFile
}
Wait-Endpoint 'http://127.0.0.1:8000/api/v1/health/'
$health=Invoke-RestMethod 'http://127.0.0.1:8000/api/v1/health/'
if ($databaseUrlLine) {
    if ($health.engine -notmatch 'PostgreSQL') { throw 'Port 8000 is not connected to PostgreSQL.' }
} elseif ($health.database -ne 'roomfinder_db') {
    throw 'Port 8000 belongs to an unexpected application/database.'
}
if (-not (Get-NetTCPConnection -LocalPort 5173 -State Listen -ErrorAction SilentlyContinue)) {
    $nodePath=(Get-Command node -ErrorAction Stop).Source
    $vitePath=Join-Path $projectRoot 'frontend/node_modules/vite/bin/vite.js'
    $process=Start-Process -FilePath $nodePath -ArgumentList ('"'+$vitePath+'"'),'--host','127.0.0.1' -WorkingDirectory (Join-Path $projectRoot 'frontend') -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $localDirectory 'frontend.out.log') -RedirectStandardError (Join-Path $localDirectory 'frontend.err.log')
    $owned+=@{id=$process.Id;service='frontend'}
    ConvertTo-Json -InputObject $owned | Set-Content -LiteralPath $stateFile
}
Wait-Endpoint 'http://127.0.0.1:5173/api/v1/health/'
Write-Host 'RoomFinder frontend: http://localhost:5173'
Write-Host 'Django API: http://127.0.0.1:8000/api/v1/'
Write-Host 'Logs: .local/. Stop the app with scripts/stop.ps1.'
