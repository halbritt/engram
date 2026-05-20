from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from uuid import UUID, uuid4

import psycopg
import pytest

from engram.claim_grounding import CLAIM_GROUNDING_REQUEST_SCHEMA_VERSION, ClaimGroundingRequest
from engram.claim_grounding_network import ClaimGroundingNetworkResultRow
from engram.claim_grounding_runtime import (
    record_claim_grounding_approved_grant,
    record_claim_grounding_denied_grant,
    record_claim_grounding_request,
    record_claim_grounding_revoked_grant,
)
from engram.entity_grounding_materialization import process_approved_grounding_grants

_PROCESSED_AT = datetime(2026, 5, 19, 12, 0, 0, tzinfo=UTC)


class _MockSearchAdapter:
    def __init__(
        self,
        rows: tuple[ClaimGroundingNetworkResultRow, ...],
        *,
        error: BaseException | None = None,
    ) -> None:
        self.rows = rows
        self.error = error
        self.calls: list[Mapping[str, object]] = []

    def raw_result_rows(
        self,
        dispatch_payload: Mapping[str, object],
    ) -> tuple[ClaimGroundingNetworkResultRow, ...]:
        self.calls.append(dispatch_payload)
        if self.error is not None:
            raise self.error
        return self.rows

    def __call__(self, dispatch_payload: Mapping[str, object]) -> Mapping[str, object]:
        raise AssertionError("materializer must consume raw_result_rows, not adapter responses")


def test_approved_grant_materializes_evidence_before_cited_response(
    conn: psycopg.Connection,
) -> None:
    request = _record_request_and_approved_grant(conn)
    adapter = _MockSearchAdapter((_provider_row(rank=1),))

    result = process_approved_grounding_grants(
        conn,
        adapter=adapter,
        processed_at=_PROCESSED_AT,
        provider_name="mock_search",
    )

    assert len(result.processed) == 1
    processed = result.processed[0]
    assert processed.status == "resolved"
    assert processed.adapter_invoked is True
    assert len(processed.evidence_ids) == 1
    assert len(adapter.calls) == 1
    assert sorted(adapter.calls[0]) == [
        "corpus_id",
        "network_grant",
        "request_id",
        "requested_at",
        "schema_version",
        "surface_form",
        "tenant_id",
    ]
    assert "source_refs" not in adapter.calls[0]
    assert "local_context_capsule" not in adapter.calls[0]

    evidence_row = conn.execute(
        """
        SELECT
            id,
            query_text,
            entity_kind,
            source_url,
            source_label,
            content_excerpt,
            fetch_tool_version,
            privacy_tier,
            raw_payload
        FROM entity_grounding_evidence
        """
    ).fetchone()
    assert evidence_row is not None
    assert evidence_row[0] == processed.evidence_ids[0]
    assert evidence_row[1:8] == (
        "Project Atlas",
        "unknown",
        "https://example.com/project-atlas",
        "Project Atlas public page",
        "Project Atlas is a public software project.",
        "entity_grounding_materialization.v1:mock_search",
        1,
    )
    assert evidence_row[8]["provider_row_id"] == "provider-row-1"

    response_row = conn.execute(
        """
        SELECT status, candidates
        FROM claim_grounding_responses
        WHERE request_id = (
            SELECT id
            FROM claim_grounding_requests
            WHERE request_payload->>'request_id' = %s
        )
        """,
        (request.request_id,),
    ).fetchone()
    assert response_row is not None
    assert response_row[0] == "resolved"
    assert response_row[1][0]["grounding_evidence_ids"] == [str(processed.evidence_ids[0])]
    assert response_row[1][0]["candidate_id"] != "provider-row-1"

    dispatch_statuses = conn.execute(
        """
        SELECT dispatch_status
        FROM claim_grounding_network_dispatches
        ORDER BY requested_at, attempt_number
        """
    ).fetchall()
    assert [row[0] for row in dispatch_statuses] == ["prepared", "succeeded"]

    link_row = conn.execute(
        """
        SELECT grounding_evidence_id
        FROM claim_grounding_links
        """
    ).fetchone()
    assert link_row == (processed.evidence_ids[0],)


def test_approved_grant_is_not_processed_twice(
    conn: psycopg.Connection,
) -> None:
    _record_request_and_approved_grant(conn)
    first_adapter = _MockSearchAdapter((_provider_row(rank=1),))

    first_result = process_approved_grounding_grants(
        conn,
        adapter=first_adapter,
        processed_at=_PROCESSED_AT,
        provider_name="mock_search",
    )

    second_adapter = _MockSearchAdapter((_provider_row(rank=2),))
    second_result = process_approved_grounding_grants(
        conn,
        adapter=second_adapter,
        processed_at=_PROCESSED_AT,
        provider_name="mock_search",
    )

    assert len(first_result.processed) == 1
    assert len(first_adapter.calls) == 1
    assert second_result.processed == ()
    assert second_adapter.calls == []
    assert conn.execute("SELECT count(*) FROM claim_grounding_network_dispatches").fetchone() == (
        2,
    )


@pytest.mark.parametrize("lifecycle", ["missing", "denied", "revoked", "expired"])
def test_non_latest_approved_grants_do_not_invoke_adapter(
    conn: psycopg.Connection,
    lifecycle: str,
) -> None:
    payload = _network_request_payload()
    if lifecycle == "expired":
        grant = payload["network_grant"]
        assert isinstance(grant, dict)
        grant["expires_at"] = "2026-05-19T11:59:59Z"
    request = ClaimGroundingRequest.from_json(payload)
    record_claim_grounding_request(
        conn,
        request,
        recorded_at=datetime(2026, 5, 19, 11, 0, tzinfo=UTC),
    )
    if lifecycle == "denied":
        record_claim_grounding_approved_grant(
            conn,
            request,
            recorded_at=datetime(2026, 5, 19, 11, 1, tzinfo=UTC),
        )
        record_claim_grounding_denied_grant(
            conn,
            request,
            denied_by="operator",
            reason="no longer approved",
            recorded_at=datetime(2026, 5, 19, 11, 2, tzinfo=UTC),
        )
    elif lifecycle == "revoked":
        record_claim_grounding_approved_grant(
            conn,
            request,
            recorded_at=datetime(2026, 5, 19, 11, 1, tzinfo=UTC),
        )
        record_claim_grounding_revoked_grant(
            conn,
            request,
            revoked_by="operator",
            reason="operator revoked",
            revoked_at=datetime(2026, 5, 19, 11, 2, tzinfo=UTC),
        )
    elif lifecycle == "expired":
        record_claim_grounding_approved_grant(
            conn,
            request,
            recorded_at=datetime(2026, 5, 19, 11, 1, tzinfo=UTC),
        )

    adapter = _MockSearchAdapter((_provider_row(rank=1),))

    result = process_approved_grounding_grants(
        conn,
        adapter=adapter,
        processed_at=_PROCESSED_AT,
    )

    assert result.processed == ()
    assert adapter.calls == []
    assert conn.execute(
        "SELECT count(*) FROM claim_grounding_network_dispatches"
    ).fetchone() == (0,)
    assert conn.execute("SELECT count(*) FROM entity_grounding_evidence").fetchone() == (0,)
    assert conn.execute("SELECT count(*) FROM claim_grounding_responses").fetchone() == (0,)


def test_duplicate_provider_rows_reuse_one_grounding_evidence_row(
    conn: psycopg.Connection,
) -> None:
    _record_request_and_approved_grant(conn)
    duplicate_row = _provider_row(rank=1)
    adapter = _MockSearchAdapter((duplicate_row, duplicate_row))

    result = process_approved_grounding_grants(
        conn,
        adapter=adapter,
        processed_at=_PROCESSED_AT,
    )

    assert len(result.processed) == 1
    assert result.processed[0].status == "resolved"
    assert len(result.processed[0].evidence_ids) == 1
    assert conn.execute("SELECT count(*) FROM entity_grounding_evidence").fetchone() == (1,)
    response = conn.execute("SELECT candidates FROM claim_grounding_responses").fetchone()
    assert response is not None
    assert len(response[0]) == 1


def test_entity_source_reference_appends_only_grounding_evidence_attach_action(
    conn: psycopg.Connection,
) -> None:
    entity_id = _insert_unknown_entity(conn)
    request = _insert_request_with_entity_payload(conn, entity_id=entity_id)
    record_claim_grounding_approved_grant(
        conn,
        request,
        recorded_at=datetime(2026, 5, 19, 11, 1, tzinfo=UTC),
    )
    adapter = _MockSearchAdapter((_provider_row(rank=1),))

    result = process_approved_grounding_grants(
        conn,
        adapter=adapter,
        processed_at=_PROCESSED_AT,
    )

    evidence_id = result.processed[0].evidence_ids[0]
    action = conn.execute(
        """
        SELECT
            action_kind,
            entity_id,
            related_entity_id,
            grounding_evidence_id,
            alias_text,
            external_id_kind,
            external_id_value,
            actor,
            raw_payload
        FROM entity_identity_review_actions
        """
    ).fetchone()
    assert action is not None
    assert action[:8] == (
        "grounding_evidence_attach",
        entity_id,
        None,
        evidence_id,
        None,
        None,
        None,
        "grounding-broker",
    )
    assert action[8]["request_id"] == request.request_id
    assert action[8]["grant_id"] == "grant-materialization-001"
    assert action[8]["rank"] == 1


def test_entity_source_reference_keeps_approved_query_privacy_tier(
    conn: psycopg.Connection,
) -> None:
    entity_id = _insert_unknown_entity(conn, privacy_tier=4)
    request_payload = _network_request_payload()
    grant = request_payload["network_grant"]
    assert isinstance(grant, dict)
    grant["query_privacy_tier"] = 4
    request_payload["privacy_tier_ceiling"] = 4
    _insert_request_with_entity_payload(
        conn,
        entity_id=entity_id,
        request_payload=request_payload,
    )
    record_claim_grounding_approved_grant(
        conn,
        ClaimGroundingRequest.from_json(
            {key: value for key, value in request_payload.items() if key != "entity_id"}
        ),
        recorded_at=datetime(2026, 5, 19, 11, 1, tzinfo=UTC),
    )
    adapter = _MockSearchAdapter((_provider_row(rank=1),))

    result = process_approved_grounding_grants(
        conn,
        adapter=adapter,
        processed_at=_PROCESSED_AT,
    )

    assert result.processed[0].status == "resolved"
    tiers = conn.execute(
        """
        SELECT e.privacy_tier, a.privacy_tier
        FROM entity_grounding_evidence e
        JOIN entity_identity_review_actions a
          ON a.grounding_evidence_id = e.id
        WHERE a.entity_id = %s
        """,
        (entity_id,),
    ).fetchone()
    assert tiers == (4, 4)


@pytest.mark.parametrize(
    "url",
    [
        "http://localhost/project-atlas",
        "http://search.localhost/project-atlas",
        "http://127.0.0.1/project-atlas",
        "http://10.0.0.8/project-atlas",
        "http://169.254.0.1/project-atlas",
        "http://[::1]/project-atlas",
    ],
)
def test_provider_result_private_urls_are_not_materialized(
    conn: psycopg.Connection,
    url: str,
) -> None:
    _record_request_and_approved_grant(conn)
    poisoned_row = ClaimGroundingNetworkResultRow(
        row_id="poisoned-provider-row",
        title="Project Atlas",
        url=url,
        source_label="Poisoned provider result",
        excerpt="Project Atlas poisoned result.",
        content_hash="c" * 64,
        rank=1,
    )
    adapter = _MockSearchAdapter((poisoned_row,))

    result = process_approved_grounding_grants(
        conn,
        adapter=adapter,
        processed_at=_PROCESSED_AT,
    )

    assert len(result.processed) == 1
    assert result.processed[0].status == "not_found"
    assert result.processed[0].evidence_ids == ()
    assert conn.execute("SELECT count(*) FROM entity_grounding_evidence").fetchone() == (0,)
    assert conn.execute("SELECT status FROM claim_grounding_responses").fetchone() == (
        "not_found",
    )


def test_provider_failure_records_sanitized_failure_without_evidence(
    conn: psycopg.Connection,
) -> None:
    _record_request_and_approved_grant(conn)
    adapter = _MockSearchAdapter((), error=RuntimeError("secret-key private chat sentence"))

    result = process_approved_grounding_grants(
        conn,
        adapter=adapter,
        processed_at=_PROCESSED_AT,
    )

    assert len(result.processed) == 1
    assert result.processed[0].status == "provider_fetch_error"
    assert adapter.calls
    assert conn.execute("SELECT count(*) FROM entity_grounding_evidence").fetchone() == (0,)

    dispatch_rows = conn.execute(
        """
        SELECT dispatch_status, denial_reason, dispatch_payload, result_metadata
        FROM claim_grounding_network_dispatches
        ORDER BY attempt_number
        """
    ).fetchall()
    assert [row[0] for row in dispatch_rows] == ["prepared", "failed"]
    serialized_dispatch = repr(dispatch_rows)
    assert "secret-key" not in serialized_dispatch
    assert "private chat sentence" not in serialized_dispatch

    response = conn.execute(
        """
        SELECT status, omissions, response_payload
        FROM claim_grounding_responses
        """
    ).fetchone()
    assert response is not None
    assert response[0] == "error"
    serialized_response = repr(response)
    assert "secret-key" not in serialized_response
    assert "private chat sentence" not in serialized_response


def _record_request_and_approved_grant(conn: psycopg.Connection) -> ClaimGroundingRequest:
    request = ClaimGroundingRequest.from_json(_network_request_payload())
    record_claim_grounding_request(
        conn,
        request,
        recorded_at=datetime(2026, 5, 19, 11, 0, tzinfo=UTC),
    )
    record_claim_grounding_approved_grant(
        conn,
        request,
        recorded_at=datetime(2026, 5, 19, 11, 1, tzinfo=UTC),
    )
    return request


def _insert_request_with_entity_payload(
    conn: psycopg.Connection,
    *,
    entity_id: UUID,
    request_payload: dict[str, object] | None = None,
) -> ClaimGroundingRequest:
    if request_payload is None:
        request_payload = _network_request_payload()
    request_payload["entity_id"] = str(entity_id)
    request = ClaimGroundingRequest.from_json(
        {
            key: value
            for key, value in request_payload.items()
            if key != "entity_id"
        }
    )
    conn.execute(
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
            %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s::jsonb, %s, %s::jsonb,
            %s, %s, %s::jsonb, %s, %s::timestamptz, %s
        )
        """,
        (
            request.tenant_id,
            request.corpus_id,
            request.schema_version,
            request.extraction_prompt_version,
            request.extraction_model_version,
            request.surface_form,
            request.mention_role,
            list(request.candidate_entity_kinds),
            _json(request.source_refs[0].to_json(), array=True),
            _json(request.local_context_capsule.to_json()),
            list(request.allowed_modes),
            _json(request.network_grant.to_json() if request.network_grant is not None else {}),
            request.privacy_tier_ceiling,
            list(request.sensitivity_ceiling),
            _json(request_payload),
            request.extraction_run_id,
            request.requested_at,
            datetime(2026, 5, 19, 11, 0, tzinfo=UTC),
        ),
    )
    return request


def _network_request_payload() -> dict[str, object]:
    return {
        "schema_version": CLAIM_GROUNDING_REQUEST_SCHEMA_VERSION,
        "request_id": "req-materialization-001",
        "tenant_id": "personal",
        "corpus_id": "personal",
        "extraction_run_id": "run-materialization-001",
        "extraction_prompt_version": "extractor.v-test",
        "extraction_model_version": "local-test-model",
        "surface_form": "Project Atlas",
        "mention_role": "subject",
        "candidate_entity_kinds": ["product", "organization"],
        "source_refs": [
            {
                "target_table": "messages",
                "target_id": "message-materialization-001",
                "span_hash": "a" * 64,
                "span_start": 12,
                "span_end": 25,
            }
        ],
        "local_context_capsule": {"mode": "none", "text": None},
        "allowed_modes": ["local_lookup", "network_fetch"],
        "network_grant": {
            "grant_id": "grant-materialization-001",
            "granted_by": "operator",
            "granted_at": "2026-05-19T11:00:00Z",
            "expires_at": None,
            "purpose": "entity_grounding",
            "search_query": "Project Atlas",
            "query_text_class": "entity_surface_form",
            "query_privacy_tier": 1,
            "allowed_network_targets": ["internet_search"],
        },
        "privacy_tier_ceiling": 1,
        "sensitivity_ceiling": ["routine_project"],
        "requested_at": "2026-05-19T11:00:00Z",
    }


def _provider_row(*, rank: int) -> ClaimGroundingNetworkResultRow:
    return ClaimGroundingNetworkResultRow(
        row_id=f"provider-row-{rank}",
        title="Project Atlas",
        url="https://example.com/project-atlas",
        source_label="Project Atlas public page",
        excerpt="Project Atlas is a public software project.",
        content_hash="b" * 64,
        rank=rank,
    )


def _insert_unknown_entity(conn: psycopg.Connection, *, privacy_tier: int = 1) -> UUID:
    row = conn.execute(
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
            'unknown',
            'Project Atlas',
            %s,
            'active',
            0.7,
            %s,
            '{}',
            %s,
            %s,
            'deterministic',
            'entity-grounding-materialization-test',
            '{}'::jsonb
        )
        RETURNING id
        """,
        (
            f"unknown:project-atlas:{uuid4()}",
            [uuid4()],
            [uuid4()],
            privacy_tier,
        ),
    ).fetchone()
    assert row is not None
    return row[0]


def _json(payload: Mapping[str, object], *, array: bool = False) -> str:
    import json

    value: object = [payload] if array else payload
    return json.dumps(value, sort_keys=True)
