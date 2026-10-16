from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field, field_validator


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class IncomingMessage(BaseModel):
    """Payload emitted by the Android accessibility/OCR collector."""

    clan_id: str = Field(..., min_length=1, max_length=100)
    sender: str = Field(..., min_length=1, max_length=100)
    content: str = Field(..., min_length=1, max_length=2000)
    observed_at: datetime = Field(default_factory=utc_now)
    source: str = Field(default="android_ocr", min_length=1, max_length=40)
    source_message_id: Optional[str] = Field(default=None, max_length=200)

    @field_validator("clan_id", "sender", "content", "source", "source_message_id", mode="before")
    def strip_text(cls, value):
        if value is None:
            return value
        return str(value).strip()

    @field_validator("content")
    def reject_control_content(cls, value: str) -> str:
        # Keep line breaks (they are useful in chat), but reject invisible
        # control characters that can confuse QQ clients or log processors.
        if any(ord(char) < 32 and char not in "\n\r\t" for char in value):
            raise ValueError("content contains unsupported control characters")
        return value


class IngestResponse(BaseModel):
    message_id: int
    duplicate: bool
    delivery_status: str


class HealthResponse(BaseModel):
    status: str
    dry_run: bool
    qq_configured: bool


class ReadyResponse(BaseModel):
    status: str
    mode: str
    qq: dict[str, object] | None = None
