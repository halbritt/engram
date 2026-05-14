from __future__ import annotations

import argparse
import json
import sys
from typing import Any, BinaryIO

from engram.db import connect
from engram.memory import (
    CAPABILITY_DESCRIBE,
    CAPABILITY_READ_STRIATUM,
    DEFAULT_CORPUS_ID,
    DEFAULT_TENANT_ID,
    MemoryCapabilityError,
    MemoryReferenceError,
    MemoryService,
    MemoryToken,
    TenantCorpus,
)

JSONRPC_VERSION = "2.0"
MCP_PROTOCOL_VERSION = "2024-11-05"


def tool_definitions() -> list[dict[str, Any]]:
    """Return the exact RFC 0044 Phase 1 tool surface."""
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
                },
                "required": ["query"],
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
            )
        }
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


def build_token(args: argparse.Namespace) -> MemoryToken:
    """Build an Engram-local token from CLI options."""
    capabilities = {CAPABILITY_READ_STRIATUM, CAPABILITY_DESCRIBE}
    capabilities.update(args.capability or [])
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
        except (MemoryCapabilityError, MemoryReferenceError, ValueError) as exc:
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
