import asyncio
import json

import httpx
import pytest

from app.qq import (
    OneBotAdapter,
    OneBotProtocolError,
    QQMessage,
    format_group_message,
)


def test_format_group_message_normalizes_ocr_whitespace():
    assert format_group_message("clan", "player", "  hello \n world  ") == (
        "[部落聊天 · clan]\nplayer：hello\nworld"
    )


def test_onebot_adapter_sends_authenticated_group_message():
    requests: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        assert request.url.path == "/api/send_group_msg"
        assert request.headers["Authorization"] == "Bearer secret"
        assert json.loads(request.content) == {"group_id": 123, "message": "hello"}
        return httpx.Response(200, json={"status": "ok", "retcode": 0})

    adapter = OneBotAdapter(
        "https://bot.test/api",
        "secret",
        transport=httpx.MockTransport(handler),
    )
    asyncio.run(adapter.send_group_message(QQMessage("123", "hello")))
    assert len(requests) == 1


def test_onebot_application_error_is_not_treated_as_success():
    async def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"status": "failed", "retcode": 100, "wording": "bot is not logged in"},
        )

    adapter = OneBotAdapter("https://bot.test", "", transport=httpx.MockTransport(handler))
    with pytest.raises(OneBotProtocolError, match="not logged in"):
        asyncio.run(adapter.send_group_message(QQMessage("123", "hello")))


def test_onebot_status_check_uses_get_status_action():
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/get_status"
        return httpx.Response(200, json={"status": "ok", "retcode": 0, "data": {"online": True}})

    adapter = OneBotAdapter("https://bot.test", "", transport=httpx.MockTransport(handler))
    assert asyncio.run(adapter.check_status()) == {"online": True}
