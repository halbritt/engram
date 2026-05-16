"""Shared source-audit recording helper (RFC 0050 Layer 6).

Every Engram source importer invokes ``record_source_audit`` once per
ingest, inside the same transaction as the importer's inserts. The
returned audit id can be referenced by callers (CLI, tests) without
touching ``raw_payload`` bodies on importer-specific tables.
"""

from __future__ import annotations

import hashlib
from datetime import datetime
from typing import Any

import psycopg
from psycopg.types.json import Jsonb


def compute_input_signature(parts: list[str]) -> str:
    """Return a sha256 over a tuple of input identifiers.

    Importers pass adapter-stable parts (root path, content hashes, etc.).
    The result is a hex digest used as a stable input fingerprint.
    """
    blob = "\x00".join(parts).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def record_source_audit(
    conn: psycopg.Connection,
    *,
    tenant_id: str,
    corpus_id: str,
    source_kind: str,
    source_id: str | None,
    adapter_version: str,
    input_signature: str,
    outcome: str,
    rows_inserted: int = 0,
    rows_skipped: int = 0,
    rows_tombstoned: int = 0,
    coverage_gap_count: int = 0,
    started_at: datetime | None = None,
    completed_at: datetime | None = None,
    raw_payload: dict[str, Any] | None = None,
) -> str:
    """Insert one source_audits row. Returns the audit row id."""
    payload = raw_payload or {}
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO source_audits (
                tenant_id, corpus_id, source_kind, source_id,
                adapter_version, input_signature, outcome,
                rows_inserted, rows_skipped, rows_tombstoned,
                coverage_gap_count, started_at, completed_at, raw_payload
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, COALESCE(%s, now()), %s, %s)
            RETURNING id::text
            """,
            (
                tenant_id,
                corpus_id,
                source_kind,
                source_id,
                adapter_version,
                input_signature,
                outcome,
                rows_inserted,
                rows_skipped,
                rows_tombstoned,
                coverage_gap_count,
                started_at,
                completed_at,
                Jsonb(payload),
            ),
        )
        row = cur.fetchone()
        assert row is not None
        return str(row[0])
