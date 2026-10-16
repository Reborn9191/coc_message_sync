# 运维手册

## 启动前检查

```powershell
$env:COLLECTOR_TOKEN = "随机长 Token"
$env:ADMIN_TOKEN = "另一个随机长 Token"
$env:DRY_RUN = "false"
$env:ONEBOT_URL = "http://127.0.0.1:3000"
$env:ONEBOT_ACCESS_TOKEN = "OneBot Token"
$env:QQ_GROUP_ID = "123456789"
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

先访问 `/healthz`。只有 `qq_configured=true` 且 `dry_run=false` 时，才表示服务已配置真实 QQ 投递。

## 生产 HTTPS

不要把 Uvicorn 的 8000 端口直接暴露到公网。`deploy/Caddyfile.example` 和 `deploy/nginx.example.conf` 提供反向代理模板：

- Android 设备只需要访问 `/api/v1/messages`；
- `/api/v1/admin/*`、`/metrics`、`/readyz` 应限制在内网或 VPN；
- 使用 Caddy 时由 Caddy 自动申请和续期证书；
- 使用 Nginx 时需自行配置 Let's Encrypt 证书续期。

`/healthz` 只表示服务进程可用；`/readyz` 在 `DRY_RUN=false` 时还会检查 OneBot 的 `get_status`。

## 日常检查

```powershell
curl -H "X-Admin-Token: <ADMIN_TOKEN>" http://127.0.0.1:8000/api/v1/admin/outbox
curl -H "X-Admin-Token: <ADMIN_TOKEN>" http://127.0.0.1:8000/api/v1/admin/messages?limit=20
```

暂停/恢复同步：

```powershell
curl -X POST -H "X-Admin-Token: <ADMIN_TOKEN>" "http://127.0.0.1:8000/api/v1/admin/sync?enabled=false"
curl -X POST -H "X-Admin-Token: <ADMIN_TOKEN>" "http://127.0.0.1:8000/api/v1/admin/sync?enabled=true"
```

定期清理历史数据：

```powershell
curl -X POST -H "X-Admin-Token: <ADMIN_TOKEN>" "http://127.0.0.1:8000/api/v1/admin/maintenance/purge?retention_days=30"
```

管理员操作审计：

```powershell
curl -H "X-Admin-Token: <ADMIN_TOKEN>" "http://127.0.0.1:8000/api/v1/admin/audit?limit=50"
```

在线备份 SQLite：

```powershell
.\scripts\backup-db.ps1
```

建议每天至少备份一次，并定期验证备份文件可以被 SQLite 打开。备份包含消息内容和投递记录，应使用与正式数据库相同的访问控制和加密策略。

如果 QQ 机器人短暂掉线，恢复后执行：

```powershell
curl -X POST -H "X-Admin-Token: <ADMIN_TOKEN>" `
  "http://127.0.0.1:8000/api/v1/admin/outbox/retry?limit=100"
```

## 安全边界

- `/api/v1/messages` 只给 Android 采集器使用，必须通过 HTTPS 暴露。
- `/api/v1/admin/*` 包含聊天内容和运维操作，建议仅绑定内网或通过 VPN 访问。
- 不要把 `.env`、SQLite 数据库或 QQ Token 提交到版本库。
- 设备端只采集获得授权的部落聊天区域。
- 生产环境设置 `ALLOWED_CLAN_IDS`，避免采集 Token 被用于提交其他部落的伪造消息。

