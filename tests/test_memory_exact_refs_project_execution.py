"""RFC 0050 Layer 5: exact-reference retrieval for project-execution sources."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import psycopg
import pytest

from engram.build_artifact_import import import_build_artifacts
from engram.git_import import import_git_repo
from engram.markdown_import import import_markdown_tree
from engram.memory import (
    CAPABILITY_DESCRIBE,
    CAPABILITY_READ_PERSONAL,
    MemoryCapabilityError,
    ExactRefFilter,
    MemorySearchFilters,
    MemoryService,
    MemoryToken,
    TenantCorpus,
)

PERSONAL_TENANT_ID = "personal"
PERSONAL_CORPUS_ID = "personal"
GIT_ENV = {
    "PATH": os.environ.get("PATH", ""),
    "LC_ALL": "C",
    "GIT_TERMINAL_PROMPT": "0",
    "GIT_AUTHOR_NAME": "Test Author",
    "GIT_AUTHOR_EMAIL": "author@example.invalid",
    "GIT_COMMITTER_NAME": "Test Committer",
    "GIT_COMMITTER_EMAIL": "committer@example.invalid",
    "GIT_AUTHOR_DATE": "2024-01-01T00:00:00+00:00",
    "GIT_COMMITTER_DATE": "2024-01-01T00:00:00+00:00",
}
JUNIT_XML = """<?xml version="1.0" encoding="UTF-8"?>
<testsuites>
  <testsuite name="example" tests="1" failures="0" errors="0" skipped="0">
    <testcase classname="example.module" name="test_alpha" time="0.100"/>
  </testsuite>
</testsuites>
"""
REQUIRED_HIT_KEYS = {
    "reference_id",
    "tenant_id",
    "corpus_id",
    "source_kind",
    "sub_kind",
    "external_id",
    "content",
    "score",
    "privacy_tier",
    "sensitivity_class",
    "provenance",
    "freshness",
    "dirty_working_tree",
    "observed_at",
    "imported_at",
    "target_table",
    "target_id",
}


def _run_git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", *args],
        cwd=str(repo),
        check=True,
        capture_output=True,
        text=True,
        env=GIT_ENV,
    )


def _make_fixture_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "fixture_git"
    repo.mkdir()
    _run_git(repo, "init", "--initial-branch=main")
    _run_git(repo, "config", "user.email", "test@example.invalid")
    _run_git(repo, "config", "user.name", "Test")
    _run_git(repo, "config", "commit.gpgsign", "false")
    (repo / "README.md").write_text("first\n", encoding="utf-8")
    _run_git(repo, "add", "README.md")
    _run_git(repo, "commit", "-m", "initial commit")
    return repo


def _make_default_service(conn: psycopg.Connection) -> MemoryService:
    pair = TenantCorpus(PERSONAL_TENANT_ID, PERSONAL_CORPUS_ID)
    token = MemoryToken(
        capabilities=frozenset({CAPABILITY_READ_PERSONAL, CAPABILITY_DESCRIBE}),
        allowed_pairs=frozenset({pair}),
        primary_pair=pair,
    )
    return MemoryService(conn, token=token)


def test_search_by_commit_sha_returns_git_row(
    conn: psycopg.Connection, tmp_path: Path
) -> None:
    repo = _make_fixture_repo(tmp_path)
    import_git_repo(conn, repo)
    with conn.cursor() as cur:
        cur.execute("SELECT commit_sha FROM git_commits LIMIT 1")
        sha = cur.fetchone()[0]

    svc = _make_default_service(conn)
    hits = svc.search(
        query=sha,
        tenant_id=PERSONAL_TENANT_ID,
        corpus_id=PERSONAL_CORPUS_ID,
        filters=MemorySearchFilters(
            exact_refs=(ExactRefFilter(ref_kind="commit_sha", ref_value=sha),)
        ),
    )
    assert hits
    assert hits[0]["source_kind"] == "git"
    assert sha in hits[0]["external_id"]
    assert set(hits[0]) == REQUIRED_HIT_KEYS
    assert hits[0]["target_table"] == "git_commits"
    assert hits[0]["provenance"]["commit_sha"] == sha


def test_search_by_artifact_hash_returns_build_artifact(
    conn: psycopg.Connection, tmp_path: Path
) -> None:
    root = tmp_path / "artifacts"
    root.mkdir()
    (root / "junit.xml").write_text(JUNIT_XML, encoding="utf-8")
    import_build_artifacts(conn, root)
    with conn.cursor() as cur:
        cur.execute("SELECT content_hash FROM build_artifacts LIMIT 1")
        content_hash = cur.fetchone()[0]

    svc = _make_default_service(conn)
    hits = svc.search(
        query=content_hash,
        tenant_id=PERSONAL_TENANT_ID,
        corpus_id=PERSONAL_CORPUS_ID,
        filters=MemorySearchFilters(
            exact_refs=(ExactRefFilter(ref_kind="source_hash", ref_value=content_hash),)
        ),
    )
    assert hits
    assert hits[0]["source_kind"] == "build_artifact"
    assert set(hits[0]) == REQUIRED_HIT_KEYS
    assert hits[0]["target_table"] == "build_artifacts"
    assert hits[0]["provenance"]["artifact_hash"] == content_hash


def test_search_by_run_id_returns_build_artifact(
    conn: psycopg.Connection, tmp_path: Path
) -> None:
    root = tmp_path / "artifacts"
    root.mkdir()
    (root / "junit.xml").write_text(JUNIT_XML, encoding="utf-8")
    import_build_artifacts(conn, root, run_id="run_xyz789")

    svc = _make_default_service(conn)
    hits = svc.search(
        query="run_xyz789",
        tenant_id=PERSONAL_TENANT_ID,
        corpus_id=PERSONAL_CORPUS_ID,
        filters=MemorySearchFilters(
            exact_refs=(ExactRefFilter(ref_kind="run_id", ref_value="run_xyz789"),)
        ),
    )
    assert hits
    assert hits[0]["source_kind"] == "build_artifact"
    assert set(hits[0]) == REQUIRED_HIT_KEYS
    assert hits[0]["provenance"]["run_id"] == "run_xyz789"


def test_search_by_markdown_path_returns_markdown_file(
    conn: psycopg.Connection, tmp_path: Path
) -> None:
    root = tmp_path / "vault"
    root.mkdir()
    (root / "README.md").write_text("# Root\n", encoding="utf-8")
    import_markdown_tree(conn, root)

    svc = _make_default_service(conn)
    hits = svc.search(
        query="README.md",
        tenant_id=PERSONAL_TENANT_ID,
        corpus_id=PERSONAL_CORPUS_ID,
        filters=MemorySearchFilters(
            exact_refs=(ExactRefFilter(ref_kind="path", ref_value="README.md"),)
        ),
    )
    assert hits
    assert hits[0]["source_kind"] == "markdown_tree"
    assert set(hits[0]) == REQUIRED_HIT_KEYS
    assert hits[0]["target_table"] == "markdown_files"
    assert hits[0]["provenance"]["path"] == "README.md"


def test_missing_ref_returns_no_hits(conn: psycopg.Connection, tmp_path: Path) -> None:
    svc = _make_default_service(conn)
    hits = svc.search(
        query="nope",
        tenant_id=PERSONAL_TENANT_ID,
        corpus_id=PERSONAL_CORPUS_ID,
        filters=MemorySearchFilters(
            exact_refs=(
                ExactRefFilter(
                    ref_kind="commit_sha",
                    ref_value="0" * 40,
                ),
            )
        ),
    )
    assert hits == []


def test_fetch_reference_reauthorizes_project_execution_refs(
    conn: psycopg.Connection, tmp_path: Path
) -> None:
    repo = _make_fixture_repo(tmp_path)
    import_git_repo(conn, repo)
    sha = conn.execute("SELECT commit_sha FROM git_commits LIMIT 1").fetchone()[0]
    service = _make_default_service(conn)
    reference_id = service.search(
        query=sha,
        tenant_id=PERSONAL_TENANT_ID,
        corpus_id=PERSONAL_CORPUS_ID,
        filters=MemorySearchFilters(
            exact_refs=(ExactRefFilter(ref_kind="commit_sha", ref_value=sha),)
        ),
    )[0]["reference_id"]

    with pytest.raises(MemoryCapabilityError, match=r"not allowed"):
        MemoryService(conn).fetch_reference(reference_id)

    fetched = service.fetch_reference(reference_id)
    assert fetched["target_table"] == "git_commits"
    assert fetched["tenant_id"] == PERSONAL_TENANT_ID
    assert fetched["corpus_id"] == PERSONAL_CORPUS_ID
    assert fetched["provenance"]["commit_sha"] == sha


def test_build_packet_by_commit_sha_cites_git_commit(
    conn: psycopg.Connection, tmp_path: Path
) -> None:
    repo = _make_fixture_repo(tmp_path)
    import_git_repo(conn, repo)
    sha = conn.execute("SELECT commit_sha FROM git_commits LIMIT 1").fetchone()[0]
    service = _make_default_service(conn)

    packet = service.build_packet(
        sha,
        budget=100,
        tenant_id=PERSONAL_TENANT_ID,
        corpus_id=PERSONAL_CORPUS_ID,
        filters=MemorySearchFilters(
            exact_refs=(ExactRefFilter(ref_kind="commit_sha", ref_value=sha),)
        ),
    )

    assert packet["status"] == "available"
    citation = packet["selected"][0]["citation"]
    assert citation["source_kind"] == "git"
    assert citation["commit_sha"] == sha
    assert citation["target_table"] == "git_commits"


def test_build_packet_by_artifact_hash_and_run_id_cites_build_artifact(
    conn: psycopg.Connection, tmp_path: Path
) -> None:
    root = tmp_path / "artifacts"
    root.mkdir()
    (root / "junit.xml").write_text(JUNIT_XML, encoding="utf-8")
    import_build_artifacts(conn, root, run_id="run_packet_123")
    row = conn.execute(
        "SELECT content_hash FROM build_artifacts WHERE run_id = 'run_packet_123' LIMIT 1"
    ).fetchone()
    content_hash = row[0]
    service = _make_default_service(conn)

    hash_packet = service.build_packet(
        content_hash,
        budget=100,
        tenant_id=PERSONAL_TENANT_ID,
        corpus_id=PERSONAL_CORPUS_ID,
        filters=MemorySearchFilters(
            exact_refs=(ExactRefFilter(ref_kind="source_hash", ref_value=content_hash),)
        ),
    )
    run_packet = service.build_packet(
        "run_packet_123",
        budget=100,
        tenant_id=PERSONAL_TENANT_ID,
        corpus_id=PERSONAL_CORPUS_ID,
        filters=MemorySearchFilters(
            exact_refs=(ExactRefFilter(ref_kind="run_id", ref_value="run_packet_123"),)
        ),
    )

    assert hash_packet["selected"][0]["citation"]["artifact_hash"] == content_hash
    assert run_packet["selected"][0]["citation"]["run_id"] == "run_packet_123"
    assert run_packet["selected"][0]["citation"]["target_table"] == "build_artifacts"


def test_build_packet_by_markdown_path_cites_path_and_audit_omits_body(
    conn: psycopg.Connection, tmp_path: Path
) -> None:
    root = tmp_path / "vault"
    root.mkdir()
    body = "# Root\n\nPacket body must not appear in audit rows.\n"
    (root / "README.md").write_text(body, encoding="utf-8")
    import_markdown_tree(conn, root)
    service = _make_default_service(conn)

    packet = service.build_packet(
        "README.md",
        budget=100,
        tenant_id=PERSONAL_TENANT_ID,
        corpus_id=PERSONAL_CORPUS_ID,
        filters=MemorySearchFilters(
            exact_refs=(ExactRefFilter(ref_kind="path", ref_value="README.md"),)
        ),
    )

    citation = packet["selected"][0]["citation"]
    assert citation["path"] == "README.md"
    assert citation["markdown_root_id"]
    fetched = service.fetch_reference(packet["selected"][0]["reference_id"])
    assert fetched["content"] == body

    audit_row = conn.execute(
        """
        SELECT selected::text, omitted::text
        FROM striatum_packet_audits
        WHERE packet_id = %s
        """,
        (packet["packet_id"],),
    ).fetchone()
    assert audit_row is not None
    assert "Packet body must not appear" not in audit_row[0]
    assert "Packet body must not appear" not in audit_row[1]
