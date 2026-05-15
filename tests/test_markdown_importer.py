"""Tests for the RFC 0050 Layer 3 Markdown / project-doc importer."""

from __future__ import annotations

from pathlib import Path

import psycopg
import pytest

from engram.markdown_import import (
    MarkdownImportError,
    SOURCE_KIND,
    import_markdown_tree,
)


def _make_tree(tmp_path: Path) -> Path:
    root = tmp_path / "vault"
    root.mkdir()
    (root / "README.md").write_text(
        "---\ntitle: Root readme\ntags: [project, intro]\n---\n\n"
        "# Root readme\n\nIntro paragraph.\n\n"
        "## Section A\n\nContent A with [link text](https://example.invalid/a).\n\n"
        "## Section B\n\nContent B with [[wikilink-target]] and #example_tag.\n",
        encoding="utf-8",
    )
    sub = root / "docs"
    sub.mkdir()
    (sub / "design.md").write_text(
        "# Design\n\nSome design notes with `code` and [docs](docs/other.md).\n",
        encoding="utf-8",
    )
    return root


def _count(conn: psycopg.Connection, sql: str, *params: object) -> int:
    with conn.cursor() as cur:
        cur.execute(sql, params)
        row = cur.fetchone()
        return int(row[0]) if row else 0


def test_first_import_inserts_two_files(conn: psycopg.Connection, tmp_path: Path) -> None:
    root = _make_tree(tmp_path)
    result = import_markdown_tree(conn, root)
    assert result.files_inserted == 2
    assert result.files_seen == 2
    assert result.files_skipped == 0
    assert result.chunks_inserted > 0
    assert result.links_inserted > 0
    assert _count(conn, "SELECT COUNT(*) FROM sources WHERE source_kind = %s", SOURCE_KIND) == 1


def test_reimport_is_idempotent(conn: psycopg.Connection, tmp_path: Path) -> None:
    root = _make_tree(tmp_path)
    first = import_markdown_tree(conn, root)
    assert first.files_inserted == 2
    second = import_markdown_tree(conn, root)
    assert second.files_inserted == 0
    assert second.files_skipped == 2


def test_content_drift_tombstones_old_row(
    conn: psycopg.Connection, tmp_path: Path
) -> None:
    root = _make_tree(tmp_path)
    import_markdown_tree(conn, root)
    (root / "README.md").write_text("# Root readme\n\nUpdated body.\n", encoding="utf-8")
    result = import_markdown_tree(conn, root)
    assert result.files_inserted == 1
    assert result.files_tombstoned == 1
    assert _count(
        conn,
        """
        SELECT COUNT(*) FROM markdown_files
        WHERE relative_path = 'README.md' AND superseded_at IS NULL
        """,
    ) == 1
    assert _count(
        conn,
        """
        SELECT COUNT(*) FROM markdown_files
        WHERE relative_path = 'README.md' AND superseded_at IS NOT NULL
        """,
    ) == 1


def test_file_deletion_tombstones_active_row(
    conn: psycopg.Connection, tmp_path: Path
) -> None:
    root = _make_tree(tmp_path)
    import_markdown_tree(conn, root)
    (root / "docs" / "design.md").unlink()
    result = import_markdown_tree(conn, root)
    assert result.files_tombstoned >= 1
    assert _count(
        conn,
        """
        SELECT COUNT(*) FROM markdown_files
        WHERE relative_path = 'docs/design.md' AND superseded_at IS NULL
        """,
    ) == 0


def test_frontmatter_and_title_extracted(
    conn: psycopg.Connection, tmp_path: Path
) -> None:
    root = _make_tree(tmp_path)
    import_markdown_tree(conn, root)
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT title, frontmatter FROM markdown_files
            WHERE relative_path = 'README.md' AND superseded_at IS NULL
            """
        )
        row = cur.fetchone()
    assert row is not None
    title, frontmatter = row
    assert title == "Root readme"
    assert frontmatter["title"] == "Root readme"
    assert "project" in frontmatter["tags"]


def test_chunks_have_anchors(conn: psycopg.Connection, tmp_path: Path) -> None:
    root = _make_tree(tmp_path)
    import_markdown_tree(conn, root)
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT heading_anchor
            FROM markdown_file_chunks
            WHERE heading_anchor IS NOT NULL
            """
        )
        anchors = {row[0] for row in cur.fetchall()}
    assert {"section-a", "section-b"} <= anchors


def test_links_detected(conn: psycopg.Connection, tmp_path: Path) -> None:
    root = _make_tree(tmp_path)
    import_markdown_tree(conn, root)
    with conn.cursor() as cur:
        cur.execute(
            "SELECT DISTINCT link_kind FROM markdown_file_links ORDER BY 1"
        )
        kinds = {row[0] for row in cur.fetchall()}
    assert {"inline_url", "wikilink", "tag"} <= kinds


def test_root_not_a_directory_raises(conn: psycopg.Connection, tmp_path: Path) -> None:
    with pytest.raises(MarkdownImportError):
        import_markdown_tree(conn, tmp_path / "missing")


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
    root = _make_tree(tmp_path)
    import_markdown_tree(conn, root)
    assert seen == [], f"unexpected sockets created during import: {seen}"


def test_dry_run_does_not_insert(conn: psycopg.Connection, tmp_path: Path) -> None:
    root = _make_tree(tmp_path)
    result = import_markdown_tree(conn, root, dry_run=True)
    assert result.files_inserted == 0
    assert _count(conn, "SELECT COUNT(*) FROM markdown_files") == 0
