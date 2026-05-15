"""Git metadata + diff-stat importer (RFC 0050 Layer 1).

Imports commit metadata, parent links, refs, and per-commit numstat from a
local git repository into Engram's append-only raw evidence tables. Patch
bodies are never persisted in Layer 1; ``ENGRAM_GIT_IMPORT_FULL_PATCH=1`` is
reserved for a future opt-in slice (RFC 0050 OQ-SI-001).

Identity strategy (per RFC 0050 § Identity Split):

- ``source_instance_id`` (repository root identity): a stable sha256 over
  ``"git\0" + first_commit_sha + "\0" + normalized_remote_url``. The first
  commit is the deterministic-but-arbitrary lexicographically smallest root
  reachable via ``git rev-list --max-parents=0 HEAD``. The remote URL is the
  ``origin`` URL (or empty) lowercased with ``.git`` and trailing ``/``
  stripped. This value lands in ``sources.external_id``.
- Item identity keys: ``(repository_id, commit_sha)``.
- Logical identity keys: ``(repository_id, ref_name)`` — refs are recorded
  on the commit row at import time as informational annotations, not
  authoritative state. A future ``git_refs`` table will own ref lifecycle
  when retrieval needs it.

No outbound network. The importer never invokes ``clone``, ``fetch``,
``pull``, ``push``, or ``ls-remote``. ``GIT_TERMINAL_PROMPT=0`` makes any
prompt-bearing operation fail immediately.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import psycopg
from psycopg.types.json import Jsonb

SOURCE_KIND = "git"
DEFAULT_TENANT_ID = "personal"
DEFAULT_CORPUS_ID = "personal"

ENGRAM_GIT_IMPORT_MAX_COMMITS = int(
    os.environ.get("ENGRAM_GIT_IMPORT_MAX_COMMITS", "100000")
)
ENGRAM_GIT_IMPORT_INCLUDE_BODY = (
    os.environ.get("ENGRAM_GIT_IMPORT_INCLUDE_BODY", "1") == "1"
)
ENGRAM_GIT_IMPORT_FULL_PATCH = (
    os.environ.get("ENGRAM_GIT_IMPORT_FULL_PATCH", "0") == "1"
)
ENGRAM_GIT_IMPORT_SUBPROCESS_TIMEOUT_SECONDS = int(
    os.environ.get("ENGRAM_GIT_IMPORT_SUBPROCESS_TIMEOUT_SECONDS", "120")
)
ADAPTER_VERSION = "git_import.v1"

# Closed allowlist of git verbs the importer may invoke. Anything outside
# this set is a routing bug; the no-egress tests pin this list.
GIT_VERB_ALLOWLIST: frozenset[str] = frozenset({
    "rev-parse",
    "rev-list",
    "log",
    "show",
    "status",
    "for-each-ref",
    "cat-file",
    "ls-tree",
    "config",
})

# Separators used in ``git log --pretty=format`` output. The literal escape
# sequences ``%x1e`` / ``%x00`` are accepted by git; we pass them as text to
# avoid embedding NUL bytes in subprocess argv (Python rejects NUL in argv).
_RECORD_SEPARATOR_FMT = "%x1e"
_FIELD_SEPARATOR_FMT = "%x00"
_RECORD_SEPARATOR = "\x1e"
_FIELD_SEPARATOR = "\x00"


class GitImportError(RuntimeError):
    """Root of the git import exception family."""


class GitRepositoryNotFoundError(GitImportError):
    """Raised when the target path is not a git work tree."""


class GitSubprocessError(GitImportError):
    """Raised when a git subprocess invocation fails or times out."""


class GitParseError(GitImportError):
    """Raised when git output cannot be parsed into the expected shape."""


class GitImportConflict(GitImportError):
    """Raised when an existing commit row's content hash differs from input."""


class GitDirtyWorktreeError(GitImportError):
    """Raised when --allow-dirty is false and the work tree is dirty."""


@dataclass(frozen=True)
class GitCommitMetadata:
    """Validated commit metadata extracted from ``git log``."""

    commit_sha: str
    tree_sha: str
    parent_shas: tuple[str, ...]
    author_name: str | None
    author_email: str | None
    author_date: datetime
    committer_name: str | None
    committer_email: str | None
    committer_date: datetime
    subject: str
    body: str
    refs: tuple[str, ...]
    raw_payload: dict[str, Any]
    content_hash: str


@dataclass(frozen=True)
class GitCommitPath:
    """One ``--numstat`` row associated with a commit."""

    change_index: int
    change_kind: str
    old_path: str | None
    new_path: str | None
    additions: int | None
    deletions: int | None
    is_binary: bool


@dataclass(frozen=True)
class GitImportResult:
    """Summary of one ``import_git_repo`` invocation."""

    source_id: str
    repository_id: str
    commits_inserted: int
    commits_seen: int
    commits_skipped: int
    paths_inserted: int
    coverage_gap_count: int
    dirty_worktree: bool


def import_git_repo(
    conn: psycopg.Connection,
    repo_path: Path,
    *,
    tenant_id: str = DEFAULT_TENANT_ID,
    corpus_id: str = DEFAULT_CORPUS_ID,
    repo_label: str | None = None,
    allow_dirty: bool = False,
    dry_run: bool = False,
) -> GitImportResult:
    """Import commit metadata and diff stats from a local git repository.

    The importer is idempotent on re-import: a commit whose content hash
    matches an existing row is a no-op. A content-hash mismatch raises
    ``GitImportConflict`` (callers decide whether to tombstone).
    """
    if tenant_id.strip() == "" or corpus_id.strip() == "":
        raise ValueError("tenant_id and corpus_id must be non-empty")

    repo = Path(repo_path).expanduser().resolve()
    if not (repo / ".git").exists():
        raise GitRepositoryNotFoundError(f"not a git repository: {repo}")

    _require_inside_worktree(repo)

    dirty = _is_dirty_worktree(repo)
    if dirty and not allow_dirty:
        raise GitDirtyWorktreeError(
            f"dirty worktree at {repo}; pass allow_dirty=True to ingest anyway"
        )

    root_commit = _resolve_root_commit(repo)
    remote_url = _normalized_remote_url(repo)
    repository_id = _repository_id(root_commit, remote_url)

    refs_by_commit = _collect_refs(repo)

    commits = _walk_commits(repo, refs_by_commit=refs_by_commit)
    if len(commits) > ENGRAM_GIT_IMPORT_MAX_COMMITS:
        raise GitParseError(
            f"repository has {len(commits)} commits; raise ENGRAM_GIT_IMPORT_MAX_COMMITS to ingest"
        )

    if dry_run:
        return GitImportResult(
            source_id="",
            repository_id=repository_id,
            commits_inserted=0,
            commits_seen=len(commits),
            commits_skipped=0,
            paths_inserted=0,
            coverage_gap_count=0,
            dirty_worktree=dirty,
        )

    with conn.transaction():
        source_id = _get_or_create_source(
            conn,
            repository_id=repository_id,
            tenant_id=tenant_id,
            corpus_id=corpus_id,
            repo_label=repo_label,
            repo_path=repo,
            remote_url=remote_url,
            root_commit=root_commit,
            dirty=dirty,
        )
        inserted = 0
        skipped = 0
        paths_inserted = 0
        coverage_gap_count = 0

        for commit in commits:
            commit_id, was_inserted = _insert_commit(
                conn,
                source_id=source_id,
                tenant_id=tenant_id,
                corpus_id=corpus_id,
                repository_id=repository_id,
                commit=commit,
            )
            if was_inserted:
                inserted += 1
            else:
                skipped += 1

            try:
                paths = _parse_numstat(_run_git_numstat(repo, commit.commit_sha))
            except GitParseError:
                _emit_coverage_gap(
                    conn,
                    source_id=source_id,
                    tenant_id=tenant_id,
                    corpus_id=corpus_id,
                    repository_id=repository_id,
                    commit_sha=commit.commit_sha,
                    reason="numstat_parse_failed",
                )
                coverage_gap_count += 1
                continue

            for path in paths:
                if _insert_commit_path(
                    conn,
                    commit_id=commit_id,
                    tenant_id=tenant_id,
                    corpus_id=corpus_id,
                    path=path,
                ):
                    paths_inserted += 1

        if dirty:
            _emit_coverage_gap(
                conn,
                source_id=source_id,
                tenant_id=tenant_id,
                corpus_id=corpus_id,
                repository_id=repository_id,
                commit_sha="dirty_worktree",
                reason="dirty_worktree",
            )
            coverage_gap_count += 1

    return GitImportResult(
        source_id=source_id,
        repository_id=repository_id,
        commits_inserted=inserted,
        commits_seen=len(commits),
        commits_skipped=skipped,
        paths_inserted=paths_inserted,
        coverage_gap_count=coverage_gap_count,
        dirty_worktree=dirty,
    )


# --- git subprocess helpers --------------------------------------------------


def _run_git(repo: Path, *args: str) -> str:
    """Invoke ``git`` with a minimised environment, returning stdout."""
    verb = args[0] if args else ""
    if verb not in GIT_VERB_ALLOWLIST:
        raise GitSubprocessError(
            f"git verb not in allowlist (no-egress invariant): {verb}"
        )
    env = {
        "PATH": os.environ.get("PATH", ""),
        "LC_ALL": "C",
        "GIT_TERMINAL_PROMPT": "0",
    }
    try:
        completed = subprocess.run(
            ["git", *args],
            cwd=str(repo),
            check=True,
            capture_output=True,
            text=True,
            env=env,
            timeout=ENGRAM_GIT_IMPORT_SUBPROCESS_TIMEOUT_SECONDS,
        )
    except subprocess.CalledProcessError as exc:
        raise GitSubprocessError(
            f"git {' '.join(args)} failed (exit {exc.returncode}): {exc.stderr.strip()}"
        ) from exc
    except subprocess.TimeoutExpired as exc:
        raise GitSubprocessError(
            f"git {' '.join(args)} timed out after {ENGRAM_GIT_IMPORT_SUBPROCESS_TIMEOUT_SECONDS}s"
        ) from exc
    return completed.stdout


def _require_inside_worktree(repo: Path) -> None:
    out = _run_git(repo, "rev-parse", "--is-inside-work-tree").strip()
    if out != "true":
        raise GitRepositoryNotFoundError(f"not inside a git work tree: {repo}")


def _is_dirty_worktree(repo: Path) -> bool:
    out = _run_git(repo, "status", "--porcelain=v1")
    return out.strip() != ""


def _resolve_root_commit(repo: Path) -> str:
    out = _run_git(repo, "rev-list", "--max-parents=0", "HEAD")
    roots = [line.strip() for line in out.splitlines() if line.strip()]
    if not roots:
        raise GitRepositoryNotFoundError(f"repository has no commits: {repo}")
    # Deterministic-but-arbitrary tiebreak: lexicographically smallest root SHA.
    roots.sort()
    return roots[0]


def _normalized_remote_url(repo: Path) -> str:
    try:
        out = _run_git(repo, "config", "--get", "remote.origin.url").strip()
    except GitSubprocessError:
        return ""
    url = out.strip().lower()
    if url.endswith(".git"):
        url = url[: -len(".git")]
    return url.rstrip("/")


def _repository_id(root_commit: str, remote_url: str) -> str:
    payload = f"git{_FIELD_SEPARATOR}{root_commit}{_FIELD_SEPARATOR}{remote_url}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _collect_refs(repo: Path) -> dict[str, list[str]]:
    """Return a mapping ``commit_sha -> [ref names]`` for branches and tags."""
    out = _run_git(repo, "for-each-ref", "--format=%(refname:short)%09%(objectname)")
    result: dict[str, list[str]] = {}
    for line in out.splitlines():
        if "\t" not in line:
            continue
        ref_name, sha = line.split("\t", 1)
        ref_name = ref_name.strip()
        sha = sha.strip()
        if not ref_name or not sha:
            continue
        # Resolve annotated tags to their target commit.
        peeled = _run_git(repo, "rev-parse", f"{sha}^{{commit}}").strip()
        result.setdefault(peeled, []).append(ref_name)
    return result


def _walk_commits(
    repo: Path, *, refs_by_commit: dict[str, list[str]]
) -> list[GitCommitMetadata]:
    """Walk all commits in ``--reverse`` order and produce metadata."""
    fmt = _FIELD_SEPARATOR_FMT.join(
        [
            "%H",  # commit sha
            "%T",  # tree sha
            "%P",  # parent shas (space separated)
            "%an",  # author name
            "%ae",  # author email
            "%aI",  # author date (ISO 8601 strict)
            "%cn",  # committer name
            "%ce",  # committer email
            "%cI",  # committer date
            "%B",  # full message
        ]
    ) + _RECORD_SEPARATOR_FMT
    out = _run_git(repo, "log", "--all", "--reverse", f"--pretty=format:{fmt}")
    records = [rec for rec in out.split(_RECORD_SEPARATOR) if rec.strip()]
    commits: list[GitCommitMetadata] = []
    for record in records:
        parts = record.lstrip("\n").split(_FIELD_SEPARATOR)
        if len(parts) < 10:
            raise GitParseError(f"unexpected git log record shape: {parts!r}")
        (
            commit_sha,
            tree_sha,
            parents_text,
            author_name,
            author_email,
            author_date_text,
            committer_name,
            committer_email,
            committer_date_text,
            message_text,
        ) = parts[:10]
        parent_shas = tuple(p for p in parents_text.strip().split() if p)
        try:
            author_date = datetime.fromisoformat(author_date_text)
            committer_date = datetime.fromisoformat(committer_date_text)
        except ValueError as exc:
            raise GitParseError(f"bad commit date for {commit_sha}: {exc}") from exc
        subject, _, body = message_text.partition("\n\n")
        subject = subject.strip("\n")
        body = body if ENGRAM_GIT_IMPORT_INCLUDE_BODY else ""
        refs = tuple(sorted(refs_by_commit.get(commit_sha, [])))
        raw_payload = {
            "author": {"name": author_name, "email": author_email},
            "committer": {"name": committer_name, "email": committer_email},
            "refs": list(refs),
            "adapter_version": ADAPTER_VERSION,
        }
        canonical_payload = _canonical_commit_payload(
            commit_sha=commit_sha,
            tree_sha=tree_sha,
            parent_shas=parent_shas,
            author_name=author_name,
            author_email=author_email,
            author_date=author_date,
            committer_name=committer_name,
            committer_email=committer_email,
            committer_date=committer_date,
            subject=subject,
            body=body,
            refs=refs,
        )
        content_hash = hashlib.sha256(
            json.dumps(canonical_payload, sort_keys=True, separators=(",", ":")).encode(
                "utf-8"
            )
        ).hexdigest()
        commits.append(
            GitCommitMetadata(
                commit_sha=commit_sha,
                tree_sha=tree_sha,
                parent_shas=parent_shas,
                author_name=author_name or None,
                author_email=author_email or None,
                author_date=author_date,
                committer_name=committer_name or None,
                committer_email=committer_email or None,
                committer_date=committer_date,
                subject=subject,
                body=body,
                refs=refs,
                raw_payload=raw_payload,
                content_hash=content_hash,
            )
        )
    return commits


def _canonical_commit_payload(
    *,
    commit_sha: str,
    tree_sha: str,
    parent_shas: tuple[str, ...],
    author_name: str,
    author_email: str,
    author_date: datetime,
    committer_name: str,
    committer_email: str,
    committer_date: datetime,
    subject: str,
    body: str,
    refs: tuple[str, ...],
) -> dict[str, Any]:
    return {
        "commit_sha": commit_sha,
        "tree_sha": tree_sha,
        "parent_shas": list(parent_shas),
        "author_name": author_name,
        "author_email": author_email,
        "author_date": author_date.isoformat(),
        "committer_name": committer_name,
        "committer_email": committer_email,
        "committer_date": committer_date.isoformat(),
        "subject": subject,
        "body": body,
        "refs": list(refs),
    }


def _run_git_numstat(repo: Path, commit_sha: str) -> str:
    """Return ``git show --numstat`` output with rename detection enabled."""
    return _run_git(
        repo,
        "show",
        "--no-color",
        "--numstat",
        "--format=",
        "-M",  # detect renames (default 50% similarity)
        "-C",  # detect copies
        "-m",
        "--first-parent",
        commit_sha,
    )


def _parse_numstat(text: str) -> list[GitCommitPath]:
    """Parse ``git show --numstat`` output into ``GitCommitPath`` records."""
    paths: list[GitCommitPath] = []
    for index, line in enumerate(line for line in text.splitlines() if line.strip()):
        # Format: ``additions\tdeletions\tpath`` or rename ``a\td\told => new``.
        # Binary files report ``-`` for both counts.
        parts = line.split("\t")
        if len(parts) < 3:
            raise GitParseError(f"unexpected numstat line: {line!r}")
        additions_text, deletions_text = parts[0], parts[1]
        path_text = "\t".join(parts[2:])
        is_binary = additions_text == "-" and deletions_text == "-"
        additions: int | None
        deletions: int | None
        if is_binary:
            additions = None
            deletions = None
        else:
            try:
                additions = int(additions_text)
                deletions = int(deletions_text)
            except ValueError as exc:
                raise GitParseError(f"bad numstat counts: {line!r}") from exc
        change_kind, old_path, new_path = _classify_path(path_text)
        paths.append(
            GitCommitPath(
                change_index=index,
                change_kind=change_kind,
                old_path=old_path,
                new_path=new_path,
                additions=additions,
                deletions=deletions,
                is_binary=is_binary,
            )
        )
    return paths


def _classify_path(path_text: str) -> tuple[str, str | None, str | None]:
    """Return ``(change_kind, old_path, new_path)`` from a numstat path."""
    # git emits ``{old => new}`` for renames within a directory and
    # ``old => new`` for top-level renames.
    if " => " in path_text:
        # Strip the brace form: ``a/{old => new}/b`` -> two paths.
        if "{" in path_text and "}" in path_text:
            before, _, rest = path_text.partition("{")
            inner, _, after = rest.partition("}")
            old_inner, _, new_inner = inner.partition(" => ")
            old_path = (before + old_inner + after).replace("//", "/").strip("/")
            new_path = (before + new_inner + after).replace("//", "/").strip("/")
        else:
            old_path, _, new_path = path_text.partition(" => ")
        return ("rename", old_path.strip() or None, new_path.strip() or None)
    return ("modify", None, path_text.strip() or None)


# --- database helpers --------------------------------------------------------


def _get_or_create_source(
    conn: psycopg.Connection,
    *,
    repository_id: str,
    tenant_id: str,
    corpus_id: str,
    repo_label: str | None,
    repo_path: Path,
    remote_url: str,
    root_commit: str,
    dirty: bool,
) -> str:
    raw_payload: dict[str, Any] = {
        "repository_id": repository_id,
        "remote_url": remote_url,
        "root_commit_sha": root_commit,
        "adapter_version": ADAPTER_VERSION,
        "dirty_worktree": dirty,
    }
    if repo_label:
        raw_payload["repo_label"] = repo_label

    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id FROM sources WHERE source_kind = %s AND external_id = %s
            """,
            (SOURCE_KIND, repository_id),
        )
        row = cur.fetchone()
        if row is not None:
            return str(row[0])
        cur.execute(
            """
            INSERT INTO sources (
                source_kind, external_id, filesystem_path, content_hash,
                raw_payload, tenant_id, corpus_id
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (
                SOURCE_KIND,
                repository_id,
                str(repo_path),
                None,
                Jsonb(raw_payload),
                tenant_id,
                corpus_id,
            ),
        )
        new_row = cur.fetchone()
        assert new_row is not None
        return str(new_row[0])


def _insert_commit(
    conn: psycopg.Connection,
    *,
    source_id: str,
    tenant_id: str,
    corpus_id: str,
    repository_id: str,
    commit: GitCommitMetadata,
) -> tuple[str, bool]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, content_hash FROM git_commits
            WHERE tenant_id = %s
              AND corpus_id = %s
              AND repository_id = %s
              AND commit_sha = %s
            """,
            (tenant_id, corpus_id, repository_id, commit.commit_sha),
        )
        existing = cur.fetchone()
        if existing is not None:
            existing_id, existing_hash = str(existing[0]), str(existing[1])
            if existing_hash != commit.content_hash:
                raise GitImportConflict(
                    f"commit {commit.commit_sha} content_hash drift: "
                    f"existing={existing_hash} new={commit.content_hash}"
                )
            return existing_id, False
        cur.execute(
            """
            INSERT INTO git_commits (
                source_id, tenant_id, corpus_id, repository_id, commit_sha,
                tree_sha, parent_shas, author_name, author_email,
                committer_name, committer_email, author_date, committer_date,
                subject, body, refs, content_hash, adapter_version, privacy_tier,
                raw_payload
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (
                source_id,
                tenant_id,
                corpus_id,
                repository_id,
                commit.commit_sha,
                commit.tree_sha,
                list(commit.parent_shas),
                commit.author_name,
                commit.author_email,
                commit.committer_name,
                commit.committer_email,
                commit.author_date,
                commit.committer_date,
                commit.subject,
                commit.body,
                list(commit.refs),
                commit.content_hash,
                ADAPTER_VERSION,
                1,
                Jsonb(commit.raw_payload),
            ),
        )
        new_row = cur.fetchone()
        assert new_row is not None
        return str(new_row[0]), True


def _insert_commit_path(
    conn: psycopg.Connection,
    *,
    commit_id: str,
    tenant_id: str,
    corpus_id: str,
    path: GitCommitPath,
) -> bool:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO git_commit_paths (
                commit_id, tenant_id, corpus_id, change_index, change_kind,
                old_path, new_path, additions, deletions, is_binary, raw_payload
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (commit_id, change_index) DO NOTHING
            RETURNING id
            """,
            (
                commit_id,
                tenant_id,
                corpus_id,
                path.change_index,
                path.change_kind,
                path.old_path,
                path.new_path,
                path.additions,
                path.deletions,
                path.is_binary,
                Jsonb({}),
            ),
        )
        return cur.fetchone() is not None


def _emit_coverage_gap(
    conn: psycopg.Connection,
    *,
    source_id: str,
    tenant_id: str,
    corpus_id: str,
    repository_id: str,
    commit_sha: str,
    reason: str,
) -> None:
    """Write a ``coverage_gap`` row into ``captures``.

    Layer 1 lands operational families in ``captures`` under
    ``source_kind='git'``. Layer 6 promotes them to queryable views.
    """
    external_id = f"coverage_gap:{repository_id}:{commit_sha}:{reason}"
    payload = {
        "kind": "coverage_gap",
        "reason": reason,
        "repository_id": repository_id,
        "commit_sha": commit_sha,
        "adapter_version": ADAPTER_VERSION,
    }
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO captures (
                source_id, source_kind, external_id, raw_payload, privacy_tier,
                capture_type, content_text, observed_at, tenant_id, corpus_id
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, NULL, %s, %s)
            ON CONFLICT (source_id, external_id) DO NOTHING
            """,
            (
                source_id,
                SOURCE_KIND,
                external_id,
                Jsonb(payload),
                1,
                "reference",
                f"coverage_gap: {reason}",
                tenant_id,
                corpus_id,
            ),
        )
