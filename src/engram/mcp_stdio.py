from __future__ import annotations

import argparse
import json
import sys
from typing import Any, BinaryIO

from engram.claim_grounding import ClaimGroundingError, ground_claim_entity_locally
from engram.context import (
    DEFAULT_CONTEXT_CORPUS_ID,
    DEFAULT_CONTEXT_TENANT_ID,
    DEFAULT_CONTEXT_WORD_BUDGET,
    DEFAULT_PRIVACY_TIER_CEILING,
    MAX_CONTEXT_CANDIDATES_PER_LANE,
    ContextForError,
    ContextForRequest,
    context_for,
)
from engram.db import connect
from engram.entity_grounding import search_grounding_evidence
from engram.memory import (
    CAPABILITY_DESCRIBE,
    CAPABILITY_READ_PERSONAL,
    CAPABILITY_READ_STRIATUM,
    DEFAULT_CORPUS_ID,
    DEFAULT_TENANT_ID,
    KNOWN_MEMORY_CAPABILITIES,
    ExactRefFilter,
    MemoryCapabilityError,
    MemoryReferenceError,
    MemorySearchFilters,
    MemoryService,
    MemoryToken,
    TenantCorpus,
)

JSONRPC_VERSION = "2.0"
MCP_PROTOCOL_VERSION = "2024-11-05"


def tool_definitions() -> list[dict[str, Any]]:
    """Return the local Engram MCP tool surface."""
    return [
        {
            "name": "engram.search",
            "description": "Search local Engram memory rows in an authorized tenant/corpus.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "tenant": {"type": "string", "default": DEFAULT_TENANT_ID},
                    "corpus": {"type": "string", "default": DEFAULT_CORPUS_ID},
                    "limit": {"type": "integer", "default": 10, "minimum": 1, "maximum": 50},
                    "k": {"type": "integer", "minimum": 1, "maximum": 50},
                    "filters": {
                        "anyOf": [
                            {
                                "type": "object",
                                "properties": {
                                    "exact_refs": {
                                        "anyOf": [
                                            {
                                                "type": "array",
                                                "items": {
                                                    "type": "object",
                                                    "properties": {
                                                        "ref_kind": {"type": "string"},
                                                        "ref_value": {"type": "string"},
                                                    },
                                                    "required": ["ref_kind", "ref_value"],
                                                    "additionalProperties": False,
                                                },
                                            },
                                            {"type": "null"},
                                        ],
                                        "default": None,
                                    }
                                },
                                "additionalProperties": False,
                            },
                            {"type": "null"},
                        ],
                        "default": None,
                    },
                },
                "required": ["query"],
                "additionalProperties": False,
            },
        },
        {
            "name": "engram.build_packet",
            "description": "Build a bounded cited local-memory packet for an authorized query.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "tenant": {"type": "string", "default": DEFAULT_TENANT_ID},
                    "corpus": {"type": "string", "default": DEFAULT_CORPUS_ID},
                    "budget": {"type": "integer", "default": 2000, "minimum": 1},
                    "filters": {
                        "anyOf": [
                            {
                                "type": "object",
                                "properties": {
                                    "exact_refs": {
                                        "anyOf": [
                                            {
                                                "type": "array",
                                                "items": {
                                                    "type": "object",
                                                    "properties": {
                                                        "ref_kind": {"type": "string"},
                                                        "ref_value": {"type": "string"},
                                                    },
                                                    "required": ["ref_kind", "ref_value"],
                                                    "additionalProperties": False,
                                                },
                                            },
                                            {"type": "null"},
                                        ],
                                        "default": None,
                                    }
                                },
                                "additionalProperties": False,
                            },
                            {"type": "null"},
                        ],
                        "default": None,
                    },
                },
                "required": ["query"],
                "additionalProperties": False,
            },
        },
        {
            "name": "engram.context_for",
            "description": (
                "Compile a cited local personal context package after explicit "
                "memory.read_personal authorization."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "tenant": {"type": "string", "default": DEFAULT_CONTEXT_TENANT_ID},
                    "corpus": {"type": "string", "default": DEFAULT_CONTEXT_CORPUS_ID},
                    "word_budget": {
                        "type": "integer",
                        "default": DEFAULT_CONTEXT_WORD_BUDGET,
                        "minimum": 1,
                    },
                    "privacy_tier_max": {
                        "type": "integer",
                        "default": DEFAULT_PRIVACY_TIER_CEILING,
                        "minimum": 0,
                        "maximum": 5,
                    },
                    "include_recent": {"type": "boolean", "default": True},
                    "max_items_per_lane": {
                        "type": "integer",
                        "default": MAX_CONTEXT_CANDIDATES_PER_LANE,
                        "minimum": 1,
                        "maximum": MAX_CONTEXT_CANDIDATES_PER_LANE,
                    },
                },
                "required": ["query"],
                "additionalProperties": False,
            },
        },
        {
            "name": "engram.ground_entity",
            "description": (
                "Search already-local entity grounding evidence for an authorized "
                "tenant/corpus. Network grounding fetch is unsupported."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "tenant": {"type": "string", "default": DEFAULT_CONTEXT_TENANT_ID},
                    "corpus": {"type": "string", "default": DEFAULT_CONTEXT_CORPUS_ID},
                    "limit": {"type": "integer", "default": 5, "minimum": 1, "maximum": 50},
                    "mode": {
                        "type": "string",
                        "default": "local_lookup",
                        "enum": ["local_lookup"],
                    },
                    "allow_network": {"type": "boolean", "default": False},
                },
                "required": ["query"],
                "additionalProperties": False,
            },
        },
        {
            "name": "engram.claim_ground_entity",
            "description": (
                "Resolve a claim_grounding.request.v1 against already-local grounding "
                "evidence. Network fetch remains unsupported."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "request": {
                        "type": "object",
                        "description": "RFC 0053 claim_grounding.request.v1 payload.",
                    },
                    "limit": {"type": "integer", "default": 5, "minimum": 1, "maximum": 50},
                },
                "required": ["request"],
                "additionalProperties": False,
            },
        },
        {
            "name": "engram.fetch_reference",
            "description": "Fetch a previously returned Engram reference after re-authorization.",
            "inputSchema": {
                "type": "object",
                "properties": {"reference_id": {"type": "string"}},
                "required": ["reference_id"],
                "additionalProperties": False,
            },
        },
        {
            "name": "engram.describe_corpus",
            "description": "Describe visible local Engram corpus metadata.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "tenant": {"type": "string", "default": DEFAULT_TENANT_ID},
                    "corpus": {"type": "string", "default": DEFAULT_CORPUS_ID},
                },
                "additionalProperties": False,
            },
        },
        {
            "name": "engram.health",
            "description": "Report local Engram substrate health and visible corpora.",
            "inputSchema": {
                "type": "object",
                "properties": {},
                "additionalProperties": False,
            },
        },
    ]


def call_tool(service: MemoryService, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    """Dispatch one RFC 0044 tool call."""
    if name == "engram.search":
        query = arguments.get("query")
        if not isinstance(query, str) or query.strip() == "":
            raise ValueError('engram.search requires non-empty "query"')
        limit_value = arguments.get("limit", arguments.get("k", 10))
        return {
            "results": service.search(
                query,
                tenant_id=str(arguments.get("tenant") or DEFAULT_TENANT_ID),
                corpus_id=str(arguments.get("corpus") or DEFAULT_CORPUS_ID),
                limit=int(limit_value),
                filters=parse_search_filters(arguments.get("filters")),
            )
        }
    if name == "engram.build_packet":
        query = arguments.get("query")
        if not isinstance(query, str) or query.strip() == "":
            raise ValueError('engram.build_packet requires non-empty "query"')
        budget = arguments.get("budget", 2000)
        build_packet = getattr(service, "build_packet", None)
        if build_packet is None:
            raise ValueError("engram.build_packet is unavailable")
        return build_packet(
            query,
            budget=int(budget),
            tenant_id=str(arguments.get("tenant") or DEFAULT_TENANT_ID),
            corpus_id=str(arguments.get("corpus") or DEFAULT_CORPUS_ID),
            filters=parse_search_filters(arguments.get("filters")),
        )
    if name == "engram.context_for":
        return call_context_for_tool(service, arguments)
    if name == "engram.ground_entity":
        return call_ground_entity_tool(service, arguments)
    if name == "engram.claim_ground_entity":
        return call_claim_ground_entity_tool(service, arguments)
    if name == "engram.fetch_reference":
        reference_id = arguments.get("reference_id")
        if not isinstance(reference_id, str) or reference_id.strip() == "":
            raise ValueError('engram.fetch_reference requires "reference_id"')
        return service.fetch_reference(reference_id)
    if name == "engram.describe_corpus":
        return service.describe_corpus(
            tenant_id=str(arguments.get("tenant") or DEFAULT_TENANT_ID),
            corpus_id=str(arguments.get("corpus") or DEFAULT_CORPUS_ID),
        )
    if name == "engram.health":
        return service.health()
    raise ValueError(f"unknown Engram MCP tool: {name}")


def call_context_for_tool(service: MemoryService, arguments: dict[str, Any]) -> dict[str, Any]:
    """Compile personal context through the MCP authorization boundary."""
    query = arguments.get("query")
    if not isinstance(query, str) or query.strip() == "":
        raise ValueError('engram.context_for requires non-empty "query"')

    query_text = query.strip()
    tenant_id = parse_string_argument(
        arguments,
        name="tenant",
        default=DEFAULT_CONTEXT_TENANT_ID,
    )
    corpus_id = parse_string_argument(
        arguments,
        name="corpus",
        default=DEFAULT_CONTEXT_CORPUS_ID,
    )
    word_budget = parse_int_argument(
        arguments,
        name="word_budget",
        default=DEFAULT_CONTEXT_WORD_BUDGET,
        minimum=1,
    )
    privacy_tier_max = parse_int_argument(
        arguments,
        name="privacy_tier_max",
        default=DEFAULT_PRIVACY_TIER_CEILING,
        minimum=0,
        maximum=5,
    )
    include_recent = parse_bool_argument(arguments, name="include_recent", default=True)
    max_items_per_lane = parse_int_argument(
        arguments,
        name="max_items_per_lane",
        default=MAX_CONTEXT_CANDIDATES_PER_LANE,
        minimum=1,
        maximum=MAX_CONTEXT_CANDIDATES_PER_LANE,
    )

    token = getattr(service, "token", None)
    conn = getattr(service, "conn", None)
    if not isinstance(token, MemoryToken) or conn is None:
        raise ValueError("engram.context_for is unavailable")

    if CAPABILITY_READ_PERSONAL not in token.capabilities:
        raise MemoryCapabilityError('missing capability "memory.read_personal"')
    token.authorize_read(TenantCorpus(tenant_id=tenant_id, corpus_id=corpus_id))

    request = ContextForRequest(
        query_text=query_text,
        tenant_id=tenant_id,
        corpus_id=corpus_id,
        word_budget=word_budget,
        privacy_tier_ceiling=privacy_tier_max,
    )
    result = context_for(conn, request).to_json()
    return apply_context_for_mcp_limits(
        result,
        include_recent=include_recent,
        max_items_per_lane=max_items_per_lane,
    )


def call_ground_entity_tool(service: MemoryService, arguments: dict[str, Any]) -> dict[str, Any]:
    """Search local entity-grounding evidence through MCP authorization."""
    query = arguments.get("query")
    if not isinstance(query, str) or query.strip() == "":
        raise ValueError('engram.ground_entity requires non-empty "query"')

    mode = parse_tool_string_argument(
        arguments,
        tool_name="engram.ground_entity",
        name="mode",
        default="local_lookup",
    )
    allow_network = parse_tool_bool_argument(
        arguments,
        tool_name="engram.ground_entity",
        name="allow_network",
        default=False,
    )
    if mode != "local_lookup" or allow_network:
        raise ValueError(
            "engram.ground_entity supports local_lookup only; "
            "network grounding fetch is unavailable"
        )

    tenant_id = parse_tool_string_argument(
        arguments,
        tool_name="engram.ground_entity",
        name="tenant",
        default=DEFAULT_CONTEXT_TENANT_ID,
    )
    corpus_id = parse_tool_string_argument(
        arguments,
        tool_name="engram.ground_entity",
        name="corpus",
        default=DEFAULT_CONTEXT_CORPUS_ID,
    )
    limit = parse_tool_int_argument(
        arguments,
        tool_name="engram.ground_entity",
        name="limit",
        default=5,
        minimum=1,
        maximum=50,
    )

    token = getattr(service, "token", None)
    conn = getattr(service, "conn", None)
    if not isinstance(token, MemoryToken) or conn is None:
        raise ValueError("engram.ground_entity is unavailable")

    token.authorize_read(TenantCorpus(tenant_id=tenant_id, corpus_id=corpus_id))
    return {
        "mode": "local_lookup",
        "network_fetch": "unsupported",
        "tenant_id": tenant_id,
        "corpus_id": corpus_id,
        "query": query.strip(),
        "results": search_grounding_evidence(
            conn,
            query_text=query.strip(),
            tenant_id=tenant_id,
            corpus_id=corpus_id,
            limit=limit,
        ),
    }


def call_claim_ground_entity_tool(
    service: MemoryService,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    """Resolve an RFC 0053 request through the local-only broker helper."""
    request = arguments.get("request")
    if not isinstance(request, dict):
        raise ValueError('engram.claim_ground_entity requires object "request"')
    limit = parse_tool_int_argument(
        arguments,
        tool_name="engram.claim_ground_entity",
        name="limit",
        default=5,
        minimum=1,
        maximum=50,
    )

    token = getattr(service, "token", None)
    conn = getattr(service, "conn", None)
    if not isinstance(token, MemoryToken) or conn is None:
        raise ValueError("engram.claim_ground_entity is unavailable")

    tenant_id = request.get("tenant_id")
    corpus_id = request.get("corpus_id")
    if not isinstance(tenant_id, str) or tenant_id.strip() == "":
        raise ValueError('engram.claim_ground_entity request requires "tenant_id"')
    if not isinstance(corpus_id, str) or corpus_id.strip() == "":
        raise ValueError('engram.claim_ground_entity request requires "corpus_id"')
    token.authorize_read(TenantCorpus(tenant_id=tenant_id.strip(), corpus_id=corpus_id.strip()))

    return ground_claim_entity_locally(conn, request, limit=limit).to_json()


def parse_tool_string_argument(
    arguments: dict[str, Any],
    *,
    tool_name: str,
    name: str,
    default: str,
) -> str:
    """Parse a non-empty string argument for an MCP tool."""
    value = arguments.get(name, default)
    if not isinstance(value, str) or value.strip() == "":
        raise ValueError(f"{tool_name} {name} must be a non-empty string")
    return value.strip()


def parse_tool_int_argument(
    arguments: dict[str, Any],
    *,
    tool_name: str,
    name: str,
    default: int,
    minimum: int,
    maximum: int | None = None,
) -> int:
    """Parse a bounded integer argument for an MCP tool."""
    value = arguments.get(name, default)
    if isinstance(value, bool):
        raise ValueError(f"{tool_name} {name} must be an integer")
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{tool_name} {name} must be an integer") from exc
    if parsed < minimum:
        raise ValueError(f"{tool_name} {name} must be >= {minimum}")
    if maximum is not None and parsed > maximum:
        raise ValueError(f"{tool_name} {name} must be <= {maximum}")
    return parsed


def parse_tool_bool_argument(
    arguments: dict[str, Any],
    *,
    tool_name: str,
    name: str,
    default: bool,
) -> bool:
    """Parse a boolean argument for an MCP tool without string coercion."""
    value = arguments.get(name, default)
    if not isinstance(value, bool):
        raise ValueError(f"{tool_name} {name} must be a boolean")
    return value


def parse_string_argument(arguments: dict[str, Any], *, name: str, default: str) -> str:
    """Parse a non-empty string MCP argument."""
    value = arguments.get(name, default)
    if not isinstance(value, str) or value.strip() == "":
        raise ValueError(f"engram.context_for {name} must be a non-empty string")
    return value.strip()


def parse_int_argument(
    arguments: dict[str, Any],
    *,
    name: str,
    default: int,
    minimum: int,
    maximum: int | None = None,
) -> int:
    """Parse a bounded integer MCP argument without accepting booleans."""
    value = arguments.get(name, default)
    if isinstance(value, bool):
        raise ValueError(f"engram.context_for {name} must be an integer")
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"engram.context_for {name} must be an integer") from exc
    if parsed < minimum:
        raise ValueError(f"engram.context_for {name} must be >= {minimum}")
    if maximum is not None and parsed > maximum:
        raise ValueError(f"engram.context_for {name} must be <= {maximum}")
    return parsed


def parse_bool_argument(arguments: dict[str, Any], *, name: str, default: bool) -> bool:
    """Parse a boolean MCP argument without string coercion."""
    value = arguments.get(name, default)
    if not isinstance(value, bool):
        raise ValueError(f"engram.context_for {name} must be a boolean")
    return value


def apply_context_for_mcp_limits(
    payload: dict[str, Any],
    *,
    include_recent: bool,
    max_items_per_lane: int,
) -> dict[str, Any]:
    """Apply MCP-only response limits that the current context request lacks."""
    if include_recent and max_items_per_lane == MAX_CONTEXT_CANDIDATES_PER_LANE:
        return payload

    limited = dict(payload)
    raw_sections = payload.get("sections")
    if not isinstance(raw_sections, list):
        return limited

    sections: list[dict[str, Any]] = []
    filtered = False
    all_sections_filtered = False
    for raw_section in raw_sections:
        if not isinstance(raw_section, dict):
            continue
        section = dict(raw_section)
        lane = str(section.get("lane", ""))
        if lane == "recent_signals" and not include_recent:
            filtered = True
            continue
        raw_items = section.get("items")
        if isinstance(raw_items, list):
            items = list(raw_items)
            if len(items) > max_items_per_lane:
                section["items"] = items[:max_items_per_lane]
                section["truncated"] = True
                filtered = True
        sections.append(section)

    if not sections:
        all_sections_filtered = True
        sections = [
            {
                "title": "Missing Data / Gaps",
                "lane": "gaps",
                "items": ["No matching personal memory found within requested MCP limits."],
                "truncated": False,
            }
        ]
        limited["status"] = "no_data"
        filtered = True

    limited["sections"] = sections
    limited["rendered_context"] = render_context_for_mcp_sections(sections)
    if filtered:
        limited["mcp_response_limits"] = {
            "include_recent": include_recent,
            "max_items_per_lane": max_items_per_lane,
            "metadata_scope": "original_context_package",
        }
    if all_sections_filtered:
        limited["citations"] = []
        limited["source_belief_ids"] = []
        limited["source_segment_ids"] = []
        limited["source_reference_ids"] = []
    return limited


def render_context_for_mcp_sections(sections: list[dict[str, Any]]) -> str:
    """Render JSON-shaped context sections after MCP response limiting."""
    blocks: list[str] = []
    for section in sections:
        title = str(section.get("title") or "")
        if title:
            blocks.append(f"## {title}")
        raw_items = section.get("items")
        if not isinstance(raw_items, list):
            continue
        blocks.extend(f"- {item}" for item in raw_items)
    return "\n".join(blocks)


def parse_search_filters(value: Any) -> MemorySearchFilters | None:
    """Parse optional MCP search filters into the typed memory API shape."""
    if value is None:
        return None
    if not isinstance(value, dict):
        raise ValueError("engram.search filters must be an object or null")
    exact_refs_value = value.get("exact_refs")
    if exact_refs_value is None:
        return MemorySearchFilters()
    if not isinstance(exact_refs_value, list):
        raise ValueError("engram.search filters.exact_refs must be an array or null")

    exact_refs: list[ExactRefFilter] = []
    for item in exact_refs_value:
        if not isinstance(item, dict):
            raise ValueError("engram.search filters.exact_refs entries must be objects")
        ref_kind = item.get("ref_kind")
        ref_value = item.get("ref_value")
        if not isinstance(ref_kind, str) or ref_kind.strip() == "":
            raise ValueError('engram.search filters.exact_refs entries require "ref_kind"')
        if not isinstance(ref_value, str) or ref_value.strip() == "":
            raise ValueError('engram.search filters.exact_refs entries require "ref_value"')
        exact_refs.append(ExactRefFilter(ref_kind=ref_kind, ref_value=ref_value))
    return MemorySearchFilters(exact_refs=tuple(exact_refs))


def build_token(args: argparse.Namespace) -> MemoryToken:
    """Build an Engram-local token from CLI options."""
    capabilities = {CAPABILITY_READ_STRIATUM, CAPABILITY_DESCRIBE}
    for value in args.capability or []:
        if value not in KNOWN_MEMORY_CAPABILITIES:
            raise ValueError(
                f'unknown --capability "{value}"; expected one of: '
                + ", ".join(sorted(KNOWN_MEMORY_CAPABILITIES))
            )
        capabilities.add(value)
    primary_pair = TenantCorpus(args.tenant, args.corpus)
    pairs = {primary_pair}
    for value in args.allow_pair or []:
        tenant, sep, corpus = value.partition("/")
        if sep != "/" or tenant.strip() == "" or corpus.strip() == "":
            raise ValueError('--allow-pair must use "tenant/corpus"')
        pairs.add(TenantCorpus(tenant, corpus))
    return MemoryToken(
        capabilities=frozenset(capabilities),
        allowed_pairs=frozenset(pairs),
        primary_pair=primary_pair,
    )


def mcp_success(request_id: Any, result: dict[str, Any]) -> dict[str, Any]:
    """Build a JSON-RPC success response."""
    return {"jsonrpc": JSONRPC_VERSION, "id": request_id, "result": result}


def mcp_error(request_id: Any, code: int, message: str) -> dict[str, Any]:
    """Build a JSON-RPC error response."""
    return {
        "jsonrpc": JSONRPC_VERSION,
        "id": request_id,
        "error": {"code": code, "message": message},
    }


def handle_request(service: MemoryService, request: dict[str, Any]) -> dict[str, Any] | None:
    """Handle one JSON-RPC request or notification."""
    method = request.get("method")
    request_id = request.get("id")
    if method == "notifications/initialized":
        return None
    if method == "initialize":
        return mcp_success(
            request_id,
            {
                "protocolVersion": MCP_PROTOCOL_VERSION,
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "engram-mcp-stdio", "version": "0.1.0"},
            },
        )
    if method == "tools/list":
        return mcp_success(request_id, {"tools": tool_definitions()})
    if method == "tools/call":
        params = request.get("params") or {}
        if not isinstance(params, dict):
            return mcp_error(request_id, -32602, "tools/call params must be an object")
        name = params.get("name")
        arguments = params.get("arguments") or {}
        if not isinstance(name, str) or not isinstance(arguments, dict):
            return mcp_error(request_id, -32602, "tools/call requires name and arguments")
        try:
            payload = call_tool(service, name, arguments)
        except (
            ClaimGroundingError,
            ContextForError,
            MemoryCapabilityError,
            MemoryReferenceError,
            ValueError,
        ) as exc:
            return mcp_success(
                request_id,
                {
                    "content": [{"type": "text", "text": str(exc)}],
                    "isError": True,
                },
            )
        return mcp_success(
            request_id,
            {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(payload, ensure_ascii=False, sort_keys=True),
                    }
                ],
                "isError": False,
            },
        )
    return mcp_error(request_id, -32601, f"unknown method: {method}")


def read_message(stdin: BinaryIO) -> dict[str, Any] | None:
    """Read one Content-Length framed JSON-RPC message."""
    headers: dict[str, str] = {}
    while True:
        line = stdin.readline()
        if line == b"":
            return None
        if line in {b"\r\n", b"\n"}:
            break
        name, sep, value = line.decode("ascii").partition(":")
        if sep != ":":
            raise ValueError("invalid MCP stdio header")
        headers[name.strip().lower()] = value.strip()
    length_value = headers.get("content-length")
    if length_value is None:
        raise ValueError("missing Content-Length header")
    body = stdin.read(int(length_value))
    if len(body) != int(length_value):
        raise ValueError("short MCP stdio body")
    payload = json.loads(body.decode("utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("MCP message must be a JSON object")
    return payload


def write_message(stdout: BinaryIO, payload: dict[str, Any]) -> None:
    """Write one Content-Length framed JSON-RPC message."""
    body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    stdout.write(f"Content-Length: {len(body)}\r\n\r\n".encode("ascii"))
    stdout.write(body)
    stdout.flush()


def serve_stdio(service: MemoryService, stdin: BinaryIO, stdout: BinaryIO) -> None:
    """Serve MCP requests until stdin closes."""
    while True:
        request = read_message(stdin)
        if request is None:
            return
        response = handle_request(service, request)
        if response is not None:
            write_message(stdout, response)


def build_parser() -> argparse.ArgumentParser:
    """Build the standalone MCP stdio parser."""
    parser = argparse.ArgumentParser(prog="engram-mcp-stdio")
    parser.add_argument("--tenant", default=DEFAULT_TENANT_ID)
    parser.add_argument("--corpus", default=DEFAULT_CORPUS_ID)
    parser.add_argument(
        "--capability",
        action="append",
        help="Add an Engram-local memory capability to the default token",
    )
    parser.add_argument(
        "--allow-pair",
        action="append",
        help='Add a visible tenant/corpus pair, formatted as "tenant/corpus"',
    )
    parser.add_argument(
        "--health-check",
        action="store_true",
        help="Print health JSON once and exit instead of serving MCP stdio",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the Engram read-only MCP stdio server."""
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        token = build_token(args)
    except ValueError as exc:
        print(f"engram-mcp-stdio: {exc}", file=sys.stderr)
        return 2
    with connect() as conn:
        service = MemoryService(conn, token=token)
        if args.health_check:
            print(json.dumps(service.health(), ensure_ascii=False, sort_keys=True))
            return 0
        serve_stdio(service, sys.stdin.buffer, sys.stdout.buffer)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
