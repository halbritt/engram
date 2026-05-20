from __future__ import annotations

import json
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import psycopg
import pytest
from context_eval_synthetic_harness import (
    SYNTHETIC_CONTEXT_E2E_DIR,
    load_synthetic_context_eval_dataset,
    seed_synthetic_context_eval_dataset,
)

from engram import cli
from engram.mcp_stdio import call_tool
from engram.memory import CAPABILITY_READ_PERSONAL, MemoryService, MemoryToken, TenantCorpus


def test_synthetic_context_eval_harness_loads_fixture() -> None:
    dataset = load_synthetic_context_eval_dataset()

    assert dataset.root == SYNTHETIC_CONTEXT_E2E_DIR
    assert dataset.gold_set_path.exists()
    assert [belief.external_id for belief in dataset.beliefs] == [
        "belief:atlas-postgres",
        "belief:rowan-owner",
    ]
    assert [capture.external_id for capture in dataset.captures] == [
        "capture:atlas-privacy",
        "capture:rowan-plan",
    ]
    assert [(row.query_text, row.entity_kind) for row in dataset.grounding_evidence] == [
        ("Project Atlas", "product"),
        ("Rowan", "person"),
        ("Atlas Station", "place"),
    ]


def test_synthetic_context_eval_harness_runs_real_cli_end_to_end(
    conn: psycopg.Connection,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    seed = seed_synthetic_context_eval_dataset(conn)
    output_path = tmp_path / "context-eval-report.json"
    markdown_path = tmp_path / "context-eval-report.md"

    @contextmanager
    def existing_connection() -> Iterator[psycopg.Connection]:
        yield conn

    monkeypatch.setattr(cli, "connect", existing_connection)

    rc = cli.main(
        [
            "eval",
            "context",
            "--dataset-path",
            str(SYNTHETIC_CONTEXT_E2E_DIR),
            "--output",
            str(output_path),
            "--markdown-output",
            str(markdown_path),
            "--word-budget",
            "240",
        ]
    )

    assert rc == 0
    assert seed.belief_count == 2
    assert seed.capture_count == 2
    assert seed.grounding_evidence_count == 3
    report = json.loads(output_path.read_text(encoding="utf-8"))
    assert report["item_count"] == 2
    assert report["summary"]["required_fact_recall"] == 1.0
    assert report["summary"]["forbidden_stale_fact_hits"] == 0
    assert report["summary"]["required_gap_recall"] == 1.0
    assert report["summary"]["citation_coverage"] == 1.0
    assert markdown_path.read_text(encoding="utf-8").startswith("# Context Eval Summary")
    assert all(
        item["compiler_output"]["raw_output"]["snapshot_id"]
        for item in report["items"]
    )
    assert conn.execute("SELECT count(*) FROM context_snapshots").fetchone() == (2,)


def test_synthetic_context_eval_harness_resolves_ambiguous_entities_locally(
    conn: psycopg.Connection,
) -> None:
    seed_synthetic_context_eval_dataset(conn)
    service = _personal_memory_service(conn)

    atlas = call_tool(
        service,
        "engram.ground_entity",
        {"query": "Atlas", "tenant": "personal", "corpus": "personal"},
    )
    rowan = call_tool(
        service,
        "engram.ground_entity",
        {"query": "Rowan", "tenant": "personal", "corpus": "personal"},
    )

    atlas_kinds = {
        result["query_text"]: result["entity_kind"] for result in atlas["results"]
    }
    assert atlas["network_fetch"] == "unsupported"
    assert atlas_kinds["Project Atlas"] == "product"
    assert atlas_kinds["Atlas Station"] == "place"
    assert rowan["results"][0]["entity_kind"] == "person"
    assert rowan["results"][0]["citation"]["source_label"] == (
        "Synthetic web grounding: Rowan"
    )


def test_synthetic_grounding_harness_rejects_network_fetch(
    conn: psycopg.Connection,
) -> None:
    seed_synthetic_context_eval_dataset(conn)

    with pytest.raises(ValueError, match="network grounding fetch is unavailable"):
        call_tool(
            _personal_memory_service(conn),
            "engram.ground_entity",
            {"query": "Atlas", "allow_network": True},
        )


def _personal_memory_service(conn: psycopg.Connection) -> MemoryService:
    pair = TenantCorpus("personal", "personal")
    return MemoryService(
        conn,
        token=MemoryToken(
            capabilities=frozenset({CAPABILITY_READ_PERSONAL}),
            allowed_pairs=frozenset({pair}),
            primary_pair=pair,
        ),
    )
