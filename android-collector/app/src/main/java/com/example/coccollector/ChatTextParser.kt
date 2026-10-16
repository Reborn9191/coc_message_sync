package com.example.coccollector

data class ParsedChat(val sender: String, val content: String)

/**
 * Shared parser for Accessibility text and future OCR output.
 *
 * OCR frequently returns several lines in one block, while Accessibility may
 * expose one chat bubble per node. Keeping parsing here makes both collectors
 * use the same filtering and sender detection rules.
 */
object ChatTextParser {
    private val ignoredPrefixes = listOf("部落", "设置", "攻击", "防御", "聊天", "返回")

    fun parse(raw: String): List<ParsedChat> {
        return raw
            .replace("\u0000", "")
            .lines()
            .map { it.trim() }
            .filter { it.isNotEmpty() }
            .filterNot { value -> ignoredPrefixes.any { value.startsWith(it) } }
            .filter { it.length <= 500 && it.any { char -> char.isLetterOrDigit() || char in '\u4e00'..'\u9fff' } }
            .mapNotNull(::parseLine)
    }

    private fun parseLine(line: String): ParsedChat? {
        val separator = line.indexOfAny(charArrayOf('：', ':'))
        if (separator in 1..39) {
            val sender = line.substring(0, separator).trim()
            val content = line.substring(separator + 1).trim()
            if (sender.isNotEmpty() && content.isNotEmpty()) {
                return ParsedChat(sender, content)
            }
        }
        return ParsedChat("unknown", line)
    }
}

