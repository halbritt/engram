from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pytest

from engram.claude_export import (
    IngestConflict,
    ingest_claude_export,
    parse_conversation,
    validate_unique_payloads,
)


def make_message(
    uuid: str,
    sender: str,
    text: str,
    *,
    parent_uuid: str = "00000000-0000-4000-8000-000000000000",
    extra_content: list[dict] | None = None,
    files: list[dict] | None = None,
) -> dict:
    content: list[dict] = [
        {
            "start_timestamp": "2026-04-01T00:00:00.000000Z",
            "stop_timestamp": "2026-04-01T00:00:00.000000Z",
            "flags": None,
            "type": "text",
            "text": text,
            "citations": [],
        }
    ]
    if extra_content:
        content.extend(extra_content)
    return {
        "uuid": uuid,
        "text": text,
        "content": content,
        "sender": sender,
        "created_at": "2026-04-01T00:00:00.000000Z",
        "updated_at": "2026-04-01T00:00:00.000000Z",
        "attachments": [],
        "files": files or [],
        "parent_message_uuid": parent_uuid,
    }


def make_conversation(
    conversation_uuid: str,
    name: str,
    user_text: str = "Hello",
    user_message_uuid: str = "msg-user-1",
    assistant_text: str = "Hi back",
) -> dict:
    user_message = make_message(user_message_uuid, "human", user_text)
    tool_use_part = {
        "start_timestamp": "2026-04-01T00:00:01.000000Z",
        "stop_timestamp": "2026-04-01T00:00:02.000000Z",
        "flags": None,
        "type": "tool_use",
        "id": None,
        "name": "search",
        "input": {"query": "anything"},
    }
    tool_result_part = {
        "start_timestamp": None,
        "stop_timestamp": None,
        "flags": None,
        "type": "tool_result",
        "tool_use_id": None,
        "name": "search",
        "content": [{"type": "text", "text": "result", "uuid": "r-1"}],
        "is_error": False,
    }
    assistant_message = make_message(
        "msg-assistant-1",
        "assistant",
        assistant_text,
        parent_uuid=user_message_uuid,
        extra_content=[tool_use_part, tool_result_part],
    )
    return {
        "uuid": conversation_uuid,
        "name": name,
        "summary": f"Summary for {name}",
        "created_at": "2026-04-01T00:00:00.000000Z",
        "updated_at": "2026-04-01T00:00:05.000000Z",
        "account": {"uuid": "account-uuid-1"},
        "chat_messages": [user_message, assistant_message],
    }


def write_directory_export(root: Path, user_text: str = "Hello") -> dict:
    conversation = make_conversation("conv-uuid-1", "First Conversation", user_text)
    (root / "conversations.json").write_text(
        json.dumps([conversation]),
        encoding="utf-8",
    )
    (root / "users.json").write_text(
        json.dumps(
            [
                {
                    "uuid": "account-uuid-1",
                    "full_name": "Test User",
                    "email_address": "test@example.com",
                }
            ]
        ),
        encoding="utf-8",
    )
    (root / "projects.json").write_text("[]", encoding="utf-8")
    (root / "memories.json").write_text("[]", encoding="utf-8")
    return conversation


def write_zip_export(zip_path: Path, user_text: str = "Hello") -> dict:
    conversation = make_conversation("conv-uuid-1", "First Conversation", user_text)
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("conversations.json", json.dumps([conversation]))
        zf.writestr(
            "users.json",
            json.dumps(
                [
                    {
                        "uuid": "account-uuid-1",
                        "full_name": "Test User",
                        "email_address": "test@example.com",
                    }
                ]
            ),
        )
        zf.writestr("projects.json", "[]")
        zf.writestr("memories.json", "[]")
    return conversation


def table_counts(conn) -> dict[str, int]:
    return {
        table: conn.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
        for table in [
            "sources",
            "conversations",
            "messages",
            "consolidation_progress",
        ]
    }


def test_idempotent_claude_directory_reingest(conn, tmp_path):
    write_directory_export(tmp_path)

    first = ingest_claude_export(conn, tmp_path)
    before = table_counts(conn)
    second = ingest_claude_export(conn, tmp_path)
    after = table_counts(conn)

    assert first.conversations_inserted == 1
    assert first.messages_inserted == 2
    assert second.conversations_inserted == 0
    assert second.messages_inserted == 0
    assert before == after
    assert after["consolidation_progress"] == 0


def test_idempotent_claude_zip_reingest(conn, tmp_path):
    zip_path = tmp_path / "claude-export.zip"
    write_zip_export(zip_path)

    first = ingest_claude_export(conn, zip_path)
    before = table_counts(conn)
    second = ingest_claude_export(conn, zip_path)
    after = table_counts(conn)

    assert first.conversations_inserted == 1
    assert first.messages_inserted == 2
    assert second.conversations_inserted == 0
    assert second.messages_inserted == 0
    assert before == after


def test_claude_ingest_records_role_and_content(conn, tmp_path):
    write_directory_export(tmp_path, user_text="What's up?")
    ingest_claude_export(conn, tmp_path)

    rows = conn.execute(
        "SELECT role, content_text, sequence_index "
        "FROM messages ORDER BY sequence_index"
    ).fetchall()

    assert [row[0] for row in rows] == ["human", "assistant"]
    assert rows[0][1] == "What's up?"
    assert rows[1][1].startswith("Hi back")
    assert "[tool_use:search]" in rows[1][1]
    assert "[tool_result:search]" in rows[1][1]
    assert [row[2] for row in rows] == [0, 1]


def test_changed_export_content_raises_conflict(conn, tmp_path):
    write_directory_export(tmp_path, user_text="first")
    ingest_claude_export(conn, tmp_path)

    write_directory_export(tmp_path, user_text="changed")

    with pytest.raises(IngestConflict, match="content hash differs"):
        ingest_claude_export(conn, tmp_path)


def test_duplicate_conversation_uuid_with_different_payload_raises_conflict():
    parsed = [
        parse_conversation(payload)
        for payload in [
            make_conversation("dup-uuid", "First", "first"),
            make_conversation("dup-uuid", "Second", "second"),
        ]
    ]

    with pytest.raises(IngestConflict, match="duplicate conversation external_id"):
        validate_unique_payloads(parsed)


def test_duplicate_message_uuid_with_different_payload_raises_conflict():
    conversation = make_conversation("conv-with-dups", "Duplicate Messages")
    duplicate_message = make_message(
        "msg-user-1",
        "assistant",
        "Different payload reusing the same uuid",
        parent_uuid="msg-assistant-1",
    )
    conversation["chat_messages"].append(duplicate_message)

    parsed = [parse_conversation(conversation)]

    with pytest.raises(IngestConflict, match="duplicate message external_id"):
        validate_unique_payloads(parsed)
