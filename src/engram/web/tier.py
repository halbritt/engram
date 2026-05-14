"""Shared privacy-tier ceiling helper for local web rendering routes."""

from __future__ import annotations

from fastapi import HTTPException

DEFAULT_TIER_CEILING: int = 1


def privacy_tier_envelope(
    tier: int, *, ceiling: int = DEFAULT_TIER_CEILING, message_id: str | None = None
) -> dict[str, int | str]:
    """Return the standard privacy-tier-ceiling response envelope."""
    envelope: dict[str, int | str] = {
        "error": "privacy_tier_ceiling",
        "tier": int(tier),
        "ceiling": int(ceiling),
    }
    if message_id is not None:
        envelope["message_id"] = message_id
    return envelope


def require_tier_ceiling(
    tier: int, *, ceiling: int = DEFAULT_TIER_CEILING, message_id: str | None = None
) -> None:
    """Raise 403 if ``tier`` exceeds the render ceiling."""
    if int(tier) > int(ceiling):
        raise HTTPException(
            status_code=403,
            detail=privacy_tier_envelope(tier, ceiling=ceiling, message_id=message_id),
        )
