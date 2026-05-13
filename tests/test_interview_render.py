"""Golden-output tests for the shared CLI/web rendering helpers (RFC 0027).

These tests pin the exact strings produced by the rendering helpers in
``engram.interview.render``. They run without a database; ``MagicMock`` is
used wherever a ``conn`` would otherwise be required, but the helpers
under test here either operate on plain dicts or take a ``SampledTarget``
directly.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from unittest.mock import MagicMock

import pytest

from engram.interview.render import (
    EVIDENCE_EXCERPT_LIMIT,
    EVIDENCE_ROWS_SHOWN,
    RATIONALE_PROMPT_BY_VERDICT,
    VERDICT_ALIAS,
    VERDICT_VALID,
    fetch_evidence_excerpts,
    format_evidence_dates,
    format_evidence_excerpts,
    format_header,
    format_summary_line,
    pick_question,
    rationale_prompt_for,
    subject_kind_warning,
)
from engram.interview.sampler import SampledTarget


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _claim_target(
    *,
    target_id: str = "claim-id-1234",
    stability_class: str = "identity",
    confidence: float = 0.78,
    conf_band: str = "0.6-0.8",
    recency_band: str = "<30d",
    belief_status: str | None = None,
) -> SampledTarget:
    return SampledTarget(
        target_kind="claim",
        target_id=target_id,
        stability_class=stability_class,
        confidence=confidence,
        observed_at=datetime(2024, 6, 1, 12, 0, tzinfo=timezone.utc),
        conf_band=conf_band,
        recency_band=recency_band,
        belief_status=belief_status,
        candidate_pool_snapshot_id="pool-1",
        active_learning_signal_version=None,
        extraction_prompt_version="v1",
        extraction_model_version="model-a",
        consolidation_prompt_version=None,
        consolidation_model_version=None,
        request_profile_version="profile-v1",
    )


def _belief_target(
    *,
    target_id: str = "belief-id-5678",
    stability_class: str = "identity",
    confidence: float = 0.42,
    conf_band: str = "0.4-0.6",
    recency_band: str = "<90d",
    belief_status: str | None = "candidate",
) -> SampledTarget:
    return SampledTarget(
        target_kind="belief",
        target_id=target_id,
        stability_class=stability_class,
        confidence=confidence,
        observed_at=datetime(2024, 6, 1, 12, 0, tzinfo=timezone.utc),
        conf_band=conf_band,
        recency_band=recency_band,
        belief_status=belief_status,
        candidate_pool_snapshot_id="pool-2",
        active_learning_signal_version=None,
        extraction_prompt_version=None,
        extraction_model_version=None,
        consolidation_prompt_version="cv1",
        consolidation_model_version="model-c",
        request_profile_version="profile-v1",
    )


# ---------------------------------------------------------------------------
# format_header
# ---------------------------------------------------------------------------


def test_format_header_claim() -> None:
    target = _claim_target()
    out = format_header(target, idx=2, total=10)
    expected = (
        "[2/10] claim claim-id-1234"
        "  stability=identity  conf=0.78"
        "  conf_band=0.6-0.8  recency=<30d"
    )
    assert out == expected


def test_format_header_belief() -> None:
    target = _belief_target(belief_status="provisional")
    out = format_header(target, idx=3, total=5)
    expected = (
        "[3/5] belief belief-id-5678"
        "  stability=identity  conf=0.42"
        "  conf_band=0.4-0.6  recency=<90d"
        "  status=provisional"
    )
    assert out == expected


def test_format_header_belief_without_status_omits_suffix() -> None:
    target = _belief_target(belief_status=None)
    out = format_header(target, idx=1, total=1)
    assert "status=" not in out


# ---------------------------------------------------------------------------
# format_summary_line
# ---------------------------------------------------------------------------


def test_format_summary_line_with_predicate_doc() -> None:
    display: dict[str, Any] = {
        "summary": "user -[drives]-> Subaru",
        "predicate_doc": "subject drives a vehicle",
        "subject_kind_hint": "",
    }
    assert (
        format_summary_line(display)
        == "user -[drives]-> Subaru\n  intent: subject drives a vehicle"
    )


def test_format_summary_line_with_subject_kind_hint() -> None:
    display: dict[str, Any] = {
        "summary": "Hobnob -[has_name]-> Hobnob",
        "predicate_doc": "legal or preferred name",
        "subject_kind_hint": "persons only",
    }
    assert (
        format_summary_line(display) == "Hobnob -[has_name]-> Hobnob\n"
        "  intent: legal or preferred name (persons only)"
    )


def test_format_summary_line_with_subject_kind_warning() -> None:
    display: dict[str, Any] = {
        "summary": "Hobnob -[has_name]-> Hobnob",
        "predicate_doc": "legal or preferred name",
        "subject_kind_hint": "persons only",
        "subject_kind_warning": (
            'subject "Hobnob" looks like a place/business; predicate intent '
            "is persons. Likely a `false` extraction."
        ),
    }
    assert format_summary_line(display).splitlines() == [
        "Hobnob -[has_name]-> Hobnob",
        "  intent: legal or preferred name (persons only)",
        (
            '  [warning] subject "Hobnob" looks like a place/business; '
            "predicate intent is persons. Likely a `false` extraction."
        ),
    ]


def test_format_summary_line_without_predicate_doc() -> None:
    display: dict[str, Any] = {
        "summary": "user -[prefers]-> vim",
        "predicate_doc": "",
    }
    assert format_summary_line(display) == "user -[prefers]-> vim"


def test_format_summary_line_missing_summary_key_returns_empty() -> None:
    assert format_summary_line({}) == ""


# ---------------------------------------------------------------------------
# format_evidence_dates
# ---------------------------------------------------------------------------


def test_format_evidence_dates_single_day() -> None:
    day = datetime(2024, 6, 1, 9, 0, tzinfo=timezone.utc)
    display = {
        "evidence_count": 2,
        "evidence_min": day,
        "evidence_max": day.replace(hour=18),
        "valid_from": None,
        "valid_to": None,
    }
    assert format_evidence_dates(display) == "evidence: 2 row(s), evidence dates: 2024-06-01"


def test_format_evidence_dates_range() -> None:
    display = {
        "evidence_count": 3,
        "evidence_min": datetime(2024, 6, 1, tzinfo=timezone.utc),
        "evidence_max": datetime(2024, 6, 7, tzinfo=timezone.utc),
        "valid_from": None,
        "valid_to": None,
    }
    assert (
        format_evidence_dates(display)
        == "evidence: 3 row(s), evidence dates: 2024-06-01..2024-06-07"
    )


def test_format_evidence_dates_with_valid_from() -> None:
    display = {
        "evidence_count": 1,
        "evidence_min": None,
        "evidence_max": None,
        "valid_from": datetime(2024, 1, 15, tzinfo=timezone.utc),
        "valid_to": None,
    }
    assert (
        format_evidence_dates(display)
        == "evidence: 1 row(s), valid_from 2024-01-15"
    )


def test_format_evidence_dates_with_valid_range() -> None:
    display = {
        "evidence_count": 4,
        "evidence_min": datetime(2024, 6, 1, tzinfo=timezone.utc),
        "evidence_max": datetime(2024, 6, 1, tzinfo=timezone.utc),
        "valid_from": datetime(2024, 6, 1, tzinfo=timezone.utc),
        "valid_to": datetime(2024, 7, 1, tzinfo=timezone.utc),
    }
    out = format_evidence_dates(display)
    assert out is not None
    assert "evidence dates: 2024-06-01" in out
    assert "valid 2024-06-01..2024-07-01" in out


def test_format_evidence_dates_none() -> None:
    display: dict[str, Any] = {
        "evidence_count": None,
        "evidence_min": None,
        "evidence_max": None,
    }
    assert format_evidence_dates(display) is None


# ---------------------------------------------------------------------------
# format_evidence_excerpts
# ---------------------------------------------------------------------------


def test_format_evidence_excerpts_returns_lines() -> None:
    excerpts = [
        {
            "id": "msg-1",
            "role": "user",
            "created_at": datetime(2024, 6, 1, 9, 0, tzinfo=timezone.utc),
            "content": "hello world",
            "source_kind": "chatgpt_export",
            "conv_title": "Talk A",
        },
        {
            "id": "msg-2",
            "role": "assistant",
            "created_at": datetime(2024, 6, 2, 9, 0, tzinfo=timezone.utc),
            "content": "line one\nline two",
            "source_kind": "chatgpt_export",
            "conv_title": None,
        },
    ]
    lines = format_evidence_excerpts(excerpts, total=2)
    assert isinstance(lines, list)
    assert lines == [
        "  evidence:",
        "    2024-06-01  user  (chatgpt_export)  [Talk A]",
        "      hello world",
        "    2024-06-02  assistant  (chatgpt_export)",
        "      line one",
        "      line two",
    ]


def test_format_evidence_excerpts_empty_returns_empty() -> None:
    assert format_evidence_excerpts([], total=0) == []


def test_format_evidence_excerpts_appends_more_row_count() -> None:
    excerpts = [
        {
            "id": "msg-1",
            "role": "user",
            "created_at": datetime(2024, 6, 1, 9, 0, tzinfo=timezone.utc),
            "content": "ok",
            "source_kind": "chatgpt_export",
            "conv_title": "Talk A",
        }
    ]
    lines = format_evidence_excerpts(excerpts, total=4)
    assert lines[-1] == "    … 3 more row(s) not shown"


def test_format_evidence_excerpts_handles_missing_created_at_and_role() -> None:
    excerpts = [
        {
            "id": "msg-x",
            "role": None,
            "created_at": None,
            "content": "",
            "source_kind": None,
            "conv_title": None,
        }
    ]
    lines = format_evidence_excerpts(excerpts, total=1)
    # Header line uses '?' placeholders; empty content does not produce body lines.
    assert lines == ["  evidence:", "    ?  ?  (?)"]


# ---------------------------------------------------------------------------
# pick_question
# ---------------------------------------------------------------------------


def test_pick_question_claim() -> None:
    target = _claim_target()
    display = {
        "evidence_max": datetime(2024, 6, 7, 9, 0, tzinfo=timezone.utc),
    }
    assert (
        pick_question(target, display)
        == "Q: Is this an accurate paraphrase of what was said on 2024-06-07?"
    )


def test_pick_question_belief_event_predicate() -> None:
    target = _belief_target(stability_class="identity")
    display = {
        "evidence_max": datetime(2024, 6, 7, 9, 0, tzinfo=timezone.utc),
        "cardinality_class": "event",
    }
    assert (
        pick_question(target, display)
        == "Q: Did this event happen as paraphrased on 2024-06-07?"
    )


def test_pick_question_belief_mood_stability() -> None:
    target = _belief_target(stability_class="mood")
    display = {
        "evidence_max": datetime(2024, 6, 7, 9, 0, tzinfo=timezone.utc),
        "cardinality_class": "state",
    }
    assert (
        pick_question(target, display)
        == "Q: Was this true around 2024-06-07?"
    )


def test_pick_question_belief_task_stability() -> None:
    target = _belief_target(stability_class="task")
    display = {
        "evidence_max": datetime(2024, 6, 7, 9, 0, tzinfo=timezone.utc),
        "cardinality_class": "state",
    }
    assert (
        pick_question(target, display)
        == "Q: Was this true around 2024-06-07?"
    )


def test_pick_question_belief_default() -> None:
    target = _belief_target(stability_class="identity")
    display = {
        "evidence_max": datetime(2024, 6, 7, 9, 0, tzinfo=timezone.utc),
        "cardinality_class": "state",
    }
    assert pick_question(target, display) == "Q: Is this currently true?"


def test_pick_question_uses_utc_now() -> None:
    """Passing an explicit ``now`` in a non-UTC timezone must still render
    ``ev_date`` from ``evidence_max`` in UTC. This is a regression guard for
    F015 (CLI vs web ev_date drift)."""
    target = _claim_target()
    # evidence_max at 23:30 UTC on 2024-06-07. In Pacific (UTC-7) that's
    # still 2024-06-07; the helper renders the UTC date regardless.
    display = {
        "evidence_max": datetime(2024, 6, 7, 23, 30, tzinfo=timezone.utc),
    }
    pacific_now = datetime(2024, 6, 8, 0, 0, tzinfo=timezone(timedelta(hours=-7)))
    out = pick_question(target, display, now=pacific_now)
    assert "2024-06-07" in out
    assert "2024-06-08" not in out


def test_pick_question_missing_evidence_max_uses_placeholder() -> None:
    target = _claim_target()
    display: dict[str, Any] = {"evidence_max": None}
    assert "the cited time" in pick_question(target, display)


# ---------------------------------------------------------------------------
# rationale_prompt_for
# ---------------------------------------------------------------------------


def test_rationale_prompt_for_true_returns_none() -> None:
    assert rationale_prompt_for("true") is None


def test_rationale_prompt_for_skip_returns_none() -> None:
    assert rationale_prompt_for("skip") is None


def test_rationale_prompt_for_false_returns_correct_value() -> None:
    assert rationale_prompt_for("false") == (
        "what's wrong? (e.g., wrong predicate, wrong subject, different "
        "object value, predicate doesn't apply) > "
    )


def test_rationale_prompt_for_stale_returns_when_did_it_change() -> None:
    assert rationale_prompt_for("stale") == "when did it change? > "


def test_rationale_prompt_for_unsupported_returns_what_is_missing() -> None:
    assert (
        rationale_prompt_for("unsupported")
        == "what's missing from the evidence? > "
    )


def test_rationale_prompt_for_unsure_returns_note_prompt() -> None:
    assert rationale_prompt_for("unsure") == "note (Enter to skip) > "


# ---------------------------------------------------------------------------
# Verdict vocabulary invariants
# ---------------------------------------------------------------------------


def test_verdict_valid_set_membership() -> None:
    expected = {"true", "false", "stale", "unsupported", "unsure", "skip"}
    assert set(VERDICT_VALID) == expected
    assert isinstance(VERDICT_VALID, frozenset)


def test_verdict_alias_dispatch() -> None:
    assert VERDICT_ALIAS["t"] == "true"
    assert VERDICT_ALIAS["f"] == "false"
    assert VERDICT_ALIAS["true"] == "true"
    assert VERDICT_ALIAS["false"] == "false"


def test_rationale_prompt_table_covers_all_non_terminal_verdicts() -> None:
    non_terminal = set(VERDICT_VALID) - {"true", "skip"}
    assert set(RATIONALE_PROMPT_BY_VERDICT) == non_terminal


def test_evidence_layout_caps() -> None:
    assert EVIDENCE_EXCERPT_LIMIT == 280
    assert EVIDENCE_ROWS_SHOWN == 3


# ---------------------------------------------------------------------------
# subject_kind_warning
# ---------------------------------------------------------------------------


def test_subject_kind_warning_uses_curated_non_person_terms() -> None:
    conn = MagicMock()
    conn.execute.return_value.fetchall.return_value = []
    warning = subject_kind_warning(conn, "Hobnob", "persons only")
    assert warning == (
        'subject "Hobnob" looks like a place/business; predicate intent is '
        "persons. Likely a `false` extraction."
    )


def test_subject_kind_warning_uses_active_entity_kind() -> None:
    conn = MagicMock()
    conn.execute.return_value.fetchall.return_value = [("place",)]
    warning = subject_kind_warning(conn, "The Venue", "persons only")
    assert warning == (
        'subject "The Venue" looks like a place/business; predicate intent is '
        "persons. Likely a `false` extraction."
    )


def test_subject_kind_warning_suppresses_ambiguous_person_entity() -> None:
    conn = MagicMock()
    conn.execute.return_value.fetchall.return_value = [("person",), ("place",)]
    assert subject_kind_warning(conn, "Jordan", "persons only") is None


def test_subject_kind_warning_skips_non_person_hints() -> None:
    conn = MagicMock()
    assert subject_kind_warning(conn, "A Project", "projects only") is None
    conn.execute.assert_not_called()


@pytest.mark.parametrize(
    "subject_kind_hint",
    ["persons or projects", "persons or organizations", "persons or households"],
)
def test_subject_kind_warning_skips_mixed_allowed_person_hints(
    subject_kind_hint: str,
) -> None:
    conn = MagicMock()
    assert subject_kind_warning(conn, "A Project", subject_kind_hint) is None
    conn.execute.assert_not_called()


# ---------------------------------------------------------------------------
# fetch_evidence_excerpts: smoke test with mocked conn (no real DB)
# ---------------------------------------------------------------------------


def test_fetch_evidence_excerpts_empty_input_returns_empty_without_query() -> None:
    conn = MagicMock()
    assert fetch_evidence_excerpts(conn, []) == []
    conn.execute.assert_not_called()


def test_fetch_evidence_excerpts_truncates_content_at_limit() -> None:
    conn = MagicMock()
    long_body = "x" * (EVIDENCE_EXCERPT_LIMIT + 50)
    conn.execute.return_value.fetchall.return_value = [
        (
            "msg-1",
            "user",
            datetime(2024, 6, 1, 9, 0, tzinfo=timezone.utc),
            long_body,
            "chatgpt_export",
            "Talk",
        )
    ]
    excerpts = fetch_evidence_excerpts(conn, ["msg-1"])
    assert len(excerpts) == 1
    body = excerpts[0]["content"]
    assert body.endswith("…")
    # body length is at most limit + 1 (the appended ellipsis)
    assert len(body) <= EVIDENCE_EXCERPT_LIMIT + 1
