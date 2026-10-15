from __future__ import annotations

from dataclasses import dataclass


@dataclass
class RuntimeMetrics:
    received: int = 0
    duplicates: int = 0
    queued: int = 0
    delivery_success: int = 0
    delivery_failures: int = 0

    def prometheus(self) -> str:
        values = {
            "coc_bridge_messages_received_total": self.received,
            "coc_bridge_messages_duplicates_total": self.duplicates,
            "coc_bridge_messages_queued_total": self.queued,
            "coc_bridge_delivery_success_total": self.delivery_success,
            "coc_bridge_delivery_failures_total": self.delivery_failures,
        }
        return "\n".join(
            f"# TYPE {name} counter\n{name} {value}" for name, value in values.items()
        ) + "\n"

