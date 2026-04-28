from __future__ import annotations

import json
from pathlib import Path

import pytest
from psycopg.errors import RaiseException

from engram.chatgpt_export import (
    IngestConflict,
    ingest_chatgpt_export,
    load_conversations,
    parse_conversation,
    validate_unique_payloads,
)


def write_export(root: Path, user_text: str = "Hello") -> None:
    conversation = make_conversation("conv-1", "Test Conversation", user_text)
    (root / "conversations.json").write_text(
        json.dumps([conversation]),
        encoding="utf-8",
    )
    (root / "chat.html").write_text("<html></html>", encoding="utf-8")


def make_conversation(
    conversation_id: str,
    title: str,
    user_text: str = "Hello",
    user_message_id: str = "user-1",
) -> dict:
    return {
        "title": title,
        "create_time": 1710000000.0,
        "update_time": 1710000060.0,
        "conversation_id": conversation_id,
        "mapping": {
            "root": {
                "id": "root",
                "message": None,
                "parent": None,
                "children": ["sys-1"],
            },
            "sys-1": {
                "id": "sys-1",
                "message": {
                    "id": "sys-1",
                    "author": {"role": "system", "name": None, "metadata": {}},
                    "create_time": 1710000000.0,
                    "content": {"content_type": "text", "parts": [""]},
                    "metadata": {"is_visually_hidden_from_conversation": True},
                },
                "parent": "root",
                "children": ["user-1"],
            },
            "user-1": {
                "id": "user-1",
                "message": {
                    "id": user_message_id,
                    "author": {"role": "user", "name": None, "metadata": {}},
                    "create_time": 1710000001.0,
                    "content": {"content_type": "text", "parts": [user_text]},
                    "metadata": {},
                },
                "parent": "sys-1",
                "children": ["assistant-1"],
            },
            "assistant-1": {
                "id": "assistant-1",
                "message": {
                    "id": "assistant-1",
                    "author": {"role": "assistant", "name": None, "metadata": {}},
                    "create_time": 1710000002.0,
                    "content": {"content_type": "text", "parts": ["Hi"]},
                    "metadata": {},
                },
                "parent": "user-1",
                "children": [],
            },
        },
        "current_node": "assistant-1",
    }


def write_split_export(root: Path) -> list[dict]:
    root_conversation = make_conversation(
        "split-conv-1",
        "Root Split Conversation",
        "Root split hello",
    )
    project_conversation = make_conversation(
        "project-conv-1",
        "Project Split Conversation",
        "Project split hello",
    )
    (root / "json").mkdir()
    (root / "projects" / "Project_A" / "json").mkdir(parents=True)
    (root / "conversation-index.json").write_text(
        json.dumps(
            [
                {
                    "id": root_conversation["conversation_id"],
                    "title": root_conversation["title"],
                    "create_time": "2024-03-09T16:00:00Z",
                },
                {
                    "id": project_conversation["conversation_id"],
                    "title": project_conversation["title"],
                    "create_time": "2024-03-09T16:00:00Z",
                },
            ]
        ),
        encoding="utf-8",
    )
    (root / "projects" / "project-index.json").write_text(
        json.dumps(
            [
                {
                    "id": "project-a",
                    "name": "Project A",
                    "conversation_count": 1,
                }
            ]
        ),
        encoding="utf-8",
    )
    (root / "json" / "root-conversation.json").write_text(
        json.dumps(root_conversation),
        encoding="utf-8",
    )
    (root / "projects" / "Project_A" / "json" / "project-conversation.json").write_text(
        json.dumps(project_conversation),
        encoding="utf-8",
    )
    return [root_conversation, project_conversation]


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


def test_idempotent_chatgpt_reingest_and_empty_progress(conn, tmp_path):
    write_export(tmp_path)

    first = ingest_chatgpt_export(conn, tmp_path)
    before = table_counts(conn)
    second = ingest_chatgpt_export(conn, tmp_path)
    after = table_counts(conn)

    assert first.conversations_inserted == 1
    assert first.messages_inserted == 3
    assert second.conversations_inserted == 0
    assert second.messages_inserted == 0
    assert before == after
    assert after["consolidation_progress"] == 0


def test_split_export_parses_and_reingests_idempotently(conn, tmp_path):
    write_split_export(tmp_path)

    conversations = list(load_conversations(tmp_path))
    assert [conversation.external_id for conversation in conversations] == [
        "split-conv-1",
        "project-conv-1",
    ]
    assert [conversation.title for conversation in conversations] == [
        "Root Split Conversation",
        "Project Split Conversation",
    ]
    assert all(len(conversation.messages) == 3 for conversation in conversations)

    first = ingest_chatgpt_export(conn, tmp_path)
    before = table_counts(conn)
    second = ingest_chatgpt_export(conn, tmp_path)
    after = table_counts(conn)

    assert first.conversations_inserted == 2
    assert first.messages_inserted == 6
    assert second.conversations_inserted == 0
    assert second.messages_inserted == 0
    assert before == after


def test_raw_tables_block_update_and_delete(conn, tmp_path):
    write_export(tmp_path)
    ingest_chatgpt_export(conn, tmp_path)
    conversation_id = conn.execute("SELECT id FROM conversations LIMIT 1").fetchone()[0]

    with pytest.raises(RaiseException, match="raw evidence table"):
        conn.execute(
            "UPDATE conversations SET title = 'changed' WHERE id = %s",
            (conversation_id,),
        )

    conn.rollback()

    with pytest.raises(RaiseException, match="raw evidence table"):
        conn.execute("DELETE FROM conversations WHERE id = %s", (conversation_id,))


def test_changed_export_path_content_raises_conflict(conn, tmp_path):
    write_export(tmp_path, user_text="first")
    ingest_chatgpt_export(conn, tmp_path)

    write_export(tmp_path, user_text="changed")

    with pytest.raises(IngestConflict, match="content hash differs"):
        ingest_chatgpt_export(conn, tmp_path)


def test_duplicate_conversation_id_with_different_payload_raises_conflict():
    parsed = [
        parse_conversation(payload)
        for payload in [
            make_conversation("duplicate-conv", "First", "first"),
            make_conversation("duplicate-conv", "Second", "second"),
        ]
    ]

    with pytest.raises(IngestConflict, match="duplicate conversation external_id"):
        validate_unique_payloads(parsed)


def test_duplicate_message_id_with_different_payload_raises_conflict(tmp_path):
    conversation = make_conversation("conv-with-duplicate-messages", "Duplicate Messages")
    duplicate_node = {
        "id": "user-2",
        "message": {
            "id": "user-1",
            "author": {"role": "user", "name": None, "metadata": {}},
            "create_time": 1710000003.0,
            "content": {"content_type": "text", "parts": ["Different payload"]},
            "metadata": {},
        },
        "parent": "assistant-1",
        "children": [],
    }
    conversation["mapping"]["assistant-1"]["children"] = ["user-2"]
    conversation["mapping"]["user-2"] = duplicate_node
    (tmp_path / "conversations.json").write_text(
        json.dumps([conversation]),
        encoding="utf-8",
    )

    parsed = list(load_conversations(tmp_path))
    with pytest.raises(IngestConflict, match="duplicate message external_id"):
        validate_unique_payloads(parsed)
