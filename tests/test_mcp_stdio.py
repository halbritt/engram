from __future__ import annotations

import argparse
import io
import json

import psycopg
from psycopg.types.json import Jsonb

from engram.mcp_stdio import (
    build_token,
    call_tool,
    handle_request,
    read_message,
    tool_definitions,
    write_message,
)
from engram.memory import MemorySearchFilters, MemoryService, encode_reference_id


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


def test_mcp_stdio_exposes_read_only_tools() -> None:
    assert [tool["name"] for tool in tool_definitions()] == [
        "engram.search",
        "engram.build_packet",
        "engram.fetch_reference",
        "engram.describe_corpus",
        "engram.health",
    ]


def test_mcp_search_schema_accepts_nullable_exact_refs_filter() -> None:
    search_tool = next(tool for tool in tool_definitions() if tool["name"] == "engram.search")
    filters_schema = search_tool["inputSchema"]["properties"]["filters"]

    assert filters_schema["default"] is None
    object_schema = filters_schema["anyOf"][0]
    exact_refs_schema = object_schema["properties"]["exact_refs"]
    exact_ref_item_schema = exact_refs_schema["anyOf"][0]["items"]

    assert {"type": "null"} in filters_schema["anyOf"]
    assert {"type": "null"} in exact_refs_schema["anyOf"]
    assert exact_ref_item_schema["required"] == ["ref_kind", "ref_value"]
    assert exact_ref_item_schema["additionalProperties"] is False


def test_mcp_build_packet_schema_mirrors_memory_service_inputs() -> None:
    packet_tool = next(tool for tool in tool_definitions() if tool["name"] == "engram.build_packet")
    input_schema = packet_tool["inputSchema"]
    properties = input_schema["properties"]

    assert input_schema["required"] == ["query"]
    assert properties["tenant"]["default"] == "striatum"
    assert properties["corpus"]["default"] == "striatum"
    assert properties["budget"]["default"] == 2000
    assert properties["budget"]["minimum"] == 1

    filters_schema = properties["filters"]
    object_schema = filters_schema["anyOf"][0]
    exact_refs_schema = object_schema["properties"]["exact_refs"]
    exact_ref_item_schema = exact_refs_schema["anyOf"][0]["items"]

    assert filters_schema["default"] is None
    assert {"type": "null"} in filters_schema["anyOf"]
    assert {"type": "null"} in exact_refs_schema["anyOf"]
    assert exact_ref_item_schema["required"] == ["ref_kind", "ref_value"]
    assert exact_ref_item_schema["additionalProperties"] is False


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
        "engram.build_packet",
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


def test_mcp_search_dispatch_passes_typed_exact_refs_filters() -> None:
    class StubSearchService:
        def __init__(self) -> None:
            self.search_call: dict[str, object] | None = None

        def search(
            self,
            query: str,
            *,
            tenant_id: str,
            corpus_id: str,
            limit: int,
            filters: MemorySearchFilters | None = None,
        ) -> list[dict[str, object]]:
            self.search_call = {
                "query": query,
                "tenant_id": tenant_id,
                "corpus_id": corpus_id,
                "limit": limit,
                "filters": filters,
            }
            return []

    service = StubSearchService()

    payload = call_tool(
        service,  # type: ignore[arg-type]
        "engram.search",
        {
            "query": "prior RFC boundary",
            "tenant": "striatum",
            "corpus": "striatum",
            "k": 3,
            "filters": {"exact_refs": [{"ref_kind": "rfc_id", "ref_value": "0044"}]},
        },
    )

    assert payload == {"results": []}
    assert service.search_call is not None
    assert service.search_call["limit"] == 3
    filters = service.search_call["filters"]
    assert isinstance(filters, MemorySearchFilters)
    assert len(filters.exact_refs) == 1
    assert filters.exact_refs[0].ref_kind == "rfc_id"
    assert filters.exact_refs[0].ref_value == "0044"


def test_mcp_search_dispatch_preserves_limit_over_k_with_null_filters() -> None:
    class StubSearchService:
        def __init__(self) -> None:
            self.search_call: dict[str, object] | None = None

        def search(
            self,
            query: str,
            *,
            tenant_id: str,
            corpus_id: str,
            limit: int,
            filters: MemorySearchFilters | None = None,
        ) -> list[dict[str, object]]:
            self.search_call = {"limit": limit, "filters": filters}
            return []

    service = StubSearchService()

    call_tool(
        service,  # type: ignore[arg-type]
        "engram.search",
        {"query": "boundary", "limit": 7, "k": 3, "filters": None},
    )

    assert service.search_call == {"limit": 7, "filters": None}


def test_mcp_build_packet_dispatch_passes_budget_and_typed_filters() -> None:
    class StubPacketService:
        def __init__(self) -> None:
            self.packet_call: dict[str, object] | None = None

        def build_packet(
            self,
            query: str,
            *,
            budget: int,
            tenant_id: str,
            corpus_id: str,
            filters: MemorySearchFilters | None = None,
        ) -> dict[str, object]:
            self.packet_call = {
                "query": query,
                "budget": budget,
                "tenant_id": tenant_id,
                "corpus_id": corpus_id,
                "filters": filters,
            }
            return {"packet_id": "packet-test"}

    service = StubPacketService()

    payload = call_tool(
        service,  # type: ignore[arg-type]
        "engram.build_packet",
        {
            "query": "RFC 0048 context injection",
            "tenant": "striatum",
            "corpus": "striatum",
            "budget": 512,
            "filters": {"exact_refs": [{"ref_kind": "rfc_id", "ref_value": "0048"}]},
        },
    )

    assert payload == {"packet_id": "packet-test"}
    assert service.packet_call is not None
    assert service.packet_call["query"] == "RFC 0048 context injection"
    assert service.packet_call["budget"] == 512
    assert service.packet_call["tenant_id"] == "striatum"
    assert service.packet_call["corpus_id"] == "striatum"
    filters = service.packet_call["filters"]
    assert isinstance(filters, MemorySearchFilters)
    assert len(filters.exact_refs) == 1
    assert filters.exact_refs[0].ref_kind == "rfc_id"
    assert filters.exact_refs[0].ref_value == "0048"


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
