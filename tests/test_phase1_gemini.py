from __future__ import annotations

import json
from pathlib import Path

import pytest

from engram.gemini_export import (
    GeminiConversation,
    GeminiMessage,
    IngestConflict,
    ingest_gemini_export,
    load_conversations,
    parse_activity,
    resolve_export,
    validate_unique_payloads,
)


def make_activity(
    *,
    time: str = "2026-04-28T08:53:43.029Z",
    prompt: str = "Hello Gemini",
    response_html: str | None = "<p>Hello <strong>human</strong>.</p>",
    attached_files: list[dict] | None = None,
) -> dict:
    activity = {
        "header": "Gemini Apps",
        "title": f"Prompted {prompt}",
        "time": time,
        "products": ["Gemini Apps"],
        "activityControls": ["Gemini Apps Activity"],
    }
    if response_html is not None:
        activity["safeHtmlItem"] = [{"html": response_html}]
    if attached_files is not None:
        activity["attachedFiles"] = attached_files
    return activity


def write_takeout(root: Path, activities: list[dict]) -> None:
    gemini_dir = root / "My Activity" / "Gemini Apps"
    gemini_dir.mkdir(parents=True, exist_ok=True)
    (gemini_dir / "MyActivity.json").write_text(
        json.dumps(activities),
        encoding="utf-8",
    )


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


def test_gemini_takeout_parses_and_reingests_idempotently(conn, tmp_path):
    activities = [
        make_activity(
            time="2026-04-28T08:53:43.029Z",
            prompt="Can one vinyl wrap motorcycle plastics?",
            response_html="<p>Yes.</p><ul><li>Use cast vinyl.</li></ul>",
            attached_files=[{"name": "image.png"}],
        ),
        make_activity(
            time="2026-04-28T08:41:18.708Z",
            prompt="Feature-only event",
            response_html=None,
        ),
    ]
    write_takeout(tmp_path, activities)

    export = resolve_export(tmp_path)
    conversations = list(load_conversations(export))

    assert [conversation.external_id for conversation in conversations] == [
        "2026-04-28T08:53:43.029Z",
        "2026-04-28T08:41:18.708Z",
    ]
    assert conversations[0].title == "Can one vinyl wrap motorcycle plastics?"
    assert [message.role for message in conversations[0].messages] == [
        "user",
        "assistant",
    ]
    assert conversations[0].messages[0].content_text == (
        "Can one vinyl wrap motorcycle plastics?"
    )
    assert conversations[0].messages[1].content_text == "Yes.\nUse cast vinyl."
    assert len(conversations[1].messages) == 1

    first = ingest_gemini_export(conn, tmp_path)
    before = table_counts(conn)
    second = ingest_gemini_export(conn, tmp_path)
    after = table_counts(conn)

    assert first.conversations_inserted == 2
    assert first.messages_inserted == 3
    assert second.conversations_inserted == 0
    assert second.messages_inserted == 0
    assert before == after
    assert after["consolidation_progress"] == 0


def test_changed_gemini_takeout_content_raises_conflict(conn, tmp_path):
    write_takeout(tmp_path, [make_activity(prompt="first")])
    ingest_gemini_export(conn, tmp_path)

    write_takeout(tmp_path, [make_activity(prompt="changed")])

    with pytest.raises(IngestConflict, match="content hash differs"):
        ingest_gemini_export(conn, tmp_path)


def test_duplicate_gemini_activity_time_with_different_payload_raises_conflict():
    parsed = [
        parse_activity(0, make_activity(time="2026-04-28T08:53:43.029Z", prompt="one")),
        parse_activity(1, make_activity(time="2026-04-28T08:53:43.029Z", prompt="two")),
    ]

    with pytest.raises(IngestConflict, match="duplicate conversation external_id"):
        validate_unique_payloads(parsed)


def test_duplicate_gemini_message_id_with_different_payload_raises_conflict():
    message_one = GeminiMessage(
        external_id="activity-1:user",
        sequence_index=0,
        role="user",
        content_text="one",
        created_at=None,
        raw_payload={"text": "one"},
    )
    message_two = GeminiMessage(
        external_id="activity-1:user",
        sequence_index=1,
        role="user",
        content_text="two",
        created_at=None,
        raw_payload={"text": "two"},
    )
    conversation = GeminiConversation(
        external_id="activity-1",
        title="Activity",
        created_at=None,
        updated_at=None,
        raw_payload={"activity": "one"},
        messages=[message_one, message_two],
    )

    with pytest.raises(IngestConflict, match="duplicate message external_id"):
        validate_unique_payloads([conversation])
