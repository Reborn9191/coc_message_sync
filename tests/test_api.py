import importlib

from fastapi.testclient import TestClient


def test_http_ingest_auth_dedup_and_dry_run(monkeypatch, tmp_path):
    monkeypatch.setenv("COLLECTOR_TOKEN", "collector-test")
    monkeypatch.setenv("ADMIN_TOKEN", "admin-test")
    monkeypatch.setenv("DRY_RUN", "true")
    monkeypatch.setenv("DB_PATH", str(tmp_path / "messages.db"))
    monkeypatch.setenv("POLL_INTERVAL_SECONDS", "0.01")

    import app.main as main

    main = importlib.reload(main)
    payload = {
        "clan_id": "clan",
        "sender": "player",
        "content": "hello",
        "source": "test",
        "source_message_id": "bubble-1",
    }
    with TestClient(main.app) as client:
        assert client.get("/healthz").json() == {
            "status": "ok",
            "dry_run": True,
            "qq_configured": False,
        }
        assert client.get("/readyz").json() == {"status": "ok", "mode": "dry-run", "qq": None}
        assert client.post("/api/v1/messages", json=payload).status_code == 401

        first = client.post(
            "/api/v1/messages",
            json=payload,
            headers={"X-Collector-Token": "collector-test"},
        )
        assert first.status_code == 202
        assert first.json()["duplicate"] is False

        duplicate = client.post(
            "/api/v1/messages",
            json=payload,
            headers={"X-Collector-Token": "collector-test"},
        )
        assert duplicate.status_code == 200
        assert duplicate.json()["duplicate"] is True

        outbox = client.get(
            "/api/v1/admin/outbox",
            headers={"X-Admin-Token": "admin-test"},
        )
        assert outbox.status_code == 200
        assert outbox.json()["counts"] == {"sent": 1}
        assert outbox.json()["sync_enabled"] is True

        paused = client.post(
            "/api/v1/admin/sync?enabled=false",
            headers={"X-Admin-Token": "admin-test"},
        )
        assert paused.json() == {"sync_enabled": False}
        resumed = client.post(
            "/api/v1/admin/sync?enabled=true",
            headers={"X-Admin-Token": "admin-test"},
        )
        assert resumed.json() == {"sync_enabled": True}

