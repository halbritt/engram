from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import psycopg
from psycopg.types.json import Jsonb

from engram.consolidator.transitions import transition_belief_status
from engram.migrations import migration_integrity_errors

PHASE4_RESOLUTION_VERSION = "phase4.v1.d077.tier0-smoke"
PHASE4_REVIEW_PROMPT_VERSION = "phase4-review.v1.d077.transition-api"
PHASE4_REVIEW_MODEL_VERSION = "phase4-review.v1.d077.local-cli"

# JSONB payloads can contain nested scalar/list/object values.
JsonObject = dict[str, Any]


class Phase4Error(RuntimeError):
    """Base error for Phase 4 build and review operations."""


class Phase4SchemaPreflightError(Phase4Error):
    """Raised when Phase 4 schema prerequisites are not present."""


@dataclass(frozen=True)
class ReviewActionResult:
    action_id: str
    belief_id: str
    action_kind: str
    action_status: str
    request_uuid: str
    capture_id: str | None = None
    changed: bool = False


@dataclass(frozen=True)
class EntityBuildResult:
    beliefs_processed: int
    entities_created: int
    entities_reused: int
    edges_created: int
    edges_reused: int


@dataclass(frozen=True)
class EntityNeighborhoodRow:
    entity_id: str
    depth: int


@dataclass(frozen=True)
class Phase4SmokeResult:
    current_beliefs: int
    review_queue_items: int
    beliefs_processed: int
    entities_created: int
    entities_reused: int
    edges_created: int
    edges_reused: int
    neighborhood_rows: int


def phase4_schema_preflight(conn: psycopg.Connection) -> None:
    """Fail closed if the Phase 4 schema contract is missing."""
    errors = migration_integrity_errors(conn)
    required_relations = {
        "entities": "r",
        "entity_resolution_events": "r",
        "entity_edges": "r",
        "belief_review_actions": "r",
        "pinned_beliefs": "r",
        "current_beliefs": "m",
        "belief_review_queue": "v",
    }
    for relation_name, relkind in required_relations.items():
        row = conn.execute(
            """
            SELECT c.relkind
            FROM pg_class c
            JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE n.nspname = 'public'
              AND c.relname = %s
            """,
            (relation_name,),
        ).fetchone()
        if row is None:
            errors.append(f"{relation_name} relation is missing")
        elif row[0] != relkind:
            errors.append(f"{relation_name} has relkind {row[0]!r}, expected {relkind!r}")

    required_indexes = [
        "entities_active_key_idx",
        "entity_edges_active_unique_idx",
        "current_beliefs_id_idx",
        "belief_review_actions_request_uuid_idx",
    ]
    for index_name in required_indexes:
        index_row = conn.execute(
            "SELECT to_regclass(%s)",
            (f"public.{index_name}",),
        ).fetchone()
        if index_row is None or index_row[0] is None:
            errors.append(f"{index_name} index is missing")

    function_row = conn.execute(
        "SELECT to_regprocedure(%s)",
        ("public.fn_phase4_append_only()",),
    ).fetchone()
    if function_row is None or function_row[0] is None:
        errors.append("fn_phase4_append_only() function is missing")

    if errors:
        raise Phase4SchemaPreflightError("; ".join(errors))


def refresh_current_beliefs(conn: psycopg.Connection) -> None:
    """Refresh Phase 4's status-aware current belief projection."""
    phase4_schema_preflight(conn)
    conn.execute("REFRESH MATERIALIZED VIEW current_beliefs")


def accept_belief(
    conn: psycopg.Connection,
    belief_id: str,
    *,
    actor: str = "local",
    note: str | None = None,
    request_uuid: str | None = None,
) -> ReviewActionResult:
    """Promote a candidate/provisional belief to accepted via the transition API."""
    phase4_schema_preflight(conn)
    request_uuid = request_uuid or str(uuid.uuid4())
    with conn.transaction():
        transition = transition_belief_status(
            conn,
            belief_id,
            new_status="accepted",
            transition_kind="promote",
            score_breakdown={"review_action": "accept", "note": note},
            request_uuid=request_uuid,
            prompt_version=PHASE4_REVIEW_PROMPT_VERSION,
            model_version=PHASE4_REVIEW_MODEL_VERSION,
        )
        action_id = _insert_review_action(
            conn,
            belief_id=belief_id,
            action_kind="accept",
            action_status="applied" if transition.changed else "recorded",
            request_uuid=request_uuid,
            actor=actor,
            note=note,
            raw_payload={
                "previous_status": transition.previous_status,
                "changed": transition.changed,
            },
        )
    refresh_current_beliefs(conn)
    return ReviewActionResult(
        action_id=action_id,
        belief_id=belief_id,
        action_kind="accept",
        action_status="applied" if transition.changed else "recorded",
        request_uuid=request_uuid,
        changed=transition.changed,
    )


def reject_review_belief(
    conn: psycopg.Connection,
    belief_id: str,
    *,
    actor: str = "local",
    note: str | None = None,
    request_uuid: str | None = None,
) -> ReviewActionResult:
    """Reject a review-queue belief through the audited transition path."""
    phase4_schema_preflight(conn)
    request_uuid = request_uuid or str(uuid.uuid4())
    with conn.transaction():
        transition = transition_belief_status(
            conn,
            belief_id,
            new_status="rejected",
            transition_kind="reject",
            score_breakdown={"review_action": "reject", "note": note},
            request_uuid=request_uuid,
            prompt_version=PHASE4_REVIEW_PROMPT_VERSION,
            model_version=PHASE4_REVIEW_MODEL_VERSION,
        )
        action_id = _insert_review_action(
            conn,
            belief_id=belief_id,
            action_kind="reject",
            action_status="applied" if transition.changed else "recorded",
            request_uuid=request_uuid,
            actor=actor,
            note=note,
            raw_payload={
                "previous_status": transition.previous_status,
                "changed": transition.changed,
            },
        )
    refresh_current_beliefs(conn)
    return ReviewActionResult(
        action_id=action_id,
        belief_id=belief_id,
        action_kind="reject",
        action_status="applied" if transition.changed else "recorded",
        request_uuid=request_uuid,
        changed=transition.changed,
    )


def correct_belief(
    conn: psycopg.Connection,
    belief_id: str,
    correction_text: str,
    *,
    actor: str = "local",
    request_uuid: str | None = None,
) -> ReviewActionResult:
    """Record a correction as raw capture evidence and queue reprocessing."""
    if correction_text.strip() == "":
        raise ValueError("correction_text must not be empty")
    request_uuid = request_uuid or str(uuid.uuid4())
    with conn.transaction():
        source_id = _review_capture_source_id(conn)
        capture_id = conn.execute(
            """
            INSERT INTO captures (
                source_id,
                source_kind,
                external_id,
                raw_payload,
                privacy_tier,
                capture_type,
                corrects_belief_id,
                content_text,
                observed_at
            )
            SELECT
                %s,
                'capture',
                %s,
                %s,
                privacy_tier,
                'user_correction',
                id,
                %s,
                %s
            FROM beliefs
            WHERE id = %s
            RETURNING id::text
            """,
            (
                source_id,
                f"phase4-review:{belief_id}:{request_uuid}",
                Jsonb({"request_uuid": request_uuid, "actor": actor}),
                correction_text,
                datetime.now(UTC),
                belief_id,
            ),
        ).fetchone()
        if capture_id is None:
            raise ValueError(f"belief not found: {belief_id}")
        action_id = _insert_review_action(
            conn,
            belief_id=belief_id,
            action_kind="correct",
            action_status="queued_reprocessing",
            request_uuid=request_uuid,
            actor=actor,
            note=correction_text,
            capture_id=capture_id[0],
            raw_payload={"correction_capture_id": capture_id[0]},
        )
    return ReviewActionResult(
        action_id=action_id,
        belief_id=belief_id,
        action_kind="correct",
        action_status="queued_reprocessing",
        request_uuid=request_uuid,
        capture_id=capture_id[0],
    )


def promote_to_pinned(
    conn: psycopg.Connection,
    belief_id: str,
    *,
    actor: str = "local",
    note: str | None = None,
    request_uuid: str | None = None,
) -> ReviewActionResult:
    """Accept a belief if needed and add it to the pinned-belief projection."""
    phase4_schema_preflight(conn)
    request_uuid = request_uuid or str(uuid.uuid4())
    with conn.transaction():
        transition = transition_belief_status(
            conn,
            belief_id,
            new_status="accepted",
            transition_kind="promote",
            score_breakdown={"review_action": "promote_to_pinned", "note": note},
            request_uuid=request_uuid,
            prompt_version=PHASE4_REVIEW_PROMPT_VERSION,
            model_version=PHASE4_REVIEW_MODEL_VERSION,
        )
        pinned = conn.execute(
            """
            INSERT INTO pinned_beliefs (belief_id, request_uuid, actor, raw_payload)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (belief_id) DO NOTHING
            RETURNING belief_id::text
            """,
            (belief_id, request_uuid, actor, Jsonb({"note": note})),
        ).fetchone()
        action_id = _insert_review_action(
            conn,
            belief_id=belief_id,
            action_kind="promote_to_pinned",
            action_status="applied" if pinned is not None or transition.changed else "recorded",
            request_uuid=request_uuid,
            actor=actor,
            note=note,
            raw_payload={
                "previous_status": transition.previous_status,
                "status_changed": transition.changed,
                "pinned_inserted": pinned is not None,
            },
        )
    refresh_current_beliefs(conn)
    return ReviewActionResult(
        action_id=action_id,
        belief_id=belief_id,
        action_kind="promote_to_pinned",
        action_status="applied" if pinned is not None or transition.changed else "recorded",
        request_uuid=request_uuid,
        changed=transition.changed or pinned is not None,
    )


def build_deterministic_entities(
    conn: psycopg.Connection,
    *,
    limit: int | None = None,
) -> EntityBuildResult:
    """Build deterministic Phase 4 entity and edge scaffolding from current beliefs."""
    phase4_schema_preflight(conn)
    rows = conn.execute(
        """
        SELECT
            id::text,
            subject_text,
            subject_normalized,
            predicate,
            object_text,
            object_json,
            group_object_key,
            confidence,
            evidence_ids::text[],
            claim_ids::text[],
            privacy_tier
        FROM current_beliefs
        ORDER BY id
        LIMIT %s
        """,
        (limit,),
    ).fetchall()
    totals = {
        "beliefs_processed": 0,
        "entities_created": 0,
        "entities_reused": 0,
        "edges_created": 0,
        "edges_reused": 0,
    }
    with conn.transaction():
        for row in rows:
            belief = _belief_row_to_dict(row)
            totals["beliefs_processed"] += 1
            subject = _ensure_entity(
                conn,
                canonical_text=belief["subject_text"],
                canonical_key=f"subject:{belief['subject_normalized']}",
                source_belief_ids=[belief["id"]],
                source_claim_ids=belief["claim_ids"],
                evidence_ids=belief["evidence_ids"],
                confidence=belief["confidence"],
                privacy_tier=belief["privacy_tier"],
                raw_payload={"role": "subject"},
            )
            totals["entities_created" if subject["created"] else "entities_reused"] += 1
            object_identity = _object_identity(belief)
            if object_identity is None:
                continue
            target = _ensure_entity(
                conn,
                canonical_text=object_identity["text"],
                canonical_key=object_identity["key"],
                source_belief_ids=[belief["id"]],
                source_claim_ids=belief["claim_ids"],
                evidence_ids=belief["evidence_ids"],
                confidence=belief["confidence"],
                privacy_tier=belief["privacy_tier"],
                raw_payload={"role": "object", "predicate": belief["predicate"]},
            )
            totals["entities_created" if target["created"] else "entities_reused"] += 1
            edge_created = _ensure_edge(
                conn,
                source_entity_id=subject["id"],
                target_entity_id=target["id"],
                edge_kind=belief["predicate"],
                source_belief_ids=[belief["id"]],
                source_claim_ids=belief["claim_ids"],
                evidence_ids=belief["evidence_ids"],
                confidence=belief["confidence"],
                privacy_tier=belief["privacy_tier"],
            )
            totals["edges_created" if edge_created else "edges_reused"] += 1
    return EntityBuildResult(**totals)


def entity_neighborhood(
    conn: psycopg.Connection,
    entity_id: str,
    *,
    max_depth: int = 2,
) -> list[EntityNeighborhoodRow]:
    """Return a cycle-safe 1-2 hop active entity neighborhood."""
    if max_depth < 1 or max_depth > 2:
        raise ValueError("max_depth must be 1 or 2 for the V1 entity query")
    rows = conn.execute(
        """
        WITH RECURSIVE walk(entity_id, depth, path) AS (
            SELECT %s::uuid, 0, ARRAY[%s::uuid]
            UNION ALL
            SELECT
                CASE
                    WHEN e.source_entity_id = walk.entity_id THEN e.target_entity_id
                    ELSE e.source_entity_id
                END,
                walk.depth + 1,
                path || CASE
                    WHEN e.source_entity_id = walk.entity_id THEN e.target_entity_id
                    ELSE e.source_entity_id
                END
            FROM walk
            JOIN entity_edges e
              ON e.status = 'active'
             AND (
                e.source_entity_id = walk.entity_id
                OR e.target_entity_id = walk.entity_id
             )
            WHERE walk.depth < %s
              AND NOT (
                CASE
                    WHEN e.source_entity_id = walk.entity_id THEN e.target_entity_id
                    ELSE e.source_entity_id
                END = ANY(path)
              )
        )
        SELECT DISTINCT entity_id::text, depth
        FROM walk
        WHERE depth > 0
        ORDER BY depth, entity_id::text
        """,
        (entity_id, entity_id, max_depth),
    ).fetchall()
    return [EntityNeighborhoodRow(entity_id=row[0], depth=row[1]) for row in rows]


def run_phase4_smoke(conn: psycopg.Connection, *, limit: int = 25) -> Phase4SmokeResult:
    """Run a local-only Tier 0 Phase 4 smoke build over a bounded slice."""
    phase4_schema_preflight(conn)
    refresh_current_beliefs(conn)
    current_count_row = conn.execute("SELECT count(*) FROM current_beliefs").fetchone()
    queue_count_row = conn.execute("SELECT count(*) FROM belief_review_queue").fetchone()
    if current_count_row is None or queue_count_row is None:
        raise Phase4Error("phase4 smoke count query returned no rows")
    current_count = current_count_row[0]
    queue_count = queue_count_row[0]
    build_result = build_deterministic_entities(conn, limit=limit)
    first_entity = conn.execute(
        "SELECT id::text FROM entities WHERE status = 'active' ORDER BY created_at, id LIMIT 1"
    ).fetchone()
    neighborhood_rows = 0
    if first_entity is not None:
        neighborhood_rows = len(entity_neighborhood(conn, first_entity[0], max_depth=2))
    return Phase4SmokeResult(
        current_beliefs=current_count,
        review_queue_items=queue_count,
        beliefs_processed=build_result.beliefs_processed,
        entities_created=build_result.entities_created,
        entities_reused=build_result.entities_reused,
        edges_created=build_result.edges_created,
        edges_reused=build_result.edges_reused,
        neighborhood_rows=neighborhood_rows,
    )


def _insert_review_action(
    conn: psycopg.Connection,
    *,
    belief_id: str,
    action_kind: str,
    action_status: str,
    request_uuid: str,
    actor: str,
    note: str | None,
    raw_payload: JsonObject,
    capture_id: str | None = None,
) -> str:
    row = conn.execute(
        """
        INSERT INTO belief_review_actions (
            belief_id,
            action_kind,
            action_status,
            capture_id,
            request_uuid,
            actor,
            note,
            raw_payload
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id::text
        """,
        (
            belief_id,
            action_kind,
            action_status,
            capture_id,
            request_uuid,
            actor,
            note,
            Jsonb(raw_payload),
        ),
    ).fetchone()
    if row is None:
        raise Phase4Error("failed to insert belief review action")
    return row[0]


def _review_capture_source_id(conn: psycopg.Connection) -> str:
    row = conn.execute(
        """
        INSERT INTO sources (source_kind, external_id, raw_payload)
        VALUES ('capture', 'phase4-review-queue', %s)
        ON CONFLICT (source_kind, external_id) DO NOTHING
        RETURNING id::text
        """,
        (Jsonb({"created_by": PHASE4_RESOLUTION_VERSION}),),
    ).fetchone()
    if row is not None:
        return row[0]
    existing = conn.execute(
        """
        SELECT id::text
        FROM sources
        WHERE source_kind = 'capture'
          AND external_id = 'phase4-review-queue'
        """
    ).fetchone()
    if existing is None:
        raise Phase4Error("phase4 review capture source could not be created")
    return existing[0]


def _belief_row_to_dict(row: tuple[Any, ...]) -> JsonObject:
    return {
        "id": row[0],
        "subject_text": row[1],
        "subject_normalized": row[2],
        "predicate": row[3],
        "object_text": row[4],
        "object_json": row[5],
        "group_object_key": row[6],
        "confidence": row[7],
        "evidence_ids": list(row[8]),
        "claim_ids": list(row[9]),
        "privacy_tier": row[10],
    }


def _object_identity(belief: JsonObject) -> JsonObject | None:
    object_text = belief["object_text"]
    if isinstance(object_text, str) and object_text.strip() != "":
        key = f"object:{_normalize_key(object_text)}"
        return {"text": object_text, "key": key}
    object_json = belief["object_json"]
    if isinstance(object_json, dict) and object_json:
        group_key = belief["group_object_key"]
        if isinstance(group_key, str) and group_key.strip() != "":
            key = f"object:{belief['predicate']}:{group_key}"
        else:
            encoded = json.dumps(object_json, sort_keys=True, separators=(",", ":"))
            key = f"object:{belief['predicate']}:{hashlib.sha256(encoded.encode()).hexdigest()}"
        return {"text": json.dumps(object_json, sort_keys=True), "key": key}
    return None


def _ensure_entity(
    conn: psycopg.Connection,
    *,
    canonical_text: str,
    canonical_key: str,
    source_belief_ids: list[str],
    source_claim_ids: list[str],
    evidence_ids: list[str],
    confidence: float,
    privacy_tier: int,
    raw_payload: JsonObject,
) -> JsonObject:
    existing = conn.execute(
        """
        SELECT id::text
        FROM entities
        WHERE entity_kind = 'unknown'
          AND canonical_key = %s
          AND status = 'active'
        """,
        (canonical_key,),
    ).fetchone()
    if existing is not None:
        return {"id": existing[0], "created": False}
    entity_row = conn.execute(
        """
        INSERT INTO entities (
            entity_kind,
            canonical_text,
            canonical_key,
            status,
            confidence,
            source_belief_ids,
            source_claim_ids,
            evidence_ids,
            privacy_tier,
            resolution_method,
            resolution_version,
            raw_payload
        )
        VALUES (
            'unknown', %s, %s, 'active', %s, %s::uuid[], %s::uuid[], %s::uuid[],
            %s, 'deterministic', %s, %s
        )
        RETURNING id::text
        """,
        (
            canonical_text,
            canonical_key,
            confidence,
            source_belief_ids,
            source_claim_ids,
            evidence_ids,
            privacy_tier,
            PHASE4_RESOLUTION_VERSION,
            Jsonb(raw_payload),
        ),
    ).fetchone()
    if entity_row is None:
        raise Phase4Error("failed to insert entity")
    entity_id = entity_row[0]
    conn.execute(
        """
        INSERT INTO entity_resolution_events (
            entity_id,
            event_kind,
            source_belief_ids,
            source_claim_ids,
            evidence_ids,
            resolution_method,
            resolution_version,
            actor,
            privacy_tier,
            raw_payload
        )
        VALUES (
            %s, 'create', %s::uuid[], %s::uuid[], %s::uuid[], 'deterministic',
            %s, 'phase4-smoke', %s, %s
        )
        """,
        (
            entity_id,
            source_belief_ids,
            source_claim_ids,
            evidence_ids,
            PHASE4_RESOLUTION_VERSION,
            privacy_tier,
            Jsonb(raw_payload),
        ),
    )
    return {"id": entity_id, "created": True}


def _ensure_edge(
    conn: psycopg.Connection,
    *,
    source_entity_id: str,
    target_entity_id: str,
    edge_kind: str,
    source_belief_ids: list[str],
    source_claim_ids: list[str],
    evidence_ids: list[str],
    confidence: float,
    privacy_tier: int,
) -> bool:
    existing = conn.execute(
        """
        SELECT id
        FROM entity_edges
        WHERE source_entity_id = %s
          AND target_entity_id = %s
          AND edge_kind = %s
          AND status = 'active'
        """,
        (source_entity_id, target_entity_id, edge_kind),
    ).fetchone()
    if existing is not None:
        return False
    conn.execute(
        """
        INSERT INTO entity_edges (
            source_entity_id,
            target_entity_id,
            edge_kind,
            status,
            confidence,
            source_belief_ids,
            source_claim_ids,
            evidence_ids,
            privacy_tier,
            resolution_version,
            raw_payload
        )
        VALUES (
            %s, %s, %s, 'active', %s, %s::uuid[], %s::uuid[], %s::uuid[],
            %s, %s, %s
        )
        """,
        (
            source_entity_id,
            target_entity_id,
            edge_kind,
            confidence,
            source_belief_ids,
            source_claim_ids,
            evidence_ids,
            privacy_tier,
            PHASE4_RESOLUTION_VERSION,
            Jsonb({"source": "current_beliefs"}),
        ),
    )
    return True


def _normalize_key(value: str) -> str:
    return " ".join(value.casefold().split())
