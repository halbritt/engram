from __future__ import annotations

import os
from collections.abc import Iterator
from datetime import UTC, datetime
from uuid import UUID, uuid4

import psycopg
import pytest

from engram.claim_grounding import (
    CLAIM_GROUNDING_REQUEST_SCHEMA_VERSION,
    CLAIM_GROUNDING_RESPONSE_SCHEMA_VERSION,
    ClaimGroundingRequest,
    ClaimGroundingResponse,
)
from engram.claim_grounding_runtime import (
    ClaimGroundingPersistenceConflict,
    ClaimGroundingPersistenceSchemaMissing,
    record_claim_grounding_approved_grant,
    record_claim_grounding_denied_grant,
    record_claim_grounding_draft_grant,
    record_claim_grounding_grant,
    record_claim_grounding_grant_use,
    record_claim_grounding_links,
    record_claim_grounding_network_dispatch_attempt,
    record_claim_grounding_request,
    record_claim_grounding_response,
    record_claim_grounding_revoked_grant,
    verify_claim_grounding_grant_for_dispatch,
)
from engram.migrations import migrate

TEST_DATABASE_URL = os.environ.get("ENGRAM_TEST_DATABASE_URL")


@pytest.fixture()
def conn() -> Iterator[psycopg.Connection]:
    if not TEST_DATABASE_URL:
        pytest.skip("ENGRAM_TEST_DATABASE_URL is required for database tests")
    with psycopg.connect(TEST_DATABASE_URL, autocommit=True) as admin:
        _drop_public_non_extension_objects(admin)
    with psycopg.connect(TEST_DATABASE_URL) as connection:
        migrate(connection)
        connection.autocommit = True
        yield connection


def _drop_public_non_extension_objects(conn: psycopg.Connection) -> None:
    conn.execute(
        """
        DO $$
        DECLARE
            item record;
        BEGIN
            FOR item IN
                SELECT schemaname, matviewname
                FROM pg_matviews
                WHERE schemaname = 'public'
            LOOP
                EXECUTE format(
                    'DROP MATERIALIZED VIEW IF EXISTS %I.%I CASCADE',
                    item.schemaname,
                    item.matviewname
                );
            END LOOP;

            FOR item IN
                SELECT schemaname, viewname
                FROM pg_views
                WHERE schemaname = 'public'
            LOOP
                EXECUTE format(
                    'DROP VIEW IF EXISTS %I.%I CASCADE',
                    item.schemaname,
                    item.viewname
                );
            END LOOP;

            FOR item IN
                SELECT schemaname, tablename
                FROM pg_tables
                WHERE schemaname = 'public'
            LOOP
                EXECUTE format(
                    'DROP TABLE IF EXISTS %I.%I CASCADE',
                    item.schemaname,
                    item.tablename
                );
            END LOOP;

            FOR item IN
                SELECT sequence_schema, sequence_name
                FROM information_schema.sequences
                WHERE sequence_schema = 'public'
            LOOP
                EXECUTE format(
                    'DROP SEQUENCE IF EXISTS %I.%I CASCADE',
                    item.sequence_schema,
                    item.sequence_name
                );
            END LOOP;

            FOR item IN
                SELECT n.nspname, p.oid::regprocedure AS signature
                FROM pg_proc p
                JOIN pg_namespace n ON n.oid = p.pronamespace
                WHERE n.nspname = 'public'
                  AND NOT EXISTS (
                      SELECT 1
                      FROM pg_depend d
                      WHERE d.objid = p.oid
                        AND d.deptype = 'e'
                  )
            LOOP
                EXECUTE format('DROP FUNCTION IF EXISTS %s CASCADE', item.signature);
            END LOOP;

            FOR item IN
                SELECT n.nspname, t.typname
                FROM pg_type t
                JOIN pg_namespace n ON n.oid = t.typnamespace
                WHERE n.nspname = 'public'
                  AND t.typtype IN ('e', 'c')
                  AND NOT EXISTS (
                      SELECT 1
                      FROM pg_depend d
                      WHERE d.objid = t.oid
                        AND d.deptype = 'e'
                  )
            LOOP
                EXECUTE format('DROP TYPE IF EXISTS %I.%I CASCADE', item.nspname, item.typname);
            END LOOP;

            DROP TYPE IF EXISTS public.schema_migrations CASCADE;
        END
        $$;
        """
    )


def test_records_full_claim_grounding_exchange_without_raw_corpus_text(
    conn: psycopg.Connection,
) -> None:
    grounding_evidence_id = _insert_grounding_evidence(conn)
    request = ClaimGroundingRequest.from_json(_network_request_payload())
    response = ClaimGroundingResponse.from_json(_resolved_response_payload(grounding_evidence_id))

    request_record = record_claim_grounding_request(conn, request)
    grant_record = record_claim_grounding_grant(conn, request)
    use_record = record_claim_grounding_grant_use(conn, request)
    dispatch_record = record_claim_grounding_network_dispatch_attempt(
        conn,
        request,
        broker_version="claim_grounding.network_broker.test",
        target="internet_search",
        status="succeeded",
    )
    response_record = record_claim_grounding_response(conn, request, response)
    links = record_claim_grounding_links(
        conn,
        request,
        response,
        link_kind="response_candidate_to_evidence",
    )

    assert request_record.request_id == "req-runtime-001"
    assert grant_record.grant_id == "grant-runtime-001"
    assert use_record.grant_id == "grant-runtime-001"
    assert dispatch_record.status == "succeeded"
    assert response_record.status == "resolved"
    assert [(link.candidate_id, link.grounding_evidence_id) for link in links] == [
        ("grounding-runtime-001", str(grounding_evidence_id))
    ]

    dispatch_payload_row = conn.execute(
        """
        SELECT dispatch_payload
        FROM claim_grounding_network_dispatches
        WHERE id = %s
        """,
        (dispatch_record.id,),
    ).fetchone()
    assert dispatch_payload_row is not None
    dispatch_payload = dispatch_payload_row[0]
    assert sorted(dispatch_payload) == [
        "corpus_id",
        "network_grant",
        "request_id",
        "requested_at",
        "schema_version",
        "surface_form",
        "tenant_id",
    ]
    assert dispatch_payload["network_grant"]["search_query"] == "Project Atlas"
    assert "source_refs" not in dispatch_payload
    assert "local_context_capsule" not in dispatch_payload

    request_payload_row = conn.execute(
        """
        SELECT request_payload
        FROM claim_grounding_requests
        WHERE request_payload->>'request_id' = %s
        """,
        ("req-runtime-001",),
    ).fetchone()
    assert request_payload_row is not None
    request_payload = request_payload_row[0]
    assert request_payload["local_context_capsule"] == {"mode": "none", "text": None}
    assert "private chat sentence" not in str(request_payload)


def test_network_dispatch_requires_persisted_matching_grant(conn: psycopg.Connection) -> None:
    request = ClaimGroundingRequest.from_json(_network_request_payload())

    with pytest.raises(ClaimGroundingPersistenceConflict, match="has not been persisted"):
        record_claim_grounding_network_dispatch_attempt(
            conn,
            request,
            broker_version="claim_grounding.network_broker.test",
            target="internet_search",
            status="denied",
        )

    record_claim_grounding_request(conn, request)
    record_claim_grounding_grant(conn, request)

    dispatch = record_claim_grounding_network_dispatch_attempt(
        conn,
        request,
        broker_version="claim_grounding.network_broker.test",
        target="internet_search",
        status="denied",
        error_code="operator_denied",
    )

    assert dispatch.grant_id == "grant-runtime-001"


def test_grant_lifecycle_rows_are_append_only_and_revocation_blocks_dispatch(
    conn: psycopg.Connection,
) -> None:
    request = ClaimGroundingRequest.from_json(_network_request_payload())

    record_claim_grounding_request(conn, request)
    draft = record_claim_grounding_draft_grant(conn, request)
    approved = record_claim_grounding_approved_grant(conn, request)
    verified = verify_claim_grounding_grant_for_dispatch(
        conn,
        request,
        target="internet_search",
    )
    revoked = record_claim_grounding_revoked_grant(
        conn,
        request,
        revoked_by="operator",
        reason="operator changed decision",
    )

    assert draft.status == "draft"
    assert approved.status == "approved"
    assert verified.grant_id == "grant-runtime-001"
    assert revoked.status == "revoked"
    assert len({draft.id, approved.id, revoked.id}) == 3

    rows = conn.execute(
        """
        SELECT grant_status
        FROM claim_grounding_grants
        ORDER BY created_at, id
        """
    ).fetchall()
    assert [row[0] for row in rows] == ["draft", "approved", "revoked"]

    with pytest.raises(ClaimGroundingPersistenceConflict, match="latest status is \"revoked\""):
        record_claim_grounding_network_dispatch_attempt(
            conn,
            request,
            broker_version="claim_grounding.network_broker.test",
            target="internet_search",
            status="succeeded",
        )


def test_denied_grant_row_blocks_dispatch_without_updating_prior_rows(
    conn: psycopg.Connection,
) -> None:
    request = ClaimGroundingRequest.from_json(_network_request_payload())

    record_claim_grounding_request(conn, request)
    denied = record_claim_grounding_denied_grant(
        conn,
        request,
        denied_by="operator",
        reason="query reveals private project name",
    )

    assert denied.status == "denied"
    with pytest.raises(ClaimGroundingPersistenceConflict, match="latest status is \"denied\""):
        record_claim_grounding_network_dispatch_attempt(
            conn,
            request,
            broker_version="claim_grounding.network_broker.test",
            target="internet_search",
            status="succeeded",
        )

    count_row = conn.execute("SELECT count(*) FROM claim_grounding_grants").fetchone()
    assert count_row == (1,)


def test_dispatch_verification_rejects_expired_grant(conn: psycopg.Connection) -> None:
    payload = _network_request_payload()
    grant_payload = payload["network_grant"]
    assert isinstance(grant_payload, dict)
    grant_payload["expires_at"] = "2026-05-18T00:00:01Z"
    request = ClaimGroundingRequest.from_json(payload)

    record_claim_grounding_request(conn, request)
    record_claim_grounding_grant(conn, request)

    with pytest.raises(ClaimGroundingPersistenceConflict, match="is expired"):
        verify_claim_grounding_grant_for_dispatch(
            conn,
            request,
            target="internet_search",
            verified_at=datetime(2026, 5, 18, 0, 0, 2, tzinfo=UTC),
        )


def test_dispatch_verification_rejects_unapproved_target(conn: psycopg.Connection) -> None:
    request = ClaimGroundingRequest.from_json(_network_request_payload())

    record_claim_grounding_request(conn, request)
    record_claim_grounding_grant(conn, request)

    with pytest.raises(ClaimGroundingPersistenceConflict, match="does not allow target"):
        record_claim_grounding_network_dispatch_attempt(
            conn,
            request,
            broker_version="claim_grounding.network_broker.test",
            target="public_dataset_api",
            status="succeeded",
        )

    count_row = conn.execute("SELECT count(*) FROM claim_grounding_network_dispatches").fetchone()
    assert count_row == (0,)


def test_response_recording_rejects_request_id_drift(conn: psycopg.Connection) -> None:
    request = ClaimGroundingRequest.from_json(_network_request_payload())
    payload = _resolved_response_payload(uuid4())
    payload["request_id"] = "other-request"
    response = ClaimGroundingResponse.from_json(payload)

    with pytest.raises(ClaimGroundingPersistenceConflict, match="does not match"):
        record_claim_grounding_response(conn, request, response)


def test_helpers_report_missing_runtime_tables(conn: psycopg.Connection) -> None:
    conn.execute("DROP TABLE claim_grounding_requests CASCADE")
    request = ClaimGroundingRequest.from_json(_network_request_payload())

    with pytest.raises(ClaimGroundingPersistenceSchemaMissing, match="persistence tables"):
        record_claim_grounding_request(conn, request)


def _network_request_payload() -> dict[str, object]:
    return {
        "schema_version": CLAIM_GROUNDING_REQUEST_SCHEMA_VERSION,
        "request_id": "req-runtime-001",
        "tenant_id": "personal",
        "corpus_id": "personal",
        "extraction_run_id": "run-runtime-001",
        "extraction_prompt_version": "extractor.v-test",
        "extraction_model_version": "local-test-model",
        "surface_form": "Project Atlas",
        "mention_role": "subject",
        "candidate_entity_kinds": ["product", "organization"],
        "source_refs": [
            {
                "target_table": "messages",
                "target_id": "message-runtime-001",
                "span_hash": "a" * 64,
                "span_start": 12,
                "span_end": 25,
            }
        ],
        "local_context_capsule": {"mode": "none", "text": None},
        "allowed_modes": ["local_lookup", "network_fetch"],
        "network_grant": {
            "grant_id": "grant-runtime-001",
            "granted_by": "operator",
            "granted_at": "2026-05-18T00:00:00Z",
            "expires_at": None,
            "purpose": "entity_grounding",
            "search_query": "Project Atlas",
            "query_text_class": "entity_surface_form",
            "query_privacy_tier": 1,
            "allowed_network_targets": ["internet_search"],
        },
        "privacy_tier_ceiling": 1,
        "sensitivity_ceiling": ["routine_project"],
        "requested_at": "2026-05-18T00:00:00Z",
    }


def _resolved_response_payload(grounding_evidence_id: UUID) -> dict[str, object]:
    return {
        "schema_version": CLAIM_GROUNDING_RESPONSE_SCHEMA_VERSION,
        "request_id": "req-runtime-001",
        "status": "resolved",
        "mode": "network_fetch",
        "network_fetch": "performed_by_grounding_broker",
        "candidates": [
            {
                "candidate_id": "grounding-runtime-001",
                "entity_kind": "product",
                "canonical_label": "Project Atlas",
                "external_ids": [{"kind": "wikidata_qid", "value": "QTEST"}],
                "grounding_evidence_ids": [str(grounding_evidence_id)],
                "source_url": "https://example.invalid/project-atlas",
                "source_label": "Fixture public page",
                "content_hash": "b" * 64,
                "content_excerpt": "Project Atlas is a local-first software product.",
                "confidence": 0.91,
                "stability": "stable_public_entity",
                "ambiguity_reasons": [],
            }
        ],
        "omissions": [],
        "broker_version": "claim_grounding.network_broker.test",
        "dataset_snapshots": [],
        "created_at": "2026-05-18T00:00:01Z",
    }


def _insert_grounding_evidence(conn: psycopg.Connection) -> UUID:
    row = conn.execute(
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
            'personal',
            'personal',
            'Project Atlas',
            'product',
            'https://example.invalid/project-atlas',
            'Fixture public page',
            %s,
            'Project Atlas is a local-first software product.',
            '2026-05-18T00:00:00Z',
            'manual.local.test',
            'none',
            1,
            'routine_project',
            '{}'::jsonb
        )
        RETURNING id
        """,
        ("b" * 64,),
    ).fetchone()
    assert row is not None
    return row[0]
