"""RFC 0054 draft-only entity grounding batch workflow."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import NAMESPACE_URL, UUID, uuid5

import psycopg
from psycopg.types.json import Jsonb

from engram.claim_grounding import (
    CLAIM_GROUNDING_REQUEST_SCHEMA_VERSION,
    ClaimGroundingRequest,
)
from engram.entity_grounding import search_grounding_evidence

ENTITY_GROUNDING_BATCH_WORKFLOW_VERSION = "entity_grounding_batch.v1"
ENTITY_GROUNDING_BATCH_PROMPT_VERSION = "entity_grounding_batch.v1.draft"
ENTITY_GROUNDING_BATCH_MODEL_VERSION = "none.local.workflow"
ENTITY_GROUNDING_BATCH_ACTOR = "entity-grounding-workflow"
ENTITY_GROUNDING_BATCH_GRANT_ACTOR = "operator"
ENTITY_GROUNDING_ALLOWED_NETWORK_TARGETS = ("internet_search",)
ENTITY_GROUNDING_CANDIDATE_KINDS = (
    "person",
    "product",
    "place",
    "organization",
    "media_work",
    "tool",
    "concept",
)
ENTITY_GROUNDING_ID_NAMESPACE = uuid5(NAMESPACE_URL, "engram:rfc0054:entity-grounding-batch")


JsonValue = (
    str
    | int
    | float
    | bool
    | None
    | dict[str, "JsonValue"]
    | list["JsonValue"]
)


@dataclass(frozen=True)
class EntityGroundingDraftSkip:
    """One entity omitted from the draft workflow."""

    entity_id: str
    reason: str

    def to_json(self) -> dict[str, JsonValue]:
        """Return a JSON-compatible skip row."""
        return {"entity_id": self.entity_id, "reason": self.reason}


@dataclass(frozen=True)
class EntityGroundingDraftSummary:
    """Compact RFC 0054 draft workflow result."""

    workflow_version: str
    selected: int
    local_hits: int
    local_actions_created: int
    local_actions_reused: int
    drafts_created: int
    drafts_reused: int
    skipped: tuple[EntityGroundingDraftSkip, ...]

    def to_json(self) -> dict[str, JsonValue]:
        """Return a JSON-compatible workflow summary."""
        return {
            "workflow_version": self.workflow_version,
            "selected": self.selected,
            "local_hits": self.local_hits,
            "local_actions_created": self.local_actions_created,
            "local_actions_reused": self.local_actions_reused,
            "drafts_created": self.drafts_created,
            "drafts_reused": self.drafts_reused,
            "skipped": [skip.to_json() for skip in self.skipped],
        }


@dataclass(frozen=True)
class _EntityGroundingCandidate:
    id: str
    tenant_id: str
    corpus_id: str
    canonical_text: str
    confidence: float
    source_claim_ids: tuple[str, ...]
    privacy_tier: int
    created_at: datetime


def draft_entity_grounding_batch(
    conn: psycopg.Connection,
    *,
    tenant_id: str,
    corpus_id: str,
    limit: int,
    entity_id: str | None = None,
    local_lookup_limit: int = 5,
    requested_at: datetime | None = None,
) -> EntityGroundingDraftSummary:
    """Draft RFC 0053 entity-grounding work for active unresolved entities."""
    if not tenant_id.strip():
        raise ValueError("tenant_id must be non-empty")
    if not corpus_id.strip():
        raise ValueError("corpus_id must be non-empty")
    if limit < 1:
        raise ValueError("limit must be positive")
    if local_lookup_limit < 1:
        raise ValueError("local_lookup_limit must be positive")

    active_requested_at = requested_at or datetime.now(tz=UTC)
    selected = _select_unknown_entities(
        conn,
        tenant_id=tenant_id,
        corpus_id=corpus_id,
        limit=limit,
        entity_id=entity_id,
    )
    local_hits = 0
    local_actions_created = 0
    local_actions_reused = 0
    drafts_created = 0
    drafts_reused = 0
    skipped: list[EntityGroundingDraftSkip] = []

    for candidate in selected:
        if not candidate.source_claim_ids:
            skipped.append(EntityGroundingDraftSkip(candidate.id, "missing_claim_source_refs"))
            continue
        if candidate.privacy_tier > 5:
            skipped.append(EntityGroundingDraftSkip(candidate.id, "privacy_tier_unsupported"))
            continue

        hits = search_grounding_evidence(
            conn,
            query_text=candidate.canonical_text,
            tenant_id=candidate.tenant_id,
            corpus_id=candidate.corpus_id,
            limit=local_lookup_limit,
        )
        if hits:
            local_hits += 1
            for hit in hits:
                created = _ensure_grounding_evidence_action(
                    conn,
                    candidate=candidate,
                    hit=hit,
                    requested_at=active_requested_at,
                )
                if created:
                    local_actions_created += 1
                else:
                    local_actions_reused += 1
            continue

        request = _request_for_entity(candidate, requested_at=active_requested_at)
        if _existing_draft_or_grant(conn, request):
            drafts_reused += 1
            continue
        _insert_grounding_request_and_draft_grant(conn, request, candidate=candidate)
        drafts_created += 1

    return EntityGroundingDraftSummary(
        workflow_version=ENTITY_GROUNDING_BATCH_WORKFLOW_VERSION,
        selected=len(selected),
        local_hits=local_hits,
        local_actions_created=local_actions_created,
        local_actions_reused=local_actions_reused,
        drafts_created=drafts_created,
        drafts_reused=drafts_reused,
        skipped=tuple(skipped),
    )


def _select_unknown_entities(
    conn: psycopg.Connection,
    *,
    tenant_id: str,
    corpus_id: str,
    limit: int,
    entity_id: str | None,
) -> tuple[_EntityGroundingCandidate, ...]:
    rows = conn.execute(
        """
        SELECT
            e.id::text,
            e.tenant_id,
            e.corpus_id,
            e.canonical_text,
            e.confidence,
            e.source_claim_ids,
            e.privacy_tier,
            e.created_at
        FROM entities e
        WHERE e.status = 'active'
          AND e.entity_kind = 'unknown'
          AND btrim(e.canonical_text) <> ''
          AND e.tenant_id = %s
          AND e.corpus_id = %s
          AND (%s::uuid IS NULL OR e.id = %s::uuid)
          AND NOT EXISTS (
              SELECT 1
              FROM entity_identity_review_actions a
              WHERE a.tenant_id = e.tenant_id
                AND a.corpus_id = e.corpus_id
                AND a.entity_id = e.id
                AND a.action_kind = 'grounding_evidence_attach'
          )
        ORDER BY e.privacy_tier ASC, e.confidence DESC, e.created_at ASC, e.id ASC
        LIMIT %s
        """,
        (tenant_id, corpus_id, entity_id, entity_id, limit),
    ).fetchall()
    return tuple(
        _EntityGroundingCandidate(
            id=str(row[0]),
            tenant_id=str(row[1]),
            corpus_id=str(row[2]),
            canonical_text=str(row[3]).strip(),
            confidence=float(row[4]),
            source_claim_ids=tuple(str(claim_id) for claim_id in row[5]),
            privacy_tier=int(row[6]),
            created_at=row[7],
        )
        for row in rows
    )


def _ensure_grounding_evidence_action(
    conn: psycopg.Connection,
    *,
    candidate: _EntityGroundingCandidate,
    hit: dict[str, object],
    requested_at: datetime,
) -> bool:
    evidence_id = _required_uuid_string(hit, "id")
    action_id = _uuid_for(
        "grounding-action",
        candidate.id,
        evidence_id,
        ENTITY_GROUNDING_BATCH_WORKFLOW_VERSION,
    )
    existing = conn.execute(
        """
        SELECT id
        FROM entity_identity_review_actions
        WHERE id = %s
           OR (
                tenant_id = %s
                AND corpus_id = %s
                AND entity_id = %s
                AND grounding_evidence_id = %s
                AND action_kind = 'grounding_evidence_attach'
           )
        LIMIT 1
        """,
        (action_id, candidate.tenant_id, candidate.corpus_id, candidate.id, evidence_id),
    ).fetchone()
    if existing is not None:
        return False

    raw_payload = {
        "entity_grounding_workflow": {
            "workflow_version": ENTITY_GROUNDING_BATCH_WORKFLOW_VERSION,
            "entity_id": candidate.id,
            "surface_form": candidate.canonical_text,
            "source_claim_ids": list(candidate.source_claim_ids),
            "extraction_run_id": _extraction_run_id(candidate),
            "attached_at": _rfc3339(requested_at),
            "local_hit": {
                "grounding_evidence_id": evidence_id,
                "score": _json_number(hit.get("score")),
            },
        }
    }
    conn.execute(
        """
        INSERT INTO entity_identity_review_actions (
            id,
            tenant_id,
            corpus_id,
            action_kind,
            entity_id,
            grounding_evidence_id,
            actor,
            rationale,
            privacy_tier,
            raw_payload,
            created_at
        )
        VALUES (
            %s, %s, %s, 'grounding_evidence_attach', %s, %s,
            %s, %s, %s, %s, %s
        )
        """,
        (
            action_id,
            candidate.tenant_id,
            candidate.corpus_id,
            candidate.id,
            evidence_id,
            ENTITY_GROUNDING_BATCH_ACTOR,
            "local grounding evidence matched entity surface",
            candidate.privacy_tier,
            Jsonb(raw_payload),
            requested_at,
        ),
    )
    return True


def _request_for_entity(
    candidate: _EntityGroundingCandidate,
    *,
    requested_at: datetime,
) -> ClaimGroundingRequest:
    source_refs = [
        {"target_table": "claims", "target_id": claim_id}
        for claim_id in sorted(candidate.source_claim_ids)
    ]
    idempotency_key = _idempotency_key(candidate)
    request_id = str(_uuid_for("request", idempotency_key))
    grant_id = str(_uuid_for("grant", idempotency_key))
    payload = {
        "schema_version": CLAIM_GROUNDING_REQUEST_SCHEMA_VERSION,
        "request_id": request_id,
        "tenant_id": candidate.tenant_id,
        "corpus_id": candidate.corpus_id,
        "extraction_run_id": _extraction_run_id(candidate),
        "extraction_prompt_version": ENTITY_GROUNDING_BATCH_PROMPT_VERSION,
        "extraction_model_version": ENTITY_GROUNDING_BATCH_MODEL_VERSION,
        "surface_form": candidate.canonical_text,
        "mention_role": "context",
        "candidate_entity_kinds": list(ENTITY_GROUNDING_CANDIDATE_KINDS),
        "source_refs": source_refs,
        "local_context_capsule": {"mode": "none", "text": None},
        "allowed_modes": ["local_lookup", "network_fetch"],
        "network_grant": {
            "grant_id": grant_id,
            "granted_by": ENTITY_GROUNDING_BATCH_GRANT_ACTOR,
            "granted_at": _rfc3339(requested_at),
            "expires_at": None,
            "purpose": "entity_grounding",
            "search_query": candidate.canonical_text,
            "query_text_class": "entity_surface_form",
            "query_privacy_tier": candidate.privacy_tier,
            "allowed_network_targets": list(ENTITY_GROUNDING_ALLOWED_NETWORK_TARGETS),
        },
        "privacy_tier_ceiling": candidate.privacy_tier,
        "sensitivity_ceiling": ["routine_project"],
        "requested_at": _rfc3339(requested_at),
    }
    return ClaimGroundingRequest.from_json(payload)


def _insert_grounding_request_and_draft_grant(
    conn: psycopg.Connection,
    request: ClaimGroundingRequest,
    *,
    candidate: _EntityGroundingCandidate,
) -> None:
    network_grant = request.network_grant
    if network_grant is None:
        raise EntityGroundingWorkflowError("network grant is required for draft requests")
    request_uuid = UUID(request.request_id)
    grant_uuid = UUID(network_grant.grant_id)
    request_payload = request.to_json()
    grant_payload = {
        **network_grant.to_json(),
        "lifecycle_status": "draft",
        "entity_grounding_workflow": {
            "workflow_version": ENTITY_GROUNDING_BATCH_WORKFLOW_VERSION,
            "entity_id": candidate.id,
            "surface_form": candidate.canonical_text,
            "source_claim_ids": list(candidate.source_claim_ids),
            "idempotency_key": _idempotency_key(candidate),
            "extraction_run_id": request.extraction_run_id,
        },
    }
    conn.execute(
        """
        INSERT INTO claim_grounding_requests (
            id,
            tenant_id,
            corpus_id,
            schema_version,
            extraction_prompt_version,
            extraction_model_version,
            surface_form,
            mention_role,
            candidate_entity_kinds,
            source_refs,
            local_context_capsule,
            allowed_modes,
            network_grant,
            privacy_tier_ceiling,
            sensitivity_ceiling,
            request_payload,
            extraction_run_id,
            requested_at,
            created_at
        )
        VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
            %s::timestamptz, %s::timestamptz
        )
        """,
        (
            request_uuid,
            request.tenant_id,
            request.corpus_id,
            request.schema_version,
            request.extraction_prompt_version,
            request.extraction_model_version,
            request.surface_form,
            request.mention_role,
            list(request.candidate_entity_kinds),
            Jsonb([source_ref.to_json() for source_ref in request.source_refs]),
            Jsonb(request.local_context_capsule.to_json()),
            list(request.allowed_modes),
            Jsonb(network_grant.to_json()),
            request.privacy_tier_ceiling,
            list(request.sensitivity_ceiling),
            Jsonb(request_payload),
            request.extraction_run_id,
            request.requested_at,
            request.requested_at,
        ),
    )
    conn.execute(
        """
        INSERT INTO claim_grounding_grants (
            id,
            tenant_id,
            corpus_id,
            request_id,
            grant_status,
            grant_purpose,
            target_mode,
            surface_form,
            search_query,
            query_text_class,
            query_privacy_tier,
            allowed_network_targets,
            granted_by,
            granted_at,
            expires_at,
            grant_payload,
            created_at
        )
        VALUES (
            %s, %s, %s, %s, 'draft', 'entity_grounding', 'network_fetch', %s, %s, %s,
            %s, %s, NULL, NULL, %s::timestamptz, %s, %s::timestamptz
        )
        """,
        (
            grant_uuid,
            request.tenant_id,
            request.corpus_id,
            request_uuid,
            request.surface_form,
            network_grant.search_query,
            network_grant.query_text_class,
            network_grant.query_privacy_tier,
            list(network_grant.allowed_network_targets),
            network_grant.expires_at,
            Jsonb(grant_payload),
            request.requested_at,
        ),
    )


def _existing_draft_or_grant(
    conn: psycopg.Connection,
    request: ClaimGroundingRequest,
) -> bool:
    network_grant = request.network_grant
    if network_grant is None:
        return False
    row = conn.execute(
        """
        SELECT 1
        FROM claim_grounding_requests r
        WHERE r.id = %s
           OR r.request_payload->>'request_id' = %s
        UNION ALL
        SELECT 1
        FROM claim_grounding_grants g
        WHERE g.id = %s
           OR g.grant_payload->>'grant_id' = %s
        LIMIT 1
        """,
        (
            UUID(request.request_id),
            request.request_id,
            UUID(network_grant.grant_id),
            network_grant.grant_id,
        ),
    ).fetchone()
    return row is not None


def _idempotency_key(candidate: _EntityGroundingCandidate) -> str:
    payload = {
        "workflow_version": ENTITY_GROUNDING_BATCH_WORKFLOW_VERSION,
        "schema_version": CLAIM_GROUNDING_REQUEST_SCHEMA_VERSION,
        "tenant_id": candidate.tenant_id,
        "corpus_id": candidate.corpus_id,
        "entity_id": candidate.id,
        "surface_form": candidate.canonical_text,
        "query_privacy_tier": candidate.privacy_tier,
        "allowed_network_targets": list(ENTITY_GROUNDING_ALLOWED_NETWORK_TARGETS),
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _extraction_run_id(candidate: _EntityGroundingCandidate) -> str:
    return (
        f"{ENTITY_GROUNDING_BATCH_WORKFLOW_VERSION}:"
        f"{_uuid_for('extraction-run', _idempotency_key(candidate))}"
    )


def _uuid_for(*parts: object) -> UUID:
    encoded = "\x1f".join(str(part) for part in parts)
    return uuid5(ENTITY_GROUNDING_ID_NAMESPACE, encoded)


def _required_uuid_string(payload: dict[str, object], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str):
        raise EntityGroundingWorkflowError(f'grounding hit "{key}" must be a UUID string')
    try:
        UUID(value)
    except ValueError as exc:
        raise EntityGroundingWorkflowError(f'grounding hit "{key}" must be a UUID string') from exc
    return value


def _json_number(value: object) -> float | int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int | float):
        return value
    return None


def _rfc3339(value: datetime) -> str:
    active = value if value.tzinfo is not None else value.replace(tzinfo=UTC)
    return active.astimezone(UTC).isoformat().replace("+00:00", "Z")


class EntityGroundingWorkflowError(RuntimeError):
    """Raised when the RFC 0054 draft workflow cannot preserve its contract."""
