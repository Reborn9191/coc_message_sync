from __future__ import annotations


def blocked_term(content: str, terms: tuple[str, ...]) -> str | None:
    """Return the first configured blocked term found in a message."""
    normalized = content.casefold()
    for term in terms:
        if term and term in normalized:
            return term
    return None


def clan_allowed(clan_id: str, allowed_ids: tuple[str, ...]) -> bool:
    """An empty allowlist means single-clan development mode."""
    return not allowed_ids or clan_id in allowed_ids

