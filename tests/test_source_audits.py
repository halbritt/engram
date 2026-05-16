"""Tests for RFC 0050 Layer 6 source_audits and EG-SI-090 reconstruction."""

from __future__ import annotations

import json
from pathlib import Path

import psycopg
import pytest

from engram.build_artifact_import import import_build_artifacts
from engram.git_import import import_git_repo
from engram.markdown_import import import_markdown_tree


def _audit_count(conn: psycopg.Connection, source_kind: str) -> int:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT COUNT(*) FROM source_audits WHERE source_kind = %s",
            (source_kind,),
        )
        return int(cur.fetchone()[0])


def test_git_import_records_source_audit(conn: psycopg.Connection, tmp_path: Path) -> None:
    from tests.test_git_importer import make_fixture_repo

    repo = make_fixture_repo(tmp_path)
    import_git_repo(conn, repo)
    assert _audit_count(conn, "git") == 1
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT outcome, rows_inserted, completed_at, raw_payload
            FROM source_audits
            WHERE source_kind = 'git'
            """
        )
        outcome, rows_inserted, completed_at, raw_payload = cur.fetchone()
    assert outcome in {"ok", "partial"}
    assert rows_inserted >= 2
    assert completed_at is not None
    assert raw_payload["root_commit_sha"]


def test_build_artifact_import_records_source_audit(
    conn: psycopg.Connection, tmp_path: Path
) -> None:
    from tests.test_build_artifact_importer import JUNIT_XML

    root = tmp_path / "artifacts"
    root.mkdir()
    (root / "junit.xml").write_text(JUNIT_XML, encoding="utf-8")
    import_build_artifacts(conn, root, run_id="run_smoke")
    assert _audit_count(conn, "build_artifact") == 1
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT rows_inserted, raw_payload
            FROM source_audits
            WHERE source_kind = 'build_artifact'
            """
        )
        rows_inserted, payload = cur.fetchone()
    assert rows_inserted == 1
    assert payload["run_id"] == "run_smoke"


def test_markdown_import_records_source_audit(
    conn: psycopg.Connection, tmp_path: Path
) -> None:
    root = tmp_path / "vault"
    root.mkdir()
    (root / "README.md").write_text("# README\n\nBody.\n", encoding="utf-8")
    import_markdown_tree(conn, root)
    assert _audit_count(conn, "markdown_tree") == 1
    with conn.cursor() as cur:
        cur.execute(
            "SELECT rows_inserted FROM source_audits WHERE source_kind = 'markdown_tree'"
        )
        rows_inserted = int(cur.fetchone()[0])
    assert rows_inserted == 1


def test_eg_si_090_audit_reconstruction(conn: psycopg.Connection, tmp_path: Path) -> None:
    """EG-SI-090: audit reconstruction reads source_audits and rebuilds the
    importer outcome without loading importer raw_payload bodies."""
    from tests.test_git_importer import make_fixture_repo

    repo = make_fixture_repo(tmp_path)
    import_git_repo(conn, repo)
    import_git_repo(conn, repo)  # second invocation, idempotent

    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT outcome, rows_inserted, rows_skipped, coverage_gap_count,
                   adapter_version, input_signature, started_at, completed_at
            FROM source_audits
            WHERE source_kind = 'git'
            ORDER BY started_at
            """
        )
        rows = cur.fetchall()
    assert len(rows) == 2
    first, second = rows
    # First invocation imported all commits; second was idempotent.
    assert first[1] > 0  # first.rows_inserted > 0
    assert second[1] == 0  # second.rows_inserted == 0
    assert second[2] >= first[1]  # second.rows_skipped >= first.rows_inserted
    assert first[5] == second[5]  # same input_signature across runs
    # Both completed cleanly.
    assert first[7] is not None
    assert second[7] is not None


def test_no_derived_product_leak_invariant_audit_payload(
    conn: psycopg.Connection, tmp_path: Path
) -> None:
    """The audit row's raw_payload records counts and identifiers, not generated
    body content. Verifies the RFC 0050 § No-Derived-Product-Leak Invariant."""
    root = tmp_path / "vault"
    root.mkdir()
    (root / "secret.md").write_text(
        "# secret\n\nThis body must not appear in the audit payload.\n",
        encoding="utf-8",
    )
    import_markdown_tree(conn, root)
    with conn.cursor() as cur:
        cur.execute(
            "SELECT raw_payload FROM source_audits WHERE source_kind = 'markdown_tree'"
        )
        payload = cur.fetchone()[0]
    serialized = json.dumps(payload)
    assert "This body must not appear" not in serialized
