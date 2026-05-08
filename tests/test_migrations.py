from __future__ import annotations

from uuid import uuid4

import pytest

from engram.migrations import MIGRATIONS_DIR, MigrationDriftError, migrate


def test_rfc0021_migration_010_exists_on_disk() -> None:
    path = MIGRATIONS_DIR / "010_gold_labels.sql"
    assert path.exists(), f"missing migration: {path}"
    text = path.read_text(encoding="utf-8")
    # Sanity checks on the header and core schema landmarks.
    assert "RFC 0021" in text
    assert "gold_label_sessions" in text
    assert "gold_label_strata_vocabulary" in text
    assert "gold_label_verdict_vocabulary" in text
    assert "gold_labels" in text
    assert "fn_gold_labels_append_only" in text
    assert "fn_gold_labels_validate_target" in text
    assert "fn_gold_labels_carry_privacy_tier" in text
    assert "current_gold_label" in text


def test_rfc0021_migration_010_applies_via_conn_fixture(conn) -> None:
    """The conftest fixture already runs ``migrate(conn)``; presence of the
    new tables/views is the contract."""

    for table in (
        "gold_label_sessions",
        "gold_label_strata_vocabulary",
        "gold_label_verdict_vocabulary",
        "gold_labels",
    ):
        row = conn.execute(
            "SELECT to_regclass(%s) IS NOT NULL", (f"public.{table}",)
        ).fetchone()
        assert row[0] is True, f"table missing: {table}"
    view_row = conn.execute(
        "SELECT to_regclass('public.current_gold_label') IS NOT NULL"
    ).fetchone()
    assert view_row[0] is True


def test_migration_checksums_detect_changed_applied_file(conn, tmp_path):
    probe_suffix = uuid4().hex
    probe_table = f"migration_checksum_probe_{probe_suffix}"
    changed_table = f"migration_checksum_probe_changed_{probe_suffix}"
    migration = tmp_path / f"999_checksum_probe_{probe_suffix}.sql"
    migration.write_text(
        f"CREATE TABLE {probe_table} (id INT PRIMARY KEY);",
        encoding="utf-8",
    )

    assert migrate(conn, migrations_dir=tmp_path) == [migration.name]
    assert (
        conn.execute(
            "SELECT checksum IS NOT NULL FROM schema_migrations WHERE filename = %s",
            (migration.name,),
        ).fetchone()[0]
        is True
    )

    migration.write_text(
        f"CREATE TABLE {changed_table} (id INT PRIMARY KEY);",
        encoding="utf-8",
    )

    with pytest.raises(MigrationDriftError, match=migration.name):
        migrate(conn, migrations_dir=tmp_path)
