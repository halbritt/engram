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
        admin.execute("DROP TYPE IF EXISTS source_kind CASCADE")
        admin.execute("DROP TYPE IF EXISTS capture_type CASCADE")
        admin.execute("DROP TYPE IF EXISTS consolidation_status CASCADE")
    with psycopg.connect(TEST_DATABASE_URL) as connection:
        migrate(connection)
        yield connection
