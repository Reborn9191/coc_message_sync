param(
    [string] $Output = "backups\messages-$((Get-Date).ToString('yyyyMMdd-HHmmss')).db"
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $projectRoot
if (-not (Test-Path ".venv\Scripts\python.exe")) {
    throw "未找到 .venv。请先运行 .\scripts\setup.ps1"
}
& ".\.venv\Scripts\python.exe" scripts\backup-db.py --output $Output

