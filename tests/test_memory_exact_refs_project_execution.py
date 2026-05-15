"""RFC 0050 Layer 5: exact-reference retrieval for project-execution sources."""

from __future__ import annotations

from pathlib import Path

import psycopg
import pytest

from engram.build_artifact_import import import_build_artifacts
from engram.git_import import import_git_repo
from engram.markdown_import import import_markdown_tree
from engram.memory import (
    CAPABILITY_DESCRIBE,
    CAPABILITY_READ_PERSONAL,
    ExactRefFilter,
    MemorySearchFilters,
    MemoryService,
    MemoryToken,
    TenantCorpus,
)

PERSONAL_TENANT_ID = "personal"
PERSONAL_CORPUS_ID = "personal"


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
    from tests.test_git_importer import make_fixture_repo

    repo = make_fixture_repo(tmp_path)
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


def test_search_by_artifact_hash_returns_build_artifact(
    conn: psycopg.Connection, tmp_path: Path
) -> None:
    from tests.test_build_artifact_importer import JUNIT_XML

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


def test_search_by_run_id_returns_build_artifact(
    conn: psycopg.Connection, tmp_path: Path
) -> None:
    from tests.test_build_artifact_importer import JUNIT_XML

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
    assert hits[0]["raw_payload"]["run_id"] == "run_xyz789"


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
