from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from uuid import UUID, uuid4

import psycopg
import pytest
from psycopg import sql
from psycopg.errors import InsufficientPrivilege

from scripts.provision_grounding_broker_role import (
    BROKER_INSERT_TABLES,
    BROKER_SELECT_TABLES,
    RAW_CORPUS_TABLES,
    provision_grounding_broker_role,
)

BROKER_DENIED_INSERT_TABLES = (
    "claim_grounding_requests",
    "claim_grounding_grants",
    "messages",
    "segments",
    "claims",
    "beliefs",
)


@pytest.fixture()
def broker_role(conn: psycopg.Connection) -> Iterator[str]:
    role_name = f"engram_test_broker_{uuid4().hex[:16]}"
    current_user_row = conn.execute("SELECT current_user").fetchone()
    assert current_user_row is not None
    current_user = current_user_row[0]

    try:
        provision_grounding_broker_role(conn, role_name=role_name, login=False)
        conn.execute(
            sql.SQL("GRANT {} TO {}").format(
                sql.Identifier(role_name),
                sql.Identifier(current_user),
            )
        )
        _assert_role_switchable(conn, role_name)
    except InsufficientPrivilege:
        _drop_role_if_present(conn, role_name)
        pytest.skip("local test database user cannot create or switch PostgreSQL roles")

    try:
        yield role_name
    finally:
        conn.execute("RESET ROLE")
        _drop_role_if_present(conn, role_name)


def test_broker_role_privilege_contract_denies_raw_corpus_reads(
    conn: psycopg.Connection,
    broker_role: str,
) -> None:
    for table in RAW_CORPUS_TABLES:
        assert not _has_table_privilege(conn, broker_role, table, "SELECT")

    with _using_role(conn, broker_role):
        for table in RAW_CORPUS_TABLES:
            _assert_select_denied(conn, table)

        for table in BROKER_SELECT_TABLES:
            row = conn.execute(
                sql.SQL("SELECT count(*) FROM {}").format(sql.Identifier(table))
            ).fetchone()
            assert row is not None


def test_broker_role_can_insert_only_minimized_grounding_rows(
    conn: psycopg.Connection,
    broker_role: str,
) -> None:
    request_id, grant_id = _insert_broker_visible_request_and_grant(conn)

    for table in BROKER_INSERT_TABLES:
        assert _has_table_privilege(conn, broker_role, table, "INSERT")
        assert not _has_table_privilege(conn, broker_role, table, "UPDATE")
        assert not _has_table_privilege(conn, broker_role, table, "DELETE")
    for table in BROKER_DENIED_INSERT_TABLES:
        assert not _has_table_privilege(conn, broker_role, table, "INSERT")

    with _using_role(conn, broker_role):
        conn.execute(
            """
            INSERT INTO claim_grounding_network_dispatches (
                request_id,
                grant_id,
                target_mode,
                target_adapter,
                search_query,
                query_privacy_tier,
                dispatch_status,
                dispatch_payload,
                result_metadata
            )
            VALUES (
                %s,
                %s,
                'network_fetch',
                'internet_search',
                'Project Atlas',
                1,
                'succeeded',
                '{"schema_version":"claim_grounding.network_dispatch.v1"}'::jsonb,
                '{"broker":"fixture"}'::jsonb
            )
            """,
            (request_id, grant_id),
        )
        conn.execute(
            """
            INSERT INTO claim_grounding_grant_uses (
                grant_id,
                request_id,
                use_status,
                target_adapter,
                search_query,
                query_privacy_tier,
                use_payload
            )
            VALUES (
                %s,
                %s,
                'verified',
                'internet_search',
                'Project Atlas',
                1,
                '{"broker":"fixture"}'::jsonb
            )
            """,
            (grant_id, request_id),
        )
        evidence_row = conn.execute(
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
                'Broker credential fixture',
                %s,
                'Project Atlas is a public fixture used for broker credential tests.',
                '2026-05-18T00:00:00Z',
                'broker.credential.fixture',
                'none',
                1,
                'routine_project',
                '{}'::jsonb
            )
            RETURNING id
            """,
            ("c" * 64,),
        ).fetchone()
        assert evidence_row is not None
        evidence_id = evidence_row[0]

        response_row = conn.execute(
            """
            INSERT INTO claim_grounding_responses (
                request_id,
                tenant_id,
                corpus_id,
                status,
                mode,
                network_fetch,
                broker_version,
                response_payload
            )
            VALUES (
                %s,
                'personal',
                'personal',
                'not_found',
                'network_fetch',
                'performed_by_grounding_broker',
                'broker.credential.fixture',
                '{"schema_version":"claim_grounding.response.v1"}'::jsonb
            )
            RETURNING id
            """,
            (request_id,),
        ).fetchone()
        assert response_row is not None
        response_id = response_row[0]

        conn.execute(
            """
            INSERT INTO claim_grounding_links (
                request_id,
                response_id,
                grounding_evidence_id,
                tenant_id,
                corpus_id,
                link_kind,
                response_candidate_id
            )
            VALUES (
                %s,
                %s,
                %s,
                'personal',
                'personal',
                'response_candidate_to_evidence',
                'broker-credential-fixture'
            )
            RETURNING id
            """,
            (request_id, response_id, evidence_id),
        )
        conn.execute(
            """
            INSERT INTO entity_identity_review_actions (
                tenant_id,
                corpus_id,
                action_kind,
                grounding_evidence_id,
                actor,
                rationale,
                privacy_tier,
                raw_payload
            )
            VALUES (
                'personal',
                'personal',
                'grounding_evidence_attach',
                %s,
                'grounding-broker',
                'Broker credential fixture.',
                1,
                '{}'::jsonb
            )
            """,
            (evidence_id,),
        )


def _assert_role_switchable(conn: psycopg.Connection, role_name: str) -> None:
    conn.execute(sql.SQL("SET ROLE {}").format(sql.Identifier(role_name)))
    conn.execute("RESET ROLE")


@contextmanager
def _using_role(conn: psycopg.Connection, role_name: str) -> Iterator[None]:
    conn.execute(sql.SQL("SET ROLE {}").format(sql.Identifier(role_name)))
    try:
        yield
    finally:
        conn.execute("RESET ROLE")


def _has_table_privilege(
    conn: psycopg.Connection,
    role_name: str,
    table_name: str,
    privilege: str,
) -> bool:
    row = conn.execute(
        "SELECT has_table_privilege(%s, %s, %s)",
        (role_name, f"public.{table_name}", privilege),
    ).fetchone()
    assert row is not None
    return bool(row[0])


def _assert_select_denied(conn: psycopg.Connection, table_name: str) -> None:
    with pytest.raises(InsufficientPrivilege):
        conn.execute(sql.SQL("SELECT count(*) FROM {}").format(sql.Identifier(table_name)))
    conn.rollback()


def _assert_insert_denied(
    conn: psycopg.Connection,
    statement: str,
    params: tuple[object, ...],
) -> None:
    with pytest.raises(InsufficientPrivilege):
        conn.execute(statement, params)
    conn.rollback()


def _insert_broker_visible_request_and_grant(conn: psycopg.Connection) -> tuple[UUID, UUID]:
    request_row = conn.execute(
        """
        INSERT INTO claim_grounding_requests (
            extraction_prompt_version,
            extraction_model_version,
            surface_form,
            mention_role,
            candidate_entity_kinds,
            source_refs,
            allowed_modes,
            network_grant,
            request_payload
        )
        VALUES (
            'extractor.v-test',
            'local-test-model',
            'Project Atlas',
            'subject',
            ARRAY['product'],
            '[{"target_table":"messages","target_id":"message-credential-001"}]'::jsonb,
            ARRAY['local_lookup','network_fetch'],
            '{
                "grant_id":"grant-credential-001",
                "granted_by":"operator",
                "granted_at":"2026-05-18T00:00:00Z",
                "purpose":"entity_grounding",
                "search_query":"Project Atlas",
                "query_text_class":"entity_surface_form",
                "query_privacy_tier":1,
                "allowed_network_targets":["internet_search"]
            }'::jsonb,
            '{"request_id":"request-credential-001"}'::jsonb
        )
        RETURNING id
        """
    ).fetchone()
    assert request_row is not None
    request_id = request_row[0]

    grant_row = conn.execute(
        """
        INSERT INTO claim_grounding_grants (
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
            grant_payload
        )
        VALUES (
            %s,
            'approved',
            'entity_grounding',
            'network_fetch',
            'Project Atlas',
            'Project Atlas',
            'entity_surface_form',
            1,
            ARRAY['internet_search'],
            'operator',
            '2026-05-18T00:00:00Z',
            '{"grant_id":"grant-credential-001"}'::jsonb
        )
        RETURNING id
        """,
        (request_id,),
    ).fetchone()
    assert grant_row is not None
    return request_id, grant_row[0]


def _drop_role_if_present(conn: psycopg.Connection, role_name: str) -> None:
    conn.execute("RESET ROLE")
    if not _role_exists(conn, role_name):
        return
    conn.execute(sql.SQL("DROP OWNED BY {}").format(sql.Identifier(role_name)))
    conn.execute(sql.SQL("DROP ROLE IF EXISTS {}").format(sql.Identifier(role_name)))


def _role_exists(conn: psycopg.Connection, role_name: str) -> bool:
    row = conn.execute(
        "SELECT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = %s)",
        (role_name,),
    ).fetchone()
    assert row is not None
    return bool(row[0])
