# 终端启动环境

## 推荐配置

项目已经验证以下环境：

- Windows PowerShell 7.6.5
- Python 3.13.15
- Java（Android Studio 使用）
- 项目虚拟环境：`.venv`

初始化项目：

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\scripts\setup.ps1
```

设置本地 dry-run 配置：

```powershell
$env:COLLECTOR_TOKEN = "local-test-token"
$env:ADMIN_TOKEN = "local-admin-token"
$env:DRY_RUN = "true"
```

启动：

```powershell
.\scripts\start-server.ps1
```

如果 PowerShell 脚本执行策略受限，使用 cmd 入口：

```bat
set COLLECTOR_TOKEN=local-test-token
set ADMIN_TOKEN=local-admin-token
set DRY_RUN=true
scripts\start-server.cmd
```

## Codex 终端权限

本项目只需要在本地监听 `127.0.0.1`，不需要管理员权限。若 Codex 返回 `helper_unknown_error: setup refresh had errors`，说明终端辅助进程被当前沙箱策略拦截：

1. 重新执行终端命令并允许“提升权限”；
2. 工作目录选择 `D:\vibe_coding\clash_of_clans\message_sync`；
3. 使用 `powershell.exe` 或 `cmd.exe` 作为 shell；
4. 不要把 QQ Token、管理员 Token 写进脚本或提交到 Git。

提升权限只用于启动诊断/开发进程，不会自动安装系统软件，也不会开放公网端口。终端验证命令：

```powershell
Get-Location
python --version
.\.venv\Scripts\python.exe -m pytest -q
```

## Android 构建环境

Android 项目需要在 Android Studio 中打开 `android-collector/`。当前主机已检测到 Java，但没有检测到 `ANDROID_HOME`/`ANDROID_SDK_ROOT`，也没有 Gradle Wrapper；因此 Android SDK/Gradle 应通过 Android Studio 安装和管理，不建议由服务端启动脚本自动修改系统环境。

