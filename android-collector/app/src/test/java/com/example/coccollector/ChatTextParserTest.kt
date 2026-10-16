package com.example.coccollector

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class ChatTextParserTest {
    @Test
    fun parses_sender_and_content_from_chinese_and_ascii_separators() {
        assertEquals(ParsedChat("玩家A", "晚上打战"), ChatTextParser.parse("玩家A：晚上打战").single())
        assertEquals(ParsedChat("Player", "hello"), ChatTextParser.parse("Player: hello").single())
    }

    @Test
    fun filters_ui_text_and_keeps_unknown_sender_for_plain_ocr_lines() {
        val parsed = ChatTextParser.parse("聊天\n大家集合\n设置")
        assertEquals(1, parsed.size)
        assertEquals("unknown", parsed.single().sender)
        assertEquals("大家集合", parsed.single().content)
    }

    @Test
    fun rejects_empty_and_oversized_lines() {
        assertTrue(ChatTextParser.parse("\n设置\n").isEmpty())
        assertTrue(ChatTextParser.parse("x".repeat(501)).isEmpty())
    }
}
