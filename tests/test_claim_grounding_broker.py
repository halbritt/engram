from __future__ import annotations

import hashlib
import socket
from collections.abc import Mapping

import psycopg
import pytest

from engram.claim_grounding import (
    CLAIM_GROUNDING_RESPONSE_SCHEMA_VERSION,
    ClaimGroundingSchemaError,
)
from engram.claim_grounding_broker import (
    ClaimGroundingBroker,
    DeferredClaimGroundingDispatch,
    handle_claim_grounding_request,
)
from engram.claim_grounding_runtime import (
    ClaimGroundingPersistenceConflict,
    ClaimGroundingRuntimeError,
    record_claim_grounding_approved_grant,
    record_claim_grounding_draft_grant,
    record_claim_grounding_request,
)


def test_claim_grounding_broker_resolves_local_hit_without_adapter(
    conn: psycopg.Connection,
) -> None:
    _insert_grounding_evidence(conn, query_text="Project Atlas")
    broker = ClaimGroundingBroker(conn=conn, created_at="2026-05-18T00:00:01Z")

    response = broker.handle(_request_payload())

    assert response.status == "resolved"
    assert response.mode == "local_lookup"
    assert response.network_fetch == "not_requested"
    assert response.candidates[0].canonical_label == "Project Atlas"
    assert broker.deferred_dispatches == []


def test_claim_grounding_broker_records_deferred_granted_miss_without_adapter(
    conn: psycopg.Connection,
) -> None:
    deferred: list[DeferredClaimGroundingDispatch] = []

    response = handle_claim_grounding_request(
        conn,
        _network_request_payload("Missing Product"),
        deferred_dispatches=deferred,
        created_at="2026-05-18T00:00:01Z",
    )

    assert response.status == "deferred"
    assert response.network_fetch == "unsupported"
    assert response.candidates == ()
    assert [item.request_id for item in deferred] == ["req-001"]
    assert deferred[0].dispatch_payload == {
        "schema_version": "claim_grounding.network_dispatch.v1",
        "request_id": "req-001",
        "tenant_id": "personal",
        "corpus_id": "personal",
        "surface_form": "Missing Product",
        "network_grant": _network_grant("Missing Product"),
        "requested_at": "2026-05-18T00:00:00Z",
    }


def test_claim_grounding_broker_can_persist_deferred_runtime_sidecars(
    conn: psycopg.Connection,
) -> None:
    response = handle_claim_grounding_request(
        conn,
        _network_request_payload("Missing Product"),
        created_at="2026-05-18T00:00:01Z",
        persist_sidecars=True,
    )

    assert response.status == "deferred"
    request_count = conn.execute("SELECT count(*) FROM claim_grounding_requests").fetchone()
    grant_count = conn.execute("SELECT count(*) FROM claim_grounding_grants").fetchone()
    use_count = conn.execute("SELECT count(*) FROM claim_grounding_grant_uses").fetchone()
    response_status = conn.execute("SELECT status FROM claim_grounding_responses").fetchone()
    assert request_count is not None
    assert grant_count is not None
    assert use_count is not None
    assert response_status is not None
    assert request_count[0] == 1
    assert grant_count[0] == 1
    assert use_count[0] == 1
    assert response_status[0] == "deferred"
    dispatch_row = conn.execute(
        """
        SELECT dispatch_status, denial_reason, dispatch_payload
        FROM claim_grounding_network_dispatches
        """
    ).fetchone()
    assert dispatch_row is not None
    assert dispatch_row[0] == "skipped"
    assert dispatch_row[1] == "network_adapter_unavailable"
    assert dispatch_row[2]["schema_version"] == "claim_grounding.network_dispatch.v1"
    assert "source_refs" not in dispatch_row[2]


def test_claim_grounding_broker_has_no_default_live_network_access(
    conn: psycopg.Connection,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_socket(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("default claim-grounding broker must not open sockets")

    monkeypatch.setattr(socket, "create_connection", fail_socket)
    broker = ClaimGroundingBroker(conn=conn, created_at="2026-05-18T00:00:01Z")

    response = broker.handle(_network_request_payload("Missing Product"))

    assert response.status == "deferred"
    assert response.network_fetch == "unsupported"
    assert len(broker.deferred_dispatches) == 1


def test_claim_grounding_broker_rejects_live_adapter_without_persisted_sidecars(
    conn: psycopg.Connection,
) -> None:
    def fake_adapter(dispatch_payload: Mapping[str, object]) -> Mapping[str, object]:
        raise AssertionError("adapter must not be invoked without persisted sidecars")

    with pytest.raises(ClaimGroundingRuntimeError, match="persisted sidecars"):
        handle_claim_grounding_request(
            conn,
            _network_request_payload("Missing Product"),
            network_adapter=fake_adapter,
        )


def test_claim_grounding_broker_uses_injected_adapter_after_persisted_grant(
    conn: psycopg.Connection,
) -> None:
    seen_dispatches: list[Mapping[str, object]] = []
    request_payload = _network_request_payload("Missing Product")
    _persist_approved_grant(conn, request_payload)

    def fake_adapter(dispatch_payload: Mapping[str, object]) -> Mapping[str, object]:
        seen_dispatches.append(dispatch_payload)
        return _network_response_payload(str(dispatch_payload["request_id"]))

    response = handle_claim_grounding_request(
        conn,
        request_payload,
        network_adapter=fake_adapter,
        persist_sidecars=True,
    )

    assert response.status == "resolved"
    assert response.mode == "network_fetch"
    assert response.network_fetch == "performed_by_grounding_broker"
    assert response.candidates[0].source_label == "Injected fake network fixture"
    assert len(seen_dispatches) == 1
    assert "source_refs" not in seen_dispatches[0]
    assert "local_context_capsule" not in seen_dispatches[0]


def test_claim_grounding_broker_rejects_unapproved_grant_before_adapter(
    conn: psycopg.Connection,
) -> None:
    request_payload = _network_request_payload("Missing Product")
    record_claim_grounding_request(conn, request_payload)
    record_claim_grounding_draft_grant(conn, request_payload)

    def fake_adapter(dispatch_payload: Mapping[str, object]) -> Mapping[str, object]:
        raise AssertionError("adapter must not be invoked for draft grants")

    with pytest.raises(ClaimGroundingPersistenceConflict, match="latest status is \"draft\""):
        handle_claim_grounding_request(
            conn,
            request_payload,
            network_adapter=fake_adapter,
            persist_sidecars=True,
        )


def test_claim_grounding_broker_rejects_adapter_request_id_drift(
    conn: psycopg.Connection,
) -> None:
    request_payload = _network_request_payload("Missing Product")
    _persist_approved_grant(conn, request_payload)

    def fake_adapter(dispatch_payload: Mapping[str, object]) -> Mapping[str, object]:
        assert dispatch_payload["schema_version"] == "claim_grounding.network_dispatch.v1"
        return _network_response_payload("wrong-request")

    broker = ClaimGroundingBroker(
        conn=conn,
        network_adapter=fake_adapter,
        persist_sidecars=True,
    )

    with pytest.raises(ClaimGroundingSchemaError, match="request_id"):
        broker.handle(request_payload)


def _request_payload() -> dict[str, object]:
    return {
        "schema_version": "claim_grounding.request.v1",
        "request_id": "req-001",
        "tenant_id": "personal",
        "corpus_id": "personal",
        "extraction_run_id": "run-001",
        "extraction_prompt_version": "extractor.v-test",
        "extraction_model_version": "local-test-model",
        "surface_form": "Project Atlas",
        "mention_role": "subject",
        "candidate_entity_kinds": ["product", "organization"],
        "source_refs": [
            {
                "target_table": "messages",
                "target_id": "message-001",
                "span_hash": "a" * 64,
                "span_start": 12,
                "span_end": 25,
            }
        ],
        "local_context_capsule": {"mode": "none", "text": None},
        "allowed_modes": ["local_lookup"],
        "privacy_tier_ceiling": 1,
        "sensitivity_ceiling": ["routine_project"],
        "requested_at": "2026-05-18T00:00:00Z",
    }


def _network_request_payload(surface_form: str) -> dict[str, object]:
    payload = _request_payload()
    payload["surface_form"] = surface_form
    payload["allowed_modes"] = ["local_lookup", "network_fetch"]
    payload["network_grant"] = _network_grant(surface_form)
    return payload


def _network_grant(search_query: str) -> dict[str, object]:
    return {
        "grant_id": "grant-001",
        "granted_by": "operator",
        "granted_at": "2026-05-18T00:00:00Z",
        "expires_at": None,
        "purpose": "entity_grounding",
        "search_query": search_query,
        "query_text_class": "entity_surface_form",
        "query_privacy_tier": 1,
        "allowed_network_targets": ["internet_search"],
    }


def _network_response_payload(request_id: str) -> dict[str, object]:
    content = "Missing Product is a public fixture resolved by an injected adapter."
    return {
        "schema_version": CLAIM_GROUNDING_RESPONSE_SCHEMA_VERSION,
        "request_id": request_id,
        "status": "resolved",
        "mode": "network_fetch",
        "network_fetch": "performed_by_grounding_broker",
        "candidates": [
            {
                "candidate_id": "fake-grounding-001",
                "entity_kind": "product",
                "canonical_label": "Missing Product",
                "external_ids": [],
                "grounding_evidence_ids": ["fake-grounding-001"],
                "source_url": "https://example.invalid/missing-product",
                "source_label": "Injected fake network fixture",
                "content_hash": hashlib.sha256(content.encode("utf-8")).hexdigest(),
                "content_excerpt": content,
                "confidence": 0.9,
                "stability": "stable_public_entity",
                "ambiguity_reasons": [],
            }
        ],
        "omissions": [],
        "broker_version": "claim_grounding.network_broker.fake",
        "dataset_snapshots": [],
        "created_at": "2026-05-18T00:00:02Z",
    }


def _persist_approved_grant(
    conn: psycopg.Connection,
    request_payload: Mapping[str, object],
) -> None:
    record_claim_grounding_request(conn, request_payload)
    record_claim_grounding_approved_grant(conn, request_payload)


def _insert_grounding_evidence(conn: psycopg.Connection, *, query_text: str) -> None:
    body = f"{query_text} is a local public grounding fixture."
    conn.execute(
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
            extractor_version
        )
        VALUES (
            'personal',
            'personal',
            %s,
            'product',
            'https://example.invalid/project-atlas',
            'Local broker fixture',
            %s,
            %s,
            '2026-05-18T00:00:00Z',
            'manual.local.test',
            'none'
        )
        """,
        (query_text, hashlib.sha256(body.encode("utf-8")).hexdigest(), body),
    )
