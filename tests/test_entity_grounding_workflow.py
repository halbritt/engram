from __future__ import annotations

import json
import os
import socket
from collections.abc import Iterator
from datetime import UTC, datetime
from uuid import UUID, uuid4

import psycopg
import pytest

from engram import entity_grounding_workflow as workflow
from engram.claim_grounding import ClaimGroundingRequest

REQUESTED_AT = datetime(2026, 5, 19, 10, 0, 0, tzinfo=UTC)
TEST_DATABASE_URL = os.environ.get("ENGRAM_TEST_DATABASE_URL")


@pytest.fixture()
def conn() -> Iterator[psycopg.Connection]:
    database_url = TEST_DATABASE_URL
    if not database_url:
        pytest.skip("ENGRAM_TEST_DATABASE_URL is required for database tests")
    assert database_url is not None
    with psycopg.connect(database_url, autocommit=True) as admin:
        _reset_minimal_entity_grounding_schema(admin)
    with psycopg.connect(database_url) as connection:
        connection.autocommit = True
        yield connection


def test_draft_batch_selects_active_unknown_entities_deterministically(
    conn: psycopg.Connection,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    call_order: list[str] = []

    def miss_lookup(
        connection: psycopg.Connection,
        *,
        query_text: str,
        tenant_id: str,
        corpus_id: str,
        limit: int,
    ) -> list[dict[str, object]]:
        assert connection is conn
        assert tenant_id == "personal"
        assert corpus_id == "personal"
        assert limit == 5
        call_order.append(query_text)
        return []

    monkeypatch.setattr(workflow, "search_grounding_evidence", miss_lookup)
    _insert_entity(
        conn,
        canonical_text="Third",
        canonical_key="subject:third",
        confidence=0.99,
        privacy_tier=2,
        created_at=datetime(2026, 5, 19, 9, 0, 0, tzinfo=UTC),
    )
    _insert_entity(
        conn,
        canonical_text="First",
        canonical_key="subject:first",
        confidence=0.80,
        privacy_tier=1,
        created_at=datetime(2026, 5, 19, 9, 1, 0, tzinfo=UTC),
    )
    _insert_entity(
        conn,
        canonical_text="Second",
        canonical_key="subject:second",
        confidence=0.90,
        privacy_tier=1,
        created_at=datetime(2026, 5, 19, 9, 2, 0, tzinfo=UTC),
    )
    _insert_entity(
        conn,
        canonical_text="Ignored Known",
        canonical_key="subject:ignored-known",
        entity_kind="tool",
    )
    _insert_entity(
        conn,
        canonical_text="Ignored Tenant",
        canonical_key="subject:ignored-tenant",
        tenant_id="other",
        corpus_id="personal",
    )

    summary = workflow.draft_entity_grounding_batch(
        conn,
        tenant_id="personal",
        corpus_id="personal",
        limit=10,
        requested_at=REQUESTED_AT,
    )

    assert call_order == ["Second", "First", "Third"]
    assert summary.selected == 3
    assert summary.drafts_created == 3


def test_local_hit_attaches_grounding_evidence_without_network_grant(
    conn: psycopg.Connection,
) -> None:
    entity_id = _insert_entity(conn, canonical_text="OpenAI Codex", canonical_key="object:codex")
    evidence_id = _insert_grounding_evidence(conn, query_text="OpenAI Codex")

    summary = workflow.draft_entity_grounding_batch(
        conn,
        tenant_id="personal",
        corpus_id="personal",
        limit=10,
        requested_at=REQUESTED_AT,
    )

    assert summary.local_hits == 1
    assert summary.local_actions_created == 1
    assert summary.drafts_created == 0
    assert conn.execute("SELECT count(*) FROM claim_grounding_requests").fetchone() == (0,)
    assert conn.execute("SELECT count(*) FROM claim_grounding_grants").fetchone() == (0,)
    action = conn.execute(
        """
        SELECT
            action_kind,
            entity_id::text,
            grounding_evidence_id::text,
            actor,
            raw_payload
        FROM entity_identity_review_actions
        """
    ).fetchone()
    assert action is not None
    assert action[0:4] == (
        "grounding_evidence_attach",
        entity_id,
        str(evidence_id),
        workflow.ENTITY_GROUNDING_BATCH_ACTOR,
    )
    assert action[4]["entity_grounding_workflow"]["source_claim_ids"]
    assert "network_grant" not in json.dumps(action[4], sort_keys=True)


def test_network_miss_persists_valid_request_and_draft_grant_from_claim_refs(
    conn: psycopg.Connection,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(workflow, "search_grounding_evidence", _always_miss)
    entity_id = _insert_entity(
        conn,
        canonical_text="Tartine",
        canonical_key="object:tartine",
        source_claim_ids=(str(uuid4()), str(uuid4())),
        raw_payload={"raw_text": "private chat sentence that must not leak"},
    )

    summary = workflow.draft_entity_grounding_batch(
        conn,
        tenant_id="personal",
        corpus_id="personal",
        limit=10,
        requested_at=REQUESTED_AT,
    )

    assert summary.drafts_created == 1
    request_row = conn.execute(
        """
        SELECT
            id::text,
            extraction_run_id,
            surface_form,
            source_refs,
            local_context_capsule,
            allowed_modes,
            network_grant,
            request_payload
        FROM claim_grounding_requests
        """
    ).fetchone()
    assert request_row is not None
    request_payload = request_row[7]
    parsed_request = ClaimGroundingRequest.from_json(request_payload)
    assert parsed_request.request_id == request_row[0]
    assert request_row[1].startswith("entity_grounding_batch.v1:")
    assert request_row[2] == "Tartine"
    assert request_row[3] == request_payload["source_refs"]
    assert {ref["target_table"] for ref in request_row[3]} == {"claims"}
    assert all(ref["target_id"] != entity_id for ref in request_row[3])
    assert request_row[4] == {"mode": "none", "text": None}
    assert request_row[5] == ["local_lookup", "network_fetch"]
    assert request_row[6]["search_query"] == "Tartine"
    assert request_row[6]["query_text_class"] == "entity_surface_form"

    grant_row = conn.execute(
        """
        SELECT
            id::text,
            request_id::text,
            grant_status,
            surface_form,
            search_query,
            query_text_class,
            allowed_network_targets,
            granted_by,
            granted_at,
            grant_payload
        FROM claim_grounding_grants
        """
    ).fetchone()
    assert grant_row is not None
    assert UUID(grant_row[0])
    assert grant_row[1] == request_row[0]
    assert grant_row[2:7] == (
        "draft",
        "Tartine",
        "Tartine",
        "entity_surface_form",
        ["internet_search"],
    )
    assert grant_row[7] is None
    assert grant_row[8] is None
    assert grant_row[9]["grant_id"] == request_payload["network_grant"]["grant_id"]
    assert grant_row[9]["entity_grounding_workflow"]["entity_id"] == entity_id

    persisted_json = json.dumps(
        {"request": request_payload, "grant": grant_row[9]},
        sort_keys=True,
    )
    assert "private chat sentence" not in persisted_json
    assert "raw_text" not in persisted_json
    assert '"target_table": "entities"' not in persisted_json


def test_network_miss_rerun_reuses_deterministic_request_and_grant(
    conn: psycopg.Connection,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(workflow, "search_grounding_evidence", _always_miss)
    _insert_entity(conn, canonical_text="Project Atlas", canonical_key="project:atlas")

    first = workflow.draft_entity_grounding_batch(
        conn,
        tenant_id="personal",
        corpus_id="personal",
        limit=10,
        requested_at=REQUESTED_AT,
    )
    second = workflow.draft_entity_grounding_batch(
        conn,
        tenant_id="personal",
        corpus_id="personal",
        limit=10,
        requested_at=datetime(2026, 5, 19, 11, 0, 0, tzinfo=UTC),
    )

    assert first.drafts_created == 1
    assert second.drafts_created == 0
    assert second.drafts_reused == 1
    assert conn.execute("SELECT count(*) FROM claim_grounding_requests").fetchone() == (1,)
    assert conn.execute("SELECT count(*) FROM claim_grounding_grants").fetchone() == (1,)
    ids = conn.execute(
        """
        SELECT
            r.id::text,
            g.id::text,
            r.request_payload->>'request_id',
            g.grant_payload->>'grant_id'
        FROM claim_grounding_requests r
        JOIN claim_grounding_grants g ON g.request_id = r.id
        """
    ).fetchone()
    assert ids is not None
    assert ids[0] == ids[2]
    assert ids[1] == ids[3]


def test_draft_workflow_opens_no_sockets_or_network_adapters(
    conn: psycopg.Connection,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _insert_entity(conn, canonical_text="No Network Entity", canonical_key="subject:no-network")
    monkeypatch.setattr(workflow, "search_grounding_evidence", _always_miss)

    def fail_socket(*args: object, **kwargs: object) -> socket.socket:
        raise AssertionError("draft workflow must not open sockets")

    monkeypatch.setattr(socket, "socket", fail_socket)

    summary = workflow.draft_entity_grounding_batch(
        conn,
        tenant_id="personal",
        corpus_id="personal",
        limit=10,
        requested_at=REQUESTED_AT,
    )

    assert summary.drafts_created == 1


def _always_miss(
    connection: psycopg.Connection,
    *,
    query_text: str,
    tenant_id: str,
    corpus_id: str,
    limit: int,
) -> list[dict[str, object]]:
    return []


def _insert_entity(
    conn: psycopg.Connection,
    *,
    canonical_text: str,
    canonical_key: str,
    tenant_id: str = "personal",
    corpus_id: str = "personal",
    entity_kind: str = "unknown",
    confidence: float = 0.8,
    privacy_tier: int = 1,
    created_at: datetime = REQUESTED_AT,
    source_claim_ids: tuple[str, ...] | None = None,
    raw_payload: dict[str, object] | None = None,
) -> str:
    entity_id = str(uuid4())
    claim_ids = source_claim_ids or (str(uuid4()),)
    row = conn.execute(
        """
        INSERT INTO entities (
            id,
            tenant_id,
            corpus_id,
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
            created_at,
            raw_payload
        )
        VALUES (
            %s, %s, %s, %s, %s, %s, 'active', %s, %s::uuid[], %s::uuid[], %s::uuid[],
            %s, 'deterministic', 'test.v1', %s, %s::jsonb
        )
        RETURNING id::text
        """,
        (
            entity_id,
            tenant_id,
            corpus_id,
            entity_kind,
            canonical_text,
            canonical_key,
            confidence,
            [str(uuid4())],
            list(claim_ids),
            [str(uuid4())],
            privacy_tier,
            created_at,
            json.dumps(raw_payload or {"test": "entity-grounding-workflow"}),
        ),
    ).fetchone()
    assert row is not None
    return str(row[0])


def _insert_grounding_evidence(
    conn: psycopg.Connection,
    *,
    query_text: str,
) -> UUID:
    evidence_id = uuid4()
    row = conn.execute(
        """
        INSERT INTO entity_grounding_evidence (
            id,
            tenant_id,
            corpus_id,
            query_text,
            entity_kind,
            source_label,
            content_hash,
            content_excerpt,
            privacy_tier
        )
        VALUES (
            %s,
            'personal',
            'personal',
            %s,
            'tool',
            'local fixture',
            repeat('a', 64),
            'OpenAI Codex is represented in this local public grounding fixture.',
            1
        )
        RETURNING id
        """,
        (evidence_id, query_text),
    ).fetchone()
    assert row is not None
    return row[0]


def _reset_minimal_entity_grounding_schema(conn: psycopg.Connection) -> None:
    conn.execute(
        """
        DROP TABLE IF EXISTS
            claim_grounding_grants,
            claim_grounding_requests,
            entity_identity_review_actions,
            entity_grounding_evidence,
            entities
        CASCADE
        """
    )
    conn.execute(
        """
        CREATE TABLE entities (
            id UUID PRIMARY KEY,
            tenant_id TEXT NOT NULL DEFAULT 'personal',
            corpus_id TEXT NOT NULL DEFAULT 'personal',
            entity_kind TEXT NOT NULL CHECK (
                entity_kind IN (
                    'person', 'project', 'organization', 'place', 'tool', 'concept', 'unknown'
                )
            ),
            canonical_text TEXT NOT NULL CHECK (btrim(canonical_text) <> ''),
            canonical_key TEXT NOT NULL CHECK (btrim(canonical_key) <> ''),
            status TEXT NOT NULL CHECK (status IN ('active', 'merged', 'rejected')),
            confidence FLOAT NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
            source_belief_ids UUID[] NOT NULL CHECK (cardinality(source_belief_ids) > 0),
            source_claim_ids UUID[] NOT NULL DEFAULT '{}'::uuid[],
            evidence_ids UUID[] NOT NULL CHECK (cardinality(evidence_ids) > 0),
            privacy_tier INT NOT NULL,
            resolution_method TEXT NOT NULL,
            resolution_version TEXT NOT NULL,
            created_at TIMESTAMPTZ NOT NULL,
            raw_payload JSONB NOT NULL DEFAULT '{}'::jsonb
        );

        CREATE TABLE entity_grounding_evidence (
            id UUID PRIMARY KEY,
            tenant_id TEXT NOT NULL DEFAULT 'personal',
            corpus_id TEXT NOT NULL DEFAULT 'personal',
            query_text TEXT NOT NULL,
            entity_kind TEXT NOT NULL DEFAULT 'unknown',
            source_url TEXT NULL,
            source_label TEXT NULL,
            content_hash TEXT NOT NULL CHECK (content_hash ~ '^[0-9a-f]{64}$'),
            content_excerpt TEXT NOT NULL,
            fetched_at TIMESTAMPTZ NULL,
            fetch_tool_version TEXT NOT NULL DEFAULT 'manual.local.v1',
            extractor_version TEXT NOT NULL DEFAULT 'none',
            privacy_tier INT NOT NULL DEFAULT 1,
            sensitivity_class TEXT NOT NULL DEFAULT 'routine_project',
            raw_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );

        CREATE TABLE entity_identity_review_actions (
            id UUID PRIMARY KEY,
            tenant_id TEXT NOT NULL DEFAULT 'personal',
            corpus_id TEXT NOT NULL DEFAULT 'personal',
            action_kind TEXT NOT NULL CHECK (action_kind IN ('grounding_evidence_attach')),
            entity_id UUID NULL REFERENCES entities(id),
            grounding_evidence_id UUID NULL REFERENCES entity_grounding_evidence(id),
            actor TEXT NOT NULL,
            rationale TEXT NULL,
            privacy_tier INT NOT NULL DEFAULT 1,
            raw_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );

        CREATE TABLE claim_grounding_requests (
            id UUID PRIMARY KEY,
            tenant_id TEXT NOT NULL DEFAULT 'personal',
            corpus_id TEXT NOT NULL DEFAULT 'personal',
            schema_version TEXT NOT NULL DEFAULT 'claim_grounding.request.v1'
                CHECK (schema_version = 'claim_grounding.request.v1'),
            extraction_run_id TEXT NULL,
            extraction_prompt_version TEXT NOT NULL,
            extraction_model_version TEXT NOT NULL,
            surface_form TEXT NOT NULL,
            mention_role TEXT NOT NULL CHECK (mention_role IN ('subject', 'object', 'context')),
            candidate_entity_kinds TEXT[] NOT NULL CHECK (cardinality(candidate_entity_kinds) > 0),
            source_refs JSONB NOT NULL DEFAULT '[]'::jsonb,
            local_context_capsule JSONB NOT NULL DEFAULT '{"mode":"none","text":null}'::jsonb,
            allowed_modes TEXT[] NOT NULL DEFAULT ARRAY['local_lookup']::TEXT[],
            network_grant JSONB NULL,
            privacy_tier_ceiling INT NOT NULL DEFAULT 1,
            sensitivity_ceiling TEXT[] NOT NULL DEFAULT ARRAY['routine_project']::TEXT[],
            request_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
            requested_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );

        CREATE TABLE claim_grounding_grants (
            id UUID PRIMARY KEY,
            tenant_id TEXT NOT NULL DEFAULT 'personal',
            corpus_id TEXT NOT NULL DEFAULT 'personal',
            request_id UUID NULL REFERENCES claim_grounding_requests(id),
            schema_version TEXT NOT NULL DEFAULT 'claim_grounding.grant.v1',
            grant_status TEXT NOT NULL CHECK (
                grant_status IN ('draft', 'approved', 'denied', 'revoked', 'expired')
            ),
            grant_purpose TEXT NOT NULL CHECK (grant_purpose IN ('entity_grounding')),
            target_mode TEXT NOT NULL CHECK (target_mode IN ('network_fetch')),
            surface_form TEXT NOT NULL,
            search_query TEXT NOT NULL,
            query_text_class TEXT NOT NULL,
            query_privacy_tier INT NOT NULL,
            allowed_network_targets TEXT[] NOT NULL,
            granted_by TEXT NULL,
            granted_at TIMESTAMPTZ NULL,
            expires_at TIMESTAMPTZ NULL,
            revoked_at TIMESTAMPTZ NULL,
            grant_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        """
    )
