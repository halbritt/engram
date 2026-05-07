"""Tiny end-to-end pipeline smoke test (RFC 0015 gap 10).

Three synthetic conversations are seeded as raw evidence, the segmenter and
embedder HTTP layers are mocked, and ``segment_pending`` /
``embed_pending_segments`` are run back-to-back. The point is to catch wiring
regressions between phases (raw -> segments -> embeddings) without needing the
200-conversation Phase-5 smoke gate.

The fakes mirror the request/response shapes the real ``IkLlamaSegmenterClient``
and ``OllamaEmbeddingClient`` parse, so a regression in either parser will fail
the smoke before it ships.
"""
from __future__ import annotations

import json
import re
from typing import Any

import psycopg
import pytest

from engram import embedder, segmenter


EMBEDDING_DIMENSION = 768
EMBEDDING_VECTOR: list[float] = [0.01] * EMBEDDING_DIMENSION

MESSAGE_ID_RE = re.compile(r'<message id="([^"]+)"')


def _seed_conversation(
    conn: psycopg.Connection,
    *,
    source_external_id: str,
    conv_external_id: str,
    messages: list[tuple[str, str]],
) -> tuple[str, str, list[str]]:
    """Insert one source + one conversation + N messages via raw SQL.

    Bypassing the loader keeps the test deterministic (no JSON-file fixtures,
    no parser drift). Returns ``(source_id, conversation_id, message_ids)``.
    """
    source_id = conn.execute(
        """
        INSERT INTO sources (source_kind, external_id, raw_payload)
        VALUES ('chatgpt', %s, '{}')
        RETURNING id::text
        """,
        (source_external_id,),
    ).fetchone()[0]
    conversation_id = conn.execute(
        """
        INSERT INTO conversations (
            source_id, source_kind, external_id, raw_payload, privacy_tier, title
        )
        VALUES (%s, 'chatgpt', %s, '{}', 1, %s)
        RETURNING id::text
        """,
        (source_id, conv_external_id, f"smoke {conv_external_id}"),
    ).fetchone()[0]
    message_ids: list[str] = []
    for index, (role, content_text) in enumerate(messages):
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
                VALUES (%s, 'chatgpt', %s, %s, '{}', %s, %s, %s, 1)
                RETURNING id::text
                """,
                (
                    source_id,
                    conversation_id,
                    f"{conv_external_id}-msg-{index}",
                    role,
                    content_text,
                    index,
                ),
            ).fetchone()[0]
        )
    return source_id, conversation_id, message_ids


def _fake_segmenter_http(
    method: str,
    url: str,
    *,
    payload: dict[str, Any] | None = None,
    timeout: int = 30,
) -> dict[str, Any]:
    """Mimic ``IkLlamaSegmenterClient`` chat-completion JSON-schema responses.

    Pulls the message ids out of the prompt the segmenter just built and emits
    one segment that covers them all, in document order. This deterministic
    shape is what ``parse_segmentation_response`` expects.
    """
    assert method == "POST", f"unexpected segmenter HTTP method: {method}"
    assert payload is not None, "segmenter payload should not be None"
    user_messages = payload["messages"]
    prompt = next(m["content"] for m in user_messages if m["role"] == "user")
    message_ids = MESSAGE_ID_RE.findall(prompt)
    assert message_ids, "fake segmenter could not find any <message id=...> in the prompt"
    content = json.dumps(
        {
            "segments": [
                {
                    "message_ids": message_ids,
                    "summary": "smoke segment",
                    "content_text": "smoke segment text",
                    "raw": {"smoke": True},
                }
            ]
        }
    )
    return {"choices": [{"message": {"content": content}}]}


def _fake_embedder_http(
    method: str,
    url: str,
    *,
    payload: dict[str, Any] | None = None,
    timeout: int = 30,
) -> dict[str, Any]:
    """Mimic Ollama ``/api/embed`` responses with a fixed-dimension vector."""
    assert method == "POST", f"unexpected embedder HTTP method: {method}"
    assert payload is not None, "embedder payload should not be None"
    inputs = payload.get("input")
    assert isinstance(inputs, list) and inputs, "embedder payload missing input list"
    return {"embeddings": [list(EMBEDDING_VECTOR) for _ in inputs]}


def test_pipeline_smoke_three_conversations(
    conn: psycopg.Connection, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Raw -> segment -> embed wiring works for three tiny conversations."""
    # Pin the segmenter context window so IkLlamaSegmenterClient does not probe
    # ik-llama's HTTP API for /v1/models or /props.
    monkeypatch.setenv("ENGRAM_SEGMENTER_CONTEXT_WINDOW", "32768")

    seeded: list[tuple[str, str, list[str]]] = []
    convo_messages: list[list[tuple[str, str]]] = [
        [("user", "hello world"), ("assistant", "hi back")],
        [
            ("user", "how does engram store memories"),
            ("assistant", "raw evidence first, segments and embeddings derive"),
            ("user", "got it, thanks"),
        ],
        [("user", "what's the smoke test for"), ("assistant", "wiring regressions")],
    ]
    for index, messages in enumerate(convo_messages):
        seeded.append(
            _seed_conversation(
                conn,
                source_external_id=f"smoke-src-{index}",
                conv_external_id=f"smoke-conv-{index}",
                messages=messages,
            )
        )

    expected_message_count = sum(len(messages) for messages in convo_messages)

    # Sanity-check raw counts before running the derived stages so a regression
    # in seeding is caught loudly rather than as a downstream miscount.
    assert conn.execute("SELECT count(*) FROM sources").fetchone()[0] == 3
    assert conn.execute("SELECT count(*) FROM conversations").fetchone()[0] == 3
    assert (
        conn.execute("SELECT count(*) FROM messages").fetchone()[0]
        == expected_message_count
    )

    # Stage 2a: segment.
    monkeypatch.setattr(segmenter, "http_json", _fake_segmenter_http)
    segment_result = segmenter.segment_pending(
        conn,
        batch_size=10,
        model_version="smoke-segmenter",
    )
    assert segment_result.processed == 3
    assert segment_result.failed == 0
    assert segment_result.created >= 3

    # Stage 2b: embed.
    monkeypatch.setattr(embedder, "http_json", _fake_embedder_http)
    embed_result = embedder.embed_pending_segments(
        conn,
        batch_size=10,
        model_version="smoke-embedder",
    )
    assert embed_result.processed >= 3
    assert embed_result.failed == 0
    assert embed_result.activated >= 3

    # End-state: every conversation produced an active segment with an active
    # embedding, and progress rows record both stages' completion.
    n_segments = conn.execute(
        "SELECT count(*) FROM segments WHERE is_active"
    ).fetchone()[0]
    n_embeddings = conn.execute(
        "SELECT count(*) FROM segment_embeddings"
    ).fetchone()[0]
    assert n_segments >= 3
    assert n_embeddings >= 3

    # Every embedding must reference a real segment (FK is enforced, but assert
    # explicitly so a future schema change does not silently break the join).
    orphaned_embeddings = conn.execute(
        """
        SELECT count(*)
        FROM segment_embeddings se
        LEFT JOIN segments s ON s.id = se.segment_id
        WHERE s.id IS NULL
        """
    ).fetchone()[0]
    assert orphaned_embeddings == 0

    # Every active segment must have an active embedding for the model we ran.
    inactive_active_segments = conn.execute(
        """
        SELECT count(*)
        FROM segments s
        WHERE s.is_active
          AND NOT EXISTS (
              SELECT 1
              FROM segment_embeddings se
              WHERE se.segment_id = s.id
                AND se.embedding_model_version = 'smoke-embedder'
                AND se.is_active
          )
        """
    ).fetchone()[0]
    assert inactive_active_segments == 0

    # Vector dimension matches what the fake returned.
    distinct_dims = conn.execute(
        "SELECT array_agg(DISTINCT embedding_dimension) FROM segment_embeddings"
    ).fetchone()[0]
    assert distinct_dims == [EMBEDDING_DIMENSION]

    # consolidation_progress carries rows for both the segmenter and embedder
    # stages -- the stage names in the source are 'segmenter' and 'embedder';
    # asserting on those guards against a rename leaking into resumability.
    progress_stages = {
        row[0]
        for row in conn.execute(
            "SELECT DISTINCT stage FROM consolidation_progress"
        ).fetchall()
    }
    assert "segmenter" in progress_stages
    assert "embedder" in progress_stages

    # The batch-scope rows for both stages should be 'completed' on a clean run.
    segmenter_batch_status = conn.execute(
        """
        SELECT status::text
        FROM consolidation_progress
        WHERE stage = 'segmenter' AND scope = 'batch'
        """
    ).fetchone()[0]
    embedder_batch_status = conn.execute(
        """
        SELECT status::text
        FROM consolidation_progress
        WHERE stage = 'embedder' AND scope = 'batch'
        """
    ).fetchone()[0]
    assert segmenter_batch_status == "completed"
    assert embedder_batch_status == "completed"
