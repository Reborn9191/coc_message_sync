# Android 采集端接入约定

服务端已经提供了稳定的采集接口，Android 端只需要把识别出的新聊天消息 POST 到：

```text
POST /api/v1/messages
X-Collector-Token: <COLLECTOR_TOKEN>
Content-Type: application/json
```

请求示例：

```json
{
  "clan_id": "my-clan",
  "sender": "玩家A",
  "content": "晚上一起打部落战",
  "observed_at": "2026-10-15T12:30:00Z",
  "source": "android_ocr",
  "source_message_id": "screen-1712345678-01"
}
```

建议实现：

1. 使用 Android AccessibilityService 读取聊天控件文本；若游戏版本无法暴露文本，再使用截图加 OCR。
2. 只截取部落聊天区域，不读取私聊或其他界面。
3. 为每个聊天气泡生成稳定的 `source_message_id`。服务端也会用发送者、内容和 30 秒时间桶去重，以防 OCR 重复上报。
4. 本地持久化最近一次已上报的消息，在网络断开时重试；收到 HTTP 202 后再推进本地游标。
5. 使用 HTTPS 访问服务端，并把 Token 放在 Android Keystore 或受保护的配置中。

服务端不会修改游戏客户端，也不会尝试把 QQ 消息写回游戏。正式部署前请征得部落成员同意，并确认游戏和 QQ 平台的使用规则。

