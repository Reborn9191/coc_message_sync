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


class DryRunQQAdapter(QQAdapter):
    async def send_group_message(self, message: QQMessage) -> None:
        logger.info("DRY_RUN QQ message group=%s text=%s", message.group_id, message.text)


class OneBotAdapter(QQAdapter):
    def __init__(self, url: str, access_token: str, timeout: float = 10.0):
        self.url = url.rstrip("/")
        self.access_token = access_token
        self.timeout = timeout

    async def send_group_message(self, message: QQMessage) -> None:
        headers = {"Content-Type": "application/json"}
        if self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"
        payload = {
            "group_id": int(message.group_id) if message.group_id.isdigit() else message.group_id,
            "message": message.text,
        }
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.url}/send_group_msg", json=payload, headers=headers
            )
            response.raise_for_status()
            body = response.json()
            if isinstance(body, dict) and body.get("status") == "failed":
                raise RuntimeError(str(body.get("wording") or body))


def format_group_message(clan_id: str, sender: str, content: str) -> str:
    return f"[部落聊天 · {clan_id}]\n{sender}：{content}"

