"""Tests for the RFC 0050 Layer 1 git metadata + diff-stat importer."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import psycopg
import pytest

from engram.git_import import (
    GitDirtyWorktreeError,
    GitImportConflict,
    GitImportError,
    GitRepositoryNotFoundError,
    SOURCE_KIND,
    import_git_repo,
)

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


def _run_git(repo: Path, *args: str, env_overrides: dict[str, str] | None = None) -> None:
    env = dict(GIT_ENV)
    if env_overrides:
        env.update(env_overrides)
    subprocess.run(
        ["git", *args],
        cwd=str(repo),
        check=True,
        capture_output=True,
        text=True,
        env=env,
    )


def make_fixture_repo(tmp_path: Path) -> Path:
    """Create a minimal git repo with two commits, a branch, a tag, and a rename."""
    repo = tmp_path / "fixture_git"
    repo.mkdir()
    _run_git(repo, "init", "--initial-branch=main")
    _run_git(repo, "config", "user.email", "test@example.invalid")
    _run_git(repo, "config", "user.name", "Test")
    _run_git(repo, "config", "commit.gpgsign", "false")
    (repo / "README.md").write_text("first\nsecond\nthird\nfourth\nfifth\n", encoding="utf-8")
    _run_git(repo, "add", "README.md")
    _run_git(repo, "commit", "-m", "initial commit")
    _run_git(repo, "mv", "README.md", "renamed.md")
    _run_git(
        repo,
        "commit",
        "-am",
        "rename README to renamed",
        env_overrides={
            "GIT_AUTHOR_DATE": "2024-01-02T00:00:00+00:00",
            "GIT_COMMITTER_DATE": "2024-01-02T00:00:00+00:00",
        },
    )
    _run_git(repo, "checkout", "-b", "feature/branch")
    _run_git(repo, "tag", "-a", "v0.1.0", "-m", "v0.1.0")
    _run_git(repo, "checkout", "main")
    return repo


def _count(conn: psycopg.Connection, sql: str, *params: object) -> int:
    with conn.cursor() as cur:
        cur.execute(sql, params)
        row = cur.fetchone()
        return int(row[0]) if row else 0


def test_first_import_inserts_two_commits(conn: psycopg.Connection, tmp_path: Path) -> None:
    repo = make_fixture_repo(tmp_path)
    result = import_git_repo(conn, repo)
    assert result.commits_inserted == 2
    assert result.commits_seen == 2
    assert result.commits_skipped == 0
    assert result.paths_inserted >= 2
    assert (
        _count(conn, "SELECT COUNT(*) FROM sources WHERE source_kind = %s", SOURCE_KIND)
        == 1
    )
    assert _count(conn, "SELECT COUNT(*) FROM git_commits") == 2


def test_reimport_is_idempotent(conn: psycopg.Connection, tmp_path: Path) -> None:
    repo = make_fixture_repo(tmp_path)
    first = import_git_repo(conn, repo)
    assert first.commits_inserted == 2
    second = import_git_repo(conn, repo)
    assert second.commits_inserted == 0
    assert second.commits_skipped == 2
    assert _count(conn, "SELECT COUNT(*) FROM git_commits") == 2


def test_rename_detected_as_rename_change_kind(
    conn: psycopg.Connection, tmp_path: Path
) -> None:
    repo = make_fixture_repo(tmp_path)
    import_git_repo(conn, repo)
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT change_kind, old_path, new_path
            FROM git_commit_paths
            WHERE change_kind = 'rename'
            """
        )
        rows = cur.fetchall()
    assert rows, "expected at least one rename path row"
    change_kind, old_path, new_path = rows[0]
    assert change_kind == "rename"
    assert old_path == "README.md"
    assert new_path == "renamed.md"


def test_conflict_on_changed_content_hash(
    conn: psycopg.Connection, tmp_path: Path
) -> None:
    repo = make_fixture_repo(tmp_path)
    import_git_repo(conn, repo)
    # Temporarily disable the append-only triggers to simulate drift.
    with conn.cursor() as cur:
        cur.execute("ALTER TABLE git_commits DISABLE TRIGGER git_commits_no_update")
        cur.execute(
            "UPDATE git_commits SET content_hash = REPEAT('0', 64) WHERE id = "
            "(SELECT id FROM git_commits LIMIT 1)"
        )
        cur.execute("ALTER TABLE git_commits ENABLE TRIGGER git_commits_no_update")
    with pytest.raises(GitImportConflict):
        import_git_repo(conn, repo)


def test_branch_and_tag_refs_recorded(conn: psycopg.Connection, tmp_path: Path) -> None:
    repo = make_fixture_repo(tmp_path)
    import_git_repo(conn, repo)
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT refs FROM git_commits
            ORDER BY committer_date DESC
            LIMIT 1
            """
        )
        row = cur.fetchone()
    assert row is not None
    refs = list(row[0])
    assert "feature/branch" in refs
    assert "v0.1.0" in refs


def test_dirty_worktree_raises_without_allow_dirty(
    conn: psycopg.Connection, tmp_path: Path
) -> None:
    repo = make_fixture_repo(tmp_path)
    (repo / "untracked.md").write_text("untracked\n", encoding="utf-8")
    with pytest.raises(GitDirtyWorktreeError):
        import_git_repo(conn, repo)


def test_dirty_worktree_with_allow_dirty_emits_coverage_gap(
    conn: psycopg.Connection, tmp_path: Path
) -> None:
    repo = make_fixture_repo(tmp_path)
    (repo / "untracked.md").write_text("untracked\n", encoding="utf-8")
    result = import_git_repo(conn, repo, allow_dirty=True)
    assert result.dirty_worktree is True
    assert result.coverage_gap_count >= 1
    assert (
        _count(
            conn,
            "SELECT COUNT(*) FROM captures WHERE source_kind = %s AND external_id LIKE %s",
            SOURCE_KIND,
            "coverage_gap:%dirty_worktree%",
        )
        >= 1
    )


def test_not_a_repository_raises(conn: psycopg.Connection, tmp_path: Path) -> None:
    bogus = tmp_path / "not_a_repo"
    bogus.mkdir()
    with pytest.raises(GitRepositoryNotFoundError):
        import_git_repo(conn, bogus)


def test_dry_run_does_not_insert(conn: psycopg.Connection, tmp_path: Path) -> None:
    repo = make_fixture_repo(tmp_path)
    result = import_git_repo(conn, repo, dry_run=True)
    assert result.commits_inserted == 0
    assert _count(conn, "SELECT COUNT(*) FROM git_commits") == 0
    assert _count(conn, "SELECT COUNT(*) FROM sources WHERE source_kind = %s", SOURCE_KIND) == 0


def test_subprocess_args_only_use_allowlisted_git_verbs(
    monkeypatch: pytest.MonkeyPatch, conn: psycopg.Connection, tmp_path: Path
) -> None:
    repo = make_fixture_repo(tmp_path)
    recorded: list[str] = []
    real_run = subprocess.run

    def recording_run(cmd, *args, **kwargs):  # type: ignore[no-untyped-def]
        if isinstance(cmd, list) and cmd and cmd[0] == "git":
            recorded.append(cmd[1] if len(cmd) > 1 else "")
        return real_run(cmd, *args, **kwargs)

    monkeypatch.setattr("engram.git_import.subprocess.run", recording_run)
    import_git_repo(conn, repo)
    forbidden = {"clone", "fetch", "pull", "push", "ls-remote", "remote", "submodule", "archive"}
    assert recorded, "expected some git invocations"
    assert not (forbidden & set(recorded)), f"network-touching git verbs invoked: {recorded}"


def test_invalid_tenant_id_raises(conn: psycopg.Connection, tmp_path: Path) -> None:
    repo = make_fixture_repo(tmp_path)
    with pytest.raises(ValueError):
        import_git_repo(conn, repo, tenant_id="   ")
