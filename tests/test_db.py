from datetime import datetime, timezone

from app.db import Database


def test_message_is_deduplicated_and_can_be_sent(tmp_path):
    db = Database(tmp_path / "messages.db")
    db.initialize()
    observed_at = datetime.now(timezone.utc)

    first = db.insert_message(
        clan_id="clan-1",
        sender="player",
        content="hello",
        observed_at=observed_at,
        source="test",
        source_message_id="bubble-1",
    )
    duplicate = db.insert_message(
        clan_id="clan-1",
        sender="player",
        content="hello",
        observed_at=observed_at,
        source="test",
        source_message_id="bubble-1",
    )

    assert first == (1, False)
    assert duplicate == (1, True)
    rows = db.claim_pending(observed_at)
    assert len(rows) == 1
    db.mark_sent(rows[0]["delivery_id"], observed_at)
    assert db.counts() == {"sent": 1}


def test_failed_delivery_is_retried_then_marked_terminal(tmp_path):
    db = Database(tmp_path / "messages.db")
    db.initialize()
    observed_at = datetime.now(timezone.utc)
    db.insert_message(
        clan_id="clan-1",
        sender="player",
        content="hello",
        observed_at=observed_at,
        source="test",
        source_message_id="bubble-1",
    )
    row = db.claim_pending(observed_at)[0]
    db.mark_failed(
        row["delivery_id"],
        error="temporary",
        attempts=1,
        max_attempts=2,
        retry_base_seconds=0,
    )
    retry = db.claim_pending(datetime.now(timezone.utc))
    assert len(retry) == 1
    db.mark_failed(
        retry[0]["delivery_id"],
        error="permanent",
        attempts=2,
        max_attempts=2,
        retry_base_seconds=0,
    )
    assert db.counts() == {"failed": 1}
