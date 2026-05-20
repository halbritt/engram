"""RFC 0055 approved-grant materialization for entity grounding evidence."""

from __future__ import annotations

import hashlib
import ipaddress
import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlsplit
from uuid import UUID

import psycopg
from psycopg import errors
from psycopg.types.json import Jsonb

from engram.claim_grounding import (
    CLAIM_GROUNDING_RESPONSE_SCHEMA_VERSION,
    ClaimGroundingRequest,
    ClaimGroundingResponse,
    GroundingOmission,
    network_broker_dispatch_payload,
)
from engram.claim_grounding_network import (
    CLAIM_GROUNDING_SEARCH_TARGET_ADAPTER,
    ClaimGroundingConfiguredSearchAdapter,
    ClaimGroundingNetworkResultRow,
    require_configured_claim_grounding_network_adapter,
)
from engram.claim_grounding_runtime import (
    ClaimGroundingPersistenceConflict,
    record_claim_grounding_links,
    record_claim_grounding_network_dispatch_attempt,
    record_claim_grounding_response,
    verify_claim_grounding_grant_for_dispatch,
)

ENTITY_GROUNDING_MATERIALIZATION_VERSION = "entity_grounding_materialization.v1"
ENTITY_GROUNDING_MATERIALIZATION_BROKER_VERSION = "claim_grounding.materializer.v1"
ENTITY_GROUNDING_REVIEW_ACTOR = "grounding-broker"
ENTITY_GROUNDING_EVIDENCE_ATTACH_ACTION = "grounding_evidence_attach"
_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_UUID_PATTERN = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)


class EntityGroundingMaterializationError(RuntimeError):
    """Base error for RFC 0055 materialization failures."""


class EntityGroundingProviderDisabled(EntityGroundingMaterializationError):
    """Raised when no network search adapter is configured or injected."""


@dataclass(frozen=True)
class MaterializedGroundingEvidence:
    """One local grounding evidence row created or reused from a provider row."""

    id: UUID
    provider_row_id: str
    rank: int
    content_hash: str
    source_url: str
    source_label: str
    content_excerpt: str

    def to_json(self) -> dict[str, object]:
        """Return a JSON-compatible materialized evidence summary."""
        return {
            "id": str(self.id),
            "provider_row_id": self.provider_row_id,
            "rank": self.rank,
            "content_hash": self.content_hash,
            "source_url": self.source_url,
            "source_label": self.source_label,
            "content_excerpt": self.content_excerpt,
        }


@dataclass(frozen=True)
class ProcessedApprovedGrant:
    """Result for one approved grant processing attempt."""

    request_id: str
    grant_id: str
    status: str
    evidence_ids: tuple[UUID, ...]
    response_id: UUID | None
    adapter_invoked: bool

    def to_json(self) -> dict[str, object]:
        """Return a JSON-compatible grant processing summary."""
        return {
            "request_id": self.request_id,
            "grant_id": self.grant_id,
            "status": self.status,
            "evidence_ids": [str(evidence_id) for evidence_id in self.evidence_ids],
            "response_id": str(self.response_id) if self.response_id is not None else None,
            "adapter_invoked": self.adapter_invoked,
        }


@dataclass(frozen=True)
class ApprovedGrantMaterializationResult:
    """Summary for one materialization batch."""

    processed: tuple[ProcessedApprovedGrant, ...]
    skipped: tuple[str, ...]

    def to_json(self) -> dict[str, object]:
        """Return a JSON-compatible batch summary."""
        return {
            "workflow_version": ENTITY_GROUNDING_MATERIALIZATION_VERSION,
            "processed": [row.to_json() for row in self.processed],
            "skipped": list(self.skipped),
        }


@dataclass(frozen=True)
class _ApprovedGrantWorkItem:
    request_row_id: UUID
    grant_row_id: UUID
    request_id: str
    grant_id: str
    tenant_id: str
    corpus_id: str
    request_payload: Mapping[str, object]
    request_row_payload: Mapping[str, object]
    grant_payload: Mapping[str, object]


def process_approved_grounding_grants(
    conn: psycopg.Connection,
    *,
    adapter: ClaimGroundingConfiguredSearchAdapter | None = None,
    tenant_id: str = "personal",
    corpus_id: str = "personal",
    request_id: UUID | str | None = None,
    grant_id: UUID | str | None = None,
    limit: int = 20,
    target_adapter: str | None = None,
    provider_name: str = "configured_search",
    processed_at: datetime | None = None,
) -> ApprovedGrantMaterializationResult:
    """Process latest approved persisted grants into local grounding evidence."""
    if limit < 1 or limit > 100:
        raise EntityGroundingMaterializationError("limit must be between 1 and 100")
    active_adapter = adapter or require_configured_claim_grounding_network_adapter()
    if active_adapter is None:
        raise EntityGroundingProviderDisabled("claim-grounding network adapter is not configured")
    active_processed_at = processed_at or _utc_now()
    active_target_adapter = target_adapter or CLAIM_GROUNDING_SEARCH_TARGET_ADAPTER
    work_items = _select_latest_approved_work_items(
        conn,
        tenant_id=tenant_id,
        corpus_id=corpus_id,
        request_id=str(request_id) if request_id is not None else None,
        grant_id=str(grant_id) if grant_id is not None else None,
        target_adapter=active_target_adapter,
        limit=limit,
        now=active_processed_at,
    )
    processed: list[ProcessedApprovedGrant] = []
    for work_item in work_items:
        processed.append(
            _process_one_grant(
                conn,
                work_item,
                adapter=active_adapter,
                target_adapter=active_target_adapter,
                provider_name=provider_name,
                processed_at=active_processed_at,
            )
        )
    return ApprovedGrantMaterializationResult(processed=tuple(processed), skipped=())


def _process_one_grant(
    conn: psycopg.Connection,
    work_item: _ApprovedGrantWorkItem,
    *,
    adapter: ClaimGroundingConfiguredSearchAdapter,
    target_adapter: str,
    provider_name: str,
    processed_at: datetime,
) -> ProcessedApprovedGrant:
    request = ClaimGroundingRequest.from_json(work_item.request_payload)
    verify_claim_grounding_grant_for_dispatch(
        conn,
        request,
        target=target_adapter,
        verified_at=processed_at,
    )
    record_claim_grounding_network_dispatch_attempt(
        conn,
        request,
        broker_version=ENTITY_GROUNDING_MATERIALIZATION_BROKER_VERSION,
        target=target_adapter,
        status="prepared",
        created_at=processed_at,
    )
    dispatch_payload = network_broker_dispatch_payload(request)
    try:
        provider_rows = adapter.raw_result_rows(dispatch_payload)
    except Exception as exc:
        _record_failed_dispatch_and_response(
            conn,
            request,
            target_adapter=target_adapter,
            error_code=_safe_error_code(exc),
            processed_at=processed_at,
        )
        return ProcessedApprovedGrant(
            request_id=work_item.request_id,
            grant_id=work_item.grant_id,
            status="provider_fetch_error",
            evidence_ids=(),
            response_id=None,
            adapter_invoked=True,
        )

    evidence = _materialize_provider_rows(
        conn,
        request,
        provider_rows,
        provider_name=provider_name,
        processed_at=processed_at,
    )
    response = _response_from_evidence(request, evidence, processed_at=processed_at)
    response_row = record_claim_grounding_response(conn, request, response)
    if evidence:
        record_claim_grounding_links(conn, request, response)
        _record_evidence_attach_actions(
            conn,
            work_item,
            evidence,
            provider_name=provider_name,
            processed_at=processed_at,
        )
    record_claim_grounding_network_dispatch_attempt(
        conn,
        request,
        broker_version=ENTITY_GROUNDING_MATERIALIZATION_BROKER_VERSION,
        target=target_adapter,
        status="succeeded",
        created_at=processed_at,
    )
    return ProcessedApprovedGrant(
        request_id=work_item.request_id,
        grant_id=work_item.grant_id,
        status=response.status,
        evidence_ids=tuple(row.id for row in evidence),
        response_id=response_row.id,
        adapter_invoked=True,
    )


def _select_latest_approved_work_items(
    conn: psycopg.Connection,
    *,
    tenant_id: str,
    corpus_id: str,
    request_id: str | None,
    grant_id: str | None,
    target_adapter: str,
    limit: int,
    now: datetime,
) -> tuple[_ApprovedGrantWorkItem, ...]:
    try:
        rows = conn.execute(
            """
            WITH latest_grants AS (
                SELECT DISTINCT ON (g.grant_payload->>'grant_id')
                    g.id AS grant_row_id,
                    g.request_id AS request_row_id,
                    g.tenant_id,
                    g.corpus_id,
                    g.grant_status,
                    g.allowed_network_targets,
                    g.expires_at,
                    g.created_at,
                    g.grant_payload
                FROM claim_grounding_grants g
                WHERE g.tenant_id = %s
                  AND g.corpus_id = %s
                  AND g.grant_payload ? 'grant_id'
                  AND (%s::text IS NULL OR g.id::text = %s OR g.grant_payload->>'grant_id' = %s)
                ORDER BY g.grant_payload->>'grant_id', g.created_at DESC, g.id DESC
            )
            SELECT
                r.id,
                lg.grant_row_id,
                r.request_payload->>'request_id',
                lg.grant_payload->>'grant_id',
                r.tenant_id,
                r.corpus_id,
                r.schema_version,
                r.extraction_run_id,
                r.extraction_prompt_version,
                r.extraction_model_version,
                r.surface_form,
                r.mention_role,
                r.candidate_entity_kinds,
                r.source_refs,
                r.local_context_capsule,
                r.allowed_modes,
                r.network_grant,
                r.privacy_tier_ceiling,
                r.sensitivity_ceiling,
                r.requested_at,
                r.request_payload,
                lg.grant_payload
            FROM latest_grants lg
            JOIN claim_grounding_requests r ON r.id = lg.request_row_id
            WHERE lg.grant_status = 'approved'
              AND (lg.expires_at IS NULL OR lg.expires_at > %s)
              AND %s = ANY(lg.allowed_network_targets)
              AND (%s::text IS NULL OR r.id::text = %s OR r.request_payload->>'request_id' = %s)
              AND NOT EXISTS (
                  SELECT 1
                  FROM claim_grounding_network_dispatches d
                  WHERE d.request_id = r.id
                    AND d.grant_id = lg.grant_row_id
                    AND d.target_adapter = %s
                    AND d.dispatch_status IN ('prepared', 'dispatched', 'succeeded', 'failed')
              )
            ORDER BY lg.created_at ASC, lg.grant_row_id ASC
            LIMIT %s
            """,
            (
                tenant_id,
                corpus_id,
                grant_id,
                grant_id,
                grant_id,
                now,
                target_adapter,
                request_id,
                request_id,
                request_id,
                target_adapter,
                limit,
            ),
        ).fetchall()
    except errors.UndefinedTable as exc:
        raise EntityGroundingMaterializationError(
            "RFC 0053/0055 materialization tables are not present"
        ) from exc
    return tuple(
        _ApprovedGrantWorkItem(
            request_row_id=row[0],
            grant_row_id=row[1],
            request_id=str(row[2]),
            grant_id=str(row[3]),
            tenant_id=str(row[4]),
            corpus_id=str(row[5]),
            request_payload={
                "schema_version": row[6],
                "request_id": str(row[2]),
                "tenant_id": row[4],
                "corpus_id": row[5],
                "extraction_run_id": row[7],
                "extraction_prompt_version": row[8],
                "extraction_model_version": row[9],
                "surface_form": row[10],
                "mention_role": row[11],
                "candidate_entity_kinds": list(row[12]),
                "source_refs": row[13],
                "local_context_capsule": row[14],
                "allowed_modes": list(row[15]),
                "network_grant": row[16],
                "privacy_tier_ceiling": row[17],
                "sensitivity_ceiling": list(row[18]),
                "requested_at": _rfc3339(row[19]),
            },
            request_row_payload=_mapping_or_empty(row[20]),
            grant_payload=_mapping_or_empty(row[21]),
        )
        for row in rows
    )


def _materialize_provider_rows(
    conn: psycopg.Connection,
    request: ClaimGroundingRequest,
    provider_rows: Sequence[ClaimGroundingNetworkResultRow],
    *,
    provider_name: str,
    processed_at: datetime,
) -> tuple[MaterializedGroundingEvidence, ...]:
    evidence: list[MaterializedGroundingEvidence] = []
    seen_evidence_ids: set[UUID] = set()
    for provider_row in provider_rows:
        row = _sanitized_provider_row(provider_row, request=request, provider_name=provider_name)
        if row is None:
            continue
        evidence_id = _find_or_insert_grounding_evidence(
            conn,
            request,
            row,
            provider_name=provider_name,
            processed_at=processed_at,
        )
        if evidence_id in seen_evidence_ids:
            continue
        seen_evidence_ids.add(evidence_id)
        evidence.append(
            MaterializedGroundingEvidence(
                id=evidence_id,
                provider_row_id=row["provider_row_id"],
                rank=int(row["rank"]),
                content_hash=row["content_hash"],
                source_url=row["source_url"],
                source_label=row["source_label"],
                content_excerpt=row["content_excerpt"],
            )
        )
    evidence.sort(key=lambda row: (row.rank, str(row.id)))
    return tuple(evidence)


def _find_or_insert_grounding_evidence(
    conn: psycopg.Connection,
    request: ClaimGroundingRequest,
    row: Mapping[str, Any],
    *,
    provider_name: str,
    processed_at: datetime,
) -> UUID:
    query_text = _query_text(request)
    query_privacy_tier = _query_privacy_tier(request)
    existing = conn.execute(
        """
        SELECT id
        FROM entity_grounding_evidence
        WHERE tenant_id = %s
          AND corpus_id = %s
          AND query_text = %s
          AND content_hash = %s
          AND source_url IS NOT DISTINCT FROM %s
          AND privacy_tier >= %s
        ORDER BY created_at ASC, id ASC
        LIMIT 1
        """,
        (
            request.tenant_id,
            request.corpus_id,
            query_text,
            row["content_hash"],
            row["source_url"],
            query_privacy_tier,
        ),
    ).fetchone()
    if existing is not None:
        return existing[0]

    inserted = conn.execute(
        """
        INSERT INTO entity_grounding_evidence (
            tenant_id,
            corpus_id,
            query_text,
            entity_kind,
            source_url,
            source_label,
            content_hash,
            content_excerpt,
            fetched_at,
            fetch_tool_version,
            extractor_version,
            privacy_tier,
            sensitivity_class,
            raw_payload
        )
        VALUES (
            %s, %s, %s, 'unknown', %s, %s, %s, %s, %s, %s, 'none', %s,
            'routine_project', %s
        )
        RETURNING id
        """,
        (
            request.tenant_id,
            request.corpus_id,
            query_text,
            row["source_url"],
            row["source_label"],
            row["content_hash"],
            row["content_excerpt"],
            processed_at,
            f"{ENTITY_GROUNDING_MATERIALIZATION_VERSION}:{provider_name}",
            query_privacy_tier,
            Jsonb(
                {
                    "schema_version": "entity_grounding.materialized_provider_row.v1",
                    "provider_name": provider_name,
                    "provider_row_id": row["provider_row_id"],
                    "provider_content_hash": row["provider_content_hash"],
                    "rank": row["rank"],
                    "title": row["title"],
                    "materializer_version": ENTITY_GROUNDING_MATERIALIZATION_VERSION,
                }
            ),
        ),
    ).fetchone()
    if inserted is None:
        raise EntityGroundingMaterializationError("grounding evidence insert returned no row")
    return inserted[0]


def _response_from_evidence(
    request: ClaimGroundingRequest,
    evidence: Sequence[MaterializedGroundingEvidence],
    *,
    processed_at: datetime,
) -> ClaimGroundingResponse:
    if not evidence:
        status = "not_found"
    elif len(evidence) == 1:
        status = "resolved"
    else:
        status = "ambiguous"
    candidates = [
        {
            "candidate_id": f"grounding-evidence-{row.id}",
            "entity_kind": "unknown",
            "canonical_label": request.surface_form,
            "external_ids": [],
            "grounding_evidence_ids": [str(row.id)],
            "source_url": row.source_url,
            "source_label": row.source_label,
            "content_hash": row.content_hash,
            "content_excerpt": row.content_excerpt,
            "confidence": 0.5,
            "stability": "public_search_result",
            "ambiguity_reasons": [] if len(evidence) == 1 else ["multiple_provider_results"],
        }
        for row in evidence
    ]
    omissions: list[Mapping[str, object | None]] = []
    if not evidence:
        omissions.append({"reason": "provider_returned_no_results", "details": None})
    return ClaimGroundingResponse.from_json(
        {
            "schema_version": CLAIM_GROUNDING_RESPONSE_SCHEMA_VERSION,
            "request_id": request.request_id,
            "status": status,
            "mode": "network_fetch",
            "network_fetch": "performed_by_grounding_broker",
            "candidates": candidates,
            "omissions": omissions,
            "broker_version": ENTITY_GROUNDING_MATERIALIZATION_BROKER_VERSION,
            "dataset_snapshots": [],
            "created_at": _rfc3339(processed_at),
        }
    )


def _record_evidence_attach_actions(
    conn: psycopg.Connection,
    work_item: _ApprovedGrantWorkItem,
    evidence: Sequence[MaterializedGroundingEvidence],
    *,
    provider_name: str,
    processed_at: datetime,
) -> None:
    entity_ids = _entity_ids_from_work_item(work_item)
    if not entity_ids:
        return
    review_privacy_tier = _query_privacy_tier_from_work_item(work_item)
    for entity_id in entity_ids:
        for row in evidence:
            conn.execute(
                """
                INSERT INTO entity_identity_review_actions (
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
                VALUES (%s, %s, %s, %s::uuid, %s, %s, %s, %s, %s, %s)
                """,
                (
                    work_item.tenant_id,
                    work_item.corpus_id,
                    ENTITY_GROUNDING_EVIDENCE_ATTACH_ACTION,
                    str(entity_id),
                    row.id,
                    ENTITY_GROUNDING_REVIEW_ACTOR,
                    "RFC0055 materialized provider row attached as review evidence.",
                    review_privacy_tier,
                    Jsonb(
                        {
                            "schema_version": "entity_identity_review_action.grounding_attach.v1",
                            "request_id": work_item.request_id,
                            "grant_id": work_item.grant_id,
                            "provider_name": provider_name,
                            "provider_row_id": row.provider_row_id,
                            "rank": row.rank,
                            "materializer_version": ENTITY_GROUNDING_MATERIALIZATION_VERSION,
                        }
                    ),
                    processed_at,
                ),
            )


def _record_failed_dispatch_and_response(
    conn: psycopg.Connection,
    request: ClaimGroundingRequest,
    *,
    target_adapter: str,
    error_code: str,
    processed_at: datetime,
) -> None:
    try:
        record_claim_grounding_network_dispatch_attempt(
            conn,
            request,
            broker_version=ENTITY_GROUNDING_MATERIALIZATION_BROKER_VERSION,
            target=target_adapter,
            status="failed",
            error_code=error_code,
            created_at=processed_at,
        )
        record_claim_grounding_response(
            conn,
            request,
            ClaimGroundingResponse(
                request_id=request.request_id,
                status="error",
                mode="network_fetch",
                network_fetch="performed_by_grounding_broker",
                candidates=(),
                omissions=(
                    GroundingOmission(
                        reason="provider_fetch_error",
                        details="Provider fetch failed before materialization.",
                    ),
                ),
                broker_version=ENTITY_GROUNDING_MATERIALIZATION_BROKER_VERSION,
                dataset_snapshots=(),
                created_at=_rfc3339(processed_at),
            ),
        )
    except ClaimGroundingPersistenceConflict:
        raise


def _sanitized_provider_row(
    provider_row: ClaimGroundingNetworkResultRow,
    *,
    request: ClaimGroundingRequest,
    provider_name: str,
) -> dict[str, Any] | None:
    source_url = _clean_public_url(provider_row.url)
    if source_url is None:
        return None
    title = _clean_text(provider_row.title, max_chars=180)
    source_label = _clean_text(
        provider_row.source_label or urlsplit(source_url).hostname or "search result",
        max_chars=180,
    )
    content_excerpt = _clean_text(provider_row.excerpt or title or source_label, max_chars=500)
    if not content_excerpt:
        return None
    row_hash_payload = {
        "query_text": _query_text(request),
        "title": title,
        "source_url": source_url,
        "source_label": source_label,
        "content_excerpt": content_excerpt,
    }
    content_hash = hashlib.sha256(
        json.dumps(row_hash_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    provider_content_hash = (
        provider_row.content_hash
        if _SHA256_PATTERN.fullmatch(provider_row.content_hash)
        else hashlib.sha256(str(provider_row.content_hash).encode("utf-8")).hexdigest()
    )
    return {
        "provider_name": provider_name,
        "provider_row_id": _clean_identifier(provider_row.row_id),
        "provider_content_hash": provider_content_hash,
        "rank": max(1, int(provider_row.rank)),
        "title": title,
        "source_url": source_url,
        "source_label": source_label,
        "content_excerpt": content_excerpt,
        "content_hash": content_hash,
    }


def _entity_ids_from_payload(payload: Mapping[str, object]) -> tuple[UUID, ...]:
    ids: list[UUID] = []
    direct_id = payload.get("entity_id")
    if isinstance(direct_id, str) and _UUID_PATTERN.fullmatch(direct_id):
        ids.append(UUID(direct_id))
    direct_ids = payload.get("entity_ids")
    if isinstance(direct_ids, Sequence) and not isinstance(direct_ids, str | bytes | bytearray):
        for value in direct_ids:
            if isinstance(value, str) and _UUID_PATTERN.fullmatch(value):
                ids.append(UUID(value))
    source_refs = payload.get("source_refs")
    if isinstance(source_refs, Sequence) and not isinstance(source_refs, str | bytes | bytearray):
        for source_ref in source_refs:
            if not isinstance(source_ref, Mapping):
                continue
            if source_ref.get("target_table") not in {"entities", "entity"}:
                continue
            target_id = source_ref.get("target_id")
            if isinstance(target_id, str) and _UUID_PATTERN.fullmatch(target_id):
                ids.append(UUID(target_id))
    return tuple(dict.fromkeys(ids))


def _entity_ids_from_work_item(work_item: _ApprovedGrantWorkItem) -> tuple[UUID, ...]:
    ids = list(_entity_ids_from_payload(work_item.request_row_payload))
    grant_entity_payload = work_item.grant_payload.get("entity_grounding_workflow")
    if isinstance(grant_entity_payload, Mapping):
        ids.extend(_entity_ids_from_payload(grant_entity_payload))
    return tuple(dict.fromkeys(ids))


def _mapping_or_empty(value: object) -> Mapping[str, object]:
    if isinstance(value, Mapping):
        return {str(key): row for key, row in value.items()}
    return {}


def _query_text(request: ClaimGroundingRequest) -> str:
    if request.network_grant is not None:
        return request.network_grant.search_query
    return request.surface_form


def _query_privacy_tier(request: ClaimGroundingRequest) -> int:
    if request.network_grant is not None:
        return request.network_grant.query_privacy_tier
    return 1


def _query_privacy_tier_from_work_item(work_item: _ApprovedGrantWorkItem) -> int:
    grant = work_item.request_payload.get("network_grant")
    if isinstance(grant, Mapping):
        tier = grant.get("query_privacy_tier")
        if isinstance(tier, int):
            return tier
    return 1


def _safe_error_code(exc: BaseException) -> str:
    name = exc.__class__.__name__.strip() or "provider_fetch_error"
    normalized = re.sub(r"[^A-Za-z0-9_.-]+", "_", name).strip("._-")
    return f"provider_fetch_error:{normalized[:80] or 'unknown'}"


def _clean_public_url(value: str) -> str | None:
    cleaned = " ".join(value.split())
    if not cleaned:
        return None
    parts = urlsplit(cleaned)
    if parts.scheme not in {"http", "https"} or not parts.netloc or parts.hostname is None:
        return None
    hostname = parts.hostname.strip("[]").casefold()
    if hostname == "localhost" or hostname.endswith(".localhost"):
        return None
    try:
        ip_address = ipaddress.ip_address(hostname)
    except ValueError:
        return cleaned
    if (
        ip_address.is_private
        or ip_address.is_loopback
        or ip_address.is_link_local
        or ip_address.is_unspecified
        or ip_address.is_multicast
        or ip_address.is_reserved
    ):
        return None
    return cleaned


def _clean_identifier(value: str) -> str:
    cleaned = " ".join(value.split())
    if not cleaned:
        return "provider-row"
    return cleaned[:120]


def _clean_text(value: str, *, max_chars: int) -> str:
    cleaned = " ".join(value.replace("\x00", " ").split())
    if len(cleaned) <= max_chars:
        return cleaned
    return cleaned[: max_chars - 1].rstrip() + "..."


def _rfc3339(value: object) -> str:
    if isinstance(value, datetime):
        active = value.astimezone(UTC)
        return active.isoformat().replace("+00:00", "Z")
    return str(value)


def _utc_now() -> datetime:
    return datetime.now(tz=UTC)
