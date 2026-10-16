# 部落冲突 → QQ 群消息同步

这是一个可运行的消息桥接服务：Android 采集端把部落聊天消息发送到 FastAPI，服务端负责去重、持久化和重试，再通过 OneBot 兼容接口发送到 QQ 群。

## 快速启动

`.env.example` 只是配置模板；下面使用 PowerShell 环境变量启动。若使用 Docker Compose、systemd 或其他进程管理器，请在对应的 secrets/environment 配置中设置同名变量。未配置 Token 时接口会拒绝请求，这是有意的安全默认值。

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:COLLECTOR_TOKEN = "local-test-token"
$env:ADMIN_TOKEN = "local-admin-token"
$env:DRY_RUN = "true"
uvicorn app.main:app --reload
```

也可以使用项目脚本自动准备环境：

```powershell
.\scripts\setup.ps1
$env:COLLECTOR_TOKEN = "local-test-token"
$env:ADMIN_TOKEN = "local-admin-token"
.\scripts\start-server.ps1
```

如果 PowerShell 禁止执行本地脚本，可只对当前进程放开：

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

终端工具若提示无法启动辅助进程，请在 Codex 中允许“提升权限”后重试；这属于运行环境权限问题，不是项目代码问题。

完整说明见 [终端环境配置](docs/terminal-environment.md)。若 PowerShell 执行策略受限，可使用 `scripts\start-server.cmd`。

检查服务：

```powershell
curl http://127.0.0.1:8000/healthz
python scripts/send_test_message.py --token local-test-token
curl -H "X-Admin-Token: local-admin-token" http://127.0.0.1:8000/api/v1/admin/outbox

# PowerShell alternative
.\scripts\post_message.ps1 -Token local-test-token -Content "晚上一起打部落战"
```

Docker Compose 启动：

```powershell
Copy-Item .env.example .env
# 编辑 .env 后执行
docker compose up -d --build
```

当 `DRY_RUN=false` 时，服务启动会校验 `ONEBOT_URL` 和 `QQ_GROUP_ID`；缺少任一配置会直接失败，避免误以为消息已经发送到 QQ。

默认 `DRY_RUN=true` 时，消息会写入 SQLite 并在日志中打印，不会访问 QQ。接入 OneBot 时设置：

```text
DRY_RUN=false
ONEBOT_URL=http://127.0.0.1:3000
ONEBOT_ACCESS_TOKEN=your-token
QQ_GROUP_ID=your-group-id
```

QQ 机器人账号需要已经加入目标群；OneBot 适配器需要允许 HTTP API 调用。推荐使用专用 QQ 账号，并限制服务端端口只允许内网或可信来源访问。

## 接口

### `POST /api/v1/messages`

采集端使用 `X-Collector-Token` 鉴权。首次接收返回 `202`，重复消息返回 `200`，响应中的 `duplicate` 标识是否已经入队。

### `GET /healthz`

返回当前是否为 dry-run 以及 QQ 连接配置是否完整。

### `GET /metrics`

返回 Prometheus 格式的进程内计数器，可用于观察接收、去重和投递失败数量。该接口不包含聊天内容；如服务暴露到公网，建议在反向代理层限制访问。

### `GET /api/v1/admin/outbox`

使用 `X-Admin-Token` 查看 `pending`、`sent`、`failed` 等投递状态数量。

### `POST /api/v1/admin/outbox/retry?limit=100`

管理员手动把失败消息重新放回队列。适用于 QQ 机器人短暂离线恢复后的补发。

### `GET /api/v1/admin/messages?limit=20`

管理员查看最近消息及其投递状态。接口受 `X-Admin-Token` 保护，不应暴露到公网。

## 测试

安装依赖后运行：

```powershell
pytest -q
```

## 生产注意事项

- 不能通过 Supercell 官方 API 直接读取部落聊天；Android 端需要用 AccessibilityService 或 OCR 读取屏幕。
- 不要修改游戏客户端、注入代码或抓取私有通信协议。
- 必须征得部落成员同意，只采集部落聊天区域。
- 请将 `COLLECTOR_TOKEN`、`ADMIN_TOKEN` 和 QQ Token 换成随机长字符串，并使用 HTTPS。
- OCR 识别规则需要随着游戏 UI 更新维护；服务端的队列、去重和重试逻辑不依赖具体 OCR 实现。
- 当前 Android OCR 默认裁剪屏幕下方 55% 区域，真机联调时需要确认聊天框位置并校准比例。
- 采集接口默认每个来源 IP 每分钟最多接受 120 条消息，可通过 `COLLECTOR_RATE_LIMIT_PER_MINUTE` 调整。

## Android 采集器

`android-collector/` 提供 Kotlin AccessibilityService + Android 11+ 截图 OCR 示例。两条路径使用相同 HTTP 协议、本地队列和去重逻辑；OCR 默认识别屏幕下方区域，并可在应用内关闭。请阅读 [docs/android-collector.md](docs/android-collector.md)；实际聊天区域比例需要在真机上校准。

部署和故障处理见 [docs/operations.md](docs/operations.md)。

生产反向代理模板位于 `deploy/`。请使用 HTTPS，并将管理接口、指标和 `/readyz` 限制在内网或 VPN。
