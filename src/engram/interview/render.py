"""Shared rendering helpers for CLI and web (RFC 0027).

This module is the unified rendering surface for the interview UX. Both
``engram.cli`` (the operator REPL loop) and ``engram.interview.web`` (the
FastAPI app introduced by Spec 0027) import the same constants and helpers
from here so the two surfaces cannot drift in formatting, vocabulary, or
truncation behaviour. Golden-output tests in
``tests/test_interview_render.py`` pin the rendered text to its current
shape so the extraction is no-behaviour-change for the CLI.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any  # noqa: F401  # used for psycopg row dicts and SampledTarget.payload

import psycopg

from engram.interview.sampler import SampledTarget


# Verdict vocabulary (moved verbatim from cli.py).
VERDICT_PROMPT: str = (
    "verdict [t/f/stale/unsupported/unsure/skip] (q to save and quit) > "
)
VERDICT_ALIAS: dict[str, str] = {
    "t": "true",
    "f": "false",
    "true": "true",
    "false": "false",
}
VERDICT_VALID: frozenset[str] = frozenset(
    {"true", "false", "stale", "unsupported", "unsure", "skip"}
)
RATIONALE_PROMPT_BY_VERDICT: dict[str, str] = {
    "false": "correct value > ",
    "stale": "when did it change? > ",
    "unsupported": "what's missing from the evidence? > ",
    "unsure": "note (Enter to skip) > ",
}

# Evidence layout caps (moved verbatim from cli.py).
EVIDENCE_EXCERPT_LIMIT: int = 280
EVIDENCE_ROWS_SHOWN: int = 3


def fetch_evidence_excerpts(
    conn: psycopg.Connection, evidence_ids: list[str]
) -> list[dict[str, Any]]:
    """Fetch up to ``EVIDENCE_ROWS_SHOWN`` messages by id, in chronological order.

    Returns a list of dicts with keys ``id``, ``role``, ``created_at``,
    ``content`` (truncated at ``EVIDENCE_EXCERPT_LIMIT`` with a trailing
    ellipsis), ``source_kind``, and ``conv_title``. Caller decides whether
    to print or render.
    """
    if not evidence_ids:
        return []
    rows = conn.execute(
        """
        SELECT
            m.id::text,
            m.role,
            m.created_at,
            m.content_text,
            m.source_kind::text,
            c.title
        FROM messages m
        LEFT JOIN conversations c ON c.id = m.conversation_id
        WHERE m.id = ANY(%s)
        ORDER BY m.created_at NULLS LAST, m.sequence_index
        LIMIT %s
        """,
        (evidence_ids, EVIDENCE_ROWS_SHOWN),
    ).fetchall()
    excerpts: list[dict[str, Any]] = []
    for row in rows:
        msg_id, role, created_at, content, source_kind, conv_title = row
        body = content or ""
        if len(body) > EVIDENCE_EXCERPT_LIMIT:
            body = body[:EVIDENCE_EXCERPT_LIMIT].rstrip() + "…"
        excerpts.append(
            {
                "id": msg_id,
                "role": role,
                "created_at": created_at,
                "content": body,
                "source_kind": source_kind,
                "conv_title": conv_title,
            }
        )
    return excerpts


def fetch_target_display(
    conn: psycopg.Connection, target: SampledTarget
) -> dict[str, Any]:
    """Pull operator-readable summary plus evidence excerpts for a target.

    Dispatches on ``target.target_kind``. Returns a dict with keys
    ``summary``, ``predicate``, ``predicate_doc``, ``cardinality_class``,
    ``excerpts``, ``evidence_count``, ``evidence_min``, ``evidence_max``,
    ``valid_from``, ``valid_to``. Missing target rows return a dict with
    ``summary='<missing claim row>'`` (or ``'<missing belief row>'``) and
    an empty ``excerpts`` list — the caller renders the missing row
    visibly rather than crashing.
    """
    if target.target_kind == "claim":
        row = conn.execute(
            """
            SELECT
                c.subject_text,
                c.predicate,
                c.object_text,
                c.object_json,
                c.evidence_message_ids,
                cardinality(c.evidence_message_ids),
                pv.description,
                pv.cardinality_class,
                (SELECT MIN(m.created_at) FROM messages m
                 WHERE m.id = ANY(c.evidence_message_ids)) AS evidence_min,
                (SELECT MAX(m.created_at) FROM messages m
                 WHERE m.id = ANY(c.evidence_message_ids)) AS evidence_max
            FROM claims c
            LEFT JOIN predicate_vocabulary pv ON pv.predicate = c.predicate
            WHERE c.id = %s
            """,
            (target.target_id,),
        ).fetchone()
        if row is None:
            return {"summary": "<missing claim row>", "excerpts": [], "evidence_count": 0}
        (
            subj, pred, obj_text, obj_json, ev_ids, ev_count,
            pred_doc, card_class, ev_min, ev_max,
        ) = row
        obj = obj_text if obj_text is not None else (str(obj_json) if obj_json else "")
        excerpts = fetch_evidence_excerpts(conn, list(ev_ids or []))
        return {
            "summary": f'{subj} -[{pred}]-> {obj}',
            "predicate": pred,
            "predicate_doc": pred_doc or "",
            "cardinality_class": card_class,
            "excerpts": excerpts,
            "evidence_count": int(ev_count),
            "evidence_min": ev_min,
            "evidence_max": ev_max,
            "valid_from": None,
            "valid_to": None,
        }
    row = conn.execute(
        """
        SELECT
            b.subject_text,
            b.predicate,
            b.object_text,
            b.object_json,
            b.valid_from,
            b.valid_to,
            b.evidence_ids,
            cardinality(b.evidence_ids),
            pv.description,
            pv.cardinality_class,
            (SELECT MIN(m.created_at) FROM messages m
             WHERE m.id = ANY(b.evidence_ids)) AS evidence_min,
            (SELECT MAX(m.created_at) FROM messages m
             WHERE m.id = ANY(b.evidence_ids)) AS evidence_max
        FROM beliefs b
        LEFT JOIN predicate_vocabulary pv ON pv.predicate = b.predicate
        WHERE b.id = %s
        """,
        (target.target_id,),
    ).fetchone()
    if row is None:
        return {"summary": "<missing belief row>", "excerpts": [], "evidence_count": 0}
    (
        subj, pred, obj_text, obj_json, vfrom, vto, ev_ids, ev_count,
        pred_doc, card_class, ev_min, ev_max,
    ) = row
    obj = obj_text if obj_text is not None else (str(obj_json) if obj_json else "")
    excerpts = fetch_evidence_excerpts(conn, list(ev_ids or []))
    return {
        "summary": f'{subj} -[{pred}]-> {obj}',
        "predicate": pred,
        "predicate_doc": pred_doc or "",
        "cardinality_class": card_class,
        "excerpts": excerpts,
        "evidence_count": int(ev_count),
        "evidence_min": ev_min,
        "evidence_max": ev_max,
        "valid_from": vfrom,
        "valid_to": vto,
    }


def pick_question(
    target: SampledTarget,
    display: dict[str, Any],
    *,
    now: datetime | None = None,
) -> str:
    """Choose a question framing based on ``stability_class`` and cardinality.

    Claim targets always ask about cited evidence — claims are time-stamped
    paraphrases by definition. Belief targets dispatch on
    ``cardinality_class == 'event'`` (point-in-time framing) or
    ``stability_class in {'mood', 'task'}`` (transient framing); else the
    "currently true" framing.

    ``now`` defaults to ``datetime.now(timezone.utc)`` and is accepted as an
    explicit kwarg so tests can pin the rendered ``ev_date`` to UTC
    regardless of host-machine timezone (RFC 0027 F015).
    ``evidence_max`` is rendered through ``.date().isoformat()`` so CLI and
    web verdicts on the same belief render identical strings.
    """
    # ``now`` is reserved for future use (e.g. relative-recency framings); the
    # current branches do not consume it. Resolving it here keeps the kwarg
    # part of the public signature without affecting current output.
    if now is None:
        now = datetime.now(timezone.utc)
    ev_max = display.get("evidence_max")
    ev_date = ev_max.date().isoformat() if ev_max else "the cited time"
    if target.target_kind == "claim":
        return f"Q: Is this an accurate paraphrase of what was said on {ev_date}?"
    cardinality = (display.get("cardinality_class") or "").strip()
    if cardinality == "event":
        return f"Q: Did this event happen as paraphrased on {ev_date}?"
    if target.stability_class in {"mood", "task"}:
        return f"Q: Was this true around {ev_date}?"
    return "Q: Is this currently true?"


def rationale_prompt_for(verdict: str) -> str | None:
    """Verdict-specific rationale prompt; returns ``None`` for ``true``/``skip``.

    Used by both the CLI ``input(...)`` call site and the web template's
    ``RATIONALE_PROMPT_BY_VERDICT`` lookup. Falls through to a generic
    "rationale (Enter to skip) > " prompt for verdicts not in the table.
    """
    if verdict in {"true", "skip"}:
        return None
    return RATIONALE_PROMPT_BY_VERDICT.get(verdict, "rationale (Enter to skip) > ")


def format_header(target: SampledTarget, idx: int, total: int) -> str:
    """Render the ``[idx/total] target_kind target_id ...`` header line.

    Includes the ``status=...`` suffix when ``target.target_kind == 'belief'
    and target.belief_status`` is truthy. Whitespace and ordering must
    match the CLI's existing output: ``[i/n] kind id  stability=...
    conf=N.NN  conf_band=...  recency=...`` with two-space separators and
    a four-space prefix on the ``status=...`` suffix.
    """
    header = (
        f"[{idx}/{total}] {target.target_kind} {target.target_id}"
        f"  stability={target.stability_class}  conf={target.confidence:.2f}"
        f"  conf_band={target.conf_band}  recency={target.recency_band}"
    )
    if target.target_kind == "belief" and target.belief_status:
        header += f"  status={target.belief_status}"
    return header


def format_summary_line(display: dict[str, Any]) -> str:
    """Render summary plus optional ``(predicate_doc)`` append.

    The four-space prefix the CLI prepends before printing is the caller's
    responsibility; this helper returns just the line content.
    """
    summary_line = display.get("summary", "")
    pred_doc = display.get("predicate_doc")
    if pred_doc:
        summary_line = f"{summary_line}    ({pred_doc})"
    return summary_line


def format_evidence_dates(display: dict[str, Any]) -> str | None:
    """Render the ``evidence: N row(s)[, ...]`` line, or None if suppressed.

    Returns ``None`` when ``display['evidence_count']`` is ``None`` (the
    CLI suppresses the line in that case). Otherwise returns the
    ``"evidence: N row(s)[, evidence dates: ...][, valid_from ...]"`` line
    without leading whitespace; caller prepends the indent.
    """
    if display.get("evidence_count") is None:
        return None
    parts: list[str] = []
    ev_min = display.get("evidence_min")
    ev_max = display.get("evidence_max")
    if ev_min and ev_max:
        if ev_min.date() == ev_max.date():
            parts.append(f"evidence dates: {ev_min.date()}")
        else:
            parts.append(
                f"evidence dates: {ev_min.date()}..{ev_max.date()}"
            )
    if display.get("valid_from") and display.get("valid_to"):
        parts.append(
            f"valid {display['valid_from'].date()}"
            f"..{display['valid_to'].date()}"
        )
    elif display.get("valid_from"):
        parts.append(f"valid_from {display['valid_from'].date()}")
    suffix = (", " + ", ".join(parts)) if parts else ""
    return f"evidence: {display['evidence_count']} row(s){suffix}"


def format_evidence_excerpts(
    excerpts: list[dict[str, Any]], total: int
) -> list[str]:
    """Return chronological evidence-row text lines (no printing).

    Each row produces one header line (``"  ts  role  (src)  [title]"``)
    followed by indented body lines (``"      <line>"`` for each line of
    ``content.splitlines()``). The CLI joins with newlines and prints; the
    web template iterates rows and renders each as
    ``_evidence_excerpt.html``. If ``total > len(excerpts)``, an additional
    ``"    … {total - len(excerpts)} more row(s) not shown"`` line is
    appended.
    """
    if not excerpts:
        return []
    lines: list[str] = ["  evidence:"]
    for ex in excerpts:
        ts = ex["created_at"].strftime("%Y-%m-%d") if ex["created_at"] else "?"
        role = ex["role"] or "?"
        src = ex["source_kind"] or "?"
        title = f"  [{ex['conv_title']}]" if ex.get("conv_title") else ""
        lines.append(f"    {ts}  {role}  ({src}){title}")
        if ex["content"]:
            for body_line in ex["content"].splitlines() or [""]:
                lines.append(f"      {body_line}")
    if total > len(excerpts):
        lines.append(f"    … {total - len(excerpts)} more row(s) not shown")
    return lines
