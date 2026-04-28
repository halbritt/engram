from __future__ import annotations

import hashlib
import io
import json
import zipfile
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import psycopg
from psycopg.types.json import Jsonb


class IngestConflict(RuntimeError):
    """Raised when an immutable raw row would need to change."""


EXPORT_FILE_NAMES = (
    "conversations.json",
    "users.json",
    "projects.json",
    "memories.json",
)


@dataclass(frozen=True)
class ClaudeMessage:
    external_id: str
    sequence_index: int
    role: str | None
    content_text: str | None
    created_at: datetime | None
    raw_payload: dict[str, Any]


@dataclass(frozen=True)
class ClaudeConversation:
    external_id: str
    title: str | None
    created_at: datetime | None
    updated_at: datetime | None
    raw_payload: dict[str, Any]
    messages: list[ClaudeMessage]


@dataclass(frozen=True)
class IngestResult:
    source_id: str
    conversations_inserted: int
    conversations_seen: int
    messages_inserted: int
    messages_seen: int


@dataclass(frozen=True)
class ExportSource:
    """Resolved Claude export — either an extracted directory or a zip archive.

    `identity_path` is what we use as the dedup `external_id` and goes into
    `sources.filesystem_path`. For zip archives this is the zip file path
    itself, so re-running on the same archive is idempotent.
    """

    identity_path: Path
    is_zip: bool
    files: dict[str, bytes]


def ingest_claude_export(conn: psycopg.Connection, path: Path) -> IngestResult:
    export = resolve_export(path)
    manifest = build_manifest(export)
    conversations = list(load_conversations(export))
    validate_unique_payloads(conversations)

    with conn.transaction():
        source_id = get_or_create_source(conn, manifest)
        conversations_before = count_rows(conn, "conversations", source_id)
        messages_before = count_rows(conn, "messages", source_id)

        insert_conversations(conn, source_id, conversations)
        conversation_ids = fetch_conversation_ids(conn, source_id)
        insert_messages(conn, source_id, conversations, conversation_ids)

        conversations_after = count_rows(conn, "conversations", source_id)
        messages_after = count_rows(conn, "messages", source_id)

    return IngestResult(
        source_id=source_id,
        conversations_inserted=conversations_after - conversations_before,
        conversations_seen=len(conversations),
        messages_inserted=messages_after - messages_before,
        messages_seen=sum(len(c.messages) for c in conversations),
    )


def resolve_export(path: Path) -> ExportSource:
    candidate = path.expanduser().resolve()
    if not candidate.exists():
        raise FileNotFoundError(f"Claude export path does not exist: {candidate}")

    if candidate.is_file() and zipfile.is_zipfile(candidate):
        files = read_zip_export(candidate)
        if "conversations.json" not in files:
            raise FileNotFoundError(
                f"Claude export zip {candidate} has no conversations.json"
            )
        return ExportSource(identity_path=candidate, is_zip=True, files=files)

    if candidate.is_dir():
        files = read_directory_export(candidate)
        if "conversations.json" not in files:
            raise FileNotFoundError(
                f"Claude export directory {candidate} has no conversations.json"
            )
        return ExportSource(identity_path=candidate, is_zip=False, files=files)

    raise FileNotFoundError(
        f"Claude export path {candidate} is neither a directory nor a zip archive"
    )


def read_zip_export(zip_path: Path) -> dict[str, bytes]:
    files: dict[str, bytes] = {}
    with zipfile.ZipFile(zip_path) as zf:
        for info in zf.infolist():
            if info.is_dir():
                continue
            name = Path(info.filename).name
            if name in EXPORT_FILE_NAMES and name not in files:
                with zf.open(info) as handle:
                    files[name] = handle.read()
    return files


def read_directory_export(directory: Path) -> dict[str, bytes]:
    files: dict[str, bytes] = {}
    for name in EXPORT_FILE_NAMES:
        path = directory / name
        if path.exists() and path.is_file():
            files[name] = path.read_bytes()
    return files


def build_manifest(export: ExportSource) -> dict[str, Any]:
    digest = hashlib.sha256()
    entries: list[dict[str, Any]] = []
    for name in EXPORT_FILE_NAMES:
        payload = export.files.get(name)
        if payload is None:
            continue
        file_hash = hashlib.sha256(payload).hexdigest()
        digest.update(name.encode("utf-8"))
        digest.update(b"\0")
        digest.update(file_hash.encode("ascii"))
        digest.update(b"\0")
        entries.append(
            {
                "path": name,
                "size": len(payload),
                "sha256": file_hash,
            }
        )
    return {
        "source_kind": "claude",
        "external_id": str(export.identity_path),
        "filesystem_path": str(export.identity_path),
        "container": "zip" if export.is_zip else "directory",
        "content_hash": digest.hexdigest(),
        "file_count": len(entries),
        "files": entries,
    }


def load_conversations(export: ExportSource) -> Iterable[ClaudeConversation]:
    raw = export.files.get("conversations.json")
    if raw is None:
        raise FileNotFoundError("Claude export is missing conversations.json")
    payload = json.loads(io.BytesIO(raw).read().decode("utf-8"))
    if not isinstance(payload, list):
        raise ValueError("conversations.json must contain a JSON array")
    for item in payload:
        yield parse_conversation(item)


def parse_conversation(payload: dict[str, Any]) -> ClaudeConversation:
    external_id = payload.get("uuid")
    if not external_id:
        raise ValueError("Claude conversation is missing uuid")
    return ClaudeConversation(
        external_id=str(external_id),
        title=payload.get("name"),
        created_at=parse_timestamp(payload.get("created_at")),
        updated_at=parse_timestamp(payload.get("updated_at")),
        raw_payload=payload,
        messages=parse_messages(str(external_id), payload.get("chat_messages") or []),
    )


def parse_messages(
    conversation_external_id: str,
    chat_messages: list[Any],
) -> list[ClaudeMessage]:
    messages: list[ClaudeMessage] = []
    for index, message in enumerate(chat_messages):
        if not isinstance(message, dict):
            continue
        source_message_id = message.get("uuid") or index
        message_external_id = f"{conversation_external_id}:{source_message_id}"
        messages.append(
            ClaudeMessage(
                external_id=str(message_external_id),
                sequence_index=index,
                role=message.get("sender"),
                content_text=extract_content_text(message),
                created_at=parse_timestamp(message.get("created_at")),
                raw_payload=message,
            )
        )
    return messages


def validate_unique_payloads(conversations: list[ClaudeConversation]) -> None:
    conversation_hashes: dict[str, str] = {}
    message_hashes: dict[str, str] = {}
    for conversation in conversations:
        conversation_hash = payload_hash(conversation.raw_payload)
        existing_conversation_hash = conversation_hashes.setdefault(
            conversation.external_id,
            conversation_hash,
        )
        if existing_conversation_hash != conversation_hash:
            raise IngestConflict(
                "Claude export contains duplicate conversation external_id "
                f"with different content: {conversation.external_id}"
            )
        for message in conversation.messages:
            message_hash = payload_hash(message.raw_payload)
            existing_message_hash = message_hashes.setdefault(
                message.external_id,
                message_hash,
            )
            if existing_message_hash != message_hash:
                raise IngestConflict(
                    "Claude export contains duplicate message external_id "
                    f"with different content: {message.external_id}"
                )


def payload_hash(payload: dict[str, Any]) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def extract_content_text(message: dict[str, Any]) -> str | None:
    content = message.get("content")
    if isinstance(content, list) and content:
        pieces: list[str] = []
        for part in content:
            piece = content_part_text(part)
            if piece:
                pieces.append(piece)
        text = "\n".join(pieces).strip()
        if text:
            return text
    fallback = message.get("text")
    if isinstance(fallback, str):
        text = fallback.strip()
        return text or None
    return None


def content_part_text(part: Any) -> str | None:
    if not isinstance(part, dict):
        return None
    part_type = part.get("type")
    if part_type == "text":
        text = part.get("text")
        if isinstance(text, str):
            return text
        return None
    if part_type == "tool_use":
        name = part.get("name") or "tool"
        return f"[tool_use:{name}]"
    if part_type == "tool_result":
        name = part.get("name") or "tool"
        nested = part.get("content")
        if isinstance(nested, list):
            nested_pieces = [content_part_text(item) for item in nested]
            joined = "\n".join(piece for piece in nested_pieces if piece).strip()
            if joined:
                return f"[tool_result:{name}]\n{joined}"
        return f"[tool_result:{name}]"
    if part_type:
        return f"[{part_type}]"
    return None


def parse_timestamp(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, int | float):
        return datetime.fromtimestamp(value, tz=UTC)
    if isinstance(value, str):
        normalized = value.removesuffix("Z") + "+00:00" if value.endswith("Z") else value
        try:
            return datetime.fromisoformat(normalized)
        except ValueError:
            return None
    return None


def get_or_create_source(conn: psycopg.Connection, manifest: dict[str, Any]) -> str:
    row = conn.execute(
        """
        INSERT INTO sources (
            source_kind,
            external_id,
            filesystem_path,
            content_hash,
            raw_payload
        )
        VALUES ('claude', %s, %s, %s, %s)
        ON CONFLICT (source_kind, external_id) DO NOTHING
        RETURNING id
        """,
        (
            manifest["external_id"],
            manifest["filesystem_path"],
            manifest["content_hash"],
            Jsonb(manifest),
        ),
    ).fetchone()
    if row:
        return str(row[0])

    existing = conn.execute(
        """
        SELECT id, content_hash, raw_payload
        FROM sources
        WHERE source_kind = 'claude' AND external_id = %s
        """,
        (manifest["external_id"],),
    ).fetchone()
    if not existing:
        raise IngestConflict(
            "Claude source insert conflicted but no existing source row was found "
            f"for {manifest['external_id']}"
        )

    source_id, existing_hash, existing_payload = existing
    if existing_hash != manifest["content_hash"]:
        raise IngestConflict(
            "Claude source content hash differs from immutable source row "
            f"for {manifest['external_id']}"
        )
    if existing_payload != manifest:
        raise IngestConflict(
            "Claude source manifest differs from immutable source row "
            f"for {manifest['external_id']}"
        )
    return str(source_id)


def count_rows(conn: psycopg.Connection, table: str, source_id: str) -> int:
    return conn.execute(
        f"SELECT count(*) FROM {table} WHERE source_id = %s",
        (source_id,),
    ).fetchone()[0]


def insert_conversations(
    conn: psycopg.Connection,
    source_id: str,
    conversations: list[ClaudeConversation],
) -> None:
    rows = [
        (
            source_id,
            conversation.external_id,
            Jsonb(conversation.raw_payload),
            conversation.title,
            conversation.created_at,
            conversation.updated_at,
        )
        for conversation in conversations
    ]
    with conn.cursor() as cur:
        cur.executemany(
            """
            INSERT INTO conversations (
                source_id,
                source_kind,
                external_id,
                raw_payload,
                title,
                created_at,
                updated_at
            )
            VALUES (%s, 'claude', %s, %s, %s, %s, %s)
            ON CONFLICT (source_id, external_id) DO NOTHING
            """,
            rows,
        )


def fetch_conversation_ids(conn: psycopg.Connection, source_id: str) -> dict[str, str]:
    return {
        external_id: str(conversation_id)
        for external_id, conversation_id in conn.execute(
            """
            SELECT external_id, id
            FROM conversations
            WHERE source_id = %s
            """,
            (source_id,),
        ).fetchall()
    }


def insert_messages(
    conn: psycopg.Connection,
    source_id: str,
    conversations: list[ClaudeConversation],
    conversation_ids: dict[str, str],
) -> None:
    sql = """
        INSERT INTO messages (
            source_id,
            source_kind,
            conversation_id,
            external_id,
            raw_payload,
            role,
            content_text,
            created_at,
            sequence_index
        )
        VALUES (%s, 'claude', %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (source_id, external_id) DO NOTHING
    """
    batch: list[tuple[Any, ...]] = []
    with conn.cursor() as cur:
        for conversation in conversations:
            conversation_id = conversation_ids[conversation.external_id]
            for message in conversation.messages:
                batch.append(
                    (
                        source_id,
                        conversation_id,
                        message.external_id,
                        Jsonb(message.raw_payload),
                        message.role,
                        message.content_text,
                        message.created_at,
                        message.sequence_index,
                    )
                )
                if len(batch) >= 1000:
                    cur.executemany(sql, batch)
                    batch.clear()
        if batch:
            cur.executemany(sql, batch)
