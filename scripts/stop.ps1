$ErrorActionPreference='Stop'
$projectRoot=(Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$stateFile=Join-Path $projectRoot '.local/servers.json'
if (-not (Test-Path -LiteralPath $stateFile)) { Write-Host 'No RoomFinder server processes were recorded.'; return }
# Assign parsed JSON directly: Windows PowerShell can wrap JSON arrays when
# ConvertFrom-Json is evaluated inside an array subexpression.
$records=ConvertFrom-Json -InputObject (Get-Content -LiteralPath $stateFile -Raw)
function Stop-OwnedProcess([int]$TargetId) {
    $process=Get-CimInstance Win32_Process -Filter "ProcessId = $TargetId" -ErrorAction SilentlyContinue
    if (-not $process) { return }
    if (-not $process.CommandLine -or $process.CommandLine.IndexOf($projectRoot,[System.StringComparison]::OrdinalIgnoreCase) -lt 0) {
        Write-Warning "Skipped process ${TargetId}: it no longer belongs to this RoomFinder checkout."
        return
    }
    # Windows venv python.exe can launch the underlying interpreter as a child.
    # Stop only descendants whose command also names this exact project path.
    $children=Get-CimInstance Win32_Process -Filter "ParentProcessId = $TargetId" -ErrorAction SilentlyContinue
    foreach($child in $children) {
        if($child.CommandLine -and $child.CommandLine.IndexOf($projectRoot,[System.StringComparison]::OrdinalIgnoreCase) -ge 0){Stop-OwnedProcess $child.ProcessId}
    }
    Stop-Process -Id $TargetId -ErrorAction SilentlyContinue
}
foreach ($record in $records) {
    Stop-OwnedProcess ([int]$record.id)
    Write-Host "Stopped $($record.service)."
}
Set-Content -LiteralPath $stateFile -Value '[]'
