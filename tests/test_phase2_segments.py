from __future__ import annotations

import re

import pytest
from psycopg.errors import CheckViolation, RaiseException, UniqueViolation
from psycopg.types.json import Jsonb

from engram import segmenter
from engram.segmenter import (
    SegmentDraft,
    SegmentationError,
    SegmenterRequestTimeout,
    SegmenterServiceUnavailable,
    segment_conversation,
)


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
    client = segmenter.IkLlamaSegmenterClient(
        "http://127.0.0.1:8081",
        context_window=4096,
    )
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


def test_ik_llama_schema_can_constrain_message_ids_to_window(monkeypatch):
    allowed_ids = [
        "11111111-1111-4111-8111-111111111111",
        "22222222-2222-4222-8222-222222222222",
    ]
    captured = {}

    def fake_http(method, url, *, payload=None, timeout=30):
        captured["payload"] = payload
        return {
            "choices": [
                {
                    "message": {
                        "content": (
                            '{"segments":[{"message_ids":["11111111-1111-4111-8111-111111111111"],'
                            '"summary":null,"content_text":"hello","raw":{}}]}'
                        )
                    }
                }
            ]
        }

    monkeypatch.setattr(segmenter, "http_json", fake_http)
    client = segmenter.IkLlamaSegmenterClient(
        "http://127.0.0.1:8081",
        context_window=4096,
    )

    drafts = client.segment(
        "prompt",
        model_id="model-a",
        max_tokens=123,
        allowed_message_ids=allowed_ids,
    )

    assert drafts[0].message_ids == [allowed_ids[0]]
    schema = captured["payload"]["response_format"]["json_schema"]["schema"]
    message_id_items = schema["properties"]["segments"]["items"]["properties"]["message_ids"][
        "items"
    ]
    assert message_id_items == {"type": "string", "enum": allowed_ids}


def test_segment_conversation_constrains_ik_llama_schema_to_window_ids(conn, monkeypatch):
    conversation_id, message_ids = insert_conversation(
        conn,
        [("user", "hello", 1), ("assistant", "hi", 1)],
    )
    captured_enums: list[list[str]] = []

    def fake_http(method, url, *, payload=None, timeout=30):
        schema = payload["response_format"]["json_schema"]["schema"]
        captured_enums.append(
            schema["properties"]["segments"]["items"]["properties"]["message_ids"]["items"][
                "enum"
            ]
        )
        return {
            "choices": [
                {
                    "message": {
                        "content": (
                            f'{{"segments":[{{"message_ids":["{message_ids[0]}"],'
                            '"summary":null,"content_text":"hello","raw":{}}}]}'
                        )
                    }
                }
            ]
        }

    monkeypatch.setattr(segmenter, "http_json", fake_http)

    result = segment_conversation(
        conn,
        conversation_id,
        model_version="model-a",
        client=segmenter.IkLlamaSegmenterClient(context_window=65536),
    )

    assert result.segments_inserted == 1
    assert captured_enums == [message_ids]


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


def test_segmenter_retries_truncation_with_larger_output_budget(conn):
    class RetryClient:
        def __init__(self, message_ids):
            self.calls: list[tuple[str, int]] = []
            self.message_ids = message_ids

        def segment(self, prompt: str, *, model_id: str, max_tokens: int) -> list[SegmentDraft]:
            self.calls.append((prompt, max_tokens))
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
        max_tokens=128,
        retries=1,
    )

    assert result.segments_inserted == 1
    assert len(client.calls) == 2
    assert client.calls[1][0] == client.calls[0][0]
    assert client.calls[1][1] > client.calls[0][1]
    raw_payload = conn.execute("SELECT raw_payload FROM segments").fetchone()[0]
    assert raw_payload["retry_count"] == 1


def test_segmenter_adaptively_splits_window_when_retry_hits_context_guard(conn):
    class SplitOnRetryGuardClient:
        def __init__(self) -> None:
            self.calls: list[tuple[list[str], int]] = []

        def segment(self, prompt: str, *, model_id: str, max_tokens: int) -> list[SegmentDraft]:
            message_ids = re.findall(r'<message id="([^"]+)"', prompt)
            self.calls.append((message_ids, max_tokens))
            if len(message_ids) > 1 and max_tokens == 100:
                raise segmenter.SegmenterResponseError(
                    "segmenter returned invalid JSON: Unterminated string",
                    response={"usage": {"completion_tokens": max_tokens}},
                )
            if len(message_ids) > 1:
                raise segmenter.SegmenterContextBudgetError(
                    "segmenter request would reach context shift"
                )
            return [
                SegmentDraft(
                    message_ids=message_ids,
                    summary=None,
                    content_text=f"segment for {message_ids[0]}",
                    raw={},
                )
            ]

    conversation_id, message_ids = insert_conversation(
        conn,
        [
            ("user", "one", 1),
            ("assistant", "two", 1),
            ("user", "three", 1),
            ("assistant", "four", 1),
        ],
    )
    client = SplitOnRetryGuardClient()

    result = segment_conversation(
        conn,
        conversation_id,
        model_version="model-a",
        client=client,
        max_tokens=100,
        retries=1,
        window_char_budget=10000,
    )

    assert result.segments_inserted == 4
    assert [call[1] for call in client.calls[:2]] == [100, 200]
    assert all(len(call[0]) == 1 for call in client.calls[-4:])
    rows = conn.execute(
        """
        SELECT message_ids::text[], window_strategy, window_index, raw_payload
        FROM segments
        ORDER BY sequence_index
        """
    ).fetchall()
    assert [row[0][0] for row in rows] == message_ids
    assert {row[1] for row in rows} == {"windowed"}
    assert {row[2] for row in rows} == {0}
    assert all(row[3]["adaptive_split_depth"] > 0 for row in rows)


def test_segmenter_replaces_invalid_utf8_surrogates_before_insert(conn):
    class SurrogateClient:
        def __init__(self, message_ids):
            self.message_ids = message_ids

        def segment(self, prompt: str, *, model_id: str, max_tokens: int) -> list[SegmentDraft]:
            return [
                SegmentDraft(
                    message_ids=self.message_ids,
                    summary="bad\ud83d",
                    content_text="text\ud803",
                    raw={"note": "raw\ud83d"},
                )
            ]

    conversation_id, message_ids = insert_conversation(conn, [("user", "hello", 1)])

    result = segment_conversation(
        conn,
        conversation_id,
        model_version="model-a",
        client=SurrogateClient(message_ids),
    )

    assert result.segments_inserted == 1
    row = conn.execute(
        "SELECT summary_text, content_text, raw_payload FROM segments"
    ).fetchone()
    assert row[0] == "bad?"
    assert row[1] == "text?"
    assert row[2]["segment"]["invalid_utf8_surrogates_replaced"] is True


def test_service_unavailable_fails_parent_and_continues(conn):
    class DownClient:
        def segment(self, prompt: str, *, model_id: str, max_tokens: int) -> list[SegmentDraft]:
            raise SegmenterServiceUnavailable("local segmenter unavailable")

    first_conversation_id, _ = insert_conversation(conn, [("user", "first", 1)])
    second_conversation_id, _ = insert_conversation(conn, [("user", "second", 1)])

    first = segmenter.segment_pending(
        conn,
        batch_size=10,
        model_version="model-a",
        client=DownClient(),
    )

    assert first.processed == 2
    assert first.failed == 2
    pending = conn.execute(
        """
        SELECT count(*)
        FROM consolidation_progress
        WHERE stage = 'segmenter'
          AND status = 'pending'
          AND error_count = 1
        """
    ).fetchone()[0]
    assert pending == 2
    assert conn.execute("SELECT count(*) FROM segment_generations").fetchone()[0] == 2

    result = segmenter.segment_pending(
        conn,
        batch_size=10,
        model_version="model-a",
        client=StaticSegmenter(),
    )

    assert result.processed == 2
    assert conn.execute("SELECT count(*) FROM segment_generations").fetchone()[0] == 4
    assert {first_conversation_id, second_conversation_id}


def test_service_unavailable_poison_cap_skips_retry_queue(conn):
    class DownClient:
        def segment(self, prompt: str, *, model_id: str, max_tokens: int) -> list[SegmentDraft]:
            raise SegmenterServiceUnavailable("local segmenter unavailable")

    insert_conversation(conn, [("user", "first", 1)])

    for _ in range(segmenter.MAX_SEGMENTER_ERROR_COUNT):
        result = segmenter.segment_pending(
            conn,
            batch_size=1,
            model_version="model-a",
            client=DownClient(),
        )
        assert result.processed == 1
        assert result.failed == 1

    capped = segmenter.segment_pending(
        conn,
        batch_size=1,
        model_version="model-a",
        client=StaticSegmenter(),
    )

    assert capped.processed == 0
    assert (
        conn.execute(
            """
            SELECT error_count
            FROM consolidation_progress
            WHERE stage = 'segmenter'
            """
        ).fetchone()[0]
        == segmenter.MAX_SEGMENTER_ERROR_COUNT
    )


def test_segmenter_request_timeout_fails_parent_and_continues(conn):
    class TimeoutThenStatic:
        def __init__(self) -> None:
            self.calls = 0

        def segment(
            self, prompt: str, *, model_id: str, max_tokens: int
        ) -> list[SegmentDraft]:
            self.calls += 1
            if self.calls == 1:
                raise SegmenterRequestTimeout("local segmenter request exceeded 180s deadline")
            message_ids = re.findall(r'<message id="([^"]+)"', prompt)
            return [
                SegmentDraft(
                    message_ids=message_ids,
                    summary=None,
                    content_text="second",
                    raw={},
                )
            ]

    insert_conversation(conn, [("user", "first", 1)])
    insert_conversation(conn, [("user", "second", 1)])

    result = segmenter.segment_pending(
        conn,
        batch_size=10,
        model_version="model-a",
        client=TimeoutThenStatic(),
        retries=0,
    )

    assert result.processed == 2
    assert result.failed == 1
    assert result.created == 1
    assert (
        conn.execute(
            """
            SELECT count(*)
            FROM segment_generations
            WHERE status = 'failed'
              AND raw_payload->>'failure_kind' = 'segmenter_timeout'
            """
        ).fetchone()[0]
        == 1
    )


def test_downstream_segment_error_marks_generation_failed(conn):
    class BadMessageClient:
        def segment(self, prompt: str, *, model_id: str, max_tokens: int) -> list[SegmentDraft]:
            return [
                SegmentDraft(
                    message_ids=["00000000-0000-0000-0000-000000000000"],
                    summary=None,
                    content_text="bad provenance",
                    raw={},
                )
            ]

    insert_conversation(conn, [("user", "hello", 1)])
    result = segmenter.segment_pending(
        conn,
        batch_size=10,
        model_version="model-a",
        client=BadMessageClient(),
    )

    assert result.failed == 1
    assert (
        conn.execute("SELECT status, raw_payload->>'failure_kind' FROM segment_generations").fetchone()
        == ("failed", "segmenter_error")
    )


def test_failed_generation_records_attempt_diagnostics(conn, monkeypatch):
    conversation_id, _ = insert_conversation(conn, [("user", "hello", 1)])
    seen_max_tokens: list[int] = []

    def fake_http(method, url, *, payload=None, timeout=30):
        assert payload is not None
        seen_max_tokens.append(payload["max_tokens"])
        return {
            "choices": [
                {
                    "message": {
                        "content": (
                            '{"segments":[{"message_ids":["00000000-0000-0000-0000-000000000000"],'
                            '"summary":null,"content_text":"unterminated'
                        )
                    }
                }
            ],
            "usage": {"completion_tokens": payload["max_tokens"]},
        }

    monkeypatch.setattr(segmenter, "http_json", fake_http)

    result = segmenter.segment_pending(
        conn,
        batch_size=10,
        model_version="model-a",
        client=segmenter.IkLlamaSegmenterClient(context_window=4096),
        max_tokens=100,
        retries=1,
    )

    assert result.processed == 1
    assert result.failed == 1
    assert seen_max_tokens == [100, 200]
    row = conn.execute(
        """
        SELECT raw_payload
        FROM segment_generations
        WHERE parent_id = %s
        """,
        (conversation_id,),
    ).fetchone()[0]
    assert row["failure_kind"] == "segmenter_error"
    assert row["attempts"] == 2
    assert row["attempt_max_tokens"] == [100, 200]
    assert row["decode_counts"] == [100, 200]
    assert "Unterminated string" in row["last_error"]
    assert len(row["attempt_errors"]) == 2


def test_segment_window_attempt_diagnostics_without_db():
    class TruncatingClient:
        def segment(self, prompt: str, *, model_id: str, max_tokens: int):
            raise segmenter.SegmenterResponseError(
                "segmenter returned invalid JSON: Unterminated string",
                response={"usage": {"completion_tokens": max_tokens}},
            )

    with pytest.raises(SegmentationError) as raised:
        segmenter.segment_window_with_retries(
            TruncatingClient(),
            "prompt",
            model_id="model-a",
            max_tokens=100,
            retries=1,
        )

    diagnostics = getattr(raised.value, "segmenter_attempt_diagnostics")
    assert diagnostics["attempts"] == 2
    assert diagnostics["attempt_max_tokens"] == [100, 200]
    assert diagnostics["decode_counts"] == [100, 200]
    assert len(diagnostics["attempt_errors"]) == 2


def test_ik_llama_context_guard_rejects_requests_near_context_shift():
    client = segmenter.IkLlamaSegmenterClient(context_window=4096)

    with pytest.raises(segmenter.SegmenterContextBudgetError, match="context shift"):
        client.segment("x" * 9000, model_id="model-a", max_tokens=100)


def test_segment_conversation_shrinks_windows_to_context_budget(conn, monkeypatch):
    conversation_id, _ = insert_conversation(
        conn,
        [
            ("user", "a" * 3500, 1),
            ("assistant", "b" * 3500, 1),
        ],
    )
    captured_prompts: list[str] = []

    def fake_http(method, url, *, payload=None, timeout=30):
        captured_prompts.append(payload["messages"][1]["content"])
        match = re.search(r'<message id="([^"]+)"', captured_prompts[-1])
        assert match is not None
        message_id = match.group(1)
        return {
            "choices": [
                {
                    "message": {
                        "content": (
                            f'{{"segments":[{{"message_ids":["{message_id}"],'
                            '"summary":null,"content_text":"hello","raw":{}}}]}'
                        )
                    }
                }
            ]
        }

    monkeypatch.setattr(segmenter, "http_json", fake_http)

    result = segment_conversation(
        conn,
        conversation_id,
        model_version="model-a",
        client=segmenter.IkLlamaSegmenterClient(context_window=3000),
        max_tokens=100,
        window_char_budget=20000,
    )

    assert result.windows_processed == 2
    assert result.segments_inserted == 2
    assert len(captured_prompts) == 2
    row = conn.execute(
        "SELECT raw_payload FROM segment_generations WHERE id = %s",
        (result.generation_id,),
    ).fetchone()[0]
    assert row["window_char_budget"] == 20000
    assert row["effective_window_char_budget"] < 20000
    assert row["context_window"] == 3000


def test_segmenter_request_deadline_raises_timeout():
    with pytest.raises(SegmenterRequestTimeout, match="exceeded 1s"):
        with segmenter.segmenter_request_deadline(1):
            import time

            time.sleep(2)


def test_http_json_wraps_socket_timeout(monkeypatch):
    def raise_timeout(*args, **kwargs):
        raise TimeoutError("timed out")

    monkeypatch.setattr(segmenter.urllib.request, "urlopen", raise_timeout)

    with pytest.raises(SegmenterServiceUnavailable, match="timed out"):
        segmenter.http_json("GET", "http://127.0.0.1:8081/v1/models")


def test_default_segmenter_model_id_caches_probe(monkeypatch):
    calls: list[str] = []

    def fake_http(method, url, *, payload=None, timeout=30):
        calls.append(url)
        if url.endswith("/v1/models"):
            return {"data": [{"id": "model-a", "max_model_len": 4096}]}
        if url.endswith("/props"):
            return {"n_ctx": 4096}
        raise AssertionError(url)

    monkeypatch.delenv("ENGRAM_SEGMENTER_MODEL", raising=False)
    monkeypatch.setattr(segmenter, "_SEGMENTER_MODEL_ID_CACHE", None)
    monkeypatch.setattr(segmenter, "http_json", fake_http)

    assert segmenter.default_segmenter_model_id() == "model-a"
    assert segmenter.default_segmenter_model_id() == "model-a"
    assert calls == [
        "http://127.0.0.1:8081/v1/models",
        "http://127.0.0.1:8081/props",
    ]


def test_probe_failure_records_batch_progress(conn, monkeypatch):
    def fail_probe():
        raise SegmenterServiceUnavailable("probe failed")

    monkeypatch.setattr(segmenter, "default_segmenter_model_id", fail_probe)

    result = segmenter.segment_pending(conn, batch_size=10)

    assert result.processed == 0
    assert result.failed == 1
    assert (
        conn.execute(
            """
            SELECT status, error_count, last_error
            FROM consolidation_progress
            WHERE stage = 'segmenter'
              AND scope = 'probe'
            """
        ).fetchone()
        == ("failed", 1, "probe failed")
    )


def test_default_windowing_does_not_overlap_messages():
    messages = [
        segmenter.ConversationMessage(
            id=f"00000000-0000-0000-0000-00000000000{index}",
            sequence_index=index,
            role="user",
            content_text="x" * 80,
            privacy_tier=1,
        )
        for index in range(4)
    ]

    windows = segmenter.build_windows(messages, window_char_budget=170)

    assert len(windows) > 1
    for previous, current in zip(windows, windows[1:]):
        previous_ids = {message.id for message in previous.messages}
        current_ids = {message.id for message in current.messages}
        assert previous_ids.isdisjoint(current_ids)


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
