from __future__ import annotations

import logging
from dataclasses import dataclass

import httpx

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class QQMessage:
    group_id: str
    text: str


class QQAdapter:
    async def send_group_message(self, message: QQMessage) -> None:
        raise NotImplementedError


class OneBotProtocolError(RuntimeError):
    """The OneBot endpoint responded, but reported an application failure."""


class DryRunQQAdapter(QQAdapter):
    async def send_group_message(self, message: QQMessage) -> None:
        logger.info("DRY_RUN QQ message group=%s text=%s", message.group_id, message.text)


class OneBotAdapter(QQAdapter):
    def __init__(
        self,
        url: str,
        access_token: str,
        timeout: float = 10.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ):
        self.url = url.rstrip("/")
        self.access_token = access_token
        self.timeout = timeout
        self.transport = transport

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"
        return headers

    async def _call(self, action: str, payload: dict[str, object]) -> dict[str, object]:
        async with httpx.AsyncClient(timeout=self.timeout, transport=self.transport) as client:
            response = await client.post(
                f"{self.url}/{action}", json=payload, headers=self._headers()
            )
            response.raise_for_status()
            try:
                body = response.json()
            except ValueError as exc:
                raise OneBotProtocolError("OneBot returned invalid JSON") from exc
            if not isinstance(body, dict):
                raise OneBotProtocolError("OneBot returned a non-object response")
            if body.get("status") not in (None, "ok") or body.get("retcode") not in (None, 0):
                raise OneBotProtocolError(str(body.get("wording") or body))
            return body

    async def send_group_message(self, message: QQMessage) -> None:
        payload = {
            "group_id": int(message.group_id) if message.group_id.isdigit() else message.group_id,
            "message": message.text,
        }
        await self._call("send_group_msg", payload)

    async def check_status(self) -> dict[str, object]:
        """Check that the OneBot process is reachable and reports healthy."""
        body = await self._call("get_status", {})
        data = body.get("data")
        return data if isinstance(data, dict) else {}


def format_group_message(clan_id: str, sender: str, content: str) -> str:
    # Normalize excessive whitespace from OCR while preserving intentional
    # line breaks in a player's message.
    normalized = "\n".join(line.strip() for line in content.splitlines()).strip()
    return f"[部落聊天 · {clan_id}]\n{sender}：{normalized}"
