package com.example.coccollector

import android.content.ContentValues
import android.content.Context
import android.database.sqlite.SQLiteDatabase
import android.database.sqlite.SQLiteOpenHelper

/** Durable FIFO for messages waiting on a server response. */
class CollectorQueue(context: Context) : SQLiteOpenHelper(
    context.applicationContext,
    "collector_queue.db",
    null,
    1,
) {
    override fun onCreate(db: SQLiteDatabase) {
        db.execSQL(
            """
            CREATE TABLE pending_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_id TEXT NOT NULL UNIQUE,
                payload TEXT NOT NULL,
                created_at INTEGER NOT NULL
            )
            """.trimIndent(),
        )
    }

    override fun onUpgrade(db: SQLiteDatabase, oldVersion: Int, newVersion: Int) = Unit

    fun enqueue(sourceId: String, payload: String): Boolean {
        val values = ContentValues().apply {
            put("source_id", sourceId)
            put("payload", payload)
            put("created_at", System.currentTimeMillis())
        }
        return writableDatabase.insertWithOnConflict(
            "pending_messages",
            null,
            values,
            SQLiteDatabase.CONFLICT_IGNORE,
        ) != -1L
    }

    fun peek(): String? = readableDatabase.query(
        "pending_messages",
        arrayOf("payload"),
        null,
        null,
        null,
        null,
        "id ASC",
        "1",
    ).use { cursor ->
        if (cursor.moveToFirst()) cursor.getString(0) else null
    }

    fun removeHead() {
        writableDatabase.delete(
            "pending_messages",
            "id = (SELECT id FROM pending_messages ORDER BY id ASC LIMIT 1)",
            null,
        )
    }
}
