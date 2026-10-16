package com.example.coccollector

import android.graphics.Bitmap

/**
 * Converts the user-selected crop percentage into a safe bitmap crop.
 * Keeping this calculation independent makes device calibration testable
 * without requiring an Android screenshot or a running AccessibilityService.
 */
object OcrCrop {
    const val DEFAULT_TOP_PERCENT = 45
    const val MIN_TOP_PERCENT = 0
    const val MAX_TOP_PERCENT = 90

    fun clampTopPercent(value: Int): Int = value.coerceIn(MIN_TOP_PERCENT, MAX_TOP_PERCENT)

    fun topPixel(height: Int, topPercent: Int): Int {
        require(height > 0) { "bitmap height must be positive" }
        return (height * (clampTopPercent(topPercent) / 100f))
            .toInt()
            .coerceIn(0, height - 1)
    }

    fun crop(bitmap: Bitmap, topPercent: Int): Bitmap {
        val top = topPixel(bitmap.height, topPercent)
        return Bitmap.createBitmap(bitmap, 0, top, bitmap.width, bitmap.height - top)
    }
}
