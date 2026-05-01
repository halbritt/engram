from __future__ import annotations

import hashlib
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Protocol

import psycopg

from engram.progress import upsert_progress
from engram.segmenter import canonicalize_embeddable_text


OLLAMA_BASE_URL = os.environ.get("ENGRAM_OLLAMA_BASE_URL", "http://127.0.0.1:11434")
DEFAULT_EMBEDDING_MODEL_VERSION = os.environ.get(
    "ENGRAM_EMBEDDING_MODEL_VERSION",
    "nomic-embed-text:latest",
)


class EmbeddingError(RuntimeError):
    """Raised when embedding generation or storage fails."""


@dataclass(frozen=True)
class EmbeddingResult:
    cache_id: str
    input_sha256: str
    embedding_model_version: str
    embedding_dimension: int
    cache_hit: bool


@dataclass(frozen=True)
class BatchResult:
    processed: int
    created: int
    cache_hits: int
    activated: int
    failed: int


@dataclass(frozen=True)
class EmbedderProbe:
    model: str
    dimension: int
    response_keys: list[str]


class EmbeddingClient(Protocol):
    def embed(self, texts: list[str], *, model_version: str) -> list[list[float]]:
        ...


class OllamaEmbeddingClient:
    def __init__(self, base_url: str = OLLAMA_BASE_URL) -> None:
        ensure_local_base_url(base_url)
        self.base_url = base_url.rstrip("/")

    def embed(self, texts: list[str], *, model_version: str) -> list[list[float]]:
        payload = {"model": model_version, "input": texts}
        response = http_json(
            "POST",
            f"{self.base_url}/api/embed",
            payload=payload,
            timeout=120,
        )
        embeddings = response.get("embeddings")
        if not isinstance(embeddings, list) or len(embeddings) != len(texts):
            raise EmbeddingError("Ollama /api/embed returned an invalid embeddings payload")
        parsed: list[list[float]] = []
        for index, embedding in enumerate(embeddings):
            if not isinstance(embedding, list) or not embedding:
                raise EmbeddingError(f"Ollama embedding {index} is empty or invalid")
            parsed.append([float(value) for value in embedding])
        return parsed


def probe_embedder(
    model_version: str = DEFAULT_EMBEDDING_MODEL_VERSION,
    client: EmbeddingClient | None = None,
) -> EmbedderProbe:
    embedder = client or OllamaEmbeddingClient()
    response = embedder.embed(["dimension probe"], model_version=model_version)
    return EmbedderProbe(
        model=model_version,
        dimension=len(response[0]),
        response_keys=["embeddings"],
    )


def embed_text(
    conn: psycopg.Connection,
    text: str,
    model_version: str = DEFAULT_EMBEDDING_MODEL_VERSION,
    *,
    client: EmbeddingClient | None = None,
) -> EmbeddingResult:
    canonical_text = canonicalize_embeddable_text(text)
    if not canonical_text:
        raise EmbeddingError("cannot embed empty text after canonicalization")

    encoded = canonical_text.encode("utf-8")
    input_sha256 = hashlib.sha256(encoded).hexdigest()
    existing = fetch_cache_row(conn, input_sha256, model_version)
    if existing:
        return EmbeddingResult(
            cache_id=existing["id"],
            input_sha256=input_sha256,
            embedding_model_version=model_version,
            embedding_dimension=existing["dimension"],
            cache_hit=True,
        )

    embedder = client or OllamaEmbeddingClient()
    embedding = embedder.embed([canonical_text], model_version=model_version)[0]
    dimension = len(embedding)
    row = conn.execute(
        """
        INSERT INTO embedding_cache (
            input_sha256,
            embedding_model_version,
            embedding_dimension,
            embedding
        )
        VALUES (%s, %s, %s, %s::vector)
        ON CONFLICT (input_sha256, embedding_model_version) DO NOTHING
        RETURNING id::text, embedding_dimension
        """,
        (input_sha256, model_version, dimension, vector_literal(embedding)),
    ).fetchone()
    if row:
        return EmbeddingResult(
            cache_id=row[0],
            input_sha256=input_sha256,
            embedding_model_version=model_version,
            embedding_dimension=row[1],
            cache_hit=False,
        )

    raced = fetch_cache_row(conn, input_sha256, model_version)
    if not raced:
        raise EmbeddingError("embedding cache conflict occurred but existing row was not found")
    return EmbeddingResult(
        cache_id=raced["id"],
        input_sha256=input_sha256,
        embedding_model_version=model_version,
        embedding_dimension=raced["dimension"],
        cache_hit=True,
    )


def embed_pending_segments(
    conn: psycopg.Connection,
    batch_size: int,
    model_version: str = DEFAULT_EMBEDDING_MODEL_VERSION,
    *,
    limit: int | None = None,
    client: EmbeddingClient | None = None,
    include_active: bool = True,
    progress_callback: Callable[[str, dict[str, Any]], None] | None = None,
) -> BatchResult:
    embedder = client or OllamaEmbeddingClient()
    rows = fetch_segments_needing_embeddings(
        conn,
        model_version=model_version,
        limit=min(batch_size, limit) if limit is not None else batch_size,
        include_active=include_active,
    )
    processed = created = cache_hits = failed = 0

    for row in rows:
        processed += 1
        segment_id = row["segment_id"]
        generation_id = row["generation_id"]
        started_at = time.monotonic()
        if progress_callback:
            progress_callback(
                "embed_start",
                {
                    "index": processed,
                    "batch_size": len(rows),
                    "segment_id": segment_id,
                    "generation_id": generation_id,
                },
            )
        upsert_progress(
            conn,
            stage="embedder",
            scope=f"segment:{segment_id}",
            status="in_progress",
            position={"segment_id": segment_id, "generation_id": generation_id},
        )
        try:
            if row["generation_status"] in {"segmented", "embedding"}:
                conn.execute(
                    """
                    UPDATE segment_generations
                    SET status = 'embedding'
                    WHERE id = %s
                      AND status = 'segmented'
                    """,
                    (generation_id,),
                )
            result = embed_text(
                conn,
                row["content_text"],
                model_version=model_version,
                client=embedder,
            )
            cache_hits += 1 if result.cache_hit else 0
            inserted = insert_segment_embedding(
                conn,
                segment_id=segment_id,
                generation_id=generation_id,
                cache_id=result.cache_id,
                model_version=model_version,
                privacy_tier=row["privacy_tier"],
                is_active=row["generation_status"] == "active" and row["segment_active"],
            )
            created += 1 if inserted else 0
            upsert_progress(
                conn,
                stage="embedder",
                scope=f"segment:{segment_id}",
                status="completed",
                position={"segment_id": segment_id, "generation_id": generation_id},
            )
        except Exception as exc:
            failed += 1
            upsert_progress(
                conn,
                stage="embedder",
                scope=f"segment:{segment_id}",
                status="failed",
                position={"segment_id": segment_id, "generation_id": generation_id},
                last_error=str(exc),
                increment_error=True,
            )
            if progress_callback:
                progress_callback(
                    "embed_failed",
                    {
                        "index": processed,
                        "batch_size": len(rows),
                        "segment_id": segment_id,
                        "generation_id": generation_id,
                        "elapsed_seconds": time.monotonic() - started_at,
                    },
                )
        else:
            if progress_callback:
                progress_callback(
                    "embed_done",
                    {
                        "index": processed,
                        "batch_size": len(rows),
                        "segment_id": segment_id,
                        "generation_id": generation_id,
                        "cache_hit": result.cache_hit,
                        "inserted": inserted,
                        "elapsed_seconds": time.monotonic() - started_at,
                    },
                )

    activated = activate_completed_generations(conn, model_version=model_version)
    upsert_progress(
        conn,
        stage="embedder",
        scope="batch",
        status="completed" if failed == 0 else "failed",
        position={
            "processed": processed,
            "created": created,
            "cache_hits": cache_hits,
            "activated": activated,
            "failed": failed,
        },
        last_error=None if failed == 0 else f"{failed} segment(s) failed",
        increment_error=failed > 0,
    )
    return BatchResult(
        processed=processed,
        created=created,
        cache_hits=cache_hits,
        activated=activated,
        failed=failed,
    )


def fetch_cache_row(
    conn: psycopg.Connection,
    input_sha256: str,
    model_version: str,
) -> dict[str, Any] | None:
    row = conn.execute(
        """
        SELECT id::text, embedding_dimension
        FROM embedding_cache
        WHERE input_sha256 = %s
          AND embedding_model_version = %s
        """,
        (input_sha256, model_version),
    ).fetchone()
    if not row:
        return None
    return {"id": row[0], "dimension": row[1]}


def fetch_segments_needing_embeddings(
    conn: psycopg.Connection,
    *,
    model_version: str,
    limit: int,
    include_active: bool,
) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT
            s.id::text AS segment_id,
            s.generation_id::text,
            s.content_text,
            s.privacy_tier,
            s.is_active,
            sg.status
        FROM segments s
        JOIN segment_generations sg ON sg.id = s.generation_id
        LEFT JOIN segment_embeddings se
          ON se.segment_id = s.id
         AND se.embedding_model_version = %s
        WHERE se.segment_id IS NULL
          AND (
              sg.status IN ('segmented', 'embedding')
              OR (%s AND sg.status = 'active' AND s.is_active = true)
          )
        ORDER BY sg.created_at, s.sequence_index
        LIMIT %s
        """,
        (model_version, include_active, limit),
    ).fetchall()
    return [
        {
            "segment_id": row[0],
            "generation_id": row[1],
            "content_text": row[2],
            "privacy_tier": row[3],
            "segment_active": row[4],
            "generation_status": row[5],
        }
        for row in rows
    ]


def insert_segment_embedding(
    conn: psycopg.Connection,
    *,
    segment_id: str,
    generation_id: str,
    cache_id: str,
    model_version: str,
    privacy_tier: int,
    is_active: bool,
) -> bool:
    row = conn.execute(
        """
        INSERT INTO segment_embeddings (
            segment_id,
            generation_id,
            embedding_cache_id,
            embedding,
            embedding_model_version,
            embedding_dimension,
            is_active,
            privacy_tier
        )
        SELECT
            %s,
            %s,
            ec.id,
            ec.embedding,
            ec.embedding_model_version,
            ec.embedding_dimension,
            %s,
            %s
        FROM embedding_cache ec
        WHERE ec.id = %s
          AND ec.embedding_model_version = %s
        ON CONFLICT (segment_id, embedding_model_version) DO NOTHING
        RETURNING segment_id
        """,
        (
            segment_id,
            generation_id,
            is_active,
            privacy_tier,
            cache_id,
            model_version,
        ),
    ).fetchone()
    return row is not None


def activate_completed_generations(
    conn: psycopg.Connection,
    *,
    model_version: str,
) -> int:
    rows = conn.execute(
        """
        SELECT sg.id::text
        FROM segment_generations sg
        WHERE sg.status IN ('segmented', 'embedding')
          AND NOT EXISTS (
              SELECT 1
              FROM segments s
              LEFT JOIN segment_embeddings se
                ON se.segment_id = s.id
               AND se.embedding_model_version = %s
              WHERE s.generation_id = sg.id
                AND se.segment_id IS NULL
          )
        ORDER BY sg.created_at
        """,
        (model_version,),
    ).fetchall()
    activated = 0
    for (generation_id,) in rows:
        if activate_generation(conn, generation_id, model_version=model_version):
            activated += 1
    return activated


def activate_generation(
    conn: psycopg.Connection,
    generation_id: str,
    *,
    model_version: str = DEFAULT_EMBEDDING_MODEL_VERSION,
) -> bool:
    generation = conn.execute(
        """
        SELECT id::text, parent_kind, parent_id::text, status
        FROM segment_generations
        WHERE id = %s
        """,
        (generation_id,),
    ).fetchone()
    if not generation:
        raise EmbeddingError(f"segment generation not found: {generation_id}")
    _, parent_kind, parent_id, status = generation
    if status == "active":
        return False
    if status not in {"segmented", "embedding"}:
        return False

    missing = conn.execute(
        """
        SELECT count(*)
        FROM segments s
        LEFT JOIN segment_embeddings se
          ON se.segment_id = s.id
         AND se.embedding_model_version = %s
        WHERE s.generation_id = %s
          AND se.segment_id IS NULL
        """,
        (model_version, generation_id),
    ).fetchone()[0]
    if missing:
        return False

    prior = conn.execute(
        """
        SELECT id::text
        FROM segment_generations
        WHERE parent_kind = %s
          AND parent_id = %s
          AND status = 'active'
        """,
        (parent_kind, parent_id),
    ).fetchone()
    if prior:
        prior_id = prior[0]
        conn.execute(
            """
            UPDATE segment_generations
            SET status = 'superseded',
                superseded_at = now()
            WHERE id = %s
            """,
            (prior_id,),
        )
        conn.execute(
            "UPDATE segments SET is_active = false WHERE generation_id = %s",
            (prior_id,),
        )
        conn.execute(
            "UPDATE segment_embeddings SET is_active = false WHERE generation_id = %s",
            (prior_id,),
        )

    conn.execute(
        """
        UPDATE segment_generations
        SET status = 'active',
            activated_at = now()
        WHERE id = %s
        """,
        (generation_id,),
    )
    conn.execute(
        "UPDATE segments SET is_active = true WHERE generation_id = %s",
        (generation_id,),
    )
    conn.execute(
        """
        UPDATE segment_embeddings
        SET is_active = true
        WHERE generation_id = %s
          AND embedding_model_version = %s
        """,
        (generation_id, model_version),
    )
    return True


def vector_literal(values: list[float]) -> str:
    return "[" + ",".join(format(float(value), ".9g") for value in values) + "]"


def http_json(
    method: str,
    url: str,
    *,
    payload: dict[str, Any] | None = None,
    timeout: int = 30,
) -> dict[str, Any]:
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={"Content-Type": "application/json"} if payload is not None else {},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read().decode("utf-8")
    except urllib.error.URLError as exc:
        raise EmbeddingError(f"local embedder request failed: {exc}") from exc
    try:
        parsed = json.loads(body)
    except json.JSONDecodeError as exc:
        raise EmbeddingError(f"local embedder returned non-JSON response: {exc}") from exc
    if not isinstance(parsed, dict):
        raise EmbeddingError("local embedder returned a non-object JSON response")
    return parsed


def ensure_local_base_url(url: str) -> None:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise EmbeddingError(f"invalid local embedder URL scheme: {url}")
    if parsed.hostname not in {"127.0.0.1", "localhost", "::1"}:
        raise EmbeddingError(f"embedder URL must be local-only: {url}")
