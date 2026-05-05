from __future__ import annotations

import json
import math
import re
import statistics
import time
import unicodedata
from collections import defaultdict
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Any

import psycopg
from psycopg import errors
from psycopg.types.json import Jsonb

from engram.consolidator.transitions import (
    CONSOLIDATOR_MODEL_VERSION,
    CONSOLIDATOR_PROMPT_VERSION,
    BeliefPayload,
    close_belief,
    insert_belief,
    reject_belief,
    supersede_belief,
)
from engram.progress import upsert_progress


ACTIVE_BELIEF_STATUSES = ("candidate", "provisional", "accepted")
UNIT_SEPARATOR = "\x1f"


@dataclass(frozen=True)
class ClaimRow:
    id: str
    segment_id: str
    generation_id: str
    conversation_id: str
    subject_text: str
    subject_normalized: str
    predicate: str
    cardinality_class: str
    object_kind: str
    group_object_keys: tuple[str, ...]
    object_text: str | None
    object_json: dict[str, Any] | None
    stability_class: str
    confidence: float
    evidence_message_ids: list[str]
    extracted_at: Any
    privacy_tier: int


@dataclass(frozen=True)
class BeliefRow:
    id: str
    subject_text: str
    subject_normalized: str
    predicate: str
    cardinality_class: str
    group_object_key: str
    object_text: str | None
    object_json: dict[str, Any] | None
    valid_from: Any
    valid_to: Any | None
    observed_at: Any
    extracted_at: Any
    status: str
    confidence: float
    evidence_ids: list[str]
    claim_ids: list[str]
    prompt_version: str
    model_version: str
    privacy_tier: int


@dataclass(frozen=True)
class ConsolidationBatchResult:
    processed: int
    created: int
    superseded: int
    contradictions: int
    rejected: int = 0


@dataclass(frozen=True)
class GroupResult:
    created: int = 0
    superseded: int = 0
    contradictions: int = 0
    rejected: int = 0


def normalize_subject(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", text or "")
    normalized = normalized.lower().strip()
    normalized = re.sub(r"\s+", " ", normalized)
    normalized = re.sub(r"[\.,;:!?]+$", "", normalized)
    return normalized


def normalize_group_object_value(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", text or "")
    normalized = normalized.lower().strip()
    return re.sub(r"\s+", " ", normalized)


def apply_phase3_reclassification_invalidations(conn: psycopg.Connection) -> int:
    rows = conn.execute(
        """
        UPDATE claim_extractions ce
        SET status = 'superseded',
            completed_at = COALESCE(ce.completed_at, now()),
            raw_payload = ce.raw_payload || jsonb_build_object(
                'failure_kind', 'privacy_reclassification',
                'superseded_by_phase3_invalidation', true
            )
        FROM segments s
        WHERE ce.segment_id = s.id
          AND s.invalidated_at IS NOT NULL
          AND ce.status IN ('extracting', 'extracted')
        RETURNING ce.segment_id::text, s.conversation_id::text
        """
    ).fetchall()
    conversations = {row[1] for row in rows if row[1]}
    for conversation_id in conversations:
        upsert_progress(
            conn,
            stage="extractor",
            scope=f"conversation:{conversation_id}",
            status="pending",
            position={
                "conversation_id": conversation_id,
                "queued_by": "privacy_reclassification",
            },
        )
        upsert_progress(
            conn,
            stage="consolidator",
            scope=f"conversation:{conversation_id}",
            status="pending",
            position={
                "conversation_id": conversation_id,
                "queued_by": "privacy_reclassification",
            },
        )
    return len(rows)


def consolidate_beliefs(
    conn: psycopg.Connection,
    batch_size: int,
    *,
    prompt_version: str = CONSOLIDATOR_PROMPT_VERSION,
    model_version: str = CONSOLIDATOR_MODEL_VERSION,
    conversation_id: str | None = None,
    rebuild: bool = False,
    limit: int | None = None,
    progress_callback: Callable[[str, dict[str, Any]], None] | None = None,
) -> ConsolidationBatchResult:
    apply_phase3_reclassification_invalidations(conn)
    if rebuild:
        close_active_beliefs_for_rebuild(
            conn,
            prompt_version=prompt_version,
            model_version=model_version,
        )

    conversations = (
        [conversation_id]
        if conversation_id
        else fetch_conversations_for_consolidation(
            conn,
            batch_size=batch_size,
            limit=limit,
        )
    )
    if limit is not None:
        conversations = conversations[:limit]

    totals = {"processed": 0, "created": 0, "superseded": 0, "contradictions": 0, "rejected": 0}
    for current_conversation_id in conversations:
        started_at = time.monotonic()
        if progress_callback:
            progress_callback(
                "consolidate_start",
                {"conversation_id": current_conversation_id},
            )
        try:
            result = consolidate_conversation(
                conn,
                current_conversation_id,
                prompt_version=prompt_version,
                model_version=model_version,
            )
        except Exception as exc:
            upsert_progress(
                conn,
                stage="consolidator",
                scope=f"conversation:{current_conversation_id}",
                status="failed",
                position={"conversation_id": current_conversation_id},
                last_error=str(exc),
                increment_error=True,
            )
            if progress_callback:
                progress_callback(
                    "consolidate_failed",
                    {
                        "conversation_id": current_conversation_id,
                        "error": str(exc),
                        "elapsed": time.monotonic() - started_at,
                    },
                )
            continue

        totals["processed"] += 1
        totals["created"] += result.created
        totals["superseded"] += result.superseded
        totals["contradictions"] += result.contradictions
        totals["rejected"] += result.rejected
        latest = latest_claim_extracted_at(conn, current_conversation_id)
        upsert_progress(
            conn,
            stage="consolidator",
            scope=f"conversation:{current_conversation_id}",
            status="completed",
            position={
                "conversation_id": current_conversation_id,
                "last_claim_extracted_at": latest.isoformat() if latest else None,
            },
        )
        if progress_callback:
            progress_callback(
                "consolidate_done",
                {
                    "conversation_id": current_conversation_id,
                    "beliefs_created": result.created,
                    "beliefs_superseded": result.superseded,
                    "contradictions_detected": result.contradictions,
                    "beliefs_rejected": result.rejected,
                    "elapsed": time.monotonic() - started_at,
                },
            )

    return ConsolidationBatchResult(**totals)


def consolidate_conversation(
    conn: psycopg.Connection,
    conversation_id: str,
    *,
    prompt_version: str = CONSOLIDATOR_PROMPT_VERSION,
    model_version: str = CONSOLIDATOR_MODEL_VERSION,
) -> GroupResult:
    active_claims = fetch_active_claims(conn, conversation_id=conversation_id)
    global_active_claim_ids = fetch_global_active_claim_ids(conn)
    orphan_result = apply_decision_rule_0(
        conn,
        global_active_claim_ids,
        prompt_version=prompt_version,
        model_version=model_version,
    )

    grouped = group_claims_by_value(active_claims)
    result = GroupResult(
        created=orphan_result.created,
        superseded=orphan_result.superseded,
        contradictions=orphan_result.contradictions,
        rejected=orphan_result.rejected,
    )
    for claims in grouped:
        group_result = process_claim_value_group(
            conn,
            claims,
            prompt_version=prompt_version,
            model_version=model_version,
        )
        result = GroupResult(
            created=result.created + group_result.created,
            superseded=result.superseded + group_result.superseded,
            contradictions=result.contradictions + group_result.contradictions,
            rejected=result.rejected + group_result.rejected,
        )
    return result


def fetch_conversations_for_consolidation(
    conn: psycopg.Connection,
    *,
    batch_size: int,
    limit: int | None,
) -> list[str]:
    rows = conn.execute(
        """
        WITH active_claims AS (
            SELECT c.conversation_id, max(c.extracted_at) AS last_claim_extracted_at
            FROM claims c
            JOIN claim_extractions ce ON ce.id = c.extraction_id
            JOIN segments s ON s.id = c.segment_id
            JOIN segment_generations sg ON sg.id = s.generation_id
            WHERE ce.status = 'extracted'
              AND s.is_active = true
              AND sg.status = 'active'
              AND s.source_kind IN ('chatgpt', 'claude', 'gemini')
              AND c.conversation_id IS NOT NULL
            GROUP BY c.conversation_id
        )
        SELECT ac.conversation_id::text
        FROM active_claims ac
        LEFT JOIN consolidation_progress p
          ON p.stage = 'consolidator'
         AND p.scope = 'conversation:' || ac.conversation_id::text
        WHERE p.updated_at IS NULL
           OR p.status <> 'completed'
           OR (p.position ->> 'last_claim_extracted_at') IS NULL
           OR (p.position ->> 'last_claim_extracted_at')::timestamptz
                < ac.last_claim_extracted_at
        ORDER BY ac.last_claim_extracted_at, ac.conversation_id
        LIMIT %s
        """,
        (min(batch_size, limit) if limit is not None else batch_size,),
    ).fetchall()
    return [row[0] for row in rows]


def fetch_active_claims(
    conn: psycopg.Connection,
    *,
    conversation_id: str | None = None,
) -> list[ClaimRow]:
    rows = conn.execute(
        """
        WITH latest_extractions AS (
            SELECT DISTINCT ON (ce.segment_id)
                ce.id,
                ce.segment_id
            FROM claim_extractions ce
            WHERE ce.status = 'extracted'
            ORDER BY ce.segment_id, ce.created_at DESC, ce.id DESC
        )
        SELECT
            c.id::text,
            c.segment_id::text,
            c.generation_id::text,
            c.conversation_id::text,
            c.subject_text,
            c.subject_normalized,
            c.predicate,
            pv.cardinality_class,
            pv.object_kind,
            pv.group_object_keys,
            c.object_text,
            c.object_json,
            c.stability_class,
            c.confidence,
            c.evidence_message_ids::text[],
            c.extracted_at,
            c.privacy_tier
        FROM claims c
        JOIN latest_extractions le ON le.id = c.extraction_id
        JOIN segments s ON s.id = c.segment_id
        JOIN segment_generations sg ON sg.id = s.generation_id
        JOIN predicate_vocabulary pv ON pv.predicate = c.predicate
        WHERE s.is_active = true
          AND sg.status = 'active'
          AND s.source_kind IN ('chatgpt', 'claude', 'gemini')
          AND s.conversation_id IS NOT NULL
          AND (%s::uuid IS NULL OR c.conversation_id = %s::uuid)
        ORDER BY c.extracted_at, c.id
        """,
        (conversation_id, conversation_id),
    ).fetchall()
    return [
        ClaimRow(
            id=row[0],
            segment_id=row[1],
            generation_id=row[2],
            conversation_id=row[3],
            subject_text=row[4],
            subject_normalized=row[5],
            predicate=row[6],
            cardinality_class=row[7],
            object_kind=row[8],
            group_object_keys=tuple(row[9]),
            object_text=row[10],
            object_json=dict(row[11]) if row[11] is not None else None,
            stability_class=row[12],
            confidence=float(row[13]),
            evidence_message_ids=list(row[14]),
            extracted_at=row[15],
            privacy_tier=int(row[16]),
        )
        for row in rows
    ]


def fetch_global_active_claim_ids(conn: psycopg.Connection) -> set[str]:
    return {claim.id for claim in fetch_active_claims(conn)}


def apply_decision_rule_0(
    conn: psycopg.Connection,
    active_claim_ids: set[str],
    *,
    prompt_version: str,
    model_version: str,
) -> GroupResult:
    beliefs = fetch_active_beliefs(conn)
    rejected = superseded = contradictions = created = 0
    for belief in beliefs:
        missing = [claim_id for claim_id in belief.claim_ids if claim_id not in active_claim_ids]
        if not missing:
            continue
        cause = orphan_cause_for_claims(conn, missing)
        if cause["cause"] == "orphan_after_reclassification":
            result = apply_reclassification_recompute(
                conn,
                belief,
                active_claim_ids,
                cause=cause,
                prompt_version=prompt_version,
                model_version=model_version,
            )
            rejected += result.rejected
            superseded += result.superseded
            contradictions += result.contradictions
            created += result.created
            continue
        reject_belief(
            conn,
            belief.id,
            cause,
            prompt_version=prompt_version,
            model_version=model_version,
        )
        rejected += 1
    return GroupResult(
        created=created,
        superseded=superseded,
        contradictions=contradictions,
        rejected=rejected,
    )


def apply_reclassification_recompute(
    conn: psycopg.Connection,
    belief: BeliefRow,
    active_claim_ids: set[str],
    *,
    cause: dict[str, Any],
    prompt_version: str,
    model_version: str,
) -> GroupResult:
    surviving_ids = [claim_id for claim_id in belief.claim_ids if claim_id in active_claim_ids]
    if not surviving_ids:
        reject_belief(
            conn,
            belief.id,
            cause,
            prompt_version=prompt_version,
            model_version=model_version,
        )
        return GroupResult(rejected=1)

    surviving_claims = fetch_claims_by_id(conn, surviving_ids)
    payload = build_belief_payload(
        conn,
        surviving_claims,
        prompt_version=prompt_version,
        model_version=model_version,
        raw_reason="privacy reclassification surviving claims",
    )
    if belief_reclassification_value_equal(belief, payload):
        supersede_belief(conn, belief.id, payload)
        return GroupResult(created=1, superseded=1)

    close_at = payload.valid_from
    for _ in range(2):
        try:
            with conn.transaction():
                close_belief(
                    conn,
                    belief.id,
                    cause,
                    valid_to=close_at,
                    prompt_version=prompt_version,
                    model_version=model_version,
                    transition_kind="close",
                )
                new_id = insert_belief(conn, payload)
                insert_contradiction(
                    conn,
                    belief.id,
                    new_id,
                    detection_kind="reclassification_recompute",
                    privacy_tier=max(belief.privacy_tier, payload.privacy_tier),
                    auto_resolve=False,
                    raw_payload={"reason": "privacy reclassification recompute"},
                )
            return GroupResult(created=1, superseded=1, contradictions=1)
        except errors.UniqueViolation:
            continue
    raise RuntimeError("reclassification recompute active belief conflict retry exhausted")


def fetch_active_beliefs(conn: psycopg.Connection) -> list[BeliefRow]:
    rows = conn.execute(
        """
        SELECT
            id::text,
            subject_text,
            subject_normalized,
            predicate,
            cardinality_class,
            group_object_key,
            object_text,
            object_json,
            valid_from,
            valid_to,
            observed_at,
            extracted_at,
            status,
            confidence,
            evidence_ids::text[],
            claim_ids::text[],
            prompt_version,
            model_version,
            privacy_tier
        FROM beliefs
        WHERE valid_to IS NULL
          AND status IN ('candidate', 'provisional', 'accepted')
        ORDER BY recorded_at, id
        """
    ).fetchall()
    return [_belief_from_row(row) for row in rows]


def fetch_active_belief_for_group(
    conn: psycopg.Connection,
    *,
    subject_normalized: str,
    predicate: str,
    group_object_key: str,
) -> BeliefRow | None:
    row = conn.execute(
        """
        SELECT
            id::text,
            subject_text,
            subject_normalized,
            predicate,
            cardinality_class,
            group_object_key,
            object_text,
            object_json,
            valid_from,
            valid_to,
            observed_at,
            extracted_at,
            status,
            confidence,
            evidence_ids::text[],
            claim_ids::text[],
            prompt_version,
            model_version,
            privacy_tier
        FROM beliefs
        WHERE subject_normalized = %s
          AND predicate = %s
          AND group_object_key = %s
          AND valid_to IS NULL
          AND status IN ('candidate', 'provisional', 'accepted')
        ORDER BY recorded_at DESC
        LIMIT 1
        """,
        (subject_normalized, predicate, group_object_key),
    ).fetchone()
    return _belief_from_row(row) if row else None


def _belief_from_row(row) -> BeliefRow:
    return BeliefRow(
        id=row[0],
        subject_text=row[1],
        subject_normalized=row[2],
        predicate=row[3],
        cardinality_class=row[4],
        group_object_key=row[5],
        object_text=row[6],
        object_json=dict(row[7]) if row[7] is not None else None,
        valid_from=row[8],
        valid_to=row[9],
        observed_at=row[10],
        extracted_at=row[11],
        status=row[12],
        confidence=float(row[13]),
        evidence_ids=list(row[14]),
        claim_ids=list(row[15]),
        prompt_version=row[16],
        model_version=row[17],
        privacy_tier=int(row[18]),
    )


def group_claims_by_value(claims: list[ClaimRow]) -> list[list[ClaimRow]]:
    groups: dict[tuple[str, str, str, str], list[ClaimRow]] = defaultdict(list)
    for claim in claims:
        group_object_key = compute_group_object_key(claim)
        value_key = claim_value_signature(claim)
        groups[(claim.subject_normalized, claim.predicate, group_object_key, value_key)].append(claim)
    return sorted(
        groups.values(),
        key=lambda rows: (min(row.extracted_at for row in rows), rows[0].id),
    )


def process_claim_value_group(
    conn: psycopg.Connection,
    claims: list[ClaimRow],
    *,
    prompt_version: str,
    model_version: str,
) -> GroupResult:
    if not claims:
        return GroupResult()
    first = claims[0]
    group_object_key = compute_group_object_key(first)
    payload = build_belief_payload(
        conn,
        claims,
        prompt_version=prompt_version,
        model_version=model_version,
        raw_reason="deterministic consolidation",
    )
    for _ in range(2):
        active = fetch_active_belief_for_group(
            conn,
            subject_normalized=first.subject_normalized,
            predicate=first.predicate,
            group_object_key=group_object_key,
        )
        try:
            with conn.transaction():
                if active is None:
                    insert_belief(conn, payload)
                    return GroupResult(created=1)
                if belief_value_equal(active, payload) or first.cardinality_class in {"multi_current", "event"}:
                    merged_payload = merge_with_active_belief(
                        conn,
                        active,
                        claims,
                        prompt_version=prompt_version,
                        model_version=model_version,
                    )
                    if set(merged_payload.claim_ids) == set(active.claim_ids):
                        return GroupResult()
                    supersede_belief(conn, active.id, merged_payload)
                    return GroupResult(created=1, superseded=1)
                close_belief(
                    conn,
                    active.id,
                    {"cause": "same_subject_predicate"},
                    valid_to=payload.valid_from,
                    prompt_version=prompt_version,
                    model_version=model_version,
                    transition_kind="close",
                )
                new_id = insert_belief(conn, payload)
                contradiction_id = insert_contradiction(
                    conn,
                    active.id,
                    new_id,
                    detection_kind="same_subject_predicate",
                    privacy_tier=max(active.privacy_tier, payload.privacy_tier),
                    auto_resolve=True,
                    raw_payload={"reason": "different value for current predicate"},
                )
            return GroupResult(created=1, superseded=1, contradictions=1 if contradiction_id else 0)
        except errors.UniqueViolation:
            continue
    raise RuntimeError("active belief conflict retry exhausted")


def build_belief_payload(
    conn: psycopg.Connection,
    claims: list[ClaimRow],
    *,
    prompt_version: str,
    model_version: str,
    raw_reason: str,
) -> BeliefPayload:
    first = claims[0]
    evidence_ids = stable_unique(
        evidence_id
        for claim in claims
        for evidence_id in claim.evidence_message_ids
    )
    claim_ids = stable_unique(claim.id for claim in claims)
    valid_from, observed_at = evidence_interval(conn, evidence_ids)
    extracted_at = min(claim.extracted_at for claim in claims)
    confidences = [claim.confidence for claim in claims]
    score = confidence_score_breakdown(confidences)
    return BeliefPayload(
        subject_text=first.subject_text,
        predicate=first.predicate,
        object_text=first.object_text,
        object_json=first.object_json,
        valid_from=valid_from,
        valid_to=None,
        observed_at=observed_at,
        extracted_at=extracted_at,
        status="candidate",
        confidence=score["mean"],
        evidence_ids=evidence_ids,
        claim_ids=claim_ids,
        prompt_version=prompt_version,
        model_version=model_version,
        privacy_tier=max(claim.privacy_tier for claim in claims),
        raw_payload={
            "consolidator": prompt_version,
            "reason": raw_reason,
            "group_object_key": compute_group_object_key(first),
        },
        score_breakdown=score,
    )


def merge_with_active_belief(
    conn: psycopg.Connection,
    active: BeliefRow,
    new_claims: list[ClaimRow],
    *,
    prompt_version: str,
    model_version: str,
) -> BeliefPayload:
    claims = fetch_claims_by_id(conn, stable_unique(active.claim_ids + [claim.id for claim in new_claims]))
    payload = build_belief_payload(
        conn,
        claims,
        prompt_version=prompt_version,
        model_version=model_version,
        raw_reason="same-value reinforcement",
    )
    return BeliefPayload(
        subject_text=payload.subject_text,
        predicate=payload.predicate,
        object_text=payload.object_text,
        object_json=payload.object_json,
        valid_from=active.valid_from,
        valid_to=active.valid_to,
        observed_at=payload.observed_at,
        extracted_at=payload.extracted_at,
        status="candidate",
        confidence=payload.confidence,
        evidence_ids=stable_unique(active.evidence_ids + payload.evidence_ids),
        claim_ids=stable_unique(active.claim_ids + payload.claim_ids),
        prompt_version=prompt_version,
        model_version=model_version,
        privacy_tier=max(active.privacy_tier, payload.privacy_tier),
        raw_payload=payload.raw_payload,
        score_breakdown=payload.score_breakdown,
    )


def fetch_claims_by_id(conn: psycopg.Connection, claim_ids: list[str]) -> list[ClaimRow]:
    if not claim_ids:
        return []
    rows = conn.execute(
        """
        SELECT
            c.id::text,
            c.segment_id::text,
            c.generation_id::text,
            c.conversation_id::text,
            c.subject_text,
            c.subject_normalized,
            c.predicate,
            pv.cardinality_class,
            pv.object_kind,
            pv.group_object_keys,
            c.object_text,
            c.object_json,
            c.stability_class,
            c.confidence,
            c.evidence_message_ids::text[],
            c.extracted_at,
            c.privacy_tier
        FROM claims c
        JOIN predicate_vocabulary pv ON pv.predicate = c.predicate
        WHERE c.id = ANY(%s::uuid[])
        ORDER BY array_position(%s::uuid[], c.id)
        """,
        (claim_ids, claim_ids),
    ).fetchall()
    return [
        ClaimRow(
            id=row[0],
            segment_id=row[1],
            generation_id=row[2],
            conversation_id=row[3],
            subject_text=row[4],
            subject_normalized=row[5],
            predicate=row[6],
            cardinality_class=row[7],
            object_kind=row[8],
            group_object_keys=tuple(row[9]),
            object_text=row[10],
            object_json=dict(row[11]) if row[11] is not None else None,
            stability_class=row[12],
            confidence=float(row[13]),
            evidence_message_ids=list(row[14]),
            extracted_at=row[15],
            privacy_tier=int(row[16]),
        )
        for row in rows
    ]


def compute_group_object_key(claim: ClaimRow) -> str:
    if claim.cardinality_class == "single_current":
        return ""
    if claim.object_text is not None:
        return normalize_subject(claim.object_text)
    values = [
        normalize_group_object_value(str((claim.object_json or {}).get(key, "")))
        for key in claim.group_object_keys
    ]
    return UNIT_SEPARATOR.join(values)


def claim_value_signature(claim: ClaimRow) -> str:
    if claim.object_text is not None:
        return "text:" + normalize_subject(claim.object_text)
    return "json:" + json.dumps(claim.object_json or {}, sort_keys=True, separators=(",", ":"))


def belief_value_equal(belief: BeliefRow, payload: BeliefPayload) -> bool:
    if belief.object_text is not None or payload.object_text is not None:
        return normalize_subject(belief.object_text or "") == normalize_subject(payload.object_text or "")
    return canonical_json(belief.object_json) == canonical_json(payload.object_json)


def belief_reclassification_value_equal(belief: BeliefRow, payload: BeliefPayload) -> bool:
    if belief.cardinality_class in {"multi_current", "event"}:
        return True
    return belief_value_equal(belief, payload)


def canonical_json(value: dict[str, Any] | None) -> str:
    return json.dumps(value or {}, sort_keys=True, separators=(",", ":"))


def confidence_score_breakdown(confidences: list[float]) -> dict[str, Any]:
    mean = sum(confidences) / len(confidences)
    return {
        "mean": mean,
        "max": max(confidences),
        "min": min(confidences),
        "count": len(confidences),
        "stddev": statistics.pstdev(confidences) if len(confidences) > 1 else 0.0,
    }


def evidence_interval(conn: psycopg.Connection, evidence_ids: list[str]) -> tuple[Any, Any]:
    row = conn.execute(
        """
        SELECT
            MIN(COALESCE(created_at, imported_at)),
            MAX(COALESCE(created_at, imported_at))
        FROM messages
        WHERE id = ANY(%s::uuid[])
        """,
        (evidence_ids,),
    ).fetchone()
    if row is None or row[0] is None or row[1] is None:
        raise ValueError("belief evidence ids did not resolve to messages")
    return row[0], row[1]


def stable_unique(values: Iterable[str]) -> list[str]:
    return list(dict.fromkeys(str(value) for value in values))


def insert_contradiction(
    conn: psycopg.Connection,
    belief_a_id: str,
    belief_b_id: str,
    *,
    detection_kind: str,
    privacy_tier: int,
    auto_resolve: bool,
    raw_payload: dict[str, Any],
) -> str:
    resolution_status = "open"
    resolution_kind = None
    resolved_sql = "NULL"
    if auto_resolve and contradiction_intervals_do_not_overlap(conn, belief_a_id, belief_b_id):
        resolution_status = "auto_resolved"
        resolution_kind = "temporal_ordering"
        resolved_sql = "now()"
    row = conn.execute(
        f"""
        INSERT INTO contradictions (
            belief_a_id,
            belief_b_id,
            detection_kind,
            resolution_status,
            resolution_kind,
            resolved_at,
            privacy_tier,
            raw_payload
        )
        VALUES (%s, %s, %s, %s, %s, {resolved_sql}, %s, %s)
        RETURNING id::text
        """,
        (
            belief_a_id,
            belief_b_id,
            detection_kind,
            resolution_status,
            resolution_kind,
            privacy_tier,
            Jsonb(raw_payload),
        ),
    ).fetchone()
    return row[0]


def contradiction_intervals_do_not_overlap(
    conn: psycopg.Connection,
    belief_a_id: str,
    belief_b_id: str,
) -> bool:
    row = conn.execute(
        """
        SELECT
            a.valid_from,
            a.valid_to,
            b.valid_from,
            b.valid_to
        FROM beliefs a
        CROSS JOIN beliefs b
        WHERE a.id = %s
          AND b.id = %s
        """,
        (belief_a_id, belief_b_id),
    ).fetchone()
    if not row:
        return False
    a_from, a_to, b_from, b_to = row
    return (a_to is not None and a_to <= b_from) or (b_to is not None and b_to <= a_from)


def orphan_cause_for_claims(conn: psycopg.Connection, claim_ids: list[str]) -> dict[str, Any]:
    row = conn.execute(
        """
        SELECT
            bool_or(s.invalidated_at IS NOT NULL) AS reclassified,
            bool_or(s.is_active = false AND s.invalidated_at IS NULL) AS deactivated
        FROM claims c
        JOIN segments s ON s.id = c.segment_id
        WHERE c.id = ANY(%s::uuid[])
        """,
        (claim_ids,),
    ).fetchone()
    if row and row[0]:
        cause: dict[str, Any] = {"cause": "orphan_after_reclassification"}
        capture_id = find_reclassification_capture_id(conn, claim_ids)
        if capture_id:
            cause["cause_capture_id"] = capture_id
        return cause
    if row and row[1]:
        return {"cause": "orphan_after_segment_deactivation"}
    return {"cause": "orphan_after_reextraction"}


def find_reclassification_capture_id(
    conn: psycopg.Connection,
    claim_ids: list[str],
) -> str | None:
    row = conn.execute(
        """
        SELECT replace(p.scope, 'capture:', '')
        FROM claims c
        JOIN segments s ON s.id = c.segment_id
        JOIN consolidation_progress p
          ON p.stage = 'privacy_reclassification'
         AND p.status = 'completed'
         AND p.position ->> 'parent_id' = s.conversation_id::text
        WHERE c.id = ANY(%s::uuid[])
          AND p.scope LIKE 'capture:%%'
        ORDER BY p.updated_at DESC
        LIMIT 1
        """,
        (claim_ids,),
    ).fetchone()
    return row[0] if row else None


def close_active_beliefs_for_rebuild(
    conn: psycopg.Connection,
    *,
    prompt_version: str,
    model_version: str,
) -> int:
    beliefs = fetch_active_beliefs(conn)
    for belief in beliefs:
        close_belief(
            conn,
            belief.id,
            {"cause": "rebuild"},
            prompt_version=prompt_version,
            model_version=model_version,
            transition_kind="close",
        )
    return len(beliefs)


def latest_claim_extracted_at(conn: psycopg.Connection, conversation_id: str) -> Any | None:
    row = conn.execute(
        """
        SELECT max(c.extracted_at)
        FROM claims c
        JOIN claim_extractions ce ON ce.id = c.extraction_id
        WHERE c.conversation_id = %s
          AND ce.status = 'extracted'
        """,
        (conversation_id,),
    ).fetchone()
    return row[0] if row else None


def active_beliefs_with_other_consolidator_version(
    conn: psycopg.Connection,
    prompt_version: str = CONSOLIDATOR_PROMPT_VERSION,
) -> int:
    return conn.execute(
        """
        SELECT count(*)
        FROM beliefs
        WHERE valid_to IS NULL
          AND status IN ('candidate', 'provisional', 'accepted')
          AND prompt_version <> %s
        """,
        (prompt_version,),
    ).fetchone()[0]
