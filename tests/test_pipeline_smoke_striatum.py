from __future__ import annotations

import json
import os
import select
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, BinaryIO

import psycopg
import pytest

from engram.striatum_ingest import ingest_striatum_bundle
from engram.striatum_projection import project_striatum_references

EG000_FIXTURE_DIR = Path(__file__).parent / "fixtures" / "striatum_eg000"
OMISSION_REASONS = {
    "disabled",
    "unavailable",
    "unauthorized",
    "privacy_tier_exceeded",
    "redaction_withheld",
    "stale_rejected",
    "over_budget",
    "duplicate",
    "generated_product_blocked",
    "low_score",
    "pair_mismatch",
}


def _write_mcp_message(stdin: BinaryIO, payload: dict[str, Any]) -> None:
    body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    stdin.write(f"Content-Length: {len(body)}\r\n\r\n".encode("ascii"))
    stdin.write(body)
    stdin.flush()


def _readline_with_timeout(stream: BinaryIO, *, deadline: float) -> bytes:
    while time.monotonic() < deadline:
        readable, _, _ = select.select([stream], [], [], 0.1)
        if readable:
            return stream.readline()
    raise TimeoutError("timed out waiting for MCP stdio response")


def _read_mcp_message(stdout: BinaryIO, *, timeout_seconds: float = 5.0) -> dict[str, Any]:
    deadline = time.monotonic() + timeout_seconds
    headers: dict[str, str] = {}
    while True:
        line = _readline_with_timeout(stdout, deadline=deadline)
        if line == b"":
            raise EOFError("MCP subprocess closed stdout")
        if line in {b"\r\n", b"\n"}:
            break
        name, sep, value = line.decode("ascii").partition(":")
        if sep != ":":
            raise ValueError(f"invalid MCP header line: {line!r}")
        headers[name.strip().lower()] = value.strip()

    content_length = headers.get("content-length")
    if content_length is None:
        raise ValueError("MCP response missing Content-Length header")
    length = int(content_length)
    body = stdout.read(length)
    if len(body) != length:
        raise EOFError("MCP subprocess returned a short response body")
    payload = json.loads(body.decode("utf-8"))
    assert isinstance(payload, dict)
    return payload


def _mcp_request(
    proc: subprocess.Popen[bytes],
    *,
    request_id: int,
    method: str,
    params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    assert proc.stdin is not None
    assert proc.stdout is not None
    request: dict[str, Any] = {"jsonrpc": "2.0", "id": request_id, "method": method}
    if params is not None:
        request["params"] = params
    _write_mcp_message(proc.stdin, request)
    response = _read_mcp_message(proc.stdout)
    assert response["id"] == request_id
    assert "error" not in response
    return response


def _call_tool(
    proc: subprocess.Popen[bytes],
    *,
    request_id: int,
    name: str,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    response = _mcp_request(
        proc,
        request_id=request_id,
        method="tools/call",
        params={"name": name, "arguments": arguments},
    )
    result = response["result"]
    assert result["isError"] is False, result["content"][0]["text"]
    return json.loads(result["content"][0]["text"])


def _start_mcp_stdio() -> subprocess.Popen[bytes]:
    test_database_url = os.environ.get("ENGRAM_TEST_DATABASE_URL")
    if not test_database_url:
        pytest.skip("ENGRAM_TEST_DATABASE_URL is required for the MCP subprocess")
    env = os.environ.copy()
    env["ENGRAM_DATABASE_URL"] = test_database_url
    return subprocess.Popen(
        [sys.executable, "-m", "engram.mcp_stdio"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        bufsize=0,
    )


def _stop_mcp_stdio(proc: subprocess.Popen[bytes]) -> None:
    if proc.poll() is not None:
        return
    if proc.stdin is not None:
        proc.stdin.close()
    try:
        proc.wait(timeout=2)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=2)


def _tool_names(tools_list_response: dict[str, Any]) -> set[str]:
    return {str(tool["name"]) for tool in tools_list_response["result"]["tools"]}


def _contains_text(value: Any, needle: str) -> bool:
    if isinstance(value, str):
        return needle in value
    if isinstance(value, dict):
        return any(_contains_text(item, needle) for item in value.values())
    if isinstance(value, list):
        return any(_contains_text(item, needle) for item in value)
    return False


def _collect_values(value: Any, key: str) -> list[Any]:
    if isinstance(value, dict):
        found = [value[key]] if key in value else []
        for item in value.values():
            found.extend(_collect_values(item, key))
        return found
    if isinstance(value, list):
        found: list[Any] = []
        for item in value:
            found.extend(_collect_values(item, key))
        return found
    return []


def _assert_packet_shape(packet: dict[str, Any]) -> None:
    assert isinstance(packet.get("packet_id"), str)
    assert packet["omission_reason_vocabulary"] == sorted(OMISSION_REASONS)
    selected_values = _collect_values(packet, "selected")
    omitted_values = _collect_values(packet, "omitted")
    assert any(isinstance(value, list) and value for value in selected_values)
    for omitted in omitted_values:
        if not isinstance(omitted, list):
            continue
        reasons = [item.get("reason") for item in omitted if isinstance(item, dict)]
        assert all(reason in OMISSION_REASONS for reason in reasons if reason)


def _assert_packet_audit_row(conn: psycopg.Connection, packet: dict[str, Any]) -> None:
    table_row = conn.execute("SELECT to_regclass('public.striatum_packet_audits')").fetchone()
    assert table_row is not None
    assert table_row[0] == "striatum_packet_audits"
    count = conn.execute(
        """
        SELECT count(*)::int
        FROM striatum_packet_audits
        WHERE packet_id = %s
        """,
        (packet["packet_id"],),
    ).fetchone()
    assert count == (1,)


def test_striatum_eg000_mcp_stdio_search_and_packet_smoke(
    conn: psycopg.Connection,
) -> None:
    ingest = ingest_striatum_bundle(conn, EG000_FIXTURE_DIR, repo="engram-eg000")
    assert ingest.records_seen == 5
    assert ingest.records_inserted == 5

    projection = project_striatum_references(conn)
    assert projection.captures_seen == 5
    assert projection.references_inserted >= 5
    if not conn.autocommit:
        conn.commit()

    proc = _start_mcp_stdio()
    try:
        initialize = _mcp_request(proc, request_id=1, method="initialize")
        assert initialize["result"]["serverInfo"]["name"] == "engram-mcp-stdio"

        tools = _mcp_request(proc, request_id=2, method="tools/list")
        names = _tool_names(tools)
        assert "engram.search" in names

        search_payload = _call_tool(
            proc,
            request_id=3,
            name="engram.search",
            arguments={
                "query": "RFC 0044 hardening boundary",
                "tenant": "striatum",
                "corpus": "striatum",
                "limit": 5,
                "filters": {"exact_refs": [{"ref_kind": "rfc_id", "ref_value": "RFC 0044"}]},
            },
        )
        results = search_payload["results"]
        assert len(results) == 1
        assert results[0]["tenant_id"] == "striatum"
        assert results[0]["corpus_id"] == "striatum"
        assert results[0]["sub_kind"] == "rfc"
        assert results[0]["provenance"]["path"] == "docs/rfcs/0044-striatum-memory-phase1.md"
        assert "RFC 0044" in results[0]["content"]

        if "engram.build_packet" not in names:
            pytest.skip("integration dependency: engram.build_packet is not exposed yet")

        packet = _call_tool(
            proc,
            request_id=4,
            name="engram.build_packet",
            arguments={
                "query": "RFC 0044 hardening boundary",
                "tenant": "striatum",
                "corpus": "striatum",
                "budget": 1400,
                "filters": {"exact_refs": [{"ref_kind": "rfc_id", "ref_value": "RFC 0044"}]},
            },
        )
        _assert_packet_shape(packet)
        assert _contains_text(packet, "docs/rfcs/0044-striatum-memory-phase1.md")
        _stop_mcp_stdio(proc)
        _assert_packet_audit_row(conn, packet)
    finally:
        _stop_mcp_stdio(proc)
