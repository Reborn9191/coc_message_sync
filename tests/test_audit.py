from app.db import Database


def test_audit_events_are_stored_without_message_content(tmp_path):
    db = Database(tmp_path / "messages.db")
    db.initialize()
    db.record_audit("sync_toggle", "127.0.0.1", "enabled=false")
    events = db.recent_audit()
    assert events[0]["event"] == "sync_toggle"
    assert events[0]["actor"] == "127.0.0.1"
    assert events[0]["detail"] == "enabled=false"
