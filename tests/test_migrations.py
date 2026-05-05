from __future__ import annotations

from uuid import uuid4

import pytest

from engram.migrations import MigrationDriftError, migrate


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
