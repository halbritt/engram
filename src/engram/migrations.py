from __future__ import annotations

import hashlib
from pathlib import Path

import psycopg


REPO_ROOT = Path(__file__).resolve().parents[2]
MIGRATIONS_DIR = REPO_ROOT / "migrations"


class MigrationDriftError(RuntimeError):
    """Raised when an already-applied migration file has changed on disk."""


def migration_checksum(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def migration_integrity_errors(
    conn: psycopg.Connection,
    migrations_dir: Path = MIGRATIONS_DIR,
) -> list[str]:
    if conn.execute("SELECT to_regclass('public.schema_migrations')").fetchone()[0] is None:
        return ["schema_migrations table is missing"]
    columns = {
        row[0]
        for row in conn.execute(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = 'schema_migrations'
            """
        ).fetchall()
    }
    if "checksum" not in columns:
        return ["schema_migrations.checksum is missing; run `engram migrate`"]

    errors: list[str] = []
    for filename, applied_checksum in conn.execute(
        "SELECT filename, checksum FROM schema_migrations ORDER BY filename"
    ).fetchall():
        path = migrations_dir / filename
        if not path.exists():
            errors.append(f"applied migration file is missing: {filename}")
            continue
        if applied_checksum is None:
            errors.append(f"applied migration has no checksum: {filename}")
            continue
        current_checksum = migration_checksum(path)
        if applied_checksum != current_checksum:
            errors.append(
                "applied migration checksum mismatch: "
                f"{filename} ({applied_checksum} != {current_checksum})"
            )
    return errors


def migrate(conn: psycopg.Connection, migrations_dir: Path = MIGRATIONS_DIR) -> list[str]:
    applied_now: list[str] = []
    with conn.transaction():
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                filename TEXT PRIMARY KEY,
                applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
            """
        )
        columns = {
            row[0]
            for row in conn.execute(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = 'schema_migrations'
                """
            ).fetchall()
        }
        if "checksum" not in columns:
            conn.execute("ALTER TABLE schema_migrations ADD COLUMN checksum TEXT")
        applied = {
            row[0]: row[1]
            for row in conn.execute(
                "SELECT filename, checksum FROM schema_migrations"
            ).fetchall()
        }
        for path in sorted(migrations_dir.glob("*.sql")):
            checksum = migration_checksum(path)
            if path.name in applied:
                applied_checksum = applied[path.name]
                if applied_checksum is None:
                    conn.execute(
                        "UPDATE schema_migrations SET checksum = %s WHERE filename = %s",
                        (checksum, path.name),
                    )
                elif applied_checksum != checksum:
                    raise MigrationDriftError(
                        "applied migration has changed on disk: "
                        f"{path.name} ({applied_checksum} != {checksum})"
                    )
                continue
            conn.execute(path.read_text(encoding="utf-8"))
            conn.execute(
                "INSERT INTO schema_migrations (filename, checksum) VALUES (%s, %s)",
                (path.name, checksum),
            )
            applied_now.append(path.name)
    return applied_now
