package com.example.coccollector

import android.accessibilityservice.AccessibilityService
import android.accessibilityservice.AccessibilityService.ScreenshotResult
import android.accessibilityservice.AccessibilityService.TakeScreenshotCallback
import android.graphics.Bitmap
import android.os.Build
import android.view.Display
import android.view.accessibility.AccessibilityEvent
import android.view.accessibility.AccessibilityNodeInfo
import com.google.mlkit.vision.common.InputImage
import com.google.mlkit.vision.text.chinese.ChineseTextRecognizerOptions
import com.google.mlkit.vision.text.TextRecognition
import org.json.JSONArray
import java.net.HttpURLConnection
import java.net.URL
import java.nio.charset.StandardCharsets
import java.security.MessageDigest
import java.util.concurrent.ExecutorService
import java.util.concurrent.Executors
import kotlin.math.pow

class GameChatAccessibilityService : AccessibilityService() {
    private val executor: ExecutorService = Executors.newSingleThreadExecutor()
    private val preferences by lazy { getSharedPreferences("collector", MODE_PRIVATE) }
    private val gamePackage = "com.supercell.clashofclans"
    private val queueLock = Any()
    private val queueKey = "pending_payloads"
    private val recognizer by lazy {
        TextRecognition.getClient(ChineseTextRecognizerOptions.Builder().build())
    }
    @Volatile private var lastOcrAt = 0L

    override fun onAccessibilityEvent(event: AccessibilityEvent?) {
        if (event == null || event.packageName?.toString() != gamePackage) return
        if (event.eventType != AccessibilityEvent.TYPE_WINDOW_CONTENT_CHANGED &&
            event.eventType != AccessibilityEvent.TYPE_VIEW_TEXT_CHANGED &&
            event.eventType != AccessibilityEvent.TYPE_WINDOW_STATE_CHANGED
        ) return

        val root = rootInActiveWindow ?: return
        val candidates = mutableSetOf<String>()
        collectText(root, candidates)
        candidates
            .flatMap { ChatTextParser.parse(it) }
            .forEach { entry -> submit(entry.sender, entry.content) }
        requestOcrIfEnabled()
    }

    private fun requestOcrIfEnabled() {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.R) return
        if (!preferences.getBoolean("ocr_enabled", true)) return
        val now = System.currentTimeMillis()
        if (now - lastOcrAt < 1_500L) return
        lastOcrAt = now
        try {
            takeScreenshot(
                Display.DEFAULT_DISPLAY,
                mainExecutor,
                object : TakeScreenshotCallback {
                override fun onSuccess(screenshot: ScreenshotResult) {
                    val hardwareBuffer = screenshot.hardwareBuffer
                    val full = Bitmap.wrapHardwareBuffer(hardwareBuffer, screenshot.colorSpace)
                    hardwareBuffer.close()
                    if (full == null) return
                    val bitmap = full.copy(Bitmap.Config.ARGB_8888, false) ?: return
                    full.recycle()
                    val cropPercent = preferences.getInt("ocr_crop_top_percent", 45).coerceIn(0, 90)
                    val top = (bitmap.height * (cropPercent / 100f)).toInt().coerceIn(0, bitmap.height - 1)
                    val crop = Bitmap.createBitmap(bitmap, 0, top, bitmap.width, bitmap.height - top)
                    bitmap.recycle()
                    recognizer.process(InputImage.fromBitmap(crop, 0))
                        .addOnSuccessListener { result ->
                            ChatTextParser.parse(result.text)
                                .forEach { entry -> submit(entry.sender, entry.content) }
                        }
                        .addOnCompleteListener { crop.recycle() }
                }

                override fun onFailure(errorCode: Int) = Unit
                },
            )
        } catch (_: SecurityException) {
            // Some vendor Android builds disable screenshots for accessibility
            // services. Accessibility text collection can continue normally.
        } catch (_: IllegalStateException) {
            // The service may be shutting down while a window event arrives.
        }
    }

    private fun collectText(node: AccessibilityNodeInfo, result: MutableSet<String>) {
        node.text?.toString()?.trim()?.takeIf { it.isNotEmpty() }?.let(result::add)
        node.contentDescription?.toString()?.trim()?.takeIf { it.isNotEmpty() }?.let(result::add)
        for (index in 0 until node.childCount) {
            node.getChild(index)?.let { child ->
                collectText(child, result)
                child.recycle()
            }
        }
    }

    private fun submit(sender: String, content: String) {
        val serverUrl = preferences.getString("server_url", "")?.trim().orEmpty()
        val token = preferences.getString("collector_token", "")?.trim().orEmpty()
        val clanId = preferences.getString("clan_id", "")?.trim().orEmpty()
        if (serverUrl.isEmpty() || token.isEmpty() || clanId.isEmpty()) return
        val bucket = System.currentTimeMillis() / 30_000L
        val sourceId = sha256("$clanId|$sender|$content|$bucket")
        val json = "{" +
            "\"clan_id\":${jsonString(clanId)}," +
            "\"sender\":${jsonString(sender)}," +
            "\"content\":${jsonString(content)}," +
            "\"source\":\"android_collector\"," +
            "\"source_message_id\":${jsonString(sourceId)}" +
            "}"
        enqueue(json)
        executor.submit { drain(serverUrl, token) }
    }

    private fun enqueue(json: String) {
        synchronized(queueLock) {
            val existing = readQueue()
            val sourceId = try {
                org.json.JSONObject(json).optString("source_message_id")
            } catch (_: Exception) {
                ""
            }
            if (sourceId.isNotEmpty()) {
                for (index in 0 until existing.length()) {
                    if (try { org.json.JSONObject(existing.optString(index)).optString("source_message_id") } catch (_: Exception) { "" } == sourceId) {
                        return
                    }
                }
            }
            existing.put(json)
            // A disconnected device must not grow without bound. The server's
            // source ID still makes retries idempotent if a bubble is repeated.
            while (existing.length() > 100) existing.remove(0)
            preferences.edit().putString(queueKey, existing.toString()).commit()
        }
    }

    private fun drain(serverUrl: String, token: String) {
        while (true) {
            val next = synchronized(queueLock) { readQueue().optString(0, "") }
            if (next.isEmpty()) return
            if (!postWithRetry(serverUrl, token, next)) return
            synchronized(queueLock) {
                val queue = readQueue()
                if (queue.length() > 0) queue.remove(0)
                preferences.edit().putString(queueKey, queue.toString()).commit()
            }
        }
    }

    private fun readQueue(): JSONArray {
        val raw = preferences.getString(queueKey, "[]") ?: "[]"
        return try {
            JSONArray(raw)
        } catch (_: Exception) {
            JSONArray()
        }
    }

    private fun postWithRetry(serverUrl: String, token: String, json: String): Boolean {
        val endpoint = serverUrl.trimEnd('/') + "/api/v1/messages"
        repeat(3) { attempt ->
            try {
                val connection = (URL(endpoint).openConnection() as HttpURLConnection).apply {
                    requestMethod = "POST"
                    connectTimeout = 8_000
                    readTimeout = 8_000
                    doOutput = true
                    setRequestProperty("Content-Type", "application/json")
                    setRequestProperty("X-Collector-Token", token)
                }
                connection.outputStream.use { it.write(json.toByteArray(StandardCharsets.UTF_8)) }
                val code = connection.responseCode
                connection.inputStream.close()
                connection.disconnect()
                if (code in 200..299) return true
            } catch (_: Exception) {
                // Retry below; the source ID makes retries idempotent server-side.
            }
            try {
                Thread.sleep((500L * 2.0.pow(attempt.toDouble())).toLong())
            } catch (_: InterruptedException) {
                Thread.currentThread().interrupt()
                return false
            }
        }
        return false
    }

    private fun jsonString(value: String): String {
        val escaped = buildString {
            value.forEach { character ->
                when (character) {
                    '\\' -> append("\\\\")
                    '"' -> append("\\\"")
                    '\n' -> append("\\n")
                    '\r' -> append("\\r")
                    '\t' -> append("\\t")
                    else -> append(character)
                }
            }
        }
        return "\"$escaped\""
    }

    private fun sha256(value: String): String {
        val digest = MessageDigest.getInstance("SHA-256").digest(value.toByteArray(StandardCharsets.UTF_8))
        return digest.joinToString("") { "%02x".format(it) }
    }

    override fun onInterrupt() = Unit

    override fun onDestroy() {
        executor.shutdownNow()
        super.onDestroy()
    }
}
