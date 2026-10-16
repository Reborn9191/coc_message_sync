package com.example.coccollector

import android.app.Activity
import android.content.Context
import android.content.Intent
import android.os.Bundle
import android.provider.Settings
import android.text.InputType
import android.widget.Button
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.Switch
import android.widget.TextView
import android.widget.Toast

class MainActivity : Activity() {
    private val preferences by lazy { getSharedPreferences("collector", Context.MODE_PRIVATE) }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val server = EditText(this).apply {
            hint = "服务端地址，例如 https://bridge.example.com"
            setText(preferences.getString("server_url", ""))
            setSingleLine(true)
        }
        val token = EditText(this).apply {
            hint = "采集 Token"
            setText(preferences.getString("collector_token", ""))
            setSingleLine(true)
            inputType = InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_VARIATION_PASSWORD
        }
        val clan = EditText(this).apply {
            hint = "部落 ID 或名称"
            setText(preferences.getString("clan_id", ""))
            setSingleLine(true)
        }
        val cropTop = EditText(this).apply {
            hint = "OCR 裁剪起始百分比（默认 45）"
            setText(preferences.getInt("ocr_crop_top_percent", OcrCrop.DEFAULT_TOP_PERCENT).toString())
            setSingleLine(true)
            inputType = InputType.TYPE_CLASS_NUMBER
        }
        val ocr = Switch(this).apply {
            text = "启用截图 OCR（Android 11+）"
            isChecked = preferences.getBoolean("ocr_enabled", true)
            setOnCheckedChangeListener { _, checked ->
                preferences.edit().putBoolean("ocr_enabled", checked).apply()
            }
        }
        val save = Button(this).apply {
            text = "保存配置"
            setOnClickListener {
                preferences.edit()
                    .putString("server_url", server.text.toString().trim())
                    .putString("collector_token", token.text.toString().trim())
                    .putString("clan_id", clan.text.toString().trim())
                    .putInt(
                        "ocr_crop_top_percent",
                        cropTop.text.toString().toIntOrNull()?.let(OcrCrop::clampTopPercent)
                            ?: OcrCrop.DEFAULT_TOP_PERCENT,
                    )
                    .apply()
                Toast.makeText(this@MainActivity, "配置已保存", Toast.LENGTH_SHORT).show()
            }
        }
        val settings = Button(this).apply {
            text = "打开无障碍服务设置"
            setOnClickListener { startActivity(Intent(Settings.ACTION_ACCESSIBILITY_SETTINGS)) }
        }
        val note = TextView(this).apply {
            text = "请先保存配置，再启用“CoC 聊天采集服务”。仅在获得部落成员同意后使用。\n\nOCR 校准：进入部落聊天并调整裁剪起始百分比，使预览区域只覆盖聊天气泡；通常从 45 开始，每次调整 5。校准后发送一条测试消息，并在服务端 /api/v1/admin/messages 确认只出现一次。\n\n如果当前游戏版本不提供可访问文本，服务会使用 Android 11+ 截图 OCR。"
            setPadding(24, 24, 24, 24)
        }
        setContentView(LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(24, 24, 24, 24)
            addView(server)
            addView(token)
            addView(clan)
            addView(cropTop)
            addView(ocr)
            addView(save)
            addView(settings)
            addView(note)
        })
    }
}
