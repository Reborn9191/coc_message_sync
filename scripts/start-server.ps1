param(
    [int] $Port = 8000,
    [switch] $RealQQ
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $projectRoot

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    throw "未找到 .venv。请先运行 .\scripts\setup.ps1"
}

if (-not $env:COLLECTOR_TOKEN) {
    throw "必须先设置 COLLECTOR_TOKEN，例如 `$env:COLLECTOR_TOKEN='change-this'"
}
if (-not $env:ADMIN_TOKEN) {
    throw "必须先设置 ADMIN_TOKEN，例如 `$env:ADMIN_TOKEN='change-this-admin'"
}

if ($RealQQ) {
    $env:DRY_RUN = "false"
    foreach ($name in @("ONEBOT_URL", "QQ_GROUP_ID")) {
        if (-not (Get-Item "Env:$name" -ErrorAction SilentlyContinue)) {
            throw "真实 QQ 模式必须设置 $name"
        }
    }
} else {
    $env:DRY_RUN = "true"
}

if (-not $env:DB_PATH) { $env:DB_PATH = "data/messages.db" }
Write-Host "启动消息桥接服务: http://127.0.0.1:$Port"
& ".\.venv\Scripts\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port $Port

