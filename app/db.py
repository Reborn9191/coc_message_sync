from __future__ import annotations

import hashlib
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional


def iso(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat()


class Database:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=30)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA foreign_keys=ON")
        return connection

    def initialize(self) -> None:
        with self.connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    clan_id TEXT NOT NULL,
                    sender TEXT NOT NULL,
                    content TEXT NOT NULL,
                    observed_at TEXT NOT NULL,
                    source TEXT NOT NULL,
                    source_message_id TEXT,
                    fingerprint TEXT NOT NULL UNIQUE,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS deliveries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    message_id INTEGER NOT NULL UNIQUE REFERENCES messages(id) ON DELETE CASCADE,
                    status TEXT NOT NULL DEFAULT 'pending',
                    attempts INTEGER NOT NULL DEFAULT 0,
                    next_attempt_at TEXT NOT NULL,
                    last_error TEXT,
                    sent_at TEXT
                );

                CREATE INDEX IF NOT EXISTS idx_deliveries_pending
                    ON deliveries(status, next_attempt_at);
                """
            )
            # A process can be terminated while a delivery is being sent. It is
            # safe to retry those messages after the next process starts.
            connection.execute(
                "UPDATE deliveries SET status='pending' WHERE status='processing'"
            )

    @staticmethod
    def fingerprint(
        clan_id: str,
        sender: str,
        content: str,
        observed_at: datetime,
        source: str,
        source_message_id: Optional[str],
    ) -> str:
        if source_message_id:
            raw = f"{source}|{clan_id}|id|{source_message_id}"
        else:
            # OCR sees the same bubble on several consecutive screen reads. A
            # 30-second bucket suppresses those repeats while still allowing a
            # later identical message to pass through.
            timestamp = int(observed_at.timestamp()) // 30
            raw = f"{source}|{clan_id}|{sender}|{content}|{timestamp}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def insert_message(
        self,
        *,
        clan_id: str,
        sender: str,
        content: str,
        observed_at: datetime,
        source: str,
        source_message_id: Optional[str],
    ) -> tuple[int, bool]:
        fingerprint = self.fingerprint(
            clan_id, sender, content, observed_at, source, source_message_id
        )
        now = iso(datetime.now(timezone.utc))
        observed = iso(observed_at)
        with self.connect() as connection:
            connection.execute(
                """
                INSERT OR IGNORE INTO messages
                    (clan_id, sender, content, observed_at, source,
                     source_message_id, fingerprint, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    clan_id,
                    sender,
                    content,
                    observed,
                    source,
                    source_message_id,
                    fingerprint,
                    now,
                ),
            )
            row = connection.execute(
                "SELECT id FROM messages WHERE fingerprint = ?", (fingerprint,)
            ).fetchone()
            if row is None:
                raise RuntimeError("message insert failed")
            message_id = int(row["id"])
            inserted = connection.execute(
                "SELECT changes() AS count"
            ).fetchone()["count"] == 1
            if inserted:
                connection.execute(
                    "INSERT INTO deliveries(message_id, next_attempt_at) VALUES (?, ?)",
                    (message_id, now),
                )
            return message_id, not inserted

    def claim_pending(self, now: datetime, limit: int = 10) -> list[sqlite3.Row]:
        now_value = iso(now)
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT d.id AS delivery_id, d.message_id, d.attempts,
                       m.clan_id, m.sender, m.content, m.observed_at
                FROM deliveries d
                JOIN messages m ON m.id = d.message_id
                WHERE d.status = 'pending' AND d.next_attempt_at <= ?
                ORDER BY d.id ASC LIMIT ?
                """,
                (now_value, limit),
            ).fetchall()
            for row in rows:
                connection.execute(
                    "UPDATE deliveries SET status='processing', attempts=attempts+1 WHERE id=?",
                    (row["delivery_id"],),
                )
            return rows

    def mark_sent(self, delivery_id: int, sent_at: Optional[datetime] = None) -> None:
        with self.connect() as connection:
            connection.execute(
                "UPDATE deliveries SET status='sent', sent_at=?, last_error=NULL WHERE id=?",
                (iso(sent_at or datetime.now(timezone.utc)), delivery_id),
            )

    def mark_failed(
        self,
        delivery_id: int,
        *,
        error: str,
        attempts: int,
        max_attempts: int,
        retry_base_seconds: int,
    ) -> None:
        terminal = attempts >= max_attempts
        next_status = "failed" if terminal else "pending"
        delay = retry_base_seconds * (2 ** max(0, attempts - 1))
        next_time = datetime.now(timezone.utc) + timedelta(seconds=min(delay, 3600))
        with self.connect() as connection:
            connection.execute(
                """
                UPDATE deliveries
                SET status=?, next_attempt_at=?, last_error=?
                WHERE id=?
                """,
                (next_status, iso(next_time), error[:1000], delivery_id),
            )

    def counts(self) -> dict[str, int]:
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT status, COUNT(*) AS count FROM deliveries GROUP BY status"
            ).fetchall()
        return {str(row["status"]): int(row["count"]) for row in rows}
