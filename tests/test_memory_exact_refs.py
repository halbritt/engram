from __future__ import annotations

import hashlib
from typing import Any

import psycopg
import pytest
from psycopg.types.json import Jsonb

from engram.memory import (
    CAPABILITY_DESCRIBE,
    CAPABILITY_READ_STRIATUM,
    ExactRefFilter,
    MemoryCapabilityError,
    MemorySearchFilters,
    MemoryService,
    MemoryToken,
    TenantCorpus,
)


def _write_generation(conn: psycopg.Connection, *, corpus_id: str = "striatum") -> str:
    row = conn.execute(
        """
        INSERT INTO striatum_projection_generations (
            tenant_id,
            corpus_id,
            parent_kind,
            parent_id,
            bundle_id,
            contract_version,
            projection_schema_version,
            projection_code_version,
            input_manifest_sha256,
            input_item_count,
            status,
            completed_at,
            activated_at,
            raw_payload
        )
        VALUES (
            'striatum',
            %s,
            'bundle',
            %s,
            'exact-ref-test',
            'striatum.corpus_export.v1',
            'striatum.references.v1',
            'test',
            %s,
            1,
            'activated',
            now(),
            now(),
            '{}'
        )
        RETURNING id::text
        """,
        (corpus_id, f"bundle:{corpus_id}", "0" * 64),
    ).fetchone()
    assert row is not None
    return str(row[0])


def _content_hash(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _capture_raw_payload(*, dirty_working_tree: bool = False) -> dict[str, Any]:
    return {
        "sub_kind": "rfc",
        "provenance": {
            "path": "docs/rfcs/0044.md",
            "dirty_working_tree": dirty_working_tree,
        },
    }


def _projection_raw_payload(dirty_working_tree: bool, freshness: str | None) -> dict[str, Any]:
    payload: dict[str, Any] = {"source_dirty_working_tree": dirty_working_tree}
    if freshness is not None:
        payload["freshness"] = freshness
    return payload


def _normalized_ref_value(ref_kind: str, ref_value: str) -> str:
    if ref_kind == "rfc_id":
        return f"rfc {int(ref_value):04d}"
    return ref_value.lower()


def _write_capture(
    conn: psycopg.Connection,
    *,
    corpus_id: str = "striatum",
    external_id: str,
    content: str,
    raw_payload: dict[str, Any] | None = None,
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
        VALUES ('striatum', %s, '{}', 'striatum', %s, 'exact-ref-test')
        RETURNING id
        """,
        (f"source:{corpus_id}:{external_id}", corpus_id),
    ).fetchone()
    assert source_row is not None
    capture_row = conn.execute(
        """
        INSERT INTO captures (
            source_id,
            source_kind,
            external_id,
            raw_payload,
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
            'reference',
            %s,
            '2026-05-15T00:00:00Z',
            'striatum',
            %s,
            'exact-ref-test'
        )
        RETURNING id::text
        """,
        (
            source_row[0],
            external_id,
            Jsonb(raw_payload or _capture_raw_payload()),
            content,
            corpus_id,
        ),
    ).fetchone()
    assert capture_row is not None
    return str(capture_row[0])


def _write_reference(
    conn: psycopg.Connection,
    *,
    capture_id: str,
    generation_id: str,
    content: str,
    corpus_id: str = "striatum",
    ref_kind: str,
    ref_value: str,
    dirty_working_tree: bool = False,
    freshness: str | None = None,
    is_active: bool = True,
) -> None:
    conn.execute(
        """
        INSERT INTO striatum_references (
            capture_id,
            tenant_id,
            corpus_id,
            ref_kind,
            ref_value,
            ref_value_normalized,
            content_hash,
            generation_id,
            is_active,
            observed_at,
            privacy_tier,
            source_sub_kind,
            raw_payload
        )
        VALUES (
            %s,
            'striatum',
            %s,
            %s,
            %s,
            %s,
            %s,
            %s,
            %s,
            '2026-05-15T00:00:00Z',
            1,
            'rfc',
            %s
        )
        """,
        (
            capture_id,
            corpus_id,
            ref_kind,
            ref_value,
            _normalized_ref_value(ref_kind, ref_value),
            _content_hash(content),
            generation_id,
            is_active,
            Jsonb(_projection_raw_payload(dirty_working_tree, freshness)),
        ),
    )


def test_search_exact_refs_returns_only_matching_projected_rows(conn: psycopg.Connection) -> None:
    generation_id = _write_generation(conn)
    matching_content = "RFC 0044 exact reference boundary"
    other_content = "RFC 0045 corpus contract"
    matching_id = _write_capture(
        conn,
        external_id="rfc:0044#accepted",
        content=matching_content,
        raw_payload=_capture_raw_payload(),
    )
    other_id = _write_capture(
        conn,
        external_id="rfc:0045#proposal",
        content=other_content,
        raw_payload=_capture_raw_payload(),
    )
    _write_reference(
        conn,
        capture_id=matching_id,
        generation_id=generation_id,
        content=matching_content,
        ref_kind="rfc_id",
        ref_value="0044",
        freshness="fresh",
    )
    _write_reference(
        conn,
        capture_id=other_id,
        generation_id=generation_id,
        content=other_content,
        ref_kind="rfc_id",
        ref_value="0045",
    )
    service = MemoryService(conn)

    hits = service.search(
        "",
        filters=MemorySearchFilters(exact_refs=(ExactRefFilter("rfc_id", "0044"),)),
    )

    assert [hit["external_id"] for hit in hits] == ["rfc:0044#accepted"]
    assert hits[0]["dirty_working_tree"] is False
    assert hits[0]["freshness"] == "fresh"


def test_search_exact_refs_mismatched_ref_kind_returns_empty(conn: psycopg.Connection) -> None:
    generation_id = _write_generation(conn)
    content = "RFC 0044 exact reference boundary"
    capture_id = _write_capture(
        conn,
        external_id="rfc:0044#accepted",
        content=content,
        raw_payload=_capture_raw_payload(),
    )
    _write_reference(
        conn,
        capture_id=capture_id,
        generation_id=generation_id,
        content=content,
        ref_kind="rfc_id",
        ref_value="0044",
    )
    service = MemoryService(conn)

    hits = service.search(
        "RFC 0044",
        filters=MemorySearchFilters(exact_refs=(ExactRefFilter("decision_id", "0044"),)),
    )

    assert hits == []


def test_search_exact_refs_marks_dirty_source_rows(conn: psycopg.Connection) -> None:
    generation_id = _write_generation(conn)
    content = "RFC 0044 dirty working tree evidence"
    capture_id = _write_capture(
        conn,
        external_id="rfc:0044#dirty",
        content=content,
        raw_payload=_capture_raw_payload(dirty_working_tree=True),
    )
    _write_reference(
        conn,
        capture_id=capture_id,
        generation_id=generation_id,
        content=content,
        ref_kind="rfc_id",
        ref_value="0044",
        dirty_working_tree=True,
    )
    service = MemoryService(conn)

    hits = service.search(
        "dirty working tree",
        filters=MemorySearchFilters(exact_refs=(ExactRefFilter("rfc_id", "0044"),)),
    )

    assert [hit["external_id"] for hit in hits] == ["rfc:0044#dirty"]
    assert hits[0]["dirty_working_tree"] is True
    assert hits[0]["freshness"] == "dirty_working_tree"


def test_search_exact_refs_preserves_primary_pair_boundary(conn: psycopg.Connection) -> None:
    generation_id = _write_generation(conn, corpus_id="secondary")
    content = "secondary corpus RFC 0044"
    capture_id = _write_capture(
        conn,
        corpus_id="secondary",
        external_id="rfc:secondary#0044",
        content=content,
        raw_payload=_capture_raw_payload(),
    )
    _write_reference(
        conn,
        capture_id=capture_id,
        generation_id=generation_id,
        content=content,
        corpus_id="secondary",
        ref_kind="rfc_id",
        ref_value="0044",
    )
    token = MemoryToken(
        capabilities=frozenset({CAPABILITY_READ_STRIATUM, CAPABILITY_DESCRIBE}),
        allowed_pairs=frozenset(
            {
                TenantCorpus("striatum", "striatum"),
                TenantCorpus("striatum", "secondary"),
            }
        ),
    )
    service = MemoryService(conn, token=token)

    with pytest.raises(MemoryCapabilityError, match=r"memory.read_cross_corpus"):
        service.search(
            "RFC 0044",
            corpus_id="secondary",
            filters=MemorySearchFilters(exact_refs=(ExactRefFilter("rfc_id", "0044"),)),
        )


def test_search_lexical_fallback_still_reads_captures(conn: psycopg.Connection) -> None:
    _write_capture(
        conn,
        external_id="rfc:0044#lexical",
        content="RFC 0044 lexical fallback remains compatible",
        raw_payload={
            "sub_kind": "rfc",
            "provenance": {"path": "docs/rfcs/0044.md"},
        },
    )
    service = MemoryService(conn)

    hits = service.search("lexical fallback")

    assert [hit["external_id"] for hit in hits] == ["rfc:0044#lexical"]
    assert hits[0]["dirty_working_tree"] is False
    assert hits[0]["freshness"] == "unknown"
