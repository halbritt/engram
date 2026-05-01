from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import psycopg
import pytest
from psycopg.types.json import Jsonb

from engram.embedder import embed_pending_segments, embed_text
from engram.migrations import migrate


class CountingEmbedder:
    def __init__(self, vector: list[float] | None = None, fail_after: int | None = None) -> None:
        self.vector = vector or [1.0, 0.0, 0.0]
        self.fail_after = fail_after
        self.calls = 0

    def embed(self, texts, *, model_version):
        self.calls += 1
        if self.fail_after is not None and self.calls > self.fail_after:
            raise RuntimeError("interrupted")
        return [self.vector for _ in texts]


def insert_conversation_with_segment(
    conn,
    *,
    text: str = "segment text",
    status: str = "segmented",
    active: bool = False,
) -> tuple[str, str, str]:
    source_id = conn.execute(
        """
        INSERT INTO sources (source_kind, external_id, raw_payload)
        VALUES ('chatgpt', gen_random_uuid()::text, '{}')
        RETURNING id::text
        """
    ).fetchone()[0]
    conversation_id = conn.execute(
        """
        INSERT INTO conversations (source_id, source_kind, external_id, raw_payload)
        VALUES (%s, 'chatgpt', gen_random_uuid()::text, '{}')
        RETURNING id::text
        """,
        (source_id,),
    ).fetchone()[0]
    message_id = conn.execute(
        """
        INSERT INTO messages (
            source_id,
            source_kind,
            conversation_id,
            external_id,
            raw_payload,
            role,
            content_text,
            sequence_index
        )
        VALUES (%s, 'chatgpt', %s, gen_random_uuid()::text, '{}', 'user', %s, 0)
        RETURNING id::text
        """,
        (source_id, conversation_id, text),
    ).fetchone()[0]
    generation_id = conn.execute(
        """
        INSERT INTO segment_generations (
            parent_kind,
            parent_id,
            segmenter_prompt_version,
            segmenter_model_version,
            status,
            raw_payload
        )
        VALUES ('conversation', %s, gen_random_uuid()::text, 'model', %s, '{}')
        RETURNING id::text
        """,
        (conversation_id, status),
    ).fetchone()[0]
    segment_id = conn.execute(
        """
        INSERT INTO segments (
            generation_id,
            source_id,
            source_kind,
            conversation_id,
            message_ids,
            sequence_index,
            content_text,
            segmenter_prompt_version,
            segmenter_model_version,
            is_active,
            privacy_tier,
            raw_payload
        )
        VALUES (%s, %s, 'chatgpt', %s, %s::uuid[], 0, %s, 'prompt', 'model', %s, 1, '{}')
        RETURNING id::text
        """,
        (generation_id, source_id, conversation_id, [message_id], text, active),
    ).fetchone()[0]
    return generation_id, segment_id, message_id


def add_segment_to_generation(conn, generation_id: str, message_id: str, *, text: str, index: int) -> str:
    source_id, source_kind, conversation_id = conn.execute(
        """
        SELECT source_id::text, source_kind::text, conversation_id::text
        FROM segments
        WHERE generation_id = %s
        LIMIT 1
        """,
        (generation_id,),
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
            segmenter_prompt_version,
            segmenter_model_version,
            privacy_tier,
            raw_payload
        )
        VALUES (%s, %s, %s, %s, %s::uuid[], %s, %s, 'prompt', 'model', 1, '{}')
        RETURNING id::text
        """,
        (generation_id, source_id, source_kind, conversation_id, [message_id], index, text),
    ).fetchone()[0]


def test_embedder_cache_hit_for_identical_input_and_activation(conn):
    generation_id, segment_id, message_id = insert_conversation_with_segment(conn, text="same")
    second_segment_id = add_segment_to_generation(
        conn,
        generation_id,
        message_id,
        text="same",
        index=1,
    )
    client = CountingEmbedder()

    result = embed_pending_segments(conn, batch_size=10, model_version="embed-a", client=client)

    assert result.created == 2
    assert result.cache_hits == 1
    assert result.activated == 1
    assert client.calls == 1
    assert conn.execute("SELECT count(*) FROM embedding_cache").fetchone()[0] == 1
    assert conn.execute("SELECT count(*) FROM segment_embeddings").fetchone()[0] == 2
    assert conn.execute("SELECT count(*) FROM segment_embeddings WHERE is_active").fetchone()[0] == 2
    nearest = conn.execute(
        """
        SELECT segment_id::text
        FROM segment_embeddings
        WHERE is_active = true
          AND privacy_tier <= 1
          AND embedding_model_version = 'embed-a'
        ORDER BY embedding <=> %s::vector
        LIMIT 1
        """,
        ("[1,0,0]",),
    ).fetchone()[0]
    assert nearest in {segment_id, second_segment_id}
    assert (
        conn.execute(
            """
            SELECT count(*)
            FROM pg_indexes
            WHERE indexname = 'segment_embeddings_nomic_768_hnsw_idx'
            """
        ).fetchone()[0]
        == 1
    )
    assert {segment_id, second_segment_id}


def test_concurrent_cache_miss_for_identical_input_creates_one_row(conn):
    database_url = os.environ.get("ENGRAM_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("ENGRAM_TEST_DATABASE_URL is required")
    conn.commit()
    barrier = Barrier(2)

    class RacingEmbedder:
        def embed(self, texts, *, model_version):
            barrier.wait(timeout=10)
            return [[0.0, 1.0, 0.0] for _ in texts]

    def worker():
        with psycopg.connect(database_url) as worker_conn:
            migrate(worker_conn)
            result = embed_text(
                worker_conn,
                "raced input",
                model_version="embed-race",
                client=RacingEmbedder(),
            )
            worker_conn.commit()
            return result.cache_id

    with ThreadPoolExecutor(max_workers=2) as pool:
        cache_ids = list(pool.map(lambda _: worker(), range(2)))

    assert len(set(cache_ids)) == 1
    assert (
        conn.execute(
            """
            SELECT count(*)
            FROM embedding_cache
            WHERE input_sha256 = encode(digest('raced input', 'sha256'), 'hex')
              AND embedding_model_version = 'embed-race'
            """
        ).fetchone()[0]
        == 1
    )


def test_two_embedding_model_versions_coexist_on_same_segment(conn):
    insert_conversation_with_segment(conn, text="coexist")
    client = CountingEmbedder()

    first = embed_pending_segments(conn, batch_size=10, model_version="embed-a", client=client)
    second = embed_pending_segments(conn, batch_size=10, model_version="embed-b", client=client)

    assert first.activated == 1
    assert second.created == 1
    assert conn.execute("SELECT count(*) FROM segment_embeddings").fetchone()[0] == 2
    assert (
        conn.execute("SELECT count(DISTINCT embedding_model_version) FROM segment_embeddings").fetchone()[0]
        == 2
    )


def test_embedder_resumes_after_mid_batch_failure(conn):
    generation_id, _, message_id = insert_conversation_with_segment(conn, text="first")
    add_segment_to_generation(conn, generation_id, message_id, text="second", index=1)
    failing = CountingEmbedder(fail_after=1)

    first = embed_pending_segments(conn, batch_size=10, model_version="embed-a", client=failing)
    assert first.failed == 1
    assert conn.execute("SELECT count(*) FROM segment_embeddings").fetchone()[0] == 1

    second = embed_pending_segments(
        conn,
        batch_size=10,
        model_version="embed-a",
        client=CountingEmbedder(),
    )

    assert second.created == 1
    assert second.activated == 1
    assert conn.execute("SELECT count(*) FROM segment_embeddings").fetchone()[0] == 2
    assert (
        conn.execute("SELECT status FROM consolidation_progress WHERE stage = 'embedder' AND scope = 'batch'").fetchone()[0]
        == "completed"
    )


def test_embedding_schema_accepts_distinct_dimensions(conn):
    first = embed_text(conn, "dimension three", model_version="embed-3", client=CountingEmbedder([1, 2, 3]))
    second = embed_text(
        conn,
        "dimension four",
        model_version="embed-4",
        client=CountingEmbedder([1, 2, 3, 4]),
    )

    assert first.embedding_dimension == 3
    assert second.embedding_dimension == 4
    assert (
        conn.execute(
            """
            SELECT count(*)
            FROM embedding_cache
            WHERE vector_dims(embedding) = embedding_dimension
            """
        ).fetchone()[0]
        == 2
    )


def test_segment_embedding_immutability_blocks_payload_updates(conn):
    insert_conversation_with_segment(conn, text="immutable")
    embed_pending_segments(conn, batch_size=10, model_version="embed-a", client=CountingEmbedder())
    segment_id = conn.execute("SELECT segment_id::text FROM segment_embeddings LIMIT 1").fetchone()[0]

    with pytest.raises(Exception, match="immutable"):
        conn.execute(
            """
            UPDATE segment_embeddings
            SET privacy_tier = 5
            WHERE segment_id = %s
              AND embedding_model_version = 'embed-a'
            """,
            (segment_id,),
        )
