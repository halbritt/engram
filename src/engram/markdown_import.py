"""Markdown / project-doc importer (RFC 0050 Layer 3).

Walks a local Markdown directory tree and projects file identity, frontmatter,
headings/anchors, chunks, and links. Idempotent re-import: a file whose content
hash matches an existing active row is a no-op. A content drift on an existing
``(root, relative_path)`` triggers a tombstone+replace: the old row's
``superseded_at`` is set and a new row lands.

Identity strategy: ``(markdown_root_id, relative_path, content_hash)`` where
``markdown_root_id`` is the sha256 over the resolved root path. Renames are
visible as: the old path's active row gains a tombstone (with
``superseded_by`` pointing at the new path's row), and a fresh active row
exists for the new path. The old raw row is never rewritten.
"""

from __future__ import annotations

import hashlib
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import psycopg
import yaml  # type: ignore[import-not-found]
from psycopg.types.json import Jsonb

SOURCE_KIND = "markdown_tree"
ADAPTER_VERSION = "markdown_import.v1"
DEFAULT_TENANT_ID = "personal"
DEFAULT_CORPUS_ID = "personal"

ENGRAM_MARKDOWN_MAX_BYTES = int(
    os.environ.get("ENGRAM_MARKDOWN_MAX_BYTES", str(2 * 1024 * 1024))  # 2 MiB
)
ENGRAM_MARKDOWN_FILE_EXTENSIONS = tuple(
    ext.strip()
    for ext in os.environ.get("ENGRAM_MARKDOWN_FILE_EXTENSIONS", ".md,.markdown,.mdx").split(",")
    if ext.strip()
)
ENGRAM_MARKDOWN_IGNORE_DIRS = tuple(
    name.strip()
    for name in os.environ.get(
        "ENGRAM_MARKDOWN_IGNORE_DIRS", ".git,node_modules,.venv,.tox,__pycache__"
    ).split(",")
    if name.strip()
)

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", re.DOTALL)
_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$", re.MULTILINE)
_INLINE_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
_WIKILINK_RE = re.compile(r"\[\[([^\]]+)\]\]")
_IMAGE_RE = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")
_AUTOLINK_RE = re.compile(r"<((?:https?://|mailto:)[^>]+)>")
_TAG_RE = re.compile(r"(?<![\w/])#([A-Za-z][A-Za-z0-9_/-]+)")


class MarkdownImportError(RuntimeError):
    """Root of the Markdown import exception family."""


@dataclass(frozen=True)
class MarkdownChunk:
    chunk_index: int
    heading_level: int | None
    heading_anchor: str | None
    heading_text: str | None
    body_text: str


@dataclass(frozen=True)
class MarkdownLink:
    link_index: int
    link_kind: str
    text: str | None
    target: str | None


@dataclass(frozen=True)
class MarkdownFileRecord:
    relative_path: str
    content_hash: str
    size_bytes: int
    mtime: datetime | None
    title: str | None
    frontmatter: dict[str, Any]
    body_text: str
    chunks: tuple[MarkdownChunk, ...]
    links: tuple[MarkdownLink, ...]


@dataclass(frozen=True)
class MarkdownImportResult:
    source_id: str
    markdown_root_id: str
    files_inserted: int
    files_seen: int
    files_skipped: int
    files_tombstoned: int
    chunks_inserted: int
    links_inserted: int
    coverage_gap_count: int


def import_markdown_tree(
    conn: psycopg.Connection,
    root: Path,
    *,
    tenant_id: str = DEFAULT_TENANT_ID,
    corpus_id: str = DEFAULT_CORPUS_ID,
    repo_label: str | None = None,
    dry_run: bool = False,
) -> MarkdownImportResult:
    """Walk ``root`` and ingest Markdown files into Engram."""
    if tenant_id.strip() == "" or corpus_id.strip() == "":
        raise ValueError("tenant_id and corpus_id must be non-empty")
    root_path = Path(root).expanduser().resolve()
    if not root_path.is_dir():
        raise MarkdownImportError(f"markdown root is not a directory: {root_path}")
    markdown_root_id = _root_id(root_path)
    records = list(_walk_markdown(root_path))

    if dry_run:
        return MarkdownImportResult(
            source_id="",
            markdown_root_id=markdown_root_id,
            files_inserted=0,
            files_seen=len(records),
            files_skipped=0,
            files_tombstoned=0,
            chunks_inserted=0,
            links_inserted=0,
            coverage_gap_count=0,
        )

    inserted = 0
    skipped = 0
    tombstoned = 0
    chunks_inserted = 0
    links_inserted = 0

    seen_paths: set[str] = {r.relative_path for r in records}

    with conn.transaction():
        source_id = _get_or_create_source(
            conn,
            markdown_root_id=markdown_root_id,
            tenant_id=tenant_id,
            corpus_id=corpus_id,
            root_path=root_path,
            repo_label=repo_label,
        )

        # Tombstone files that disappeared from disk before reinsert.
        active_paths = _list_active_paths(
            conn,
            tenant_id=tenant_id,
            corpus_id=corpus_id,
            markdown_root_id=markdown_root_id,
        )
        missing = active_paths - seen_paths
        if missing:
            tombstoned += _tombstone_missing(
                conn,
                tenant_id=tenant_id,
                corpus_id=corpus_id,
                markdown_root_id=markdown_root_id,
                missing_paths=missing,
            )

        for record in records:
            file_id, was_inserted, was_tombstoned = _insert_or_supersede(
                conn,
                source_id=source_id,
                tenant_id=tenant_id,
                corpus_id=corpus_id,
                markdown_root_id=markdown_root_id,
                record=record,
            )
            if was_inserted:
                inserted += 1
            else:
                skipped += 1
            if was_tombstoned:
                tombstoned += 1
            if was_inserted:
                for chunk in record.chunks:
                    if _insert_chunk(
                        conn,
                        file_id=file_id,
                        tenant_id=tenant_id,
                        corpus_id=corpus_id,
                        chunk=chunk,
                    ):
                        chunks_inserted += 1
                for link in record.links:
                    if _insert_link(
                        conn,
                        file_id=file_id,
                        tenant_id=tenant_id,
                        corpus_id=corpus_id,
                        link=link,
                    ):
                        links_inserted += 1

    return MarkdownImportResult(
        source_id=source_id,
        markdown_root_id=markdown_root_id,
        files_inserted=inserted,
        files_seen=len(records),
        files_skipped=skipped,
        files_tombstoned=tombstoned,
        chunks_inserted=chunks_inserted,
        links_inserted=links_inserted,
        coverage_gap_count=0,
    )


# --- discovery + parsing -----------------------------------------------------


def _root_id(root: Path) -> str:
    return hashlib.sha256(str(root).encode("utf-8")).hexdigest()


def _walk_markdown(root: Path):
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(root)
        parts = rel.parts
        if any(part in ENGRAM_MARKDOWN_IGNORE_DIRS for part in parts):
            continue
        if path.suffix.lower() not in ENGRAM_MARKDOWN_FILE_EXTENSIONS:
            continue
        try:
            stat = path.stat()
        except OSError:
            continue
        if stat.st_size > ENGRAM_MARKDOWN_MAX_BYTES:
            continue
        raw = path.read_bytes()
        text = raw.decode("utf-8", errors="replace")
        content_hash = hashlib.sha256(raw).hexdigest()
        mtime = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)
        frontmatter, body = _split_frontmatter(text)
        chunks = _build_chunks(body)
        links = _build_links(body)
        title = _extract_title(frontmatter, chunks)
        yield MarkdownFileRecord(
            relative_path=rel.as_posix(),
            content_hash=content_hash,
            size_bytes=len(raw),
            mtime=mtime,
            title=title,
            frontmatter=frontmatter,
            body_text=body,
            chunks=tuple(chunks),
            links=tuple(links),
        )


def _split_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    match = _FRONTMATTER_RE.match(text)
    if not match:
        return {}, text
    raw_yaml = match.group(1)
    body = match.group(2)
    try:
        parsed = yaml.safe_load(raw_yaml) or {}
        if not isinstance(parsed, dict):
            return {}, text
        return parsed, body
    except yaml.YAMLError:
        return {}, text


def _build_chunks(body: str) -> list[MarkdownChunk]:
    chunks: list[MarkdownChunk] = []
    matches = list(_HEADING_RE.finditer(body))
    if not matches:
        if body.strip():
            chunks.append(
                MarkdownChunk(
                    chunk_index=0,
                    heading_level=None,
                    heading_anchor=None,
                    heading_text=None,
                    body_text=body,
                )
            )
        return chunks
    # First chunk is pre-heading prose (if any).
    if matches[0].start() > 0:
        prelude = body[: matches[0].start()].strip()
        if prelude:
            chunks.append(
                MarkdownChunk(
                    chunk_index=len(chunks),
                    heading_level=None,
                    heading_anchor=None,
                    heading_text=None,
                    body_text=prelude,
                )
            )
    for i, match in enumerate(matches):
        level = len(match.group(1))
        heading_text = match.group(2).strip()
        anchor = _slugify(heading_text)
        end = matches[i + 1].start() if i + 1 < len(matches) else len(body)
        section_body = body[match.end():end].strip("\n")
        chunks.append(
            MarkdownChunk(
                chunk_index=len(chunks),
                heading_level=level,
                heading_anchor=anchor,
                heading_text=heading_text,
                body_text=section_body,
            )
        )
    return chunks


def _build_links(body: str) -> list[MarkdownLink]:
    links: list[MarkdownLink] = []
    index = 0

    def append(link_kind: str, text: str | None, target: str | None) -> None:
        nonlocal index
        links.append(
            MarkdownLink(
                link_index=index,
                link_kind=link_kind,
                text=text,
                target=target,
            )
        )
        index += 1

    for match in _IMAGE_RE.finditer(body):
        append("image", match.group(1) or None, match.group(2).strip())
    for match in _INLINE_LINK_RE.finditer(body):
        # Skip image matches already counted above.
        if body[max(0, match.start() - 1)] == "!":
            continue
        append("inline_url", match.group(1).strip(), match.group(2).strip())
    for match in _WIKILINK_RE.finditer(body):
        target = match.group(1).strip()
        append("wikilink", target, target)
    for match in _AUTOLINK_RE.finditer(body):
        append("autolink", None, match.group(1).strip())
    for match in _TAG_RE.finditer(body):
        append("tag", match.group(1), match.group(1))
    return links


def _slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9\-]+", "-", text.lower()).strip("-")
    return slug or "section"


def _extract_title(frontmatter: dict[str, Any], chunks: list[MarkdownChunk]) -> str | None:
    if isinstance(frontmatter, dict):
        title = frontmatter.get("title")
        if isinstance(title, str) and title.strip():
            return title.strip()
    for chunk in chunks:
        if chunk.heading_level == 1 and chunk.heading_text:
            return chunk.heading_text
    return None


# --- database helpers --------------------------------------------------------


def _get_or_create_source(
    conn: psycopg.Connection,
    *,
    markdown_root_id: str,
    tenant_id: str,
    corpus_id: str,
    root_path: Path,
    repo_label: str | None,
) -> str:
    raw_payload: dict[str, Any] = {
        "markdown_root_id": markdown_root_id,
        "markdown_root_path": str(root_path),
        "adapter_version": ADAPTER_VERSION,
    }
    if repo_label:
        raw_payload["repo_label"] = repo_label
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id FROM sources WHERE source_kind = %s AND external_id = %s
            """,
            (SOURCE_KIND, markdown_root_id),
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
                markdown_root_id,
                str(root_path),
                None,
                Jsonb(raw_payload),
                tenant_id,
                corpus_id,
            ),
        )
        return str(cur.fetchone()[0])


def _list_active_paths(
    conn: psycopg.Connection,
    *,
    tenant_id: str,
    corpus_id: str,
    markdown_root_id: str,
) -> set[str]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT relative_path FROM markdown_files
            WHERE tenant_id = %s
              AND corpus_id = %s
              AND markdown_root_id = %s
              AND superseded_at IS NULL
            """,
            (tenant_id, corpus_id, markdown_root_id),
        )
        return {row[0] for row in cur.fetchall()}


def _insert_or_supersede(
    conn: psycopg.Connection,
    *,
    source_id: str,
    tenant_id: str,
    corpus_id: str,
    markdown_root_id: str,
    record: MarkdownFileRecord,
) -> tuple[str, bool, bool]:
    """Insert a new file row or treat an unchanged file as a no-op.

    Returns ``(file_id, was_inserted, was_tombstoned)``. When the active row's
    content hash differs, the active row is tombstoned and a new active row
    lands; ``was_tombstoned`` is true in that case.
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, content_hash FROM markdown_files
            WHERE tenant_id = %s
              AND corpus_id = %s
              AND markdown_root_id = %s
              AND relative_path = %s
              AND superseded_at IS NULL
            """,
            (tenant_id, corpus_id, markdown_root_id, record.relative_path),
        )
        active = cur.fetchone()
        was_tombstoned = False
        if active is not None:
            active_id, active_hash = str(active[0]), str(active[1])
            if active_hash == record.content_hash:
                return active_id, False, False
            # Content drift: tombstone the active row, fall through to insert.
            was_tombstoned = True

        cur.execute(
            """
            INSERT INTO markdown_files (
                source_id, tenant_id, corpus_id, markdown_root_id, relative_path,
                content_hash, size_bytes, file_mtime, title, frontmatter,
                body_text, adapter_version, privacy_tier, sensitivity_class
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (
                source_id,
                tenant_id,
                corpus_id,
                markdown_root_id,
                record.relative_path,
                record.content_hash,
                record.size_bytes,
                record.mtime,
                record.title,
                Jsonb(_jsonable(record.frontmatter)),
                record.body_text,
                ADAPTER_VERSION,
                1,
                "routine_project",
            ),
        )
        new_id = str(cur.fetchone()[0])

        if was_tombstoned:
            cur.execute(
                """
                UPDATE markdown_files
                SET superseded_at = now(), superseded_by = %s
                WHERE id = %s
                """,
                (new_id, active[0]),
            )
        return new_id, True, was_tombstoned


def _tombstone_missing(
    conn: psycopg.Connection,
    *,
    tenant_id: str,
    corpus_id: str,
    markdown_root_id: str,
    missing_paths: set[str],
) -> int:
    if not missing_paths:
        return 0
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE markdown_files
            SET superseded_at = now()
            WHERE tenant_id = %s
              AND corpus_id = %s
              AND markdown_root_id = %s
              AND relative_path = ANY(%s)
              AND superseded_at IS NULL
            """,
            (tenant_id, corpus_id, markdown_root_id, list(missing_paths)),
        )
        return cur.rowcount or 0


def _insert_chunk(
    conn: psycopg.Connection,
    *,
    file_id: str,
    tenant_id: str,
    corpus_id: str,
    chunk: MarkdownChunk,
) -> bool:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO markdown_file_chunks (
                file_id, tenant_id, corpus_id, chunk_index, heading_level,
                heading_anchor, heading_text, body_text, raw_payload
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (file_id, chunk_index) DO NOTHING
            RETURNING id
            """,
            (
                file_id,
                tenant_id,
                corpus_id,
                chunk.chunk_index,
                chunk.heading_level,
                chunk.heading_anchor,
                chunk.heading_text,
                chunk.body_text,
                Jsonb({}),
            ),
        )
        return cur.fetchone() is not None


def _insert_link(
    conn: psycopg.Connection,
    *,
    file_id: str,
    tenant_id: str,
    corpus_id: str,
    link: MarkdownLink,
) -> bool:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO markdown_file_links (
                file_id, tenant_id, corpus_id, link_index, link_kind,
                text, target, raw_payload
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (file_id, link_index) DO NOTHING
            RETURNING id
            """,
            (
                file_id,
                tenant_id,
                corpus_id,
                link.link_index,
                link.link_kind,
                link.text,
                link.target,
                Jsonb({}),
            ),
        )
        return cur.fetchone() is not None


def _jsonable(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    if isinstance(value, (int, float, str, bool)) or value is None:
        return value
    return str(value)
