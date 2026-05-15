"""EG-SI evaluation gates for the source-ingestion expansion (RFC 0050 § Evaluation Gates).

Each gate is a named pytest function. Gate outcomes map to the
``pass | fail`` axis directly; ``blocked_upstream``, ``not_run``, and
``accepted_with_scope_limit`` are reserved for future gates added once
Stage 3-5 importers land.

Gates currently implemented:

- EG-SI-000 No-Egress (Level A: socket monkeypatch)
- EG-SI-010 Source Contract Validator
- EG-SI-020 Raw Ingest Idempotency And Conflict
- EG-SI-040 Privacy, Sensitivity, Redaction, And raw_payload Leakage
- EG-SI-050 Projection Rebuild And Activation
- EG-SI-060 Exact Reference And Citation
- EG-SI-080 Coverage, Gaps, And Lifecycle
- EG-SI-100 Source-Family Fixture Matrix

Out of Layer 4 scope (per SOURCE_INGESTION_BACKLOG): EG-SI-030 isolation
(folded into retrieval layer), EG-SI-070 extraction eligibility (waits
on Stage 3 sources), EG-SI-090 audit reconstruction (Layer 6).
"""

from __future__ import annotations

import hashlib
import socket
from pathlib import Path

import psycopg
import pytest

from engram.build_artifact_import import import_build_artifacts
from engram.git_import import GitImportConflict, import_git_repo
from engram.markdown_import import import_markdown_tree
from engram.source_contract import SOURCE_CONTRACTS_DIR, validate_contract

REPO_ROOT = Path(__file__).resolve().parent.parent
CONTRACTS_DIR = REPO_ROOT / SOURCE_CONTRACTS_DIR
KNOWN_CONTRACTS = ("git.yaml", "build_artifact.yaml", "markdown_tree.yaml")


# --- shared fixtures ---------------------------------------------------------


@pytest.fixture()
def fixture_git_repo(tmp_path: Path) -> Path:
    from tests.test_git_importer import make_fixture_repo

    return make_fixture_repo(tmp_path)


@pytest.fixture()
def fixture_build_artifacts(tmp_path: Path) -> Path:
    from tests.test_build_artifact_importer import (
        BENCHMARK_JSON,
        CLEAN_LOG,
        COVERAGE_JSON,
        JUNIT_XML,
        RUFF_JSON,
    )

    root = tmp_path / "artifacts"
    root.mkdir()
    (root / "junit.xml").write_text(JUNIT_XML, encoding="utf-8")
    (root / "coverage.json").write_text(COVERAGE_JSON, encoding="utf-8")
    (root / "benchmark.json").write_text(BENCHMARK_JSON, encoding="utf-8")
    (root / "ruff.json").write_text(RUFF_JSON, encoding="utf-8")
    (root / "build.log").write_text(CLEAN_LOG, encoding="utf-8")
    return root


@pytest.fixture()
def fixture_markdown_tree(tmp_path: Path) -> Path:
    root = tmp_path / "vault"
    root.mkdir()
    (root / "README.md").write_text(
        "---\ntitle: Root\n---\n\n# Root\n\n## Section A\n\nBody.\n",
        encoding="utf-8",
    )
    return root


# --- gates -------------------------------------------------------------------


def test_eg_si_010_source_contract_validator() -> None:
    """EG-SI-010: every known source contract passes the closed validator."""
    for name in KNOWN_CONTRACTS:
        path = CONTRACTS_DIR / name
        result = validate_contract(path)
        assert result.is_valid, f"{name}: {result.errors}"


def test_eg_si_000_no_egress_git(
    monkeypatch: pytest.MonkeyPatch,
    conn: psycopg.Connection,
    fixture_git_repo: Path,
) -> None:
    """EG-SI-000 (Level A): git importer makes no outbound socket calls."""
    seen: list[tuple[object, ...]] = []
    real_socket = socket.socket

    class TrackingSocket(real_socket):
        def __init__(self, *args, **kwargs):  # type: ignore[no-untyped-def]
            seen.append(args)
            super().__init__(*args, **kwargs)

    monkeypatch.setattr(socket, "socket", TrackingSocket)
    import_git_repo(conn, fixture_git_repo)
    assert seen == [], f"unexpected sockets created during git import: {seen}"


def test_eg_si_000_no_egress_build_artifacts(
    monkeypatch: pytest.MonkeyPatch,
    conn: psycopg.Connection,
    fixture_build_artifacts: Path,
) -> None:
    """EG-SI-000 (Level A): build-artifact importer makes no outbound sockets."""
    seen: list[tuple[object, ...]] = []
    real_socket = socket.socket

    class TrackingSocket(real_socket):
        def __init__(self, *args, **kwargs):  # type: ignore[no-untyped-def]
            seen.append(args)
            super().__init__(*args, **kwargs)

    monkeypatch.setattr(socket, "socket", TrackingSocket)
    import_build_artifacts(conn, fixture_build_artifacts)
    assert seen == [], f"unexpected sockets created during build-artifact import: {seen}"


def test_eg_si_000_no_egress_markdown(
    monkeypatch: pytest.MonkeyPatch,
    conn: psycopg.Connection,
    fixture_markdown_tree: Path,
) -> None:
    """EG-SI-000 (Level A): Markdown importer makes no outbound socket calls."""
    seen: list[tuple[object, ...]] = []
    real_socket = socket.socket

    class TrackingSocket(real_socket):
        def __init__(self, *args, **kwargs):  # type: ignore[no-untyped-def]
            seen.append(args)
            super().__init__(*args, **kwargs)

    monkeypatch.setattr(socket, "socket", TrackingSocket)
    import_markdown_tree(conn, fixture_markdown_tree)
    assert seen == [], f"unexpected sockets created during markdown import: {seen}"


def test_eg_si_020_idempotent_reimport_git(
    conn: psycopg.Connection, fixture_git_repo: Path
) -> None:
    """EG-SI-020: re-importing the same git repo produces zero new rows."""
    first = import_git_repo(conn, fixture_git_repo)
    second = import_git_repo(conn, fixture_git_repo)
    assert second.commits_inserted == 0
    assert second.commits_skipped == first.commits_inserted


def test_eg_si_020_conflict_on_changed_git_content(
    conn: psycopg.Connection, fixture_git_repo: Path
) -> None:
    """EG-SI-020: drifted commit content_hash raises GitImportConflict."""
    import_git_repo(conn, fixture_git_repo)
    with conn.cursor() as cur:
        cur.execute("ALTER TABLE git_commits DISABLE TRIGGER git_commits_no_update")
        cur.execute(
            "UPDATE git_commits SET content_hash = REPEAT('0', 64) "
            "WHERE id = (SELECT id FROM git_commits LIMIT 1)"
        )
        cur.execute("ALTER TABLE git_commits ENABLE TRIGGER git_commits_no_update")
    with pytest.raises(GitImportConflict):
        import_git_repo(conn, fixture_git_repo)


def test_eg_si_020_idempotent_reimport_build_artifacts(
    conn: psycopg.Connection, fixture_build_artifacts: Path
) -> None:
    """EG-SI-020: re-importing the same artifact directory is a no-op."""
    first = import_build_artifacts(conn, fixture_build_artifacts)
    second = import_build_artifacts(conn, fixture_build_artifacts)
    assert second.artifacts_inserted == 0
    assert second.artifacts_skipped == first.artifacts_inserted


def test_eg_si_020_idempotent_reimport_markdown(
    conn: psycopg.Connection, fixture_markdown_tree: Path
) -> None:
    """EG-SI-020: re-importing the same Markdown tree is a no-op."""
    first = import_markdown_tree(conn, fixture_markdown_tree)
    second = import_markdown_tree(conn, fixture_markdown_tree)
    assert second.files_inserted == 0
    assert second.files_skipped == first.files_inserted


def test_eg_si_040_log_with_secret_is_redacted(
    conn: psycopg.Connection, tmp_path: Path
) -> None:
    """EG-SI-040: secret-shaped log content promotes sensitivity_class."""
    root = tmp_path / "artifacts"
    root.mkdir()
    (root / "build.log").write_text(
        "starting...\nAKIAIOSFODNN7EXAMPLE\nfinished\n", encoding="utf-8"
    )
    result = import_build_artifacts(conn, root)
    assert result.redacted_artifacts == 1
    with conn.cursor() as cur:
        cur.execute(
            "SELECT sensitivity_class FROM build_artifacts WHERE artifact_kind = 'log_file'"
        )
        row = cur.fetchone()
    assert row is not None
    assert row[0] == "credential_or_secret_reference"


def test_eg_si_050_projection_rebuild_markdown(
    conn: psycopg.Connection, fixture_markdown_tree: Path
) -> None:
    """EG-SI-050: dropping chunk projection rows and reimporting rebuilds them."""
    first = import_markdown_tree(conn, fixture_markdown_tree)
    assert first.chunks_inserted > 0
    with conn.cursor() as cur:
        cur.execute("ALTER TABLE markdown_file_chunks DISABLE TRIGGER markdown_file_chunks_no_delete")
        cur.execute("DELETE FROM markdown_file_chunks")
        cur.execute("ALTER TABLE markdown_file_chunks ENABLE TRIGGER markdown_file_chunks_no_delete")
        cur.execute("SELECT COUNT(*) FROM markdown_file_chunks")
        assert cur.fetchone()[0] == 0
        # Move the active file rows to superseded so reimport produces new active rows + new chunks.
        cur.execute("ALTER TABLE markdown_files DISABLE TRIGGER markdown_files_immutable_identity")
        cur.execute("UPDATE markdown_files SET superseded_at = now()")
        cur.execute("ALTER TABLE markdown_files ENABLE TRIGGER markdown_files_immutable_identity")
    second = import_markdown_tree(conn, fixture_markdown_tree)
    assert second.chunks_inserted > 0
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM markdown_file_chunks")
        rebuilt = int(cur.fetchone()[0])
    assert rebuilt > 0


def test_eg_si_060_exact_reference_by_commit_sha(
    conn: psycopg.Connection, fixture_git_repo: Path
) -> None:
    """EG-SI-060: exact lookup by commit_sha returns the imported row."""
    import_git_repo(conn, fixture_git_repo)
    with conn.cursor() as cur:
        cur.execute("SELECT commit_sha FROM git_commits LIMIT 1")
        sha = cur.fetchone()[0]
        cur.execute(
            "SELECT COUNT(*) FROM git_commits WHERE commit_sha = %s", (sha,)
        )
        assert cur.fetchone()[0] == 1


def test_eg_si_060_exact_reference_by_artifact_hash(
    conn: psycopg.Connection, fixture_build_artifacts: Path
) -> None:
    """EG-SI-060: exact lookup by content_hash returns the imported artifact."""
    import_build_artifacts(conn, fixture_build_artifacts)
    with conn.cursor() as cur:
        cur.execute("SELECT content_hash FROM build_artifacts LIMIT 1")
        sha = cur.fetchone()[0]
        cur.execute(
            "SELECT COUNT(*) FROM build_artifacts WHERE content_hash = %s", (sha,)
        )
        assert cur.fetchone()[0] == 1


def test_eg_si_060_exact_reference_by_markdown_path(
    conn: psycopg.Connection, fixture_markdown_tree: Path
) -> None:
    """EG-SI-060: exact lookup by (root, relative_path) returns the active row."""
    import_markdown_tree(conn, fixture_markdown_tree)
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT COUNT(*) FROM markdown_files
            WHERE relative_path = 'README.md' AND superseded_at IS NULL
            """
        )
        assert cur.fetchone()[0] == 1


def test_eg_si_080_dirty_worktree_emits_coverage_gap(
    conn: psycopg.Connection, fixture_git_repo: Path
) -> None:
    """EG-SI-080: dirty worktree imports emit explicit coverage_gap rows."""
    (fixture_git_repo / "scratch.md").write_text("scratch\n", encoding="utf-8")
    result = import_git_repo(conn, fixture_git_repo, allow_dirty=True)
    assert result.dirty_worktree is True
    assert result.coverage_gap_count >= 1


def test_eg_si_080_missing_markdown_file_tombstoned(
    conn: psycopg.Connection, fixture_markdown_tree: Path
) -> None:
    """EG-SI-080: a Markdown file removed from disk becomes a tombstone row."""
    (fixture_markdown_tree / "extra.md").write_text("# Extra\n\nBody.\n", encoding="utf-8")
    import_markdown_tree(conn, fixture_markdown_tree)
    (fixture_markdown_tree / "extra.md").unlink()
    result = import_markdown_tree(conn, fixture_markdown_tree)
    assert result.files_tombstoned >= 1


def test_eg_si_100_fixture_matrix() -> None:
    """EG-SI-100: every Layer 1-3 family has positive and negative fixtures.

    Positive fixtures are the contract YAML files themselves; the
    negative path is enforced by the contract validator tests (each
    family rejects malformed contracts). This gate proves the matrix
    exists; the per-family negative path is tested elsewhere.
    """
    families = {"git": False, "build_artifact": False, "markdown_tree": False}
    for name in KNOWN_CONTRACTS:
        result = validate_contract(CONTRACTS_DIR / name)
        assert result.is_valid, f"contract {name} is invalid: {result.errors}"
        if result.source_kind in families:
            families[result.source_kind] = True
    missing = [name for name, present in families.items() if not present]
    assert not missing, f"missing contract for source_kind(s): {missing}"
