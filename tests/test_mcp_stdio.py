from __future__ import annotations

import argparse
import io
import json

import psycopg
from psycopg.types.json import Jsonb

from engram.mcp_stdio import (
    build_token,
    handle_request,
    read_message,
    tool_definitions,
    write_message,
)
from engram.memory import MemoryService, encode_reference_id


def _write_striatum_capture(
    conn: psycopg.Connection,
    *,
    corpus_id: str,
    external_id: str,
    content: str,
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
        VALUES ('striatum', %s, %s, 'striatum', %s, 'test-bundle')
        RETURNING id
        """,
        (
            f"mcp-source-{corpus_id}-{external_id}",
            Jsonb({"fixture": "mcp-cross-boundary"}),
            corpus_id,
        ),
    ).fetchone()
    assert source_row is not None
    source_id = source_row[0]
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
            '2026-05-13T00:00:00Z',
            'striatum',
            %s,
            'test-bundle'
        )
        RETURNING id
        """,
        (
            source_id,
            external_id,
            Jsonb({"sub_kind": "rfc", "provenance": {"path": "docs/rfc.md"}}),
            content,
            corpus_id,
        ),
    ).fetchone()
    assert capture_row is not None
    capture_id = capture_row[0]
    return str(capture_id)


def test_build_token_rejects_unknown_memory_capability() -> None:
    """EG-000 baseline: --capability rejects unknown memory.* names.

    The token vocabulary is closed; the CLI must not silently accept an
    unrecognized capability and grant whatever the caller asked for.
    """
    import pytest

    with pytest.raises(ValueError) as excinfo:
        build_token(
            argparse.Namespace(
                tenant="striatum",
                corpus="striatum",
                capability=["memory.read_galaxy"],
                allow_pair=[],
            )
        )
    assert "memory.read_galaxy" in str(excinfo.value)
    assert "memory.read_cross_tenant" in str(excinfo.value)


def test_build_token_accepts_known_memory_capability() -> None:
    """EG-000 baseline: known --capability values pass validation."""
    token = build_token(
        argparse.Namespace(
            tenant="striatum",
            corpus="striatum",
            capability=["memory.read_cross_corpus"],
            allow_pair=[],
        )
    )
    assert "memory.read_cross_corpus" in token.capabilities


def test_mcp_stdio_exposes_only_rfc0044_read_only_tools() -> None:
    assert [tool["name"] for tool in tool_definitions()] == [
        "engram.search",
        "engram.fetch_reference",
        "engram.describe_corpus",
        "engram.health",
    ]


def test_mcp_initialize_and_tools_list_shape() -> None:
    class StubService:
        pass

    initialize = handle_request(
        StubService(),  # type: ignore[arg-type]
        {"jsonrpc": "2.0", "id": 1, "method": "initialize"},
    )
    assert initialize is not None
    assert initialize["result"]["serverInfo"]["name"] == "engram-mcp-stdio"

    tools = handle_request(
        StubService(),  # type: ignore[arg-type]
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
    )
    assert tools is not None
    assert [tool["name"] for tool in tools["result"]["tools"]] == [
        "engram.search",
        "engram.fetch_reference",
        "engram.describe_corpus",
        "engram.health",
    ]


def test_mcp_content_length_framing_round_trips() -> None:
    stream = io.BytesIO()
    payload = {"jsonrpc": "2.0", "id": 1, "result": {"ok": True}}

    write_message(stream, payload)
    stream.seek(0)

    assert read_message(stream) == payload
    assert json.loads(json.dumps(payload)) == payload


def test_mcp_allow_pair_does_not_bypass_cross_corpus_for_search_or_fetch(
    conn: psycopg.Connection,
) -> None:
    capture_id = _write_striatum_capture(
        conn,
        corpus_id="secondary",
        external_id="rfc:secondary#mcp",
        content="secondary mcp capability boundary",
    )
    token = build_token(
        argparse.Namespace(
            tenant="striatum",
            corpus="striatum",
            capability=[],
            allow_pair=["striatum/secondary"],
        )
    )
    service = MemoryService(conn, token=token)

    search_response = handle_request(
        service,
        {
            "jsonrpc": "2.0",
            "id": 10,
            "method": "tools/call",
            "params": {
                "name": "engram.search",
                "arguments": {
                    "query": "secondary mcp",
                    "tenant": "striatum",
                    "corpus": "secondary",
                },
            },
        },
    )
    fetch_response = handle_request(
        service,
        {
            "jsonrpc": "2.0",
            "id": 11,
            "method": "tools/call",
            "params": {
                "name": "engram.fetch_reference",
                "arguments": {"reference_id": encode_reference_id("captures", capture_id)},
            },
        },
    )

    assert search_response is not None
    assert search_response["result"]["isError"] is True
    assert "memory.read_cross_corpus" in search_response["result"]["content"][0]["text"]
    assert fetch_response is not None
    assert fetch_response["result"]["isError"] is True
    assert "memory.read_cross_corpus" in fetch_response["result"]["content"][0]["text"]
