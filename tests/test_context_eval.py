from __future__ import annotations

import json
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import psycopg
import pytest
from psycopg.types.json import Jsonb
from test_context_for import insert_context_belief

from engram import cli
from engram.context_eval import (
    CONTEXT_EVAL_DATASET_ENV_VAR,
    CONTEXT_EVAL_DATASET_GOLD_FILENAME,
    ContextCompileRequest,
    ContextCompilerOutput,
    ContextCompilerUnavailableError,
    ContextEvalItem,
    ContextEvalSchemaError,
    context_eval_gold_set_path,
    load_eval_items,
    resolve_context_eval_gold_set_path,
    run_context_eval,
    run_context_eval_file,
    validate_eval_dataset,
    write_json_report,
    write_markdown_summary,
)
from engram.phase4 import refresh_current_beliefs

FIXTURE_PATH = Path("tests/fixtures/context_eval/gold.jsonl")


def _write_eval_jsonl(path: Path, payloads: tuple[dict[str, object], ...]) -> None:
    path.write_text(
        "".join(json.dumps(payload, sort_keys=True) + "\n" for payload in payloads),
        encoding="utf-8",
    )


def _insert_stable_evidence_message(
    conn: psycopg.Connection,
    *,
    external_id: str,
    content_text: str,
) -> str:
    source_id = conn.execute(
        """
        INSERT INTO sources (source_kind, external_id, raw_payload)
        VALUES ('chatgpt', %s, '{}')
        RETURNING id
        """,
        (f"source:{external_id}",),
    ).fetchone()[0]
    conversation_id = conn.execute(
        """
        INSERT INTO conversations (
            source_id,
            source_kind,
            external_id,
            raw_payload,
            title
        )
        VALUES (%s, 'chatgpt', %s, '{}', 'synthetic context eval')
        RETURNING id
        """,
        (source_id, f"conversation:{external_id}"),
    ).fetchone()[0]
    return conn.execute(
        """
        INSERT INTO messages (
            source_id,
            source_kind,
            conversation_id,
            external_id,
            raw_payload,
            role,
            content_text,
            sequence_index
        )
        VALUES (%s, 'chatgpt', %s, %s, '{}', 'user', %s, 0)
        RETURNING id::text
        """,
        (source_id, conversation_id, external_id, content_text),
    ).fetchone()[0]


def _insert_stable_capture(
    conn: psycopg.Connection,
    *,
    external_id: str,
    content_text: str,
) -> str:
    source_id = conn.execute(
        """
        INSERT INTO sources (source_kind, external_id, raw_payload)
        VALUES ('capture', %s, '{}')
        RETURNING id
        """,
        (f"source:{external_id}",),
    ).fetchone()[0]
    return conn.execute(
        """
        INSERT INTO captures (
            source_id,
            source_kind,
            external_id,
            raw_payload,
            privacy_tier,
            capture_type,
            content_text,
            observed_at
        )
        VALUES (%s, 'capture', %s, %s, 1, 'observation', %s, now())
        RETURNING id::text
        """,
        (
            source_id,
            external_id,
            Jsonb({"sensitivity_class": "routine_project"}),
            content_text,
        ),
    ).fetchone()[0]


def _seed_synthetic_context_eval_corpus(conn: psycopg.Connection) -> None:
    atlas_evidence_id = _insert_stable_evidence_message(
        conn,
        external_id="belief:atlas-postgres",
        content_text="Project Atlas uses local Postgres.",
    )
    rowan_evidence_id = _insert_stable_evidence_message(
        conn,
        external_id="belief:rowan-owner",
        content_text="Rowan owns the migration checklist.",
    )
    insert_context_belief(
        conn,
        message_text="Project Atlas uses local Postgres.",
        predicate="uses_tool",
        object_text="Project Atlas uses local Postgres",
        evidence_message_id=atlas_evidence_id,
    )
    insert_context_belief(
        conn,
        message_text="Rowan owns the migration checklist.",
        predicate="working_on",
        object_text="Rowan owns the migration checklist",
        claim_stability_class="project_status",
        evidence_message_id=rowan_evidence_id,
    )
    _insert_stable_capture(
        conn,
        external_id="capture:atlas-privacy",
        content_text=(
            "Project Atlas uses local Postgres. "
            "Project Atlas forbids cloud telemetry. "
            "No launch date is known."
        ),
    )
    _insert_stable_capture(
        conn,
        external_id="capture:rowan-plan",
        content_text="Rowan owns the migration checklist. No budget is recorded.",
    )
    refresh_current_beliefs(conn)


def test_context_eval_dataset_env_var_name_is_stable() -> None:
    assert CONTEXT_EVAL_DATASET_ENV_VAR == "ENGRAM_EVAL_DATASET_PATH"


def test_context_eval_gold_set_path_resolves_dataset_directory(tmp_path: Path) -> None:
    dataset_path = tmp_path / "private-context-eval"
    dataset_path.mkdir()

    gold_set_path = context_eval_gold_set_path(dataset_path)

    assert gold_set_path == dataset_path / CONTEXT_EVAL_DATASET_GOLD_FILENAME


def test_context_eval_gold_set_path_accepts_direct_jsonl_file(tmp_path: Path) -> None:
    gold_set_path = tmp_path / "owner-authored-context.jsonl"
    gold_set_path.write_text("", encoding="utf-8")

    resolved_path = context_eval_gold_set_path(gold_set_path)

    assert resolved_path == gold_set_path


def test_resolve_context_eval_gold_set_path_uses_environment_dataset_path(
    tmp_path: Path,
) -> None:
    dataset_path = tmp_path / "env-dataset"
    dataset_path.mkdir()

    resolved_path = resolve_context_eval_gold_set_path(
        environ={"ENGRAM_EVAL_DATASET_PATH": str(dataset_path)}
    )

    assert resolved_path == dataset_path / CONTEXT_EVAL_DATASET_GOLD_FILENAME


def test_resolve_context_eval_gold_set_path_prefers_cli_dataset_path_over_env(
    tmp_path: Path,
) -> None:
    cli_dataset_path = tmp_path / "cli-dataset"
    env_dataset_path = tmp_path / "env-dataset"
    cli_dataset_path.mkdir()
    env_dataset_path.mkdir()

    resolved_path = resolve_context_eval_gold_set_path(
        dataset_path=cli_dataset_path,
        environ={"ENGRAM_EVAL_DATASET_PATH": str(env_dataset_path)},
    )

    assert resolved_path == cli_dataset_path / CONTEXT_EVAL_DATASET_GOLD_FILENAME


def test_resolve_context_eval_gold_set_path_preserves_gold_set_path_compatibility(
    tmp_path: Path,
) -> None:
    gold_set_path = tmp_path / "legacy-gold-set.jsonl"

    resolved_path = resolve_context_eval_gold_set_path(
        gold_set_path=gold_set_path,
        environ={"ENGRAM_EVAL_DATASET_PATH": str(tmp_path / "env-dataset")},
    )

    assert resolved_path == gold_set_path


def test_validate_eval_dataset_rejects_invalid_dataset_item(tmp_path: Path) -> None:
    dataset_path = tmp_path / "private-context-eval"
    dataset_path.mkdir()
    _write_eval_jsonl(
        dataset_path / CONTEXT_EVAL_DATASET_GOLD_FILENAME,
        (
            {
                "id": "invalid",
                "query": "What should be known?",
                "required_facts": "not a list",
            },
        ),
    )
    gold_set_path = resolve_context_eval_gold_set_path(dataset_path=dataset_path)

    with pytest.raises(ContextEvalSchemaError, match='"required_facts"'):
        validate_eval_dataset(gold_set_path)


def test_load_eval_items_accepts_query_schema_and_prompt_alias() -> None:
    item = ContextEvalItem.from_json(
        {
            "schema_version": "context_eval.item.v1",
            "id": "alias",
            "prompt": "What changed?",
            "required_facts": ["The compiler emits citations"],
            "forbidden_stale_facts": [],
            "required_gaps": ["No owner is known"],
            "relevant_entities": ["compiler"],
            "allowed_evidence_references": ["belief:compiler-citations"],
            "privacy_ceiling": 1,
        }
    )

    assert item.query == "What changed?"
    assert item.required_facts == ("The compiler emits citations",)
    assert item.allowed_evidence_references == ("belief:compiler-citations",)


def test_load_eval_items_rejects_mismatched_prompt_and_query() -> None:
    with pytest.raises(ContextEvalSchemaError, match=r"query.*prompt"):
        ContextEvalItem.from_json(
            {
                "schema_version": "context_eval.item.v1",
                "id": "bad",
                "query": "Query text",
                "prompt": "Different prompt",
            }
        )


def test_run_context_eval_scores_fixture_outputs() -> None:
    items = load_eval_items(FIXTURE_PATH)

    def fake_compiler(request: ContextCompileRequest) -> ContextCompilerOutput:
        if request.eval_item_id == "ce-001":
            return ContextCompilerOutput(
                text=(
                    "Relevant Beliefs\n"
                    "Project Atlas uses local Postgres. "
                    "Project Atlas forbids cloud telemetry. "
                    "Missing Data: No launch date is known."
                ),
                citations=("belief:atlas-postgres", "capture:atlas-privacy"),
                gaps=("No launch date is known",),
            )
        return ContextCompilerOutput(
            text=(
                "Rowan owns the migration checklist. "
                "Mira owns the migration checklist. "
                "No budget is recorded. "
                "The migration will finish during a lunar window."
            ),
            citations=(),
            gaps=("No budget is recorded",),
        )

    report = run_context_eval(items, compiler=fake_compiler)

    assert report.item_count == 2
    assert report.summary["required_fact_recall"] == 1.0
    assert report.summary["forbidden_stale_fact_hits"] == 1
    assert report.summary["required_gap_recall"] == 1.0
    assert report.summary["citation_coverage"] == 0.5
    assert report.summary["unsupported_fact_approximation"] == 1

    first, second = report.items
    assert first.required_facts_missing == ()
    assert first.citation_misses == ()
    assert second.forbidden_stale_fact_hits == ("Mira owns the migration checklist",)
    assert second.citation_misses == ("belief:rowan-owner",)
    assert second.unsupported_fact_candidates == (
        "The migration will finish during a lunar window.",
    )


def test_cli_context_eval_runs_real_compiler_against_synthetic_corpus(
    conn: psycopg.Connection,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _seed_synthetic_context_eval_corpus(conn)
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
            "--gold-set",
            str(FIXTURE_PATH),
            "--output",
            str(output_path),
            "--markdown-output",
            str(markdown_path),
            "--word-budget",
            "240",
        ]
    )

    assert rc == 0
    report = json.loads(output_path.read_text(encoding="utf-8"))
    assert report["item_count"] == 2
    assert report["summary"]["required_fact_recall"] == 1.0
    assert report["summary"]["forbidden_stale_fact_hits"] == 0
    assert report["summary"]["required_gap_recall"] == 1.0
    assert report["summary"]["citation_coverage"] == 1.0
    assert markdown_path.read_text(encoding="utf-8").startswith("# Context Eval Summary")


def test_run_context_eval_normalizes_mapping_compiler_outputs() -> None:
    item = ContextEvalItem(
        item_id="mapping",
        query="What is known?",
        required_facts=("The package builder emits omission reasons",),
        required_gaps=("No stale snapshot policy is known",),
        allowed_evidence_references=("ref:packet-policy",),
    )

    def fake_compiler(request: ContextCompileRequest) -> dict[str, object]:
        return {
            "sections": [
                {
                    "title": "Relevant Beliefs",
                    "items": [
                        {
                            "content": "The package builder emits omission reasons.",
                            "citation": {"reference_id": "ref:packet-policy"},
                        }
                    ],
                },
                {"title": "Missing Data", "content": "No stale snapshot policy is known."},
            ],
            "citations": [{"reference_id": "ref:packet-policy"}],
            "gaps": ["No stale snapshot policy is known"],
        }

    report = run_context_eval((item,), compiler=fake_compiler)
    score = report.items[0]

    assert score.required_fact_recall == 1.0
    assert score.required_gap_recall == 1.0
    assert score.citation_coverage == 1.0


def test_run_context_eval_preserves_snapshot_metadata_in_raw_output() -> None:
    item = ContextEvalItem(item_id="snapshot", query="What is known?")

    def fake_compiler(request: ContextCompileRequest) -> dict[str, object]:
        return {
            "compiler_version": "context_for.v1.phase4.minimal",
            "snapshot_id": "00000000-0000-0000-0000-000000000001",
            "memory_epoch": 42,
            "rendered_context": "Snapshot metadata is preserved.",
        }

    report = run_context_eval((item,), compiler=fake_compiler)
    raw_output = report.items[0].compiler_output.raw_output

    assert raw_output["compiler_version"] == "context_for.v1.phase4.minimal"
    assert raw_output["snapshot_id"] == "00000000-0000-0000-0000-000000000001"
    assert raw_output["memory_epoch"] == 42


def test_report_writers_emit_json_and_markdown(tmp_path: Path) -> None:
    item = ContextEvalItem(item_id="write", query="Q", required_facts=("A fact",))

    def fake_compiler(request: ContextCompileRequest) -> str:
        return "A fact."

    report = run_context_eval((item,), compiler=fake_compiler)
    json_path = tmp_path / "report.json"
    markdown_path = tmp_path / "summary.md"

    write_json_report(report, json_path)
    write_markdown_summary(report, markdown_path)

    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["runner_version"] == "context_eval.runner.v1"
    assert payload["items"][0]["item_id"] == "write"
    assert "# Context Eval Summary" in markdown_path.read_text(encoding="utf-8")


def test_run_context_eval_file_uses_fake_compiler_without_private_corpus() -> None:
    def fake_compiler(request: ContextCompileRequest) -> str:
        return (
            "Project Atlas uses local Postgres. "
            "Project Atlas forbids cloud telemetry. "
            "No launch date is known. "
            "Rowan owns the migration checklist. "
            "No budget is recorded. "
            "belief:atlas-postgres capture:atlas-privacy belief:rowan-owner"
        )

    report = run_context_eval_file(FIXTURE_PATH, compiler=fake_compiler)

    assert report.item_count == 2
    assert report.summary["required_fact_recall"] == 1.0


def test_run_context_eval_requires_compiler_until_context_service_exists() -> None:
    with pytest.raises(ContextCompilerUnavailableError, match="no context compiler"):
        run_context_eval((ContextEvalItem(item_id="no-compiler", query="Q"),))
