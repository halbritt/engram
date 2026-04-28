from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import psycopg
from psycopg.types.json import Jsonb


class IngestConflict(RuntimeError):
    """Raised when an immutable raw row would need to change."""


@dataclass(frozen=True)
class ChatGPTMessage:
    external_id: str
    sequence_index: int
    role: str | None
    content_text: str | None
    created_at: datetime | None
    raw_payload: dict[str, Any]


@dataclass(frozen=True)
class ChatGPTConversation:
    external_id: str
    title: str | None
    created_at: datetime | None
    updated_at: datetime | None
    raw_payload: dict[str, Any]
    messages: list[ChatGPTMessage]


@dataclass(frozen=True)
class IngestResult:
    source_id: str
    conversations_inserted: int
    conversations_seen: int
    messages_inserted: int
    messages_seen: int


def ingest_chatgpt_export(conn: psycopg.Connection, path: Path) -> IngestResult:
    export_root = resolve_export_root(path)
    manifest = build_manifest(export_root)
    conversations = list(load_conversations(export_root))
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


def resolve_export_root(path: Path) -> Path:
    candidate = path.expanduser().resolve()
    if not candidate.exists() or not candidate.is_dir():
        raise FileNotFoundError(f"ChatGPT export path is not a directory: {candidate}")
    if is_export_root(candidate):
        return candidate
    child_roots = [child for child in candidate.iterdir() if child.is_dir() and is_export_root(child)]
    if len(child_roots) == 1:
        return child_roots[0]
    raise FileNotFoundError(
        f"Could not find conversations.json or split ChatGPT export files under {candidate}"
    )


def is_export_root(path: Path) -> bool:
    return (
        (path / "conversations.json").exists()
        or (path / "conversation-index.json").exists()
        or (path / "json").is_dir()
    )


def build_manifest(export_root: Path) -> dict[str, Any]:
    files = list(iter_export_payload_files(export_root))
    digest = hashlib.sha256()
    entries: list[dict[str, Any]] = []
    for file_path in files:
        relative = file_path.relative_to(export_root).as_posix()
        file_hash = hash_file(file_path)
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(file_hash.encode("ascii"))
        digest.update(b"\0")
        entries.append(
            {
                "path": relative,
                "size": file_path.stat().st_size,
                "sha256": file_hash,
            }
        )
    return {
        "source_kind": "chatgpt",
        "external_id": str(export_root),
        "filesystem_path": str(export_root),
        "content_hash": digest.hexdigest(),
        "file_count": len(entries),
        "files": entries,
    }


def iter_export_payload_files(export_root: Path) -> Iterable[Path]:
    names = [
        "conversations.json",
        "chat.html",
        "conversation-index.json",
        "projects/project-index.json",
    ]
    for name in names:
        path = export_root / name
        if path.exists() and path.is_file():
            yield path
    yield from sorted((export_root / "json").glob("*.json"))
    yield from sorted((export_root / "projects").glob("*/json/*.json"))


def hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_conversations(export_root: Path) -> Iterable[ChatGPTConversation]:
    classic = export_root / "conversations.json"
    if classic.exists():
        payload = json.loads(classic.read_text(encoding="utf-8"))
        if not isinstance(payload, list):
            raise ValueError(f"{classic} must contain a JSON array")
        for item in payload:
            yield parse_conversation(item)
        return

    json_files = list(sorted((export_root / "json").glob("*.json")))
    json_files.extend(sorted((export_root / "projects").glob("*/json/*.json")))
    if not json_files:
        raise FileNotFoundError(f"No ChatGPT conversation JSON files found in {export_root}")
    for json_file in json_files:
        yield parse_conversation(json.loads(json_file.read_text(encoding="utf-8")))


def parse_conversation(payload: dict[str, Any]) -> ChatGPTConversation:
    external_id = payload.get("conversation_id") or payload.get("id")
    if not external_id:
        raise ValueError("ChatGPT conversation is missing conversation_id/id")
    return ChatGPTConversation(
        external_id=str(external_id),
        title=payload.get("title"),
        created_at=parse_timestamp(payload.get("create_time")),
        updated_at=parse_timestamp(payload.get("update_time")),
        raw_payload=payload,
        messages=parse_messages(str(external_id), payload.get("mapping") or {}),
    )


def parse_messages(
    conversation_external_id: str,
    mapping: dict[str, Any],
) -> list[ChatGPTMessage]:
    ordered_node_ids = order_mapping_nodes(mapping)
    messages: list[ChatGPTMessage] = []
    for node_id in ordered_node_ids:
        node = mapping.get(node_id) or {}
        message = node.get("message")
        if not isinstance(message, dict):
            continue
        source_message_id = message.get("id") or node.get("id") or len(messages)
        message_external_id = f"{conversation_external_id}:{source_message_id}"
        author = message.get("author") or {}
        messages.append(
            ChatGPTMessage(
                external_id=str(message_external_id),
                sequence_index=len(messages),
                role=author.get("role"),
                content_text=extract_content_text(message.get("content") or {}),
                created_at=parse_timestamp(message.get("create_time")),
                raw_payload=message,
            )
        )
    return messages


def validate_unique_payloads(conversations: list[ChatGPTConversation]) -> None:
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
                "ChatGPT export contains duplicate conversation external_id "
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
                    "ChatGPT export contains duplicate message external_id "
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


def order_mapping_nodes(mapping: dict[str, Any]) -> list[str]:
    visited: set[str] = set()
    ordered: list[str] = []

    def visit(node_id: str) -> None:
        if node_id in visited:
            return
        visited.add(node_id)
        ordered.append(node_id)
        node = mapping.get(node_id) or {}
        for child_id in node.get("children") or []:
            if child_id in mapping:
                visit(child_id)

    roots = [
        node_id
        for node_id, node in mapping.items()
        if not (node or {}).get("parent")
    ]
    for node_id in roots:
        visit(node_id)
    for node_id in mapping:
        visit(node_id)
    return ordered


def extract_content_text(content: dict[str, Any]) -> str | None:
    content_type = content.get("content_type")
    parts = content.get("parts")
    if isinstance(parts, list):
        extracted: list[str] = []
        for part in parts:
            if isinstance(part, str):
                extracted.append(part)
            elif isinstance(part, dict):
                marker = content_part_marker(part)
                if marker:
                    extracted.append(marker)
                else:
                    extracted.append(json.dumps(part, sort_keys=True, separators=(",", ":")))
        text = "\n".join(piece for piece in extracted if piece is not None).strip()
        return text or None
    if content_type == "model_editable_context":
        values = [
            content.get("model_set_context"),
            content.get("repo_summary"),
            content.get("structured_context"),
        ]
        text = "\n".join(str(value) for value in values if value).strip()
        return text or None
    return None


def content_part_marker(part: dict[str, Any]) -> str | None:
    content_type = part.get("content_type")
    if content_type == "image_asset_pointer":
        pointer = part.get("asset_pointer") or part.get("file_id") or "unknown"
        return f"[image_asset_pointer: {pointer}]"
    if content_type:
        return f"[{content_type}]"
    return None


def parse_timestamp(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, int | float):
        return datetime.fromtimestamp(value, tz=UTC)
    if isinstance(value, str):
        normalized = value.removesuffix("Z") + "+00:00" if value.endswith("Z") else value
        return datetime.fromisoformat(normalized)
    return None


def get_or_create_source(conn: psycopg.Connection, manifest: dict[str, Any]) -> str:
    row = conn.execute(
        """
        SELECT id, content_hash, raw_payload
        FROM sources
        WHERE source_kind = 'chatgpt' AND external_id = %s
        """,
        (manifest["external_id"],),
    ).fetchone()
    if row:
        source_id, existing_hash, existing_payload = row
        if existing_hash != manifest["content_hash"]:
            raise IngestConflict(
                "ChatGPT source content hash differs from immutable source row "
                f"for {manifest['external_id']}"
            )
        if existing_payload != manifest:
            raise IngestConflict(
                "ChatGPT source manifest differs from immutable source row "
                f"for {manifest['external_id']}"
            )
        return str(source_id)

    source_id = conn.execute(
        """
        INSERT INTO sources (
            source_kind,
            external_id,
            filesystem_path,
            content_hash,
            raw_payload
        )
        VALUES ('chatgpt', %s, %s, %s, %s)
        RETURNING id
        """,
        (
            manifest["external_id"],
            manifest["filesystem_path"],
            manifest["content_hash"],
            Jsonb(manifest),
        ),
    ).fetchone()[0]
    return str(source_id)


def count_rows(conn: psycopg.Connection, table: str, source_id: str) -> int:
    return conn.execute(
        f"SELECT count(*) FROM {table} WHERE source_id = %s",
        (source_id,),
    ).fetchone()[0]


def insert_conversations(
    conn: psycopg.Connection,
    source_id: str,
    conversations: list[ChatGPTConversation],
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
            VALUES (%s, 'chatgpt', %s, %s, %s, %s, %s)
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
    conversations: list[ChatGPTConversation],
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
        VALUES (%s, 'chatgpt', %s, %s, %s, %s, %s, %s, %s)
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
