# Android 采集端接入约定

仓库中的 `android-collector/` 是 Kotlin Android 应用。用 Android Studio 打开该目录，或在安装 JDK 17、Android SDK 35 后执行：

```powershell
cd android-collector
.\gradlew.bat test
.\gradlew.bat assembleDebug
```

构建前提是 Android Studio/SDK Manager 已安装 Android SDK Platform 35。工程记录了 Gradle 8.7 的 Wrapper 配置；如果仓库中的 Wrapper JAR 尚未生成，可在已安装系统 Gradle 的机器上从仓库根目录执行 `.\scripts\bootstrap-android.ps1`，或者直接用 Android Studio Sync 生成它。生成后应把 `android-collector/gradle/wrapper/gradle-wrapper.jar` 纳入版本库，保证 CI 不依赖开发机全局 Gradle。

安装到专用 Android 设备后：

1. 填写服务端 URL、`COLLECTOR_TOKEN` 对应的 Token 和部落 ID。
2. 点击“打开无障碍服务设置”，启用“CoC 聊天采集服务”。
3. 打开游戏并进入部落聊天，观察服务端日志和 `/api/v1/admin/outbox`。

这版同时提供两条采集路径：

- AccessibilityService：读取无障碍树文本；若界面没有暴露发送者，发送者会记为 `unknown`。
- Android 11+ 截图 OCR：默认启用，每 1.5 秒最多识别一次；默认从屏幕 45% 高度开始识别，可在应用内配置裁剪起始百分比或关闭 OCR，使用 ML Kit 中文模型。

文本解析已经抽成 `ChatTextParser`，两条路径共用过滤和发送者识别；`ChatTextParserTest` 和 `OcrCropTest` 会在 `gradlew test` 中运行。待发送消息保存在 Android SQLite FIFO 队列中，只有服务端返回 2xx 后才删除，断网期间不会按固定条数静默丢弃。OCR 的聊天区域比例需要按实际设备校准；应用中的“裁剪起始百分比”用于调整识别区域。示例服务会用 30 秒时间桶生成 `source_message_id`，服务端和 Android 本地队列都会再次去重。

## 真机 OCR 校准验收

1. 在服务端先确认 `GET /healthz` 正常，并用 `GET /api/v1/admin/messages` 记录当前消息数量。
2. 在采集器中打开 OCR，先把裁剪起始百分比设为 45，保存后重启无障碍服务。
3. 进入部落聊天，让聊天气泡完整显示。每次以 5 为步长调整裁剪起始百分比，使 OCR 区域覆盖聊天气泡且不包含顶部导航、输入框或其他界面文字。
4. 发送一条唯一测试消息，例如 `ocr-calibration-设备型号-时间`，等待 5 秒，在管理接口中确认只出现一条、发送者和内容正确。
5. 连续停留 2 分钟并重复观察同一气泡，确认没有重复消息；切换到非聊天页面，确认不会产生消息。
6. 记录设备型号、Android 版本、游戏版本、裁剪百分比和实际识别结果。未完成这组现场记录前，不能宣称 OCR 已完成真机校准。

首次同步需要下载 ML Kit 中文识别依赖。生产环境建议使用专用设备和专用游戏账号，并把服务端配置为 HTTPS。

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
