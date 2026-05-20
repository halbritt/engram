from __future__ import annotations

import argparse
import hashlib
import io
import json

import psycopg
import pytest
from psycopg.types.json import Jsonb

import engram.mcp_stdio as mcp_stdio
from engram.mcp_stdio import (
    build_token,
    call_tool,
    handle_request,
    read_message,
    tool_definitions,
    write_message,
)
from engram.memory import (
    CAPABILITY_READ_PERSONAL,
    MemoryCapabilityError,
    MemorySearchFilters,
    MemoryService,
    MemoryToken,
    TenantCorpus,
    encode_reference_id,
)


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


def _claim_grounding_request() -> dict[str, object]:
    return {
        "schema_version": "claim_grounding.request.v1",
        "request_id": "11111111-1111-4111-8111-111111111111",
        "tenant_id": "personal",
        "corpus_id": "personal",
        "extraction_run_id": "test-run",
        "extraction_prompt_version": "extractor.test",
        "extraction_model_version": "local.test",
        "surface_form": "OpenAI Codex",
        "mention_role": "subject",
        "candidate_entity_kinds": ["product"],
        "source_refs": [
            {
                "target_table": "messages",
                "target_id": "22222222-2222-4222-8222-222222222222",
            }
        ],
        "local_context_capsule": {"mode": "none", "text": None},
        "allowed_modes": ["local_lookup"],
        "network_grant": None,
        "privacy_tier_ceiling": 1,
        "sensitivity_ceiling": [],
        "requested_at": "2026-05-18T00:00:00Z",
    }


def test_build_token_rejects_unknown_memory_capability() -> None:
    """EG-000 baseline: --capability rejects unknown memory.* names.

    The token vocabulary is closed; the CLI must not silently accept an
    unrecognized capability and grant whatever the caller asked for.
    """
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
        "engram.context_for",
        "engram.ground_entity",
        "engram.claim_ground_entity",
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


def test_mcp_context_for_schema_defaults_to_personal_memory() -> None:
    context_tool = next(tool for tool in tool_definitions() if tool["name"] == "engram.context_for")
    input_schema = context_tool["inputSchema"]
    properties = input_schema["properties"]

    assert input_schema["required"] == ["query"]
    assert input_schema["additionalProperties"] is False
    assert properties["tenant"]["default"] == "personal"
    assert properties["corpus"]["default"] == "personal"
    assert properties["word_budget"]["default"] == 500
    assert properties["word_budget"]["minimum"] == 1
    assert properties["privacy_tier_max"]["default"] == 1
    assert properties["privacy_tier_max"]["minimum"] == 0
    assert properties["privacy_tier_max"]["maximum"] == 5
    assert properties["include_recent"]["default"] is True
    assert properties["max_items_per_lane"]["minimum"] == 1


def test_mcp_ground_entity_schema_defaults_to_local_personal_lookup() -> None:
    ground_tool = next(
        tool for tool in tool_definitions() if tool["name"] == "engram.ground_entity"
    )
    input_schema = ground_tool["inputSchema"]
    properties = input_schema["properties"]

    assert input_schema["required"] == ["query"]
    assert input_schema["additionalProperties"] is False
    assert properties["tenant"]["default"] == "personal"
    assert properties["corpus"]["default"] == "personal"
    assert properties["limit"]["default"] == 5
    assert properties["mode"]["default"] == "local_lookup"
    assert properties["allow_network"]["default"] is False


def test_mcp_claim_ground_entity_schema_accepts_rfc0053_request_object() -> None:
    claim_ground_tool = next(
        tool for tool in tool_definitions() if tool["name"] == "engram.claim_ground_entity"
    )
    input_schema = claim_ground_tool["inputSchema"]
    properties = input_schema["properties"]

    assert input_schema["required"] == ["request"]
    assert input_schema["additionalProperties"] is False
    assert properties["request"]["type"] == "object"
    assert properties["limit"]["default"] == 5
    assert properties["limit"]["minimum"] == 1
    assert properties["limit"]["maximum"] == 50


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
        "engram.context_for",
        "engram.ground_entity",
        "engram.claim_ground_entity",
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


def test_mcp_context_for_requires_personal_capability_before_service_call(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class StubContextService:
        conn = object()
        token = MemoryToken.default_striatum_operator()

    def fail_context_for(conn: object, request: object) -> object:
        raise AssertionError("context_for must not run before authorization")

    monkeypatch.setattr(mcp_stdio, "context_for", fail_context_for)

    with pytest.raises(MemoryCapabilityError) as excinfo:
        call_tool(
            StubContextService(),  # type: ignore[arg-type]
            "engram.context_for",
            {"query": "personal project context"},
        )

    assert "memory.read_personal" in str(excinfo.value)


def test_mcp_context_for_rejects_empty_query_before_service_call(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pair = TenantCorpus("personal", "personal")

    class StubContextService:
        conn = object()
        token = MemoryToken(
            capabilities=frozenset({CAPABILITY_READ_PERSONAL}),
            allowed_pairs=frozenset({pair}),
            primary_pair=pair,
        )

    def fail_context_for(conn: object, request: object) -> object:
        raise AssertionError("context_for must not run for an empty query")

    monkeypatch.setattr(mcp_stdio, "context_for", fail_context_for)

    with pytest.raises(ValueError) as excinfo:
        call_tool(
            StubContextService(),  # type: ignore[arg-type]
            "engram.context_for",
            {"query": "   "},
        )

    assert 'non-empty "query"' in str(excinfo.value)


def test_mcp_context_for_fails_closed_without_memory_service_shape() -> None:
    class StubService:
        pass

    with pytest.raises(ValueError) as excinfo:
        call_tool(
            StubService(),  # type: ignore[arg-type]
            "engram.context_for",
            {"query": "personal project context"},
        )

    assert "engram.context_for is unavailable" in str(excinfo.value)


def test_mcp_context_for_dispatches_authorized_request(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}
    pair = TenantCorpus("personal", "personal")

    class StubContextService:
        conn = object()
        token = MemoryToken(
            capabilities=frozenset({CAPABILITY_READ_PERSONAL}),
            allowed_pairs=frozenset({pair}),
            primary_pair=pair,
        )

    class FakeContextResult:
        def to_json(self) -> dict[str, object]:
            return {
                "context_id": "ctx-test",
                "status": "ok",
                "sections": [
                    {
                        "title": "Relevant Beliefs",
                        "lane": "current_beliefs",
                        "items": ["local-only context"],
                        "truncated": False,
                    }
                ],
                "citations": [],
                "source_belief_ids": [],
                "source_segment_ids": [],
                "source_reference_ids": [],
                "rendered_context": "## Relevant Beliefs\n- local-only context",
            }

    def fake_context_for(conn: object, request: object) -> FakeContextResult:
        captured["conn"] = conn
        captured["request"] = request
        return FakeContextResult()

    monkeypatch.setattr(mcp_stdio, "context_for", fake_context_for)

    payload = call_tool(
        StubContextService(),  # type: ignore[arg-type]
        "engram.context_for",
        {
            "query": "personal project context",
            "tenant": "personal",
            "corpus": "personal",
            "word_budget": 123,
            "privacy_tier_max": 2,
        },
    )

    request = captured["request"]
    assert payload["context_id"] == "ctx-test"
    assert getattr(request, "query_text") == "personal project context"
    assert getattr(request, "tenant_id") == "personal"
    assert getattr(request, "corpus_id") == "personal"
    assert getattr(request, "word_budget") == 123
    assert getattr(request, "privacy_tier_ceiling") == 2


def test_mcp_ground_entity_rejects_network_fetch_before_lookup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pair = TenantCorpus("personal", "personal")

    class StubGroundingService:
        conn = object()
        token = MemoryToken(
            capabilities=frozenset({CAPABILITY_READ_PERSONAL}),
            allowed_pairs=frozenset({pair}),
            primary_pair=pair,
        )

    def fail_lookup(*args: object, **kwargs: object) -> list[dict[str, object]]:
        raise AssertionError("local lookup must not run for network mode")

    monkeypatch.setattr(mcp_stdio, "search_grounding_evidence", fail_lookup)

    with pytest.raises(ValueError, match="network grounding fetch is unavailable"):
        call_tool(
            StubGroundingService(),  # type: ignore[arg-type]
            "engram.ground_entity",
            {"query": "OpenAI Codex", "allow_network": True},
        )


def test_mcp_ground_entity_dispatches_authorized_local_lookup(
    conn: psycopg.Connection,
) -> None:
    body = "OpenAI Codex is a product surface for coding agents."
    conn.execute(
        """
        INSERT INTO entity_grounding_evidence (
            tenant_id,
            corpus_id,
            query_text,
            entity_kind,
            source_url,
            source_label,
            content_hash,
            content_excerpt,
            fetched_at,
            fetch_tool_version,
            extractor_version
        )
        VALUES (
            'personal',
            'personal',
            'OpenAI Codex',
            'product',
            'https://example.invalid/codex',
            'Local fixture',
            %s,
            %s,
            '2026-05-17T00:00:00Z',
            'manual.local.test',
            'none'
        )
        """,
        (hashlib.sha256(body.encode("utf-8")).hexdigest(), body),
    )
    pair = TenantCorpus("personal", "personal")
    service = MemoryService(
        conn,
        token=MemoryToken(
            capabilities=frozenset({CAPABILITY_READ_PERSONAL}),
            allowed_pairs=frozenset({pair}),
            primary_pair=pair,
        ),
    )

    payload = call_tool(
        service,
        "engram.ground_entity",
        {"query": "Codex", "tenant": "personal", "corpus": "personal"},
    )

    assert payload["mode"] == "local_lookup"
    assert payload["network_fetch"] == "unsupported"
    assert payload["results"][0]["entity_kind"] == "product"
    assert payload["results"][0]["citation"]["source_label"] == "Local fixture"


def test_mcp_claim_ground_entity_dispatches_authorized_local_broker(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}
    pair = TenantCorpus("personal", "personal")

    class StubClaimGroundingService:
        conn = object()
        token = MemoryToken(
            capabilities=frozenset({CAPABILITY_READ_PERSONAL}),
            allowed_pairs=frozenset({pair}),
            primary_pair=pair,
        )

    class FakeGroundingResponse:
        def to_json(self) -> dict[str, object]:
            return {
                "schema_version": "claim_grounding.response.v1",
                "request_id": "11111111-1111-4111-8111-111111111111",
                "status": "not_found",
                "mode": "local_lookup",
                "network_fetch": "not_requested",
                "candidates": [],
                "omissions": [{"reason": "local_lookup_no_result", "details": None}],
                "broker_version": "claim_grounding.local_broker.v1",
                "dataset_snapshots": [],
                "created_at": "2026-05-18T00:00:00Z",
            }

    def fake_ground_claim_entity_locally(
        conn: object,
        request: dict[str, object],
        *,
        limit: int,
    ) -> FakeGroundingResponse:
        captured["conn"] = conn
        captured["request"] = request
        captured["limit"] = limit
        return FakeGroundingResponse()

    monkeypatch.setattr(
        mcp_stdio,
        "ground_claim_entity_locally",
        fake_ground_claim_entity_locally,
    )

    request = _claim_grounding_request()
    payload = call_tool(
        StubClaimGroundingService(),  # type: ignore[arg-type]
        "engram.claim_ground_entity",
        {"request": request, "limit": 3},
    )

    assert captured == {
        "conn": StubClaimGroundingService.conn,
        "request": request,
        "limit": 3,
    }
    assert payload["schema_version"] == "claim_grounding.response.v1"
    assert payload["mode"] == "local_lookup"
    assert payload["network_fetch"] == "not_requested"


def test_mcp_claim_ground_entity_requires_authorized_pair_before_broker_call(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class StubClaimGroundingService:
        conn = object()
        token = MemoryToken.default_striatum_operator()

    def fail_ground_claim_entity_locally(*args: object, **kwargs: object) -> object:
        raise AssertionError("claim grounding broker must not run before authorization")

    monkeypatch.setattr(
        mcp_stdio,
        "ground_claim_entity_locally",
        fail_ground_claim_entity_locally,
    )

    with pytest.raises(MemoryCapabilityError):
        call_tool(
            StubClaimGroundingService(),  # type: ignore[arg-type]
            "engram.claim_ground_entity",
            {"request": _claim_grounding_request()},
        )


def test_mcp_context_for_response_limits_drop_recent_and_extra_items(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pair = TenantCorpus("personal", "personal")

    class StubContextService:
        conn = object()
        token = MemoryToken(
            capabilities=frozenset({CAPABILITY_READ_PERSONAL}),
            allowed_pairs=frozenset({pair}),
            primary_pair=pair,
        )

    class FakeContextResult:
        def to_json(self) -> dict[str, object]:
            return {
                "context_id": "ctx-test",
                "status": "ok",
                "sections": [
                    {
                        "title": "Relevant Beliefs",
                        "lane": "current_beliefs",
                        "items": ["first belief", "second belief"],
                        "truncated": False,
                    },
                    {
                        "title": "Recent Signals",
                        "lane": "recent_signals",
                        "items": ["recent body"],
                        "truncated": False,
                    },
                ],
                "citations": [{"citation_id": "messages:test"}],
                "source_belief_ids": ["belief-test"],
                "source_segment_ids": ["segment-test"],
                "source_reference_ids": ["captures:test"],
                "rendered_context": "unfiltered",
            }

    monkeypatch.setattr(mcp_stdio, "context_for", lambda conn, request: FakeContextResult())

    payload = call_tool(
        StubContextService(),  # type: ignore[arg-type]
        "engram.context_for",
        {
            "query": "personal project context",
            "include_recent": False,
            "max_items_per_lane": 1,
        },
    )

    assert payload["sections"] == [
        {
            "title": "Relevant Beliefs",
            "lane": "current_beliefs",
            "items": ["first belief"],
            "truncated": True,
        }
    ]
    assert payload["rendered_context"] == "## Relevant Beliefs\n- first belief"
    assert payload["mcp_response_limits"] == {
        "include_recent": False,
        "max_items_per_lane": 1,
        "metadata_scope": "original_context_package",
    }
    assert payload["citations"] == [{"citation_id": "messages:test"}]
    assert payload["source_belief_ids"] == ["belief-test"]
    assert payload["source_segment_ids"] == ["segment-test"]
    assert payload["source_reference_ids"] == ["captures:test"]


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
