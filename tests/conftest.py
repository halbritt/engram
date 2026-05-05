from __future__ import annotations

import os

import psycopg
import pytest

from engram.migrations import migrate


TEST_DATABASE_URL = os.environ.get("ENGRAM_TEST_DATABASE_URL")


@pytest.fixture()
def conn():
    if not TEST_DATABASE_URL:
        pytest.skip("ENGRAM_TEST_DATABASE_URL is required for database tests")
    with psycopg.connect(TEST_DATABASE_URL, autocommit=True) as admin:
        admin.execute(
            """
            DROP TABLE IF EXISTS
                schema_migrations,
                contradictions,
                belief_audit,
                beliefs,
                claims,
                claim_extractions,
                predicate_vocabulary,
                segment_embeddings,
                embedding_cache,
                segments,
                segment_generations,
                captures,
                notes,
                messages,
                conversations,
                sources,
                consolidation_progress
            CASCADE
            """
        )
        admin.execute("DROP FUNCTION IF EXISTS prevent_raw_evidence_mutation() CASCADE")
        admin.execute("DROP FUNCTION IF EXISTS prevent_segment_mutation() CASCADE")
        admin.execute("DROP FUNCTION IF EXISTS prevent_embedding_cache_mutation() CASCADE")
        admin.execute("DROP FUNCTION IF EXISTS prevent_segment_embedding_mutation() CASCADE")
        admin.execute(
            "DROP FUNCTION IF EXISTS validate_conversation_segment_message_ids() CASCADE"
        )
        admin.execute("DROP FUNCTION IF EXISTS engram_normalize_subject(TEXT) CASCADE")
        admin.execute("DROP FUNCTION IF EXISTS engram_normalize_group_object_value(TEXT) CASCADE")
        admin.execute("DROP FUNCTION IF EXISTS fn_claim_extractions_mutation_guard() CASCADE")
        admin.execute("DROP FUNCTION IF EXISTS fn_claims_insert_prepare_validate() CASCADE")
        admin.execute("DROP FUNCTION IF EXISTS fn_claims_insert_only() CASCADE")
        admin.execute("DROP FUNCTION IF EXISTS fn_beliefs_prepare_validate() CASCADE")
        admin.execute("DROP FUNCTION IF EXISTS fn_belief_audit_append_only() CASCADE")
        admin.execute("DROP FUNCTION IF EXISTS fn_contradictions_mutation_guard() CASCADE")
        admin.execute("DROP TYPE IF EXISTS source_kind CASCADE")
        admin.execute("DROP TYPE IF EXISTS capture_type CASCADE")
        admin.execute("DROP TYPE IF EXISTS consolidation_status CASCADE")
    with psycopg.connect(TEST_DATABASE_URL) as connection:
        migrate(connection)
        connection.autocommit = True
        yield connection
