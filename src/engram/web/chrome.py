"""Shared local-first chrome helpers for operator web surfaces."""

from __future__ import annotations

LOCAL_ONLY_HELP_COPY: str = (
    "Engram runs entirely on your machine. No cloud service. No telemetry. "
    "No CDN. The browser fetches assets from this process only."
)

PHASE4_FUTURE_COPY: str = "Phase 4 work is not yet built. Tracked in RFC 0021 / D044 / D069 / D079."

AUDIT_EGRESS_STATUS: str = "no network egress"


def audit_footer_copy(bind_address: str, *, egress_status: str = AUDIT_EGRESS_STATUS) -> str:
    """Render the local-only audit footer sentence."""
    return f"local-only · loopback bind: {bind_address} · {egress_status}."
