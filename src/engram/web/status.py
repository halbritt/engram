"""Shared status-chip vocabulary for truthful operator UI states."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class StatusDefinition:
    """User-facing status chip definition."""

    token: str
    label: str
    long_copy: str
    color_token: str
    icon: str
    data_status: str


STATUS_DEFINITIONS: dict[str, StatusDefinition] = {
    "accepted": StatusDefinition(
        token="accepted",
        label="Accepted",
        long_copy="Reviewed and accepted as canonical.",
        color_token="--color-ok-strong",
        icon="✓",
        data_status="accepted",
    ),
    "candidate": StatusDefinition(
        token="candidate",
        label="Candidate",
        long_copy="Derived; not yet reviewed.",
        color_token="--color-info",
        icon="※",
        data_status="candidate",
    ),
    "provisional": StatusDefinition(
        token="provisional",
        label="Provisional",
        long_copy="Auto-consolidated; awaiting review.",
        color_token="--color-info-muted",
        icon="※",
        data_status="provisional",
    ),
    "proposed": StatusDefinition(
        token="proposed",
        label="Proposed",
        long_copy="Operator recorded a non-authoritative recommendation.",
        color_token="--color-warn-muted",
        icon="※",
        data_status="proposed",
    ),
    "reviewed": StatusDefinition(
        token="reviewed",
        label="Reviewed",
        long_copy="An operator has ruled on this row.",
        color_token="--color-fg-muted",
        icon="✓",
        data_status="reviewed",
    ),
    "advisory": StatusDefinition(
        token="advisory",
        label="Advisory",
        long_copy="Advisory eval input; does not change belief status (D044).",
        color_token="--color-info",
        icon="※",
        data_status="advisory",
    ),
    "blocked": StatusDefinition(
        token="blocked",
        label="Blocked",
        long_copy="One or more hard blockers prevent recommendation.",
        color_token="--color-danger",
        icon="!",
        data_status="blocked",
    ),
    "stale": StatusDefinition(
        token="stale",
        label="Stale",
        long_copy="Was true at evidence time; no longer true.",
        color_token="--color-warn",
        icon="◷",
        data_status="stale",
    ),
    "unsupported": StatusDefinition(
        token="unsupported",
        label="Unsupported",
        long_copy="Evidence does not establish the claim, regardless of world truth.",
        color_token="--color-warn-muted",
        icon="⚠",
        data_status="unsupported",
    ),
    "unsure": StatusDefinition(
        token="unsure",
        label="Unsure",
        long_copy="Operator could not rule.",
        color_token="--color-fg-muted",
        icon="?",
        data_status="unsure",
    ),
    "redacted": StatusDefinition(
        token="redacted",
        label="Redacted",
        long_copy="Structured fields preserved; text intentionally absent.",
        color_token="--color-fg-muted",
        icon="🔒",
        data_status="redacted",
    ),
    "unavailable": StatusDefinition(
        token="unavailable",
        label="Unavailable",
        long_copy="Candidate / prior record missing for this segment.",
        color_token="--color-fg-muted",
        icon="∅",
        data_status="unavailable",
    ),
    "failed": StatusDefinition(
        token="failed",
        label="Failed",
        long_copy="Candidate record failed schema or parse validation.",
        color_token="--color-danger",
        icon="!",
        data_status="failed",
    ),
    "future / backlog": StatusDefinition(
        token="future / backlog",
        label="Future / backlog",
        long_copy="Not yet implemented. Tracked in <RFC ref>.",
        color_token="--color-fg-muted",
        icon="←",
        data_status="future-backlog",
    ),
}


def status_definition(token: str) -> StatusDefinition:
    """Return a status definition by token."""
    try:
        return STATUS_DEFINITIONS[token]
    except KeyError as exc:
        raise KeyError(f"unknown status token: {token!r}") from exc
