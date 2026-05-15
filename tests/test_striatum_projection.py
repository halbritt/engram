from __future__ import annotations

import hashlib
from typing import Any

import psycopg
from psycopg.types.json import Jsonb

from engram.striatum_projection import project_striatum_references


def _insert_capture(
    conn: psycopg.Connection,
    *,
    external_id: str,
    sub_kind: str,
    content: str,
    raw_payload: dict[str, Any] | None = None,
    privacy_tier: int = 1,
) -> str:
    source_row = conn.execute(
        """
        INSERT INTO sources (
            source_kind,
            external_id,
            raw_payload,
            tenant_id,
            corpus_id,
            bundle_id
        )
        VALUES ('striatum', %s, '{}', 'striatum', 'striatum', 'bundle-test')
        RETURNING id
        """,
        (f"source-{external_id}",),
    ).fetchone()
    assert source_row is not None
    payload = {
        "source_kind": "striatum",
        "external_id": external_id,
        "sub_kind": sub_kind,
        "content": content,
        "content_sha256": hashlib.sha256(content.encode("utf-8")).hexdigest(),
        "provenance": {
            "path": f"docs/{external_id}.md",
            "commit": "ABC123",
        },
    }
    if raw_payload is not None:
        payload.update(raw_payload)
    capture_row = conn.execute(
        """
        INSERT INTO captures (
            source_id,
            source_kind,
            external_id,
            raw_payload,
            privacy_tier,
            capture_type,
            content_text,
            observed_at,
            tenant_id,
            corpus_id,
            bundle_id
        )
        VALUES (
            %s,
            'striatum',
            %s,
            %s,
            %s,
            'reference',
            %s,
            '2026-05-13T00:00:00Z',
            'striatum',
            'striatum',
            'bundle-test'
        )
        RETURNING id::text
        """,
        (
            source_row[0],
            external_id,
            Jsonb(payload),
            privacy_tier,
            content,
        ),
    ).fetchone()
    assert capture_row is not None
    return str(capture_row[0])


def test_projection_derives_closed_references_and_inherits_capture_boundary(
    conn: psycopg.Connection,
) -> None:
    capture_id = _insert_capture(
        conn,
        external_id="rfc:0046#projection",
        sub_kind="rfc",
        content="RFC 0046 projection",
        raw_payload={"rfc_id": "RFC-0046"},
        privacy_tier=2,
    )

    result = project_striatum_references(conn)

    assert result.captures_seen == 1
    assert result.references_inserted == 4
    rows = conn.execute(
        """
        SELECT
            capture_id::text,
            tenant_id,
            corpus_id,
            privacy_tier,
            ref_kind,
            ref_value_normalized,
            is_active,
            raw_payload ->> 'source_sub_kind'
        FROM striatum_references
        ORDER BY ref_kind
        """
    ).fetchall()
    assert rows == [
        (capture_id, "striatum", "striatum", 2, "commit_sha", "abc123", True, "rfc"),
        (
            capture_id,
            "striatum",
            "striatum",
            2,
            "item_id",
            "rfc:0046#projection",
            True,
            "rfc",
        ),
        (capture_id, "striatum", "striatum", 2, "path", "docs/rfc:0046#projection.md", True, "rfc"),
        (capture_id, "striatum", "striatum", 2, "rfc_id", "rfc 0046", True, "rfc"),
    ]


def test_projection_rerun_reuses_unchanged_active_generation(
    conn: psycopg.Connection,
) -> None:
    _insert_capture(
        conn,
        external_id="decision:D082",
        sub_kind="decision_log_row",
        content="D082 subject kind hints",
        raw_payload={"decision_id": "D082"},
    )

    first = project_striatum_references(conn)
    second = project_striatum_references(conn)

    assert first.references_inserted == 4
    assert second.generation_id == first.generation_id
    assert second.references_inserted == 0
    assert second.reused_active_generation is True
    assert conn.execute("SELECT count(*)::int FROM striatum_references").fetchone() == (4,)


def test_projection_new_input_swaps_active_generation(
    conn: psycopg.Connection,
) -> None:
    _insert_capture(
        conn,
        external_id="rfc:0044#hardening-baseline",
        sub_kind="rfc",
        content="RFC 0044 hardening baseline",
    )

    first = project_striatum_references(conn)
    _insert_capture(
        conn,
        external_id="decision:D082",
        sub_kind="decision_log_row",
        content="D082 subject kind hints",
    )
    second = project_striatum_references(conn)

    assert second.generation_id != first.generation_id
    assert second.superseded_generation_ids == (first.generation_id,)
    generations = conn.execute(
        """
        SELECT id::text, status, superseded_at IS NOT NULL
        FROM striatum_projection_generations
        ORDER BY started_at, id::text
        """
    ).fetchall()
    assert generations == [
        (first.generation_id, "superseded", True),
        (second.generation_id, "activated", False),
    ]
    active_counts = conn.execute(
        """
        SELECT generation_id::text, count(*)::int
        FROM striatum_references
        WHERE is_active
        GROUP BY generation_id
        """
    ).fetchall()
    assert active_counts == [(second.generation_id, 8)]
