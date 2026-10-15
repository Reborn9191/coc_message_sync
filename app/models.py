from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field, validator


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

    @validator("clan_id", "sender", "content", "source", "source_message_id", pre=True)
    def strip_text(cls, value):
        if value is None:
            return value
        return str(value).strip()


class IngestResponse(BaseModel):
    message_id: int
    duplicate: bool
    delivery_status: str


class HealthResponse(BaseModel):
    status: str
    dry_run: bool
    qq_configured: bool

