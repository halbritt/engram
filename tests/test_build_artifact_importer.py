"""Tests for the RFC 0050 Layer 2 build-artifact importer."""

from __future__ import annotations

import json
from pathlib import Path

import psycopg
import pytest

from engram.build_artifact_import import (
    BuildArtifactImportError,
    SOURCE_KIND,
    import_build_artifacts,
)

JUNIT_XML = """<?xml version="1.0" encoding="UTF-8"?>
<testsuites>
  <testsuite name="example" tests="3" failures="1" errors="0" skipped="1" time="0.500">
    <testcase classname="example.module" name="test_alpha" time="0.100"/>
    <testcase classname="example.module" name="test_beta" time="0.200">
      <failure message="assert failed">stack trace here</failure>
    </testcase>
    <testcase classname="example.module" name="test_skipped" time="0.000">
      <skipped/>
    </testcase>
  </testsuite>
</testsuites>
"""

COVERAGE_JSON = json.dumps(
    {
        "totals": {"percent_covered": 92.5, "covered_lines": 925, "num_statements": 1000},
        "files": {
            "src/engram/example.py": {"summary": {"percent_covered": 91.0}},
            "src/engram/other.py": {"summary": {"percent_covered": 100.0}},
        },
    }
)

BENCHMARK_JSON = json.dumps(
    {
        "benchmarks": [
            {"name": "benchmark_a", "mean": 0.0123, "stddev": 0.001},
            {"name": "benchmark_b", "mean": 0.0456, "stddev": 0.002},
        ]
    }
)

RUFF_JSON = json.dumps(
    [
        {
            "filename": "src/engram/example.py",
            "location": {"row": 10, "column": 4},
            "code": "E501",
            "message": "line too long",
        }
    ]
)

CLEAN_LOG = "build started\nstep 1 ok\nstep 2 ok\nbuild ok\n"
LOG_WITH_SECRET = "starting...\nAKIAABCDEFGHIJKLMNOP\ndone\n"


def _make_dir(tmp_path: Path) -> Path:
    root = tmp_path / "artifacts"
    root.mkdir()
    return root


def test_imports_junit_coverage_benchmark_lint_log(
    conn: psycopg.Connection, tmp_path: Path
) -> None:
    root = _make_dir(tmp_path)
    (root / "junit.xml").write_text(JUNIT_XML, encoding="utf-8")
    (root / "coverage.json").write_text(COVERAGE_JSON, encoding="utf-8")
    (root / "benchmark.json").write_text(BENCHMARK_JSON, encoding="utf-8")
    (root / "ruff.json").write_text(RUFF_JSON, encoding="utf-8")
    (root / "build.log").write_text(CLEAN_LOG, encoding="utf-8")
    result = import_build_artifacts(conn, root)
    assert result.artifacts_inserted == 5
    assert result.artifacts_seen == 5
    assert result.findings_inserted > 0
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM build_artifacts")
        assert cur.fetchone()[0] == 5
        cur.execute("SELECT DISTINCT artifact_kind FROM build_artifacts ORDER BY 1")
        kinds = {row[0] for row in cur.fetchall()}
    assert {"junit_xml", "coverage_report", "benchmark_json", "lint_report", "log_file"} <= kinds


def test_reimport_is_idempotent(conn: psycopg.Connection, tmp_path: Path) -> None:
    root = _make_dir(tmp_path)
    (root / "junit.xml").write_text(JUNIT_XML, encoding="utf-8")
    first = import_build_artifacts(conn, root)
    assert first.artifacts_inserted == 1
    second = import_build_artifacts(conn, root)
    assert second.artifacts_inserted == 0
    assert second.artifacts_skipped == 1


def test_log_with_secret_is_redacted_and_promoted(
    conn: psycopg.Connection, tmp_path: Path
) -> None:
    root = _make_dir(tmp_path)
    (root / "build.log").write_text(LOG_WITH_SECRET, encoding="utf-8")
    result = import_build_artifacts(conn, root)
    assert result.redacted_artifacts == 1
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT sensitivity_class
            FROM build_artifacts
            WHERE artifact_kind = 'log_file'
            """
        )
        row = cur.fetchone()
    assert row is not None
    assert row[0] == "credential_or_secret_reference"


def test_unknown_artifact_kind_emits_coverage_gap(
    conn: psycopg.Connection, tmp_path: Path
) -> None:
    root = _make_dir(tmp_path)
    (root / "image.png").write_bytes(b"\x89PNG\r\n\x1a\n\x00\x00\x00")
    result = import_build_artifacts(conn, root)
    assert result.artifacts_inserted == 1
    assert result.coverage_gap_count == 1
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT COUNT(*) FROM captures
            WHERE source_kind = %s AND external_id LIKE %s
            """,
            (SOURCE_KIND, "coverage_gap:%unrecognized_artifact_kind%"),
        )
        assert cur.fetchone()[0] >= 1


def test_run_id_and_commit_sha_recorded(conn: psycopg.Connection, tmp_path: Path) -> None:
    root = _make_dir(tmp_path)
    (root / "junit.xml").write_text(JUNIT_XML, encoding="utf-8")
    import_build_artifacts(
        conn,
        root,
        run_id="run_abc123",
        commit_sha="0123456789abcdef0123456789abcdef01234567",
    )
    with conn.cursor() as cur:
        cur.execute("SELECT run_id, commit_sha FROM build_artifacts")
        row = cur.fetchone()
    assert row == ("run_abc123", "0123456789abcdef0123456789abcdef01234567")


def test_dry_run_does_not_insert(conn: psycopg.Connection, tmp_path: Path) -> None:
    root = _make_dir(tmp_path)
    (root / "junit.xml").write_text(JUNIT_XML, encoding="utf-8")
    result = import_build_artifacts(conn, root, dry_run=True)
    assert result.artifacts_inserted == 0
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM build_artifacts")
        assert cur.fetchone()[0] == 0


def test_root_not_a_directory_raises(conn: psycopg.Connection, tmp_path: Path) -> None:
    with pytest.raises(BuildArtifactImportError):
        import_build_artifacts(conn, tmp_path / "missing_root")


def test_no_socket_during_import(
    monkeypatch: pytest.MonkeyPatch, conn: psycopg.Connection, tmp_path: Path
) -> None:
    import socket as _socket

    seen: list[tuple[object, ...]] = []
    real_socket = _socket.socket

    class TrackingSocket(real_socket):
        def __init__(self, *args, **kwargs):  # type: ignore[no-untyped-def]
            seen.append(args)
            super().__init__(*args, **kwargs)

    monkeypatch.setattr(_socket, "socket", TrackingSocket)
    root = _make_dir(tmp_path)
    (root / "junit.xml").write_text(JUNIT_XML, encoding="utf-8")
    (root / "build.log").write_text(CLEAN_LOG, encoding="utf-8")
    import_build_artifacts(conn, root)
    assert seen == [], f"unexpected sockets created during import: {seen}"
