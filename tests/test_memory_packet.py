from __future__ import annotations

import hashlib

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


def _write_generation(conn: psycopg.Connection) -> str:
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
            'striatum',
            'bundle',
            'bundle:striatum',
            'packet-test',
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
        ("1" * 64,),
    ).fetchone()
    assert row is not None
    return str(row[0])


def _content_hash(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _write_capture(conn: psycopg.Connection, *, external_id: str, content: str) -> str:
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
        VALUES ('striatum', %s, '{}', 'striatum', 'striatum', 'packet-test')
        RETURNING id
        """,
        (f"source:{external_id}",),
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
            'striatum',
            'packet-test'
        )
        RETURNING id::text
        """,
        (
            source_row[0],
            external_id,
            Jsonb(
                {
                    "sub_kind": "rfc",
                    "provenance": {
                        "path": "docs/rfcs/0048-striatum-context-injection-policy.md"
                    },
                }
            ),
            content,
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
            'striatum',
            'rfc_id',
            '0048',
            'rfc 0048',
            %s,
            %s,
            true,
            '2026-05-15T00:00:00Z',
            1,
            'rfc',
            %s
        )
        """,
        (
            capture_id,
            _content_hash(content),
            generation_id,
            Jsonb({"freshness": "fresh", "source_dirty_working_tree": False}),
        ),
    )


def test_build_packet_returns_selected_items_citations_and_audit(
    conn: psycopg.Connection,
) -> None:
    generation_id = _write_generation(conn)
    selected_content = "needle rfc packet"
    omitted_content = " ".join(["rfc", "packet", *["overflow"] * 80])
    selected_id = _write_capture(conn, external_id="a-rfc-0048", content=selected_content)
    omitted_id = _write_capture(conn, external_id="b-rfc-0048", content=omitted_content)
    _write_reference(
        conn,
        capture_id=selected_id,
        generation_id=generation_id,
        content=selected_content,
    )
    _write_reference(
        conn,
        capture_id=omitted_id,
        generation_id=generation_id,
        content=omitted_content,
    )
    service = MemoryService(conn)

    packet = service.build_packet(
        "needle",
        budget=40,
        tenant_id="striatum",
        corpus_id="striatum",
        filters=MemorySearchFilters(exact_refs=(ExactRefFilter("rfc_id", "0048"),)),
    )

    assert packet["status"] == "available"
    assert packet["generation_id"] == generation_id
    assert [item["reference_id"] for item in packet["selected"]]
    assert packet["selected"][0]["citation"]["tenant_id"] == "striatum"
    assert (
        packet["selected"][0]["citation"]["reference_id"]
        == packet["selected"][0]["reference_id"]
    )
    assert packet["omitted"][0]["reason"] == "over_budget"
    assert "over_budget" in packet["omission_reason_vocabulary"]

    audit_row = conn.execute(
        """
        SELECT packet_id::text, generation_id::text, query, budget, selected, omitted
        FROM striatum_packet_audits
        """
    ).fetchone()
    assert audit_row is not None
    assert audit_row[0] == packet["packet_id"]
    assert audit_row[1] == generation_id
    assert audit_row[2] == "needle"
    assert audit_row[3] == {"max_tokens": 40}
    assert audit_row[4][0]["selected"] is True
    assert audit_row[5][0]["reason"] == "over_budget"
    assert "content" not in audit_row[4][0]
    assert "content" not in audit_row[5][0]


def test_build_packet_accepts_json_shaped_filters(conn: psycopg.Connection) -> None:
    generation_id = _write_generation(conn)
    content = "packet json filters"
    capture_id = _write_capture(conn, external_id="a-rfc-0048", content=content)
    _write_reference(conn, capture_id=capture_id, generation_id=generation_id, content=content)
    service = MemoryService(conn)

    packet = service.build_packet(
        "json filters",
        budget=100,
        tenant_id="striatum",
        corpus_id="striatum",
        filters={"exact_refs": [{"ref_kind": "rfc_id", "ref_value": "0048"}]},
    )

    assert len(packet["selected"]) == 1
    assert packet["selected"][0]["freshness"] == "fresh"


def test_build_packet_cross_tenant_failure_inserts_no_audit(
    conn: psycopg.Connection,
) -> None:
    token = MemoryToken(
        capabilities=frozenset({CAPABILITY_READ_STRIATUM, CAPABILITY_DESCRIBE}),
        allowed_pairs=frozenset(
            {
                TenantCorpus("striatum", "striatum"),
                TenantCorpus("personal", "striatum"),
            }
        ),
        primary_pair=TenantCorpus("striatum", "striatum"),
    )
    service = MemoryService(conn, token=token)

    with pytest.raises(MemoryCapabilityError, match=r"memory.read_cross_tenant"):
        service.build_packet(
            "private",
            budget=100,
            tenant_id="personal",
            corpus_id="striatum",
            filters={"exact_refs": [{"ref_kind": "rfc_id", "ref_value": "0048"}]},
        )

    row = conn.execute("SELECT count(*)::int FROM striatum_packet_audits").fetchone()
    assert row is not None
    assert row[0] == 0
