"""Helpers for recording memory event ledger rows."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from uuid import UUID, uuid4

import psycopg
from psycopg.types.json import Jsonb


@dataclass(frozen=True)
class MemoryEventRecord:
    """Inserted memory event identity and epoch."""

    id: str
    memory_epoch: int


@dataclass(frozen=True)
class ContextFeedbackRecord:
    """Inserted context feedback identity and companion event."""

    id: str
    event_id: str
    memory_epoch: int


def insert_memory_event(
    conn: psycopg.Connection,
    *,
    event_type: str,
    aggregate_type: str,
    scope_type: str,
    scope_key: str,
    tenant_id: str = "personal",
    corpus_id: str = "personal",
    aggregate_id: str | UUID | None = None,
    payload: Mapping[str, object] | None = None,
) -> MemoryEventRecord:
    """Insert one append-only memory event and return its id and epoch."""
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO memory_events (
                tenant_id,
                corpus_id,
                event_type,
                aggregate_type,
                aggregate_id,
                scope_type,
                scope_key,
                payload
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id::text, memory_epoch
            """,
            (
                tenant_id,
                corpus_id,
                event_type,
                aggregate_type,
                aggregate_id,
                scope_type,
                scope_key,
                Jsonb(dict(payload or {})),
            ),
        )
        row = cur.fetchone()
        assert row is not None
        return MemoryEventRecord(id=str(row[0]), memory_epoch=int(row[1]))


def insert_context_feedback(
    conn: psycopg.Connection,
    *,
    snapshot_id: str | UUID,
    feedback_kind: str,
    source_belief_ids: Sequence[str | UUID] | None = None,
    source_segment_ids: Sequence[str | UUID] | None = None,
    source_reference_ids: Sequence[str] | None = None,
    correction_note: str | None = None,
    actor: str = "operator",
    request_uuid: str | UUID | None = None,
    payload: Mapping[str, object] | None = None,
) -> ContextFeedbackRecord:
    """Insert context feedback and its append-only memory event."""
    feedback_id = str(uuid4())
    feedback_request_uuid = str(request_uuid or uuid4())
    with conn.transaction():
        snapshot = conn.execute(
            """
            SELECT
                tenant_id,
                corpus_id,
                scope_type,
                scope_key,
                source_belief_ids,
                source_segment_ids,
                source_reference_ids
            FROM context_snapshots
            WHERE id = %s
            """,
            (snapshot_id,),
        ).fetchone()
        if snapshot is None:
            raise ValueError(f"context snapshot not found: {snapshot_id}")

        tenant_id = str(snapshot[0])
        corpus_id = str(snapshot[1])
        scope_type = str(snapshot[2])
        scope_key = str(snapshot[3])
        belief_ids = _uuid_strings(source_belief_ids, fallback=snapshot[4])
        segment_ids = _uuid_strings(source_segment_ids, fallback=snapshot[5])
        reference_ids = _string_list(source_reference_ids, fallback=snapshot[6])
        event = insert_memory_event(
            conn,
            event_type="context_feedback_captured",
            aggregate_type="context_feedback",
            aggregate_id=feedback_id,
            tenant_id=tenant_id,
            corpus_id=corpus_id,
            scope_type=scope_type,
            scope_key=scope_key,
            payload={
                "snapshot_id": str(snapshot_id),
                "feedback_kind": feedback_kind,
                "source_belief_count": len(belief_ids),
                "source_segment_count": len(segment_ids),
                "source_reference_count": len(reference_ids),
                "request_uuid": feedback_request_uuid,
            },
        )
        conn.execute(
            """
            INSERT INTO context_feedback (
                id,
                snapshot_id,
                tenant_id,
                corpus_id,
                feedback_kind,
                source_belief_ids,
                source_segment_ids,
                source_reference_ids,
                correction_note,
                actor,
                request_uuid,
                payload
            )
            VALUES (
                %s,
                %s,
                %s,
                %s,
                %s,
                %s::uuid[],
                %s::uuid[],
                %s,
                %s,
                %s,
                %s,
                %s
            )
            """,
            (
                feedback_id,
                snapshot_id,
                tenant_id,
                corpus_id,
                feedback_kind,
                belief_ids,
                segment_ids,
                reference_ids,
                correction_note,
                actor,
                feedback_request_uuid,
                Jsonb(dict(payload or {})),
            ),
        )
    return ContextFeedbackRecord(
        id=feedback_id,
        event_id=event.id,
        memory_epoch=event.memory_epoch,
    )


def _uuid_strings(
    values: Sequence[str | UUID] | None,
    *,
    fallback: object,
) -> list[str]:
    active_values = fallback if values is None else values
    if active_values is None:
        return []
    return [str(value) for value in active_values]


def _string_list(values: Sequence[str] | None, *, fallback: object) -> list[str]:
    active_values = fallback if values is None else values
    if active_values is None:
        return []
    return [str(value) for value in active_values]
