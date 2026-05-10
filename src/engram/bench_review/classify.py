"""Classification helpers for the RFC 0029 bench triage workbench."""

from __future__ import annotations

import os

HIGH_DROP_COUNT_THRESHOLD: int = int(
    os.environ.get("ENGRAM_BENCH_REVIEW_HIGH_DROP_COUNT", "3")
)

DATA_STATE_RANK: dict[str, int] = {
    "candidate_zero": 0,
    "complete": 1,
    "candidate_redacted": 2,
    "candidate_malformed": 3,
    "candidate_missing": 4,
    "prior_missing": 5,
}

RISK_RANK: dict[str, int] = {
    "zeroed": 0,
    "high_drop_count": 1,
    "provenance_anomaly": 2,
    "count_changed": 3,
    "predicate_mix_changed": 4,
    "newly_nonzero": 5,
    "unchanged": 6,
}

STRONG_DECISION_DISABLED_STATES: frozenset[str] = frozenset(
    {"candidate_malformed", "candidate_missing", "prior_missing"}
)

STATE_INSTRUCTIONS: dict[str, str] = {
    "candidate_malformed": "Regenerate or inspect the candidate artifact.",
    "candidate_missing": "Regenerate the candidate segment records.",
    "prior_missing": "Inspect prior version filters or prior extraction state.",
    "candidate_redacted": "Review counts-only behavior; confidence is lower.",
    "candidate_zero": "Review the zeroed candidate carefully.",
    "complete": "Review the candidate delta and choose a decision.",
}


def classify_tags(
    *,
    data_state: str,
    prior_claim_count: int | None,
    candidate_claim_count: int | None,
    prior_dropped_count: int | None,
    candidate_dropped_count: int | None,
    prior_predicates: tuple[str, ...],
    candidate_predicates: tuple[str, ...],
    prior_provenance_count: int | None,
    candidate_provenance_count: int | None,
) -> tuple[str, ...]:
    """Return stable comparison tags for one segment."""
    tags: list[str] = []
    if prior_claim_count is not None and candidate_claim_count is not None:
        if prior_claim_count > 0 and candidate_claim_count == 0:
            tags.append("zeroed")
        if prior_claim_count == 0 and candidate_claim_count > 0:
            tags.append("newly_nonzero")
        if prior_claim_count != candidate_claim_count:
            tags.append("count_changed")
    if (
        candidate_dropped_count is not None
        and candidate_dropped_count >= HIGH_DROP_COUNT_THRESHOLD
    ):
        tags.append("high_drop_count")
    if set(prior_predicates) != set(candidate_predicates):
        tags.append("predicate_mix_changed")
    if candidate_claim_count and candidate_claim_count > 0 and (
        candidate_provenance_count is None
        or candidate_provenance_count == 0
        or (
            prior_provenance_count is not None
            and candidate_provenance_count < prior_provenance_count
        )
    ):
        tags.append("provenance_anomaly")
    if not tags:
        tags.append("unchanged")
    return tuple(sorted(set(tags), key=lambda tag: RISK_RANK.get(tag, 99)))


def resolve_data_state(
    *,
    candidate_malformed: bool,
    candidate_missing: bool,
    prior_missing: bool,
    candidate_redacted: bool,
    candidate_claim_count: int | None,
) -> str:
    """Resolve the single data state using Spec 0029 precedence."""
    if candidate_malformed:
        return "candidate_malformed"
    if candidate_missing:
        return "candidate_missing"
    if prior_missing:
        return "prior_missing"
    if candidate_redacted:
        return "candidate_redacted"
    if candidate_claim_count == 0:
        return "candidate_zero"
    return "complete"


def queue_sort_key(data_state: str, tags: tuple[str, ...], segment_id: str) -> tuple[int, int, str]:
    """Return the stable queue key for one row."""
    first_risk = min((RISK_RANK.get(tag, 99) for tag in tags), default=99)
    return (DATA_STATE_RANK.get(data_state, 99), first_risk, segment_id)


def state_instruction(data_state: str) -> str:
    """Return the one-line instruction for a data state."""
    return STATE_INSTRUCTIONS.get(data_state, "Review the segment state.")
