import asyncio
from datetime import datetime, timezone

from app.config import Settings
from app.db import Database
from app.qq import QQAdapter, QQMessage
from app.service import DeliveryWorker


class RecordingAdapter(QQAdapter):
    def __init__(self):
        self.messages: list[QQMessage] = []

    async def send_group_message(self, message: QQMessage) -> None:
        self.messages.append(message)


def test_delivery_worker_formats_and_sends_message(tmp_path):
    db = Database(tmp_path / "messages.db")
    db.initialize()
    now = datetime.now(timezone.utc)
    db.insert_message(
        clan_id="clan",
        sender="player",
        content="hello",
        observed_at=now,
        source="test",
        source_message_id="one",
    )
    row = db.claim_pending(datetime.now(timezone.utc))[0]
    adapter = RecordingAdapter()
    settings = Settings(
        db_path=tmp_path / "messages.db",
        collector_token="collector",
        admin_token="admin",
        onebot_url="http://bot.test",
        onebot_access_token="",
        qq_group_id="123",
        dry_run=False,
        poll_interval_seconds=1,
        max_attempts=3,
        retry_base_seconds=0,
        max_message_length=2000,
        collector_rate_limit_per_minute=120,
    )
    asyncio.run(DeliveryWorker(db, adapter, settings)._deliver(row))
    assert adapter.messages[0].group_id == "123"
    assert "player：hello" in adapter.messages[0].text
    assert db.counts() == {"sent": 1}

