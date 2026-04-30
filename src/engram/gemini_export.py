from __future__ import annotations

import hashlib
import html
import json
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

import psycopg
from psycopg.types.json import Jsonb


class IngestConflict(RuntimeError):
    """Raised when an immutable raw row would need to change."""


GEMINI_ACTIVITY_RELATIVE_PATH = Path("My Activity") / "Gemini Apps" / "MyActivity.json"


@dataclass(frozen=True)
class GeminiMessage:
    external_id: str
    sequence_index: int
    role: str | None
    content_text: str | None
    created_at: datetime | None
    raw_payload: dict[str, Any]


@dataclass(frozen=True)
class GeminiConversation:
    external_id: str
    title: str | None
    created_at: datetime | None
    updated_at: datetime | None
    raw_payload: dict[str, Any]
    messages: list[GeminiMessage]


@dataclass(frozen=True)
class IngestResult:
    source_id: str
    conversations_inserted: int
    conversations_seen: int
    messages_inserted: int
    messages_seen: int


@dataclass(frozen=True)
class ExportSource:
    identity_path: Path
    activity_path: Path
    activity_payload: bytes


def ingest_gemini_export(conn: psycopg.Connection, path: Path) -> IngestResult:
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
    if not candidate.exists() or not candidate.is_dir():
        raise FileNotFoundError(f"Gemini Takeout path is not a directory: {candidate}")

    activity_path = candidate / GEMINI_ACTIVITY_RELATIVE_PATH
    if activity_path.exists() and activity_path.is_file():
        return ExportSource(
            identity_path=candidate,
            activity_path=activity_path,
            activity_payload=activity_path.read_bytes(),
        )

    if candidate.name == "Gemini Apps":
        direct_activity_path = candidate / "MyActivity.json"
        if direct_activity_path.exists() and direct_activity_path.is_file():
            return ExportSource(
                identity_path=candidate,
                activity_path=direct_activity_path,
                activity_payload=direct_activity_path.read_bytes(),
            )

    raise FileNotFoundError(
        "Gemini Takeout directory must contain "
        f"{GEMINI_ACTIVITY_RELATIVE_PATH.as_posix()}"
    )


def build_manifest(export: ExportSource) -> dict[str, Any]:
    file_hash = hashlib.sha256(export.activity_payload).hexdigest()
    return {
        "source_kind": "gemini",
        "external_id": str(export.identity_path),
        "filesystem_path": str(export.identity_path),
        "content_hash": file_hash,
        "file_count": 1,
        "files": [
            {
                "path": export.activity_path.relative_to(export.identity_path).as_posix(),
                "size": len(export.activity_payload),
                "sha256": file_hash,
            }
        ],
    }


def load_conversations(export: ExportSource) -> Iterable[GeminiConversation]:
    payload = json.loads(export.activity_payload.decode("utf-8"))
    if not isinstance(payload, list):
        raise ValueError("Gemini MyActivity.json must contain a JSON array")
    for index, item in enumerate(payload):
        if not isinstance(item, dict):
            continue
        yield parse_activity(index, item)


def parse_activity(index: int, payload: dict[str, Any]) -> GeminiConversation:
    created_at = parse_timestamp(payload.get("time"))
    external_id = activity_external_id(payload)
    title = activity_title(payload)
    return GeminiConversation(
        external_id=external_id,
        title=title,
        created_at=created_at,
        updated_at=None,
        raw_payload=payload,
        messages=parse_messages(external_id, index, payload, created_at),
    )


def activity_external_id(payload: dict[str, Any]) -> str:
    timestamp = payload.get("time")
    if isinstance(timestamp, str) and timestamp:
        return timestamp
    return payload_hash(payload)


def activity_title(payload: dict[str, Any]) -> str | None:
    title = payload.get("title")
    if not isinstance(title, str):
        return None
    prompt = prompt_text_from_title(title)
    return prompt or title


def parse_messages(
    conversation_external_id: str,
    activity_index: int,
    payload: dict[str, Any],
    created_at: datetime | None,
) -> list[GeminiMessage]:
    messages: list[GeminiMessage] = []
    title = payload.get("title")
    if isinstance(title, str):
        prompt_text = prompt_text_from_title(title)
        if prompt_text:
            messages.append(
                GeminiMessage(
                    external_id=f"{conversation_external_id}:user",
                    sequence_index=0,
                    role="user",
                    content_text=prompt_text,
                    created_at=created_at,
                    raw_payload={
                        "kind": "title_prompt",
                        "activity_index": activity_index,
                        "title": title,
                        "activity": payload,
                    },
                )
            )

    safe_html_items = payload.get("safeHtmlItem")
    if isinstance(safe_html_items, list):
        html_parts = [
            item.get("html")
            for item in safe_html_items
            if isinstance(item, dict) and isinstance(item.get("html"), str)
        ]
        if html_parts:
            html_text = "\n".join(html_parts)
            content_text = html_to_text(html_text)
            if content_text:
                messages.append(
                    GeminiMessage(
                        external_id=f"{conversation_external_id}:assistant",
                        sequence_index=len(messages),
                        role="assistant",
                        content_text=content_text,
                        created_at=created_at,
                        raw_payload={
                            "kind": "safe_html_response",
                            "activity_index": activity_index,
                            "safeHtmlItem": safe_html_items,
                            "activity": payload,
                        },
                    )
                )

    return messages


def prompt_text_from_title(title: str) -> str | None:
    prefix = "Prompted "
    if not title.startswith(prefix):
        return None
    text = title[len(prefix) :].strip()
    return text or None


def validate_unique_payloads(conversations: list[GeminiConversation]) -> None:
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
                "Gemini export contains duplicate conversation external_id "
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
                    "Gemini export contains duplicate message external_id "
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


class TextHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag in {"p", "br", "div", "li", "h1", "h2", "h3", "h4", "tr"}:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"p", "div", "li", "h1", "h2", "h3", "h4", "tr"}:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        self.parts.append(data)

    def text(self) -> str:
        collapsed_lines = [
            " ".join(line.split())
            for line in "".join(self.parts).splitlines()
            if line.strip()
        ]
        return "\n".join(collapsed_lines).strip()


def html_to_text(value: str) -> str | None:
    parser = TextHTMLParser()
    parser.feed(value)
    text = html.unescape(parser.text()).strip()
    return text or None


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
        VALUES ('gemini', %s, %s, %s, %s)
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
        WHERE source_kind = 'gemini' AND external_id = %s
        """,
        (manifest["external_id"],),
    ).fetchone()
    if not existing:
        raise IngestConflict(
            "Gemini source insert conflicted but no existing source row was found "
            f"for {manifest['external_id']}"
        )

    source_id, existing_hash, existing_payload = existing
    if existing_hash != manifest["content_hash"]:
        raise IngestConflict(
            "Gemini source content hash differs from immutable source row "
            f"for {manifest['external_id']}"
        )
    if existing_payload != manifest:
        raise IngestConflict(
            "Gemini source manifest differs from immutable source row "
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
    conversations: list[GeminiConversation],
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
            VALUES (%s, 'gemini', %s, %s, %s, %s, %s)
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
    conversations: list[GeminiConversation],
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
        VALUES (%s, 'gemini', %s, %s, %s, %s, %s, %s, %s)
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
