# Android 采集端接入约定

仓库中的 `android-collector/` 是一个无需第三方网络库的 Kotlin 示例应用。用 Android Studio 打开该目录，安装到专用 Android 设备后：

1. 填写服务端 URL、`COLLECTOR_TOKEN` 对应的 Token 和部落 ID。
2. 点击“打开无障碍服务设置”，启用“CoC 聊天采集服务”。
3. 打开游戏并进入部落聊天，观察服务端日志和 `/api/v1/admin/outbox`。

这版同时提供两条采集路径：

- AccessibilityService：读取无障碍树文本；若界面没有暴露发送者，发送者会记为 `unknown`。
- Android 11+ 截图 OCR：默认启用，每 1.5 秒最多识别一次屏幕下方 55% 区域，使用 ML Kit 中文模型；可在应用内关闭。

文本解析已经抽成 `ChatTextParser`，两条路径共用过滤和发送者识别。OCR 的聊天区域比例需要按实际设备校准；如果游戏聊天不在屏幕下方，后续应把裁剪区域改为可配置。示例服务会用 30 秒时间桶生成 `source_message_id`，服务端还会再次去重。

构建要求：Android Studio、JDK 17 和 Android SDK 35。项目没有提交 Gradle Wrapper，请在 Android Studio 中打开 `android-collector/` 后直接 Sync/Run；首次同步需要下载 ML Kit 中文识别依赖。生产环境建议使用专用设备和专用游戏账号，并把服务端配置为 HTTPS。

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

服务端对每个来源 IP 有默认每分钟 120 条的限流。若设备频繁重试收到 429，应降低采集频率或调整 `COLLECTOR_RATE_LIMIT_PER_MINUTE`；不要通过并发请求绕过限流。

服务端不会修改游戏客户端，也不会尝试把 QQ 消息写回游戏。正式部署前请征得部落成员同意，并确认游戏和 QQ 平台的使用规则。
