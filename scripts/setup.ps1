param(
    [switch] $SkipInstall
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $projectRoot

if (-not (Get-Command python.exe -ErrorAction SilentlyContinue)) {
    throw "未找到 python.exe，请先安装 Python 3.11+ 并加入 PATH。"
}

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    Write-Host "创建项目虚拟环境 .venv ..."
    python -m venv .venv
}

if (-not $SkipInstall) {
    Write-Host "安装/更新 Python 依赖 ..."
    & ".\.venv\Scripts\python.exe" -m pip install --disable-pip-version-check -r requirements.txt
}

Write-Host "验证项目语法和测试 ..."
& ".\.venv\Scripts\python.exe" -m compileall -q app scripts
& ".\.venv\Scripts\python.exe" -m pytest -q
Write-Host "项目环境准备完成。"

