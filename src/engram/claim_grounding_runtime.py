"""Append-only RFC 0053 claim-grounding persistence helpers."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

import psycopg
from psycopg import errors
from psycopg.types.json import Jsonb

from engram.claim_grounding import (
    ClaimGroundingRequest,
    ClaimGroundingResponse,
    NetworkGroundingGrant,
    network_broker_dispatch_payload,
)

CLAIM_GROUNDING_REQUESTS_TABLE = "claim_grounding_requests"
CLAIM_GROUNDING_GRANTS_TABLE = "claim_grounding_grants"
CLAIM_GROUNDING_GRANT_USES_TABLE = "claim_grounding_grant_uses"
CLAIM_GROUNDING_NETWORK_DISPATCHES_TABLE = "claim_grounding_network_dispatches"
CLAIM_GROUNDING_RESPONSES_TABLE = "claim_grounding_responses"
CLAIM_GROUNDING_LINKS_TABLE = "claim_grounding_links"
CLAIM_GROUNDING_RUNTIME_VERSION = "claim_grounding_runtime.v1"


class ClaimGroundingRuntimeError(RuntimeError):
    """Base error for claim-grounding persistence failures."""


class ClaimGroundingPersistenceSchemaMissing(ClaimGroundingRuntimeError):
    """Raised when RFC 0053 sidecar tables have not been migrated yet."""


class ClaimGroundingPersistenceConflict(ClaimGroundingRuntimeError):
    """Raised when persisted grant/request lineage does not match the payload."""


@dataclass(frozen=True)
class RecordedClaimGroundingRequest:
    """Persisted RFC 0053 request sidecar row."""

    id: UUID
    request_id: str


@dataclass(frozen=True)
class RecordedClaimGroundingGrant:
    """Persisted operator grant row."""

    id: UUID
    grant_id: str
    request_id: str
    status: str


@dataclass(frozen=True)
class RecordedClaimGroundingGrantUse:
    """Persisted grant-use audit row."""

    id: UUID
    grant_id: str
    request_id: str


@dataclass(frozen=True)
class RecordedClaimGroundingDispatch:
    """Persisted minimized network-dispatch attempt row."""

    id: UUID
    request_id: str
    grant_id: str
    status: str


@dataclass(frozen=True)
class VerifiedClaimGroundingGrant:
    """Persisted grant row verified for a specific outbound dispatch."""

    id: UUID
    grant_id: str
    request_id: str
    target: str
    search_query: str
    query_privacy_tier: int
    expires_at: datetime | None


@dataclass(frozen=True)
class RecordedClaimGroundingResponse:
    """Persisted RFC 0053 response sidecar row."""

    id: UUID
    request_id: str
    status: str


@dataclass(frozen=True)
class RecordedClaimGroundingLink:
    """Persisted link between a grounding response candidate and extraction output."""

    id: UUID
    request_id: str
    candidate_id: str
    grounding_evidence_id: str


def record_claim_grounding_request(
    conn: psycopg.Connection,
    request: ClaimGroundingRequest | Mapping[str, object],
    *,
    recorded_at: datetime | None = None,
) -> RecordedClaimGroundingRequest:
    """Record one validated extractor-to-broker grounding request."""
    active_request = _request(request)
    payload = active_request.to_json()
    try:
        row = conn.execute(
            """
            INSERT INTO claim_grounding_requests (
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
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s::timestamptz, %s
            )
            RETURNING id
            """,
            (
                active_request.tenant_id,
                active_request.corpus_id,
                active_request.schema_version,
                active_request.extraction_prompt_version,
                active_request.extraction_model_version,
                active_request.surface_form,
                active_request.mention_role,
                list(active_request.candidate_entity_kinds),
                Jsonb([source_ref.to_json() for source_ref in active_request.source_refs]),
                Jsonb(active_request.local_context_capsule.to_json()),
                list(active_request.allowed_modes),
                Jsonb(active_request.network_grant.to_json())
                if active_request.network_grant is not None
                else None,
                active_request.privacy_tier_ceiling,
                list(active_request.sensitivity_ceiling),
                Jsonb(payload),
                active_request.extraction_run_id,
                active_request.requested_at,
                recorded_at or _utc_now(),
            ),
        ).fetchone()
    except errors.UndefinedTable as exc:
        raise _missing_tables_error() from exc
    if row is None:
        raise ClaimGroundingRuntimeError("claim-grounding request insert returned no row")
    return RecordedClaimGroundingRequest(id=row[0], request_id=active_request.request_id)


def record_claim_grounding_grant(
    conn: psycopg.Connection,
    request: ClaimGroundingRequest | Mapping[str, object],
    *,
    recorded_at: datetime | None = None,
) -> RecordedClaimGroundingGrant:
    """Record the approved operator network grant embedded in a request."""
    return record_claim_grounding_approved_grant(conn, request, recorded_at=recorded_at)


def record_claim_grounding_draft_grant(
    conn: psycopg.Connection,
    request: ClaimGroundingRequest | Mapping[str, object],
    *,
    recorded_at: datetime | None = None,
) -> RecordedClaimGroundingGrant:
    """Record a draft operator grant row without approving dispatch."""
    return _record_claim_grounding_grant_lifecycle_row(
        conn,
        request,
        status="draft",
        recorded_at=recorded_at,
    )


def record_claim_grounding_approved_grant(
    conn: psycopg.Connection,
    request: ClaimGroundingRequest | Mapping[str, object],
    *,
    recorded_at: datetime | None = None,
) -> RecordedClaimGroundingGrant:
    """Record an approved operator grant row for later dispatch verification."""
    return _record_claim_grounding_grant_lifecycle_row(
        conn,
        request,
        status="approved",
        recorded_at=recorded_at,
    )


def record_claim_grounding_denied_grant(
    conn: psycopg.Connection,
    request: ClaimGroundingRequest | Mapping[str, object],
    *,
    denied_by: str,
    reason: str,
    recorded_at: datetime | None = None,
) -> RecordedClaimGroundingGrant:
    """Record a denied operator grant row without mutating earlier rows."""
    return _record_claim_grounding_grant_lifecycle_row(
        conn,
        request,
        status="denied",
        actor=denied_by,
        lifecycle_payload={"denied_by": denied_by, "denial_reason": reason},
        recorded_at=recorded_at,
    )


def record_claim_grounding_revoked_grant(
    conn: psycopg.Connection,
    request: ClaimGroundingRequest | Mapping[str, object],
    *,
    revoked_by: str,
    reason: str,
    revoked_at: datetime | None = None,
) -> RecordedClaimGroundingGrant:
    """Record a revoked operator grant row without mutating earlier rows."""
    active_revoked_at = revoked_at or _utc_now()
    return _record_claim_grounding_grant_lifecycle_row(
        conn,
        request,
        status="revoked",
        actor=revoked_by,
        lifecycle_payload={"revoked_by": revoked_by, "revocation_reason": reason},
        revoked_at=active_revoked_at,
        recorded_at=active_revoked_at,
    )


def verify_claim_grounding_grant_for_dispatch(
    conn: psycopg.Connection,
    request: ClaimGroundingRequest | Mapping[str, object],
    *,
    target: str,
    verified_at: datetime | None = None,
) -> VerifiedClaimGroundingGrant:
    """Verify that the latest persisted grant row authorizes one dispatch target."""
    active_request = _request(request)
    grant = _require_grant(active_request)
    _select_request_record(conn, active_request)
    grant_row = _assert_persisted_grant_matches_request(conn, active_request, grant)
    active_verified_at = verified_at or _utc_now()
    if grant_row.status != "approved":
        raise ClaimGroundingPersistenceConflict(
            f'network grant "{grant.grant_id}" is not approved; latest status is '
            f'"{grant_row.status}"'
        )
    if grant_row.expires_at is not None and grant_row.expires_at <= active_verified_at:
        raise ClaimGroundingPersistenceConflict(f'network grant "{grant.grant_id}" is expired')
    if target not in grant_row.allowed_network_targets:
        raise ClaimGroundingPersistenceConflict(
            f'network grant "{grant.grant_id}" does not allow target "{target}"'
        )
    return VerifiedClaimGroundingGrant(
        id=grant_row.id,
        grant_id=grant.grant_id,
        request_id=active_request.request_id,
        target=target,
        search_query=grant_row.search_query,
        query_privacy_tier=grant_row.query_privacy_tier,
        expires_at=grant_row.expires_at,
    )


def _record_claim_grounding_grant_lifecycle_row(
    conn: psycopg.Connection,
    request: ClaimGroundingRequest | Mapping[str, object],
    *,
    status: str,
    actor: str | None = None,
    lifecycle_payload: Mapping[str, object] | None = None,
    revoked_at: datetime | None = None,
    recorded_at: datetime | None = None,
) -> RecordedClaimGroundingGrant:
    active_request = _request(request)
    grant = _require_grant(active_request)
    request_row = _select_request_record(conn, active_request)
    grant_payload = {
        **grant.to_json(),
        "lifecycle_status": status,
        **dict(lifecycle_payload or {}),
    }
    granted_at = grant.granted_at if status == "approved" else None
    granted_by = grant.granted_by if status == "approved" else actor
    try:
        row = conn.execute(
            """
            INSERT INTO claim_grounding_grants (
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
                revoked_at,
                grant_payload,
                created_at
            )
            VALUES (
                %s, %s, %s, %s, %s, 'network_fetch', %s, %s, %s, %s, %s,
                %s, %s::timestamptz, %s::timestamptz, %s::timestamptz, %s, %s
            )
            RETURNING id
            """,
            (
                active_request.tenant_id,
                active_request.corpus_id,
                request_row.id,
                status,
                grant.purpose,
                active_request.surface_form,
                grant.search_query,
                grant.query_text_class,
                grant.query_privacy_tier,
                list(grant.allowed_network_targets),
                granted_by,
                granted_at,
                grant.expires_at,
                revoked_at,
                Jsonb(grant_payload),
                recorded_at or _utc_now(),
            ),
        ).fetchone()
    except errors.UndefinedTable as exc:
        raise _missing_tables_error() from exc
    if row is None:
        raise ClaimGroundingRuntimeError("claim-grounding grant insert returned no row")
    _assert_persisted_grant_matches_request(conn, active_request, grant)
    return RecordedClaimGroundingGrant(
        id=row[0],
        grant_id=grant.grant_id,
        request_id=active_request.request_id,
        status=status,
    )


def record_claim_grounding_grant_use(
    conn: psycopg.Connection,
    request: ClaimGroundingRequest | Mapping[str, object],
    *,
    use_kind: str = "network_dispatch_attempt",
    payload: Mapping[str, object] | None = None,
    used_at: datetime | None = None,
) -> RecordedClaimGroundingGrantUse:
    """Record one broker-side use of a persisted network grant."""
    active_request = _request(request)
    grant = _require_grant(active_request)
    request_row = _select_request_record(conn, active_request)
    grant_row = _assert_persisted_grant_matches_request(conn, active_request, grant)
    try:
        row = conn.execute(
            """
            INSERT INTO claim_grounding_grant_uses (
                grant_id,
                request_id,
                dispatch_id,
                tenant_id,
                corpus_id,
                use_status,
                target_adapter,
                search_query,
                query_privacy_tier,
                expires_at_snapshot,
                use_payload,
                verified_at
            )
            VALUES (%s, %s, NULL, %s, %s, %s, NULL, %s, %s, %s::timestamptz, %s, %s)
            RETURNING id
            """,
            (
                grant_row.id,
                request_row.id,
                active_request.tenant_id,
                active_request.corpus_id,
                _grant_use_status(use_kind),
                grant.search_query,
                grant.query_privacy_tier,
                grant.expires_at,
                Jsonb({"use_kind": use_kind, **dict(payload or {})}),
                used_at or _utc_now(),
            ),
        ).fetchone()
    except errors.UndefinedTable as exc:
        raise _missing_tables_error() from exc
    if row is None:
        raise ClaimGroundingRuntimeError("claim-grounding grant-use insert returned no row")
    return RecordedClaimGroundingGrantUse(
        id=row[0],
        grant_id=grant.grant_id,
        request_id=active_request.request_id,
    )


def record_claim_grounding_network_dispatch_attempt(
    conn: psycopg.Connection,
    request: ClaimGroundingRequest | Mapping[str, object],
    *,
    broker_version: str,
    target: str,
    status: str,
    error_code: str | None = None,
    created_at: datetime | None = None,
) -> RecordedClaimGroundingDispatch:
    """Record one minimized outbound dispatch attempt without performing network I/O."""
    active_request = _request(request)
    request_row = _select_request_record(conn, active_request)
    verified_grant = verify_claim_grounding_grant_for_dispatch(
        conn,
        active_request,
        target=target,
        verified_at=created_at,
    )
    attempt_number = _next_dispatch_attempt_number(conn, request_row.id, verified_grant.id, target)
    dispatch_payload = network_broker_dispatch_payload(active_request)
    try:
        row = conn.execute(
            """
            INSERT INTO claim_grounding_network_dispatches (
                request_id,
                grant_id,
                tenant_id,
                corpus_id,
                target_mode,
                target_adapter,
                search_query,
                query_privacy_tier,
                attempt_number,
                dispatch_status,
                dispatch_payload,
                denial_reason,
                result_metadata,
                requested_at,
                completed_at
            )
            VALUES (%s, %s, %s, %s, 'network_fetch', %s, %s, %s, %s, %s, %s, %s, %s, %s, NULL)
            RETURNING id
            """,
            (
                request_row.id,
                verified_grant.id,
                active_request.tenant_id,
                active_request.corpus_id,
                target,
                verified_grant.search_query,
                verified_grant.query_privacy_tier,
                attempt_number,
                status,
                Jsonb(dispatch_payload),
                error_code,
                Jsonb({"broker_version": broker_version}),
                created_at or _utc_now(),
            ),
        ).fetchone()
    except errors.UndefinedTable as exc:
        raise _missing_tables_error() from exc
    if row is None:
        raise ClaimGroundingRuntimeError("claim-grounding dispatch insert returned no row")
    return RecordedClaimGroundingDispatch(
        id=row[0],
        request_id=active_request.request_id,
        grant_id=verified_grant.grant_id,
        status=status,
    )


def record_claim_grounding_response(
    conn: psycopg.Connection,
    request: ClaimGroundingRequest | Mapping[str, object],
    response: ClaimGroundingResponse | Mapping[str, object],
) -> RecordedClaimGroundingResponse:
    """Record one validated broker response for a request."""
    active_request = _request(request)
    active_response = _response(response)
    _assert_response_matches_request(active_request, active_response)
    request_row = _select_request_record(conn, active_request)
    try:
        row = conn.execute(
            """
            INSERT INTO claim_grounding_responses (
                request_id,
                tenant_id,
                corpus_id,
                status,
                mode,
                network_fetch,
                candidates,
                omissions,
                broker_version,
                dataset_snapshots,
                response_payload,
                created_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::timestamptz)
            RETURNING id
            """,
            (
                request_row.id,
                active_request.tenant_id,
                active_request.corpus_id,
                active_response.status,
                active_response.mode,
                active_response.network_fetch,
                Jsonb([candidate.to_json() for candidate in active_response.candidates]),
                Jsonb([omission.to_json() for omission in active_response.omissions]),
                active_response.broker_version,
                Jsonb([snapshot.to_json() for snapshot in active_response.dataset_snapshots]),
                Jsonb(active_response.to_json()),
                active_response.created_at,
            ),
        ).fetchone()
    except errors.UndefinedTable as exc:
        raise _missing_tables_error() from exc
    if row is None:
        raise ClaimGroundingRuntimeError("claim-grounding response insert returned no row")
    return RecordedClaimGroundingResponse(
        id=row[0],
        request_id=active_request.request_id,
        status=active_response.status,
    )


def record_claim_grounding_links(
    conn: psycopg.Connection,
    request: ClaimGroundingRequest | Mapping[str, object],
    response: ClaimGroundingResponse | Mapping[str, object],
    *,
    claim_id: UUID | str | None = None,
    extraction_id: UUID | str | None = None,
    link_kind: str = "response_candidate_to_evidence",
    payload: Mapping[str, object] | None = None,
) -> tuple[RecordedClaimGroundingLink, ...]:
    """Record candidate-to-claim/extraction grounding provenance links."""
    active_request = _request(request)
    active_response = _response(response)
    _assert_response_matches_request(active_request, active_response)
    request_row = _select_request_record(conn, active_request)
    response_row = _select_response_record(conn, request_row.id)
    links: list[RecordedClaimGroundingLink] = []
    try:
        for candidate in active_response.candidates:
            for grounding_evidence_id in candidate.grounding_evidence_ids:
                row = conn.execute(
                    """
                    INSERT INTO claim_grounding_links (
                        request_id,
                        response_id,
                        claim_id,
                        extraction_id,
                        grounding_evidence_id,
                        tenant_id,
                        corpus_id,
                        link_kind,
                        response_candidate_id,
                        link_payload,
                        created_at
                    )
                    VALUES (%s, %s, %s::uuid, %s::uuid, %s::uuid, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                    """,
                    (
                        request_row.id,
                        response_row.id,
                        str(claim_id) if claim_id is not None else None,
                        str(extraction_id) if extraction_id is not None else None,
                        grounding_evidence_id,
                        active_request.tenant_id,
                        active_request.corpus_id,
                        link_kind,
                        candidate.candidate_id,
                        Jsonb(dict(payload or {})),
                        _utc_now(),
                    ),
                ).fetchone()
                if row is None:
                    raise ClaimGroundingRuntimeError("claim-grounding link insert returned no row")
                links.append(
                    RecordedClaimGroundingLink(
                        id=row[0],
                        request_id=active_request.request_id,
                        candidate_id=candidate.candidate_id,
                        grounding_evidence_id=grounding_evidence_id,
                    )
                )
    except errors.UndefinedTable as exc:
        raise _missing_tables_error() from exc
    return tuple(links)


def _request(request: ClaimGroundingRequest | Mapping[str, object]) -> ClaimGroundingRequest:
    if isinstance(request, ClaimGroundingRequest):
        return request
    return ClaimGroundingRequest.from_json(request)


def _response(response: ClaimGroundingResponse | Mapping[str, object]) -> ClaimGroundingResponse:
    return (
        response
        if isinstance(response, ClaimGroundingResponse)
        else ClaimGroundingResponse.from_json(response)
    )


def _require_grant(request: ClaimGroundingRequest) -> NetworkGroundingGrant:
    if request.network_grant is None:
        raise ClaimGroundingPersistenceConflict("claim-grounding request has no network_grant")
    return request.network_grant


@dataclass(frozen=True)
class _PersistedRequest:
    id: UUID


@dataclass(frozen=True)
class _PersistedGrant:
    id: UUID
    status: str
    request_id: UUID
    tenant_id: str
    corpus_id: str
    grant_purpose: str
    surface_form: str
    search_query: str
    query_text_class: str
    query_privacy_tier: int
    allowed_network_targets: tuple[str, ...]
    expires_at: datetime | None


@dataclass(frozen=True)
class _PersistedResponse:
    id: UUID


def _select_request_record(
    conn: psycopg.Connection,
    request: ClaimGroundingRequest,
) -> _PersistedRequest:
    try:
        row = conn.execute(
            """
            SELECT id
            FROM claim_grounding_requests
            WHERE request_payload->>'request_id' = %s
              AND tenant_id = %s
              AND corpus_id = %s
            ORDER BY created_at DESC, id DESC
            LIMIT 1
            """,
            (request.request_id, request.tenant_id, request.corpus_id),
        ).fetchone()
    except errors.UndefinedTable as exc:
        raise _missing_tables_error() from exc
    if row is None:
        raise ClaimGroundingPersistenceConflict(
            f'claim-grounding request "{request.request_id}" has not been persisted'
        )
    return _PersistedRequest(id=row[0])


def _select_response_record(
    conn: psycopg.Connection,
    request_record_id: UUID,
) -> _PersistedResponse:
    try:
        row = conn.execute(
            """
            SELECT id
            FROM claim_grounding_responses
            WHERE request_id = %s
            ORDER BY created_at DESC, id DESC
            LIMIT 1
            """,
            (request_record_id,),
        ).fetchone()
    except errors.UndefinedTable as exc:
        raise _missing_tables_error() from exc
    if row is None:
        raise ClaimGroundingPersistenceConflict(
            "claim-grounding response has not been persisted for this request"
        )
    return _PersistedResponse(id=row[0])


def _select_grant(
    conn: psycopg.Connection,
    grant_id: str,
) -> _PersistedGrant | None:
    row = conn.execute(
        """
        SELECT
            id,
            grant_status,
            request_id,
            tenant_id,
            corpus_id,
            grant_purpose,
            surface_form,
            search_query,
            query_text_class,
            query_privacy_tier,
            allowed_network_targets,
            expires_at
        FROM claim_grounding_grants
        WHERE grant_payload->>'grant_id' = %s
        ORDER BY created_at DESC, id DESC
        LIMIT 1
        """,
        (grant_id,),
    ).fetchone()
    if row is None:
        return None
    return _PersistedGrant(
        id=row[0],
        status=row[1],
        request_id=row[2],
        tenant_id=row[3],
        corpus_id=row[4],
        grant_purpose=row[5],
        surface_form=row[6],
        search_query=row[7],
        query_text_class=row[8],
        query_privacy_tier=row[9],
        allowed_network_targets=tuple(row[10]),
        expires_at=row[11],
    )


def _next_dispatch_attempt_number(
    conn: psycopg.Connection,
    request_record_id: UUID,
    grant_record_id: UUID,
    target_adapter: str,
) -> int:
    try:
        row = conn.execute(
            """
            SELECT COALESCE(max(attempt_number), 0) + 1
            FROM claim_grounding_network_dispatches
            WHERE request_id = %s
              AND grant_id = %s
              AND target_adapter = %s
            """,
            (request_record_id, grant_record_id, target_adapter),
        ).fetchone()
    except errors.UndefinedTable as exc:
        raise _missing_tables_error() from exc
    if row is None:
        return 1
    return row[0]


def _assert_persisted_grant_matches_request(
    conn: psycopg.Connection,
    request: ClaimGroundingRequest,
    grant: NetworkGroundingGrant,
) -> _PersistedGrant:
    try:
        row = _select_grant(conn, grant.grant_id)
    except errors.UndefinedTable as exc:
        raise _missing_tables_error() from exc
    if row is None:
        raise ClaimGroundingPersistenceConflict(
            f'network grant "{grant.grant_id}" has not been persisted'
        )
    request_row = _select_request_record(conn, request)
    if (
        row.request_id != request_row.id
        or row.tenant_id != request.tenant_id
        or row.corpus_id != request.corpus_id
        or row.grant_purpose != grant.purpose
        or row.surface_form != request.surface_form
        or row.search_query != grant.search_query
        or row.query_text_class != grant.query_text_class
        or row.query_privacy_tier != grant.query_privacy_tier
        or row.allowed_network_targets != grant.allowed_network_targets
    ):
        raise ClaimGroundingPersistenceConflict(
            f'persisted network grant "{grant.grant_id}" does not match request lineage'
        )
    return row


def _assert_response_matches_request(
    request: ClaimGroundingRequest,
    response: ClaimGroundingResponse,
) -> None:
    if response.request_id != request.request_id:
        raise ClaimGroundingPersistenceConflict(
            f'response request_id "{response.request_id}" does not match request '
            f'"{request.request_id}"'
        )


def _missing_tables_error() -> ClaimGroundingPersistenceSchemaMissing:
    return ClaimGroundingPersistenceSchemaMissing(
        "RFC 0053 claim-grounding persistence tables are not present; expected "
        "claim_grounding_requests, claim_grounding_responses, "
        "claim_grounding_network_dispatches, claim_grounding_grant_uses, "
        "claim_grounding_grants, and claim_grounding_links"
    )


def _utc_now() -> datetime:
    return datetime.now(tz=UTC)


def _grant_use_status(use_kind: str) -> str:
    if use_kind in {
        "verified",
        "denied",
        "expired",
        "revoked",
        "query_mismatch",
        "target_mismatch",
        "privacy_exceeded",
        "error",
    }:
        return use_kind
    return "verified"
