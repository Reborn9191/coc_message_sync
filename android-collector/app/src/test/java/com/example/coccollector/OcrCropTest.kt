package com.example.coccollector

import org.junit.Assert.assertEquals
import org.junit.Test

class OcrCropTest {
    @Test
    fun clamps_percent_and_calculates_safe_top_pixel() {
        assertEquals(0, OcrCrop.clampTopPercent(-10))
        assertEquals(90, OcrCrop.clampTopPercent(120))
        assertEquals(450, OcrCrop.topPixel(1000, 45))
        assertEquals(899, OcrCrop.topPixel(1000, 100))
    }
}
