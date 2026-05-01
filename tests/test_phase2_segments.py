from __future__ import annotations

import re

import pytest
from psycopg.errors import CheckViolation, RaiseException, UniqueViolation
from psycopg.types.json import Jsonb

from engram import segmenter
from engram.segmenter import SegmentDraft, SegmentationError, segment_conversation


class StaticSegmenter:
    def __init__(self, drafts: list[SegmentDraft] | None = None) -> None:
        self.drafts = drafts
        self.calls = 0

    def segment(self, prompt: str, *, model_id: str, max_tokens: int) -> list[SegmentDraft]:
        self.calls += 1
        if self.drafts is not None:
            return self.drafts
        message_ids = re.findall(r'<message id="([^"]+)"', prompt)
        return [
            SegmentDraft(
                message_ids=message_ids,
                summary="topic",
                content_text="topic text",
                raw={"model_id": model_id, "max_tokens": max_tokens},
            )
        ]


class ExplodingSegmenter:
    def segment(self, prompt: str, *, model_id: str, max_tokens: int) -> list[SegmentDraft]:
        raise AssertionError("segmenter should not be called")


def insert_conversation(
    conn,
    messages: list[tuple[str | None, str | None, int]],
    *,
    conversation_tier: int = 1,
) -> tuple[str, list[str]]:
    source_id = conn.execute(
        """
        INSERT INTO sources (source_kind, external_id, filesystem_path, content_hash, raw_payload)
        VALUES ('chatgpt', gen_random_uuid()::text, '/tmp/export', gen_random_uuid()::text, '{}')
        RETURNING id::text
        """
    ).fetchone()[0]
    conversation_id = conn.execute(
        """
        INSERT INTO conversations (
            source_id, source_kind, external_id, raw_payload, privacy_tier, title
        )
        VALUES (%s, 'chatgpt', gen_random_uuid()::text, '{}', %s, 'phase2')
        RETURNING id::text
        """,
        (source_id, conversation_tier),
    ).fetchone()[0]
    message_ids: list[str] = []
    for index, (role, content_text, privacy_tier) in enumerate(messages):
        message_ids.append(
            conn.execute(
                """
                INSERT INTO messages (
                    source_id,
                    source_kind,
                    conversation_id,
                    external_id,
                    raw_payload,
                    role,
                    content_text,
                    sequence_index,
                    privacy_tier
                )
                VALUES (%s, 'chatgpt', %s, %s, '{}', %s, %s, %s, %s)
                RETURNING id::text
                """,
                (
                    source_id,
                    conversation_id,
                    f"message-{index}",
                    role,
                    content_text,
                    index,
                    privacy_tier,
                ),
            ).fetchone()[0]
        )
    return conversation_id, message_ids


def insert_generation(conn, conversation_id: str, *, status: str = "segmented") -> str:
    return conn.execute(
        """
        INSERT INTO segment_generations (
            parent_kind,
            parent_id,
            segmenter_prompt_version,
            segmenter_model_version,
            status,
            raw_payload
        )
        VALUES ('conversation', %s, 'prompt', 'model', %s, '{}')
        RETURNING id::text
        """,
        (conversation_id, status),
    ).fetchone()[0]


def insert_segment_row(
    conn,
    generation_id: str,
    conversation_id: str,
    message_ids: list[str],
    *,
    sequence_index: int = 0,
    active: bool = False,
) -> str:
    source_id, source_kind = conn.execute(
        "SELECT source_id::text, source_kind::text FROM conversations WHERE id = %s",
        (conversation_id,),
    ).fetchone()
    return conn.execute(
        """
        INSERT INTO segments (
            generation_id,
            source_id,
            source_kind,
            conversation_id,
            message_ids,
            sequence_index,
            content_text,
            window_strategy,
            segmenter_prompt_version,
            segmenter_model_version,
            is_active,
            privacy_tier,
            raw_payload
        )
        VALUES (%s, %s, %s, %s, %s::uuid[], %s, 'segment text', 'whole', 'prompt', 'model', %s, 1, '{}')
        RETURNING id::text
        """,
        (
            generation_id,
            source_id,
            source_kind,
            conversation_id,
            message_ids,
            sequence_index,
            active,
        ),
    ).fetchone()[0]


def test_segmenter_end_to_end_is_inactive_and_idempotent(conn):
    conversation_id, message_ids = insert_conversation(
        conn,
        [("user", "hello", 1), ("assistant", "hi", 1)],
    )
    client = StaticSegmenter(
        [
            SegmentDraft(
                message_ids=message_ids,
                summary="greeting",
                content_text="user: hello\nassistant: hi",
                raw={"score": 1},
            )
        ]
    )

    first = segment_conversation(conn, conversation_id, model_version="model-a", client=client)
    second = segment_conversation(conn, conversation_id, model_version="model-a", client=client)

    assert first.segments_inserted == 1
    assert second.noop is True
    assert client.calls == 1
    assert conn.execute("SELECT count(*) FROM segments").fetchone()[0] == 1
    assert conn.execute("SELECT bool_or(is_active) FROM segments").fetchone()[0] is False
    assert (
        conn.execute(
            "SELECT status FROM consolidation_progress WHERE stage = 'segmenter' AND scope = %s",
            (f"conversation:{conversation_id}",),
        ).fetchone()[0]
        == "completed"
    )


def test_ik_llama_request_shape_and_response_rejections(monkeypatch):
    captured = {}

    def fake_http(method, url, *, payload=None, timeout=30):
        captured.update({"method": method, "url": url, "payload": payload, "timeout": timeout})
        return {
            "choices": [
                {
                    "message": {
                        "content": (
                            '{"segments":[{"message_ids":["00000000-0000-0000-0000-000000000000"],'
                            '"summary":null,"content_text":"hello","raw":{}}]}'
                        ),
                        "reasoning_content": "diagnostic only",
                    }
                }
            ]
        }

    monkeypatch.setattr(segmenter, "http_json", fake_http)
    client = segmenter.IkLlamaSegmenterClient("http://127.0.0.1:8081")
    drafts = client.segment("prompt", model_id="model-a", max_tokens=123)

    assert drafts[0].content_text == "hello"
    payload = captured["payload"]
    assert payload["stream"] is False
    assert payload["temperature"] == 0
    assert payload["top_p"] == 1
    assert payload["max_tokens"] == 123
    assert payload["chat_template_kwargs"]["enable_thinking"] is False
    assert payload["response_format"]["type"] == "json_schema"
    assert payload["response_format"]["json_schema"]["name"] == "SegmentationResult"

    with pytest.raises(SegmentationError, match="reasoning_content"):
        segmenter.parse_segmentation_response(
            {"choices": [{"message": {"content": "", "reasoning_content": "{}"}}]}
        )
    with pytest.raises(SegmentationError, match="Markdown-fenced"):
        segmenter.parse_segmentation_response(
            {"choices": [{"message": {"content": "```json\n{}\n```"}}]}
        )
    with pytest.raises(SegmentationError, match="schema"):
        segmenter.parse_segmentation_response(
            {"choices": [{"message": {"content": '{"segments":[{"message_ids":[]}]} '}}]}
        )


def test_version_bump_cutover_keeps_old_active_until_embedding(conn):
    from engram.embedder import embed_pending_segments

    class StubEmbedder:
        def embed(self, texts, *, model_version):
            return [[1.0, 0.0, 0.0] for _ in texts]

    conversation_id, message_ids = insert_conversation(conn, [("user", "hello", 1)])
    segment_conversation(
        conn,
        conversation_id,
        model_version="model-a",
        prompt_version="prompt-a",
        client=StaticSegmenter(
            [SegmentDraft(message_ids=message_ids, summary=None, content_text="old", raw={})]
        ),
    )
    embed_pending_segments(conn, batch_size=10, model_version="embed-a", client=StubEmbedder())
    old_segment_id = conn.execute("SELECT id::text FROM segments WHERE is_active").fetchone()[0]

    segment_conversation(
        conn,
        conversation_id,
        model_version="model-a",
        prompt_version="prompt-b",
        client=StaticSegmenter(
            [SegmentDraft(message_ids=message_ids, summary=None, content_text="new", raw={})]
        ),
    )

    assert conn.execute("SELECT id::text FROM segments WHERE is_active").fetchone()[0] == old_segment_id
    assert conn.execute("SELECT count(*) FROM segments WHERE is_active = false").fetchone()[0] == 1

    embed_pending_segments(conn, batch_size=10, model_version="embed-a", client=StubEmbedder())

    active_text = conn.execute("SELECT content_text FROM segments WHERE is_active").fetchone()[0]
    assert active_text == "new"
    assert (
        conn.execute("SELECT is_active FROM segments WHERE id = %s", (old_segment_id,)).fetchone()[0]
        is False
    )


def test_windowed_segmentation_resumes_after_interruption(conn):
    class FlakyWindowClient:
        def __init__(self) -> None:
            self.calls = 0
            self.failed_once = False

        def segment(self, prompt: str, *, model_id: str, max_tokens: int) -> list[SegmentDraft]:
            self.calls += 1
            if self.calls == 2 and not self.failed_once:
                self.failed_once = True
                raise RuntimeError("interrupted")
            message_ids = re.findall(r'<message id="([^"]+)"', prompt)
            return [
                SegmentDraft(
                    message_ids=message_ids,
                    summary=None,
                    content_text="window text",
                    raw={},
                )
            ]

    conversation_id, _ = insert_conversation(
        conn,
        [("user", "x" * 80, 1) for _ in range(5)],
    )
    client = FlakyWindowClient()

    with pytest.raises(RuntimeError, match="interrupted"):
        segment_conversation(
            conn,
            conversation_id,
            model_version="model-a",
            client=client,
            window_char_budget=170,
            retries=0,
        )

    assert conn.execute("SELECT count(*) FROM segments").fetchone()[0] == 1
    result = segment_conversation(
        conn,
        conversation_id,
        model_version="model-a",
        client=client,
        window_char_budget=170,
        retries=0,
    )

    assert result.status == "segmented"
    assert conn.execute("SELECT count(*) FROM segments WHERE window_strategy = 'windowed'").fetchone()[0] > 1


def test_segment_failure_marks_generation_failed(conn):
    conversation_id, _ = insert_conversation(conn, [("user", "hello", 1)])

    with pytest.raises(RuntimeError, match="interrupted"):
        segment_conversation(
            conn,
            conversation_id,
            model_version="model-a",
            client=type(
                "FailingSegmenter",
                (),
                {
                    "segment": lambda self, prompt, *, model_id, max_tokens: (_ for _ in ()).throw(
                        RuntimeError("interrupted")
                    )
                },
            )(),
        )

    assert conn.execute("SELECT status FROM segment_generations").fetchone()[0] == "failed"

    result = segmenter.segment_pending(
        conn,
        batch_size=10,
        model_version="model-a",
        client=StaticSegmenter(),
    )
    assert result.processed == 0


def test_segmenter_retries_compact_json_after_parse_failure(conn):
    class RetryClient:
        def __init__(self, message_ids):
            self.calls: list[str] = []
            self.message_ids = message_ids

        def segment(self, prompt: str, *, model_id: str, max_tokens: int) -> list[SegmentDraft]:
            self.calls.append(prompt)
            if len(self.calls) == 1:
                raise SegmentationError("segmenter returned invalid JSON: truncated")
            return [
                SegmentDraft(
                    message_ids=self.message_ids,
                    summary=None,
                    content_text="retried compact text",
                    raw={},
                )
            ]

    conversation_id, message_ids = insert_conversation(conn, [("user", "hello", 1)])
    client = RetryClient(message_ids)

    result = segment_conversation(
        conn,
        conversation_id,
        model_version="model-a",
        client=client,
        retries=1,
    )

    assert result.segments_inserted == 1
    assert len(client.calls) == 2
    assert "Retry with a more compact response" in client.calls[1]
    raw_payload = conn.execute("SELECT raw_payload FROM segments").fetchone()[0]
    assert raw_payload["retry_count"] == 1


def test_active_sequence_uniqueness_and_message_id_validation(conn):
    conversation_id, message_ids = insert_conversation(
        conn,
        [("user", "one", 1), ("assistant", "two", 1)],
    )
    generation_id = insert_generation(conn, conversation_id)
    insert_segment_row(conn, generation_id, conversation_id, message_ids[:1], active=True)

    with pytest.raises(UniqueViolation):
        insert_segment_row(conn, generation_id, conversation_id, message_ids[1:], active=True)
    conn.rollback()

    other_conversation_id, other_message_ids = insert_conversation(conn, [("user", "other", 1)])
    generation_id = insert_generation(conn, conversation_id)

    with pytest.raises(CheckViolation, match="same conversation"):
        insert_segment_row(conn, generation_id, conversation_id, other_message_ids)
    conn.rollback()

    generation_id = insert_generation(conn, conversation_id)
    with pytest.raises(CheckViolation, match="at least one"):
        insert_segment_row(conn, generation_id, conversation_id, [])
    conn.rollback()

    generation_id = insert_generation(conn, conversation_id)
    with pytest.raises(CheckViolation, match="sequence order"):
        insert_segment_row(conn, generation_id, conversation_id, list(reversed(message_ids)))
    conn.rollback()

    assert other_conversation_id


def test_marker_only_window_skips_without_empty_segment(conn):
    conversation_id, _ = insert_conversation(
        conn,
        [(None, None, 1), ("assistant", "[image_asset_pointer: file-1]", 1)],
    )

    result = segment_conversation(
        conn,
        conversation_id,
        model_version="model-a",
        client=ExplodingSegmenter(),
    )

    assert result.segments_inserted == 0
    assert result.skipped_windows == 1
    raw_payload = conn.execute("SELECT raw_payload FROM segment_generations").fetchone()[0]
    assert raw_payload["window_0_skip"]["reason"] == "no_embeddable_text"


def test_segment_immutability_allows_only_activation_and_invalidation(conn):
    conversation_id, message_ids = insert_conversation(conn, [("user", "hello", 1)])
    generation_id = insert_generation(conn, conversation_id)
    segment_id = insert_segment_row(conn, generation_id, conversation_id, message_ids)

    with pytest.raises(RaiseException, match="immutable"):
        conn.execute("UPDATE segments SET content_text = 'changed' WHERE id = %s", (segment_id,))
    conn.rollback()

    conn.execute("UPDATE segments SET is_active = true WHERE id = %s", (segment_id,))
    conn.execute(
        """
        UPDATE segments
        SET is_active = false,
            invalidated_at = now(),
            invalidation_reason = 'test'
        WHERE id = %s
        """,
        (segment_id,),
    )

    with pytest.raises(RaiseException, match="DELETE"):
        conn.execute("DELETE FROM segments WHERE id = %s", (segment_id,))


def test_privacy_tier_inherits_parent_and_covered_raw_rows(conn):
    conversation_id, message_ids = insert_conversation(
        conn,
        [("user", "one", 1), (None, None, 4), ("assistant", "three", 2)],
        conversation_tier=2,
    )
    segment_conversation(
        conn,
        conversation_id,
        model_version="model-a",
        client=StaticSegmenter(
            [
                SegmentDraft(
                    message_ids=[message_ids[0], message_ids[2]],
                    summary=None,
                    content_text="one three",
                    raw={},
                )
            ]
        ),
    )

    row = conn.execute("SELECT privacy_tier, message_ids::text FROM segments").fetchone()
    assert row[0] == 4
    assert message_ids[1] in row[1]


def test_reclassification_capture_invalidates_active_rows_and_queues_parent(conn):
    from engram.embedder import embed_pending_segments

    class StubEmbedder:
        def embed(self, texts, *, model_version):
            return [[0.0, 1.0, 0.0] for _ in texts]

    conversation_id, message_ids = insert_conversation(conn, [("user", "private", 1)])
    segment_conversation(conn, conversation_id, model_version="model-a", client=StaticSegmenter())
    embed_pending_segments(conn, batch_size=10, model_version="embed-a", client=StubEmbedder())
    assert conn.execute("SELECT count(*) FROM segment_embeddings WHERE is_active").fetchone()[0] == 1

    source_id = conn.execute(
        """
        INSERT INTO sources (source_kind, external_id, raw_payload)
        VALUES ('capture', gen_random_uuid()::text, '{}')
        RETURNING id::text
        """
    ).fetchone()[0]
    conn.execute(
        """
        INSERT INTO captures (
            source_id,
            source_kind,
            external_id,
            raw_payload,
            capture_type,
            content_text
        )
        VALUES (%s, 'capture', gen_random_uuid()::text, %s, 'reclassification', 'promote')
        """,
        (
            source_id,
            Jsonb({"target_kind": "message", "target_id": message_ids[0], "new_privacy_tier": 4}),
        ),
    )

    invalidated = segmenter.apply_reclassification_invalidations(conn)

    assert invalidated == 1
    assert conn.execute("SELECT count(*) FROM segments WHERE is_active").fetchone()[0] == 0
    assert conn.execute("SELECT count(*) FROM segment_embeddings WHERE is_active").fetchone()[0] == 0
    assert (
        conn.execute(
            "SELECT status FROM consolidation_progress WHERE stage = 'segmenter' AND scope = %s",
            (f"conversation:{conversation_id}",),
        ).fetchone()[0]
        == "pending"
    )

    queued = segmenter.segment_pending(
        conn,
        batch_size=10,
        model_version="model-a",
        client=StaticSegmenter(
            [
                SegmentDraft(
                    message_ids=message_ids,
                    summary=None,
                    content_text="private resegmented",
                    raw={},
                )
            ]
        ),
    )

    assert queued.processed == 1
    assert conn.execute("SELECT count(*) FROM segment_generations").fetchone()[0] == 2
    assert (
        conn.execute(
            "SELECT content_text FROM segments ORDER BY created_at DESC LIMIT 1"
        ).fetchone()[0]
        == "private resegmented"
    )
