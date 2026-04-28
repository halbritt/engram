from __future__ import annotations

import json
from pathlib import Path

import pytest
from psycopg.errors import RaiseException

from engram.chatgpt_export import IngestConflict, ingest_chatgpt_export


def write_export(root: Path, user_text: str = "Hello") -> None:
    conversation = {
        "title": "Test Conversation",
        "create_time": 1710000000.0,
        "update_time": 1710000060.0,
        "conversation_id": "conv-1",
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
                    "id": "user-1",
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
    (root / "conversations.json").write_text(
        json.dumps([conversation]),
        encoding="utf-8",
    )
    (root / "chat.html").write_text("<html></html>", encoding="utf-8")


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
