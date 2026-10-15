from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _bool_env(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    """Runtime configuration loaded from environment variables."""

    db_path: Path
    collector_token: str
    admin_token: str
    onebot_url: str
    onebot_access_token: str
    qq_group_id: str
    dry_run: bool
    poll_interval_seconds: float
    max_attempts: int
    retry_base_seconds: int
    max_message_length: int

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            db_path=Path(os.getenv("DB_PATH", "data/messages.db")),
            # Empty defaults intentionally disable authenticated endpoints until
            # the operator configures explicit secrets.
            collector_token=os.getenv("COLLECTOR_TOKEN", ""),
            admin_token=os.getenv("ADMIN_TOKEN", ""),
            onebot_url=os.getenv("ONEBOT_URL", "").rstrip("/"),
            onebot_access_token=os.getenv("ONEBOT_ACCESS_TOKEN", ""),
            qq_group_id=os.getenv("QQ_GROUP_ID", ""),
            dry_run=_bool_env("DRY_RUN", True),
            poll_interval_seconds=float(os.getenv("POLL_INTERVAL_SECONDS", "1.0")),
            max_attempts=int(os.getenv("MAX_ATTEMPTS", "8")),
            retry_base_seconds=int(os.getenv("RETRY_BASE_SECONDS", "2")),
            max_message_length=int(os.getenv("MAX_MESSAGE_LENGTH", "2000")),
        )
