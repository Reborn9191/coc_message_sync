import json

import httpx

from scripts.onebot_smoke_test import call


def test_smoke_call_uses_bearer_auth_and_validates_success():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["Authorization"] == "Bearer token"
        assert request.url.path == "/get_status"
        assert json.loads(request.content) == {}
        return httpx.Response(200, json={"status": "ok", "retcode": 0, "data": {"online": True}})

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        body = call(client, "https://bot.test", "token", "get_status", {})
    assert body["data"] == {"online": True}
