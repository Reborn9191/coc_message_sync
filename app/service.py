from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from .config import Settings
from .db import Database
from .qq import QQAdapter, QQMessage, format_group_message

logger = logging.getLogger(__name__)


class DeliveryWorker:
    def __init__(self, db: Database, adapter: QQAdapter, settings: Settings):
        self.db = db
        self.adapter = adapter
        self.settings = settings
        self._wake = asyncio.Event()
        self._stop = asyncio.Event()
        self._task: asyncio.Task | None = None

    async def start(self) -> None:
        self._task = asyncio.create_task(self._run(), name="qq-delivery-worker")

    async def stop(self) -> None:
        self._stop.set()
        self._wake.set()
        if self._task:
            await self._task

    def notify(self) -> None:
        self._wake.set()

    async def _run(self) -> None:
        while not self._stop.is_set():
            made_progress = False
            for row in self.db.claim_pending(datetime.now(timezone.utc)):
                made_progress = True
                await self._deliver(row)
            if made_progress:
                continue
            self._wake.clear()
            try:
                await asyncio.wait_for(self._wake.wait(), timeout=self.settings.poll_interval_seconds)
            except asyncio.TimeoutError:
                pass

    async def _deliver(self, row) -> None:
        delivery_id = int(row["delivery_id"])
        attempts = int(row["attempts"]) + 1
        try:
            if not self.settings.qq_group_id:
                raise RuntimeError("QQ_GROUP_ID is not configured")
            text = format_group_message(row["clan_id"], row["sender"], row["content"])
            await self.adapter.send_group_message(
                QQMessage(group_id=self.settings.qq_group_id, text=text)
            )
        except Exception as exc:  # keep the worker alive for transient QQ errors
            logger.warning("delivery %s failed (attempt %s): %s", delivery_id, attempts, exc)
            self.db.mark_failed(
                delivery_id,
                error=str(exc),
                attempts=attempts,
                max_attempts=self.settings.max_attempts,
                retry_base_seconds=self.settings.retry_base_seconds,
            )
        else:
            self.db.mark_sent(delivery_id)
            logger.info("delivery %s sent", delivery_id)

