"""Tests for ``engram.cli`` argument parsing and dispatch wiring.

Covers RFC 0015 §1: the CLI module previously had zero test coverage. These
tests drive ``cli.main()`` directly with synthetic argv (rather than spawning
a subprocess) and use ``monkeypatch`` to swap out the heavy worker functions
that ``main`` dispatches to. The intent is to verify *dispatch* — argument
parsing, exit codes, and that flags wire through to the underlying calls —
not the worker behavior, which is exercised in the phase-specific test files.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from engram import cli

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def fake_connect(monkeypatch: pytest.MonkeyPatch, conn: Any) -> Any:
    """Replace ``cli.connect`` so ``with connect() as c:`` yields the test conn.

    The CLI uses ``with connect() as conn:`` for every subcommand, so we need
    a context manager that yields the existing test connection without closing
    it (``conftest.py``'s ``conn`` fixture owns the lifecycle).
    """

    @contextmanager
    def _fake_connect(*args: Any, **kwargs: Any) -> Iterator[Any]:
        yield conn

    monkeypatch.setattr(cli, "connect", _fake_connect)
    return conn


@pytest.fixture()
def fake_cli_connect(monkeypatch: pytest.MonkeyPatch) -> Any:
    """Replace ``cli.connect`` without requiring a live test database."""

    conn = SimpleNamespace(commit=lambda: None)

    @contextmanager
    def _fake_connect(*args: Any, **kwargs: Any) -> Iterator[Any]:
        yield conn

    monkeypatch.setattr(cli, "connect", _fake_connect)
    return conn


def _make_ingest_result() -> SimpleNamespace:
    return SimpleNamespace(
        source_id="src-123",
        conversations_inserted=1,
        conversations_seen=1,
        messages_inserted=2,
        messages_seen=2,
    )


def _make_striatum_ingest_result() -> SimpleNamespace:
    return SimpleNamespace(
        source_id="src-striatum",
        bundle_id="bundle-123",
        repo="striatum",
        records_inserted=1,
        records_seen=1,
        records_skipped=0,
        row_counts={"rfc": 1},
    )


def _make_segment_result(**overrides: int) -> SimpleNamespace:
    base = {"processed": 1, "created": 1, "skipped": 0, "failed": 0}
    base.update(overrides)
    return SimpleNamespace(**base)


def _make_embed_result(**overrides: int) -> SimpleNamespace:
    base = {
        "processed": 1,
        "created": 1,
        "cache_hits": 0,
        "activated": 1,
        "failed": 0,
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def _claim_grounding_request() -> dict[str, Any]:
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


def _claim_grounding_network_request() -> dict[str, Any]:
    payload = _claim_grounding_request()
    payload["allowed_modes"] = ["local_lookup", "network_fetch"]
    payload["network_grant"] = {
        "grant_id": "grant-cli-001",
        "granted_by": "operator",
        "granted_at": "2026-05-18T00:00:00Z",
        "expires_at": None,
        "purpose": "entity_grounding",
        "search_query": "OpenAI Codex",
        "query_text_class": "entity_surface_form",
        "query_privacy_tier": 1,
        "allowed_network_targets": ["internet_search"],
    }
    payload["sensitivity_ceiling"] = ["routine_project"]
    return payload


# ---------------------------------------------------------------------------
# Help / parser-level behavior
# ---------------------------------------------------------------------------


def test_help_exits_zero_and_prints_usage(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as excinfo:
        cli.main(["--help"])
    assert excinfo.value.code == 0
    captured = capsys.readouterr()
    assert "usage" in captured.out.lower()


def test_unknown_subcommand_exits_nonzero(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as excinfo:
        cli.main(["nonsense-cmd"])
    # argparse uses code 2 for parse errors.
    assert excinfo.value.code != 0


def test_missing_required_arg_for_ingest_chatgpt_exits_nonzero(
    capsys: pytest.CaptureFixture[str],
) -> None:
    # ingest-chatgpt requires a positional <path>.
    with pytest.raises(SystemExit) as excinfo:
        cli.main(["ingest-chatgpt"])
    assert excinfo.value.code != 0


def test_no_subcommand_exits_nonzero() -> None:
    with pytest.raises(SystemExit) as excinfo:
        cli.main([])
    assert excinfo.value.code != 0


# ---------------------------------------------------------------------------
# migrate
# ---------------------------------------------------------------------------


def test_migrate_invokes_migrate_and_returns_zero(
    monkeypatch: pytest.MonkeyPatch,
    fake_connect: Any,
) -> None:
    calls: list[Any] = []

    def fake_migrate(connection: Any) -> list[str]:
        calls.append(connection)
        return ["001_init.sql"]

    monkeypatch.setattr(cli, "migrate", fake_migrate)

    rc = cli.main(["migrate"])

    assert rc == 0
    assert len(calls) == 1
    assert calls[0] is fake_connect


# ---------------------------------------------------------------------------
# ingest-chatgpt / ingest-claude / ingest-gemini
# ---------------------------------------------------------------------------


def test_ingest_chatgpt_dispatches_to_ingest_chatgpt_export(
    monkeypatch: pytest.MonkeyPatch,
    fake_connect: Any,
    tmp_path: Path,
) -> None:
    captured: dict[str, Any] = {}

    def fake_ingest(connection: Any, path: Path) -> SimpleNamespace:
        captured["conn"] = connection
        captured["path"] = path
        return _make_ingest_result()

    monkeypatch.setattr(cli, "ingest_chatgpt_export", fake_ingest)

    rc = cli.main(["ingest-chatgpt", str(tmp_path)])

    assert rc == 0
    assert captured["conn"] is fake_connect
    assert captured["path"] == tmp_path


def test_ingest_claude_dispatches_to_ingest_claude_export(
    monkeypatch: pytest.MonkeyPatch,
    fake_connect: Any,
    tmp_path: Path,
) -> None:
    captured: dict[str, Any] = {}

    def fake_ingest(connection: Any, path: Path) -> SimpleNamespace:
        captured["conn"] = connection
        captured["path"] = path
        return _make_ingest_result()

    monkeypatch.setattr(cli, "ingest_claude_export", fake_ingest)

    rc = cli.main(["ingest-claude", str(tmp_path)])

    assert rc == 0
    assert captured["path"] == tmp_path


def test_ingest_gemini_accepts_positional_path(
    monkeypatch: pytest.MonkeyPatch,
    fake_connect: Any,
    tmp_path: Path,
) -> None:
    captured: dict[str, Any] = {}

    def fake_ingest(connection: Any, path: Path) -> SimpleNamespace:
        captured["path"] = path
        return _make_ingest_result()

    monkeypatch.setattr(cli, "ingest_gemini_export", fake_ingest)

    rc = cli.main(["ingest-gemini", str(tmp_path)])

    assert rc == 0
    assert captured["path"] == tmp_path


def test_ingest_gemini_accepts_path_option(
    monkeypatch: pytest.MonkeyPatch,
    fake_connect: Any,
    tmp_path: Path,
) -> None:
    captured: dict[str, Any] = {}

    def fake_ingest(connection: Any, path: Path) -> SimpleNamespace:
        captured["path"] = path
        return _make_ingest_result()

    monkeypatch.setattr(cli, "ingest_gemini_export", fake_ingest)

    rc = cli.main(["ingest-gemini", "--path", str(tmp_path)])

    assert rc == 0
    assert captured["path"] == tmp_path


def test_ingest_striatum_dispatches_to_ingester(
    monkeypatch: pytest.MonkeyPatch,
    fake_cli_connect: Any,
    tmp_path: Path,
) -> None:
    captured: dict[str, Any] = {}

    def fake_ingest(connection: Any, bundle: Path, *, repo: str) -> SimpleNamespace:
        captured["conn"] = connection
        captured["bundle"] = bundle
        captured["repo"] = repo
        return _make_striatum_ingest_result()

    monkeypatch.setattr(cli, "ingest_striatum_bundle", fake_ingest)

    rc = cli.main(["ingest-striatum", "--bundle", str(tmp_path), "--repo", "striatum"])

    assert rc == 0
    assert captured == {"conn": fake_cli_connect, "bundle": tmp_path, "repo": "striatum"}


def test_phase1_ingest_striatum_dispatches_to_ingester(
    monkeypatch: pytest.MonkeyPatch,
    fake_cli_connect: Any,
    tmp_path: Path,
) -> None:
    captured: dict[str, Any] = {}

    def fake_ingest(connection: Any, bundle: Path, *, repo: str) -> SimpleNamespace:
        captured["conn"] = connection
        captured["bundle"] = bundle
        captured["repo"] = repo
        return _make_striatum_ingest_result()

    monkeypatch.setattr(cli, "ingest_striatum_bundle", fake_ingest)

    rc = cli.main(["phase1", "ingest-striatum", "--bundle", str(tmp_path)])

    assert rc == 0
    assert captured == {"conn": fake_cli_connect, "bundle": tmp_path, "repo": "striatum"}


def test_describe_corpus_dispatches_to_memory_service(
    monkeypatch: pytest.MonkeyPatch,
    fake_cli_connect: Any,
) -> None:
    captured: dict[str, Any] = {}

    class FakeMemoryService:
        def __init__(self, connection: Any) -> None:
            captured["conn"] = connection

        def describe_corpus(self, *, tenant_id: str, corpus_id: str) -> dict[str, Any]:
            captured["tenant_id"] = tenant_id
            captured["corpus_id"] = corpus_id
            return {"tenant_id": tenant_id, "corpus_id": corpus_id}

    monkeypatch.setattr(cli, "MemoryService", FakeMemoryService)

    rc = cli.main(["describe-corpus", "striatum"])

    assert rc == 0
    assert captured == {
        "conn": fake_cli_connect,
        "tenant_id": "striatum",
        "corpus_id": "striatum",
    }


def test_describe_corpus_rejects_non_striatum_shorthand_without_tenant(
    monkeypatch: pytest.MonkeyPatch,
    fake_cli_connect: Any,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """EG-000 baseline: positional shorthand only collapses for `striatum`.

    Any other corpus value must require an explicit `--tenant`.
    """
    called: dict[str, Any] = {}

    class FakeMemoryService:
        def __init__(self, connection: Any) -> None:
            called["conn"] = connection

        def describe_corpus(self, *, tenant_id: str, corpus_id: str) -> dict[str, Any]:
            called["tenant_id"] = tenant_id
            called["corpus_id"] = corpus_id
            return {"tenant_id": tenant_id, "corpus_id": corpus_id}

    monkeypatch.setattr(cli, "MemoryService", FakeMemoryService)

    rc = cli.main(["describe-corpus", "personal"])

    assert rc == 2
    assert "specify --tenant" in capsys.readouterr().err
    assert called == {}


def test_describe_corpus_accepts_non_striatum_corpus_with_explicit_tenant(
    monkeypatch: pytest.MonkeyPatch,
    fake_cli_connect: Any,
) -> None:
    """EG-000 baseline: non-striatum corpus is allowed when --tenant is given."""
    captured: dict[str, Any] = {}

    class FakeMemoryService:
        def __init__(self, connection: Any) -> None:
            captured["conn"] = connection

        def describe_corpus(self, *, tenant_id: str, corpus_id: str) -> dict[str, Any]:
            captured["tenant_id"] = tenant_id
            captured["corpus_id"] = corpus_id
            return {"tenant_id": tenant_id, "corpus_id": corpus_id}

    monkeypatch.setattr(cli, "MemoryService", FakeMemoryService)

    rc = cli.main(["describe-corpus", "personal", "--tenant", "personal"])

    assert rc == 0
    assert captured == {
        "conn": fake_cli_connect,
        "tenant_id": "personal",
        "corpus_id": "personal",
    }


def test_phase_projection_run_dispatches_to_projection_worker(
    monkeypatch: pytest.MonkeyPatch,
    fake_cli_connect: Any,
    capsys: pytest.CaptureFixture[str],
) -> None:
    captured: dict[str, Any] = {}

    def fake_run_projection(connection: Any, *, tenant_id: str, corpus_id: str) -> SimpleNamespace:
        captured["conn"] = connection
        captured["tenant_id"] = tenant_id
        captured["corpus_id"] = corpus_id
        return SimpleNamespace(
            generation_id="gen-123",
            captures_processed=2,
            references_created=4,
            references_activated=4,
            references_active=4,
        )

    monkeypatch.setattr(cli, "run_phase_projection", fake_run_projection)

    rc = cli.main(["phase-projection", "run", "--tenant", "striatum", "--corpus", "striatum"])

    assert rc == 0
    assert captured == {
        "conn": fake_cli_connect,
        "tenant_id": "striatum",
        "corpus_id": "striatum",
    }
    captured_output = capsys.readouterr()
    assert "phase-projection: tenant=striatum corpus=striatum" in captured_output.out
    assert "captures_processed=2" in captured_output.out
    assert "references_created=4" in captured_output.out


def test_evidence_refresh_index_dispatches_to_worker(
    monkeypatch: pytest.MonkeyPatch,
    fake_cli_connect: Any,
    capsys: pytest.CaptureFixture[str],
) -> None:
    captured: dict[str, Any] = {}

    def fake_refresh_index(connection: Any, *, tenant_id: str, corpus_id: str) -> SimpleNamespace:
        captured["conn"] = connection
        captured["tenant_id"] = tenant_id
        captured["corpus_id"] = corpus_id
        return SimpleNamespace(
            tenant_id=tenant_id,
            corpus_id=corpus_id,
            evidence_items=2,
            evidence_refs=5,
        )

    monkeypatch.setattr(cli, "refresh_evidence_reference_index", fake_refresh_index)

    rc = cli.main(
        [
            "evidence",
            "refresh-index",
            "--tenant",
            "personal",
            "--corpus",
            "personal",
        ]
    )

    assert rc == 0
    assert captured == {
        "conn": fake_cli_connect,
        "tenant_id": "personal",
        "corpus_id": "personal",
    }
    captured_output = capsys.readouterr()
    assert "evidence index: tenant=personal corpus=personal" in captured_output.out
    assert "evidence_items=2" in captured_output.out
    assert "evidence_refs=5" in captured_output.out


def test_context_for_dispatches_to_context_service_as_markdown(
    monkeypatch: pytest.MonkeyPatch,
    fake_cli_connect: Any,
    capsys: pytest.CaptureFixture[str],
) -> None:
    captured: dict[str, Any] = {}

    class FakeContextResult:
        rendered_context = "## Relevant Beliefs\n- local context"

        def to_json(self) -> dict[str, Any]:
            return {"rendered_context": self.rendered_context}

    def fake_context_for(connection: Any, request: Any) -> FakeContextResult:
        captured["conn"] = connection
        captured["request"] = request
        return FakeContextResult()

    monkeypatch.setattr(cli, "context_for", fake_context_for)

    rc = cli.main(
        [
            "context-for",
            "--query",
            "project memory",
            "--tenant",
            "personal",
            "--corpus",
            "personal",
            "--word-budget",
            "42",
            "--privacy-tier-max",
            "1",
        ]
    )

    assert rc == 0
    assert captured["conn"] is fake_cli_connect
    request = captured["request"]
    assert request.query_text == "project memory"
    assert request.tenant_id == "personal"
    assert request.corpus_id == "personal"
    assert request.word_budget == 42
    assert request.privacy_tier_ceiling == 1
    assert "## Relevant Beliefs" in capsys.readouterr().out


def test_context_for_reads_query_file_and_prints_json(
    monkeypatch: pytest.MonkeyPatch,
    fake_cli_connect: Any,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    query_file = tmp_path / "query.txt"
    query_file.write_text("file query\n", encoding="utf-8")
    captured: dict[str, Any] = {}

    class FakeContextResult:
        rendered_context = "rendered"

        def to_json(self) -> dict[str, Any]:
            return {"status": "ok", "rendered_context": self.rendered_context}

    def fake_context_for(connection: Any, request: Any) -> FakeContextResult:
        captured["request"] = request
        return FakeContextResult()

    monkeypatch.setattr(cli, "context_for", fake_context_for)

    rc = cli.main(["context-for", "--query-file", str(query_file), "--format", "json"])

    assert rc == 0
    assert captured["request"].query_text == "file query"
    output = capsys.readouterr().out
    assert '"status": "ok"' in output
    assert '"rendered_context": "rendered"' in output


def test_context_for_rejects_missing_query_before_database_connection(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def fail_connect() -> None:
        raise AssertionError("context-for should fail before connect()")

    monkeypatch.setattr(cli, "connect", fail_connect)

    with pytest.raises(SystemExit) as excinfo:
        cli.main(["context-for"])

    assert excinfo.value.code == 2
    assert "requires --query or --query-file" in capsys.readouterr().err


def test_claim_grounding_entity_dispatches_local_broker(
    monkeypatch: pytest.MonkeyPatch,
    fake_cli_connect: Any,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    request_path = tmp_path / "claim-grounding-request.json"
    request_payload = _claim_grounding_request()
    request_path.write_text(json.dumps(request_payload), encoding="utf-8")
    captured: dict[str, Any] = {}

    class FakeGroundingResponse:
        def to_json(self) -> dict[str, Any]:
            return {
                "schema_version": "claim_grounding.response.v1",
                "request_id": request_payload["request_id"],
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
        connection: Any,
        request: dict[str, Any],
        *,
        limit: int,
    ) -> FakeGroundingResponse:
        captured["conn"] = connection
        captured["request"] = request
        captured["limit"] = limit
        return FakeGroundingResponse()

    monkeypatch.setattr(cli, "ground_claim_entity_locally", fake_ground_claim_entity_locally)

    rc = cli.main(
        [
            "claim-grounding",
            "entity",
            "--request-json",
            str(request_path),
            "--limit",
            "3",
        ]
    )

    assert rc == 0
    assert captured == {
        "conn": fake_cli_connect,
        "request": request_payload,
        "limit": 3,
    }
    output = capsys.readouterr().out
    assert '"schema_version": "claim_grounding.response.v1"' in output
    assert '"mode": "local_lookup"' in output
    assert '"network_fetch": "not_requested"' in output


def test_claim_grounding_grants_cli_records_lifecycle_rows(
    fake_connect: Any,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    request_path = tmp_path / "claim-grounding-network-request.json"
    request_path.write_text(json.dumps(_claim_grounding_network_request()), encoding="utf-8")

    assert (
        cli.main(
            [
                "claim-grounding",
                "grants",
                "draft",
                "--request-json",
                str(request_path),
            ]
        )
        == 0
    )
    draft_output = json.loads(capsys.readouterr().out)
    assert draft_output["status"] == "draft"
    assert draft_output["display"]["search_query"] == "OpenAI Codex"

    assert (
        cli.main(
            [
                "claim-grounding",
                "grants",
                "list",
                "--status",
                "draft",
            ]
        )
        == 0
    )
    list_output = json.loads(capsys.readouterr().out)
    assert list_output["grants"][0]["status"] == "draft"
    assert list_output["grants"][0]["search_query"] == "OpenAI Codex"
    assert list_output["grants"][0]["source_refs"] == [
        {
            "target_id": "22222222-2222-4222-8222-222222222222",
            "target_table": "messages",
        }
    ]

    for action, actor_flag, actor in [
        ("approve", "--granted-by", "operator"),
        ("deny", "--denied-by", "operator"),
        ("revoke", "--revoked-by", "operator"),
    ]:
        argv = [
            "claim-grounding",
            "grants",
            action,
            "--request-id",
            "11111111-1111-4111-8111-111111111111",
            "--grant-id",
            "grant-cli-001",
            actor_flag,
            actor,
        ]
        if action in {"deny", "revoke"}:
            argv.extend(["--reason", f"{action} test"])
        assert cli.main(argv) == 0
        output = json.loads(capsys.readouterr().out)
        assert output["action"] == action
        assert output["grant_id"] == "grant-cli-001"
        assert output["display"]["surface_form"] == "OpenAI Codex"


def test_entity_grounding_draft_dispatches_workflow(
    monkeypatch: pytest.MonkeyPatch,
    fake_cli_connect: Any,
    capsys: pytest.CaptureFixture[str],
) -> None:
    captured: dict[str, Any] = {}

    def fake_run_entity_grounding_draft(connection: Any, **kwargs: Any) -> dict[str, Any]:
        captured["conn"] = connection
        captured.update(kwargs)
        return {
            "workflow_version": "entity_grounding_batch.v1",
            "selected": 5,
            "local_hits": 1,
            "drafts_created": 3,
            "drafts_reused": 1,
            "skipped": [],
        }

    monkeypatch.setattr(cli, "run_entity_grounding_draft", fake_run_entity_grounding_draft)

    rc = cli.main(
        [
            "entity-grounding",
            "draft",
            "--tenant",
            "personal",
            "--corpus",
            "personal",
            "--limit",
            "5",
            "--entity-id",
            "33333333-3333-4333-8333-333333333333",
        ]
    )

    assert rc == 0
    assert captured == {
        "conn": fake_cli_connect,
        "tenant_id": "personal",
        "corpus_id": "personal",
        "limit": 5,
        "entity_id": "33333333-3333-4333-8333-333333333333",
    }
    output = json.loads(capsys.readouterr().out)
    assert output["workflow_version"] == "entity_grounding_batch.v1"
    assert output["drafts_created"] == 3


def test_entity_grounding_process_approved_dispatches_and_redacts_secrets(
    monkeypatch: pytest.MonkeyPatch,
    fake_cli_connect: Any,
    capsys: pytest.CaptureFixture[str],
) -> None:
    captured: dict[str, Any] = {}

    def fake_run_entity_grounding_process_approved(
        connection: Any,
        **kwargs: Any,
    ) -> dict[str, Any]:
        captured["conn"] = connection
        captured.update(kwargs)
        return {
            "workflow_version": "entity_grounding_materialization.v1",
            "processed": 1,
            "materialized_evidence": 2,
            "provider": {
                "name": "tavily",
                "api_key": "tavily-secret-value",
                "nested": {"authorization_token": "bearer-secret-value"},
            },
        }

    monkeypatch.setattr(
        cli,
        "run_entity_grounding_process_approved",
        fake_run_entity_grounding_process_approved,
    )

    rc = cli.main(
        [
            "entity-grounding",
            "process-approved",
            "--tenant",
            "personal",
            "--corpus",
            "personal",
            "--limit",
            "2",
            "--request-id",
            "11111111-1111-4111-8111-111111111111",
            "--grant-id",
            "grant-cli-001",
            "--target-adapter",
            "internet_search",
        ]
    )

    assert rc == 0
    assert captured == {
        "conn": fake_cli_connect,
        "tenant_id": "personal",
        "corpus_id": "personal",
        "limit": 2,
        "request_id": "11111111-1111-4111-8111-111111111111",
        "grant_id": "grant-cli-001",
        "target_adapter": "internet_search",
    }
    output_text = capsys.readouterr().out
    assert "tavily-secret-value" not in output_text
    assert "bearer-secret-value" not in output_text
    output = json.loads(output_text)
    assert output["provider"]["api_key"] == "[redacted]"
    assert output["provider"]["nested"]["authorization_token"] == "[redacted]"


def test_entity_grounding_process_approved_uses_broker_database_url(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    captured: dict[str, Any] = {}
    broker_conn = SimpleNamespace(commit=lambda: None)
    broker_url = "postgresql://engram_grounding_broker@localhost/engram"
    monkeypatch.setenv(cli.ENTITY_GROUNDING_BROKER_DATABASE_URL_ENV, broker_url)

    @contextmanager
    def fake_connect(*args: Any, **kwargs: Any) -> Iterator[Any]:
        captured["connect_args"] = args
        captured["connect_kwargs"] = kwargs
        yield broker_conn

    def fake_run_entity_grounding_process_approved(
        connection: Any,
        **kwargs: Any,
    ) -> dict[str, Any]:
        captured["conn"] = connection
        captured.update(kwargs)
        return {
            "workflow_version": "entity_grounding_materialization.v1",
            "processed": 0,
            "materialized_evidence": 0,
        }

    monkeypatch.setattr(cli, "connect", fake_connect)
    monkeypatch.setattr(
        cli,
        "run_entity_grounding_process_approved",
        fake_run_entity_grounding_process_approved,
    )

    rc = cli.main(["entity-grounding", "process-approved", "--limit", "1"])

    assert rc == 0
    assert captured["connect_args"] == ()
    assert captured["connect_kwargs"] == {"url": broker_url}
    assert captured["conn"] is broker_conn
    assert captured["limit"] == 1
    assert captured["tenant_id"] == "personal"
    assert captured["corpus_id"] == "personal"
    assert broker_url not in capsys.readouterr().out


def test_entity_grounding_broker_daemon_requires_broker_database_url(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.delenv(cli.ENTITY_GROUNDING_BROKER_DATABASE_URL_ENV, raising=False)

    rc = cli.main(["entity-grounding", "broker-daemon", "--max-iterations", "1"])

    captured = capsys.readouterr()
    assert rc == 2
    assert cli.ENTITY_GROUNDING_BROKER_DATABASE_URL_ENV in captured.err


def test_entity_grounding_broker_daemon_uses_broker_database_url(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    from engram import entity_grounding_daemon

    captured: dict[str, Any] = {}
    broker_conn = SimpleNamespace(commit=lambda: None)
    broker_url = "postgresql://engram_grounding_broker@localhost/engram"
    monkeypatch.setenv(cli.ENTITY_GROUNDING_BROKER_DATABASE_URL_ENV, broker_url)

    @contextmanager
    def fake_connect(*args: Any, **kwargs: Any) -> Iterator[Any]:
        captured["connect_args"] = args
        captured["connect_kwargs"] = kwargs
        yield broker_conn

    def fake_run_entity_grounding_broker_daemon(
        connect_factory: Any,
        **kwargs: Any,
    ) -> dict[str, object]:
        captured.update(kwargs)
        with connect_factory() as conn:
            captured["conn"] = conn
        return {
            "workflow_version": "entity_grounding_broker_daemon.v1",
            "iterations": 1,
            "processed_count": 0,
            "materialized_evidence_count": 0,
            "provider": {"api_key": "daemon-secret"},
        }

    monkeypatch.setattr(cli, "connect", fake_connect)
    monkeypatch.setattr(
        entity_grounding_daemon,
        "run_entity_grounding_broker_daemon",
        fake_run_entity_grounding_broker_daemon,
    )

    rc = cli.main(
        [
            "entity-grounding",
            "broker-daemon",
            "--tenant",
            "personal",
            "--corpus",
            "personal",
            "--limit",
            "2",
            "--interval",
            "0",
            "--target-adapter",
            "internet_search",
            "--max-iterations",
            "1",
        ]
    )

    assert rc == 0
    assert captured["connect_args"] == ()
    assert captured["connect_kwargs"] == {"url": broker_url}
    assert captured["conn"] is broker_conn
    assert captured["tenant_id"] == "personal"
    assert captured["corpus_id"] == "personal"
    assert captured["limit"] == 2
    assert captured["interval_seconds"] == 0.0
    assert captured["target_adapter"] == "internet_search"
    assert captured["max_iterations"] == 1
    output_text = capsys.readouterr().out
    assert broker_url not in output_text
    assert "daemon-secret" not in output_text
    output = json.loads(output_text)
    assert output["provider"]["api_key"] == "[redacted]"


def _patch_eval_context_file_runner(
    monkeypatch: pytest.MonkeyPatch,
    captured: dict[str, Any],
) -> None:
    def fake_run_context_eval_file(path: Path, *, compiler: Any) -> SimpleNamespace:
        captured["gold_set"] = path
        captured["compiler"] = compiler
        captured["compiled"] = compiler(
            cli.ContextCompileRequest(
                query_text="dataset discovery",
                privacy_ceiling=1,
                eval_item_id="ctx-discovery",
            )
        )
        return SimpleNamespace(
            item_count=1,
            summary={"required_fact_recall": 1.0, "citation_coverage": 1.0},
            to_json=lambda: {"summary": "json"},
            to_markdown=lambda: "# summary\n",
        )

    def fake_write_json_report(report: Any, path: Path) -> None:
        captured["json_report"] = report
        captured["json_path"] = path

    def fake_context_for(connection: Any, request: Any) -> Any:
        captured["conn"] = connection
        captured["request"] = request
        return SimpleNamespace(to_json=lambda: {"rendered_context": "context"})

    monkeypatch.setattr(cli, "run_context_eval_file", fake_run_context_eval_file)
    monkeypatch.setattr(cli, "write_json_report", fake_write_json_report)
    monkeypatch.setattr(cli, "context_for", fake_context_for)


def test_eval_context_runs_gold_set_and_writes_reports(
    monkeypatch: pytest.MonkeyPatch,
    fake_cli_connect: Any,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    captured: dict[str, Any] = {}
    gold_set = tmp_path / "gold.jsonl"
    output = tmp_path / "report.json"
    markdown_output = tmp_path / "report.md"

    def fake_run_context_eval_file(path: Path, *, compiler: Any) -> SimpleNamespace:
        captured["gold_set"] = path
        compiled = compiler(
            cli.ContextCompileRequest(
                query_text="project context",
                privacy_ceiling=5,
                eval_item_id="ctx-1",
            )
        )
        captured["compiled"] = compiled
        return SimpleNamespace(
            item_count=1,
            summary={"required_fact_recall": 0.5, "citation_coverage": 1.0},
            to_json=lambda: {"summary": "json"},
            to_markdown=lambda: "# summary\n",
        )

    def fake_write_json_report(report: Any, path: Path) -> None:
        captured["json_report"] = report
        captured["json_path"] = path

    def fake_write_markdown_summary(report: Any, path: Path) -> None:
        captured["markdown_report"] = report
        captured["markdown_path"] = path

    def fake_context_for(connection: Any, request: Any) -> Any:
        captured["conn"] = connection
        captured["request"] = request
        return SimpleNamespace(to_json=lambda: {"rendered_context": "context"})

    monkeypatch.setattr(cli, "run_context_eval_file", fake_run_context_eval_file)
    monkeypatch.setattr(cli, "write_json_report", fake_write_json_report)
    monkeypatch.setattr(cli, "write_markdown_summary", fake_write_markdown_summary)
    monkeypatch.setattr(cli, "context_for", fake_context_for)

    rc = cli.main(
        [
            "eval",
            "context",
            "--gold-set",
            str(gold_set),
            "--output",
            str(output),
            "--markdown-output",
            str(markdown_output),
            "--tenant",
            "personal",
            "--corpus",
            "personal",
            "--word-budget",
            "123",
            "--privacy-tier-max",
            "2",
        ]
    )

    assert rc == 0
    assert captured["conn"] is fake_cli_connect
    assert captured["gold_set"] == gold_set
    assert captured["json_path"] == output
    assert captured["markdown_path"] == markdown_output
    assert captured["compiled"] == {"rendered_context": "context"}
    request = captured["request"]
    assert request.query_text == "project context"
    assert request.tenant_id == "personal"
    assert request.corpus_id == "personal"
    assert request.word_budget == 123
    assert request.privacy_tier_ceiling == 2
    assert "context eval: items=1" in capsys.readouterr().out


def test_eval_context_uses_env_dataset_path_when_gold_set_is_absent(
    monkeypatch: pytest.MonkeyPatch,
    fake_cli_connect: Any,
    tmp_path: Path,
) -> None:
    captured: dict[str, Any] = {}
    dataset_path = tmp_path / "env-dataset"
    dataset_path.mkdir()
    output = tmp_path / "report.json"
    monkeypatch.setenv("ENGRAM_EVAL_DATASET_PATH", str(dataset_path))
    _patch_eval_context_file_runner(monkeypatch, captured)

    rc = cli.main(["eval", "context", "--output", str(output)])

    assert rc == 0
    assert captured["conn"] is fake_cli_connect
    assert captured["gold_set"] == dataset_path / "context_eval.gold.jsonl"
    assert captured["json_path"] == output
    assert captured["compiled"] == {"rendered_context": "context"}


def test_eval_context_dataset_path_overrides_env_dataset_path(
    monkeypatch: pytest.MonkeyPatch,
    fake_cli_connect: Any,
    tmp_path: Path,
) -> None:
    captured: dict[str, Any] = {}
    cli_dataset_path = tmp_path / "cli-dataset"
    env_dataset_path = tmp_path / "env-dataset"
    cli_dataset_path.mkdir()
    env_dataset_path.mkdir()
    output = tmp_path / "report.json"
    monkeypatch.setenv("ENGRAM_EVAL_DATASET_PATH", str(env_dataset_path))
    _patch_eval_context_file_runner(monkeypatch, captured)

    rc = cli.main(
        [
            "eval",
            "context",
            "--dataset-path",
            str(cli_dataset_path),
            "--output",
            str(output),
        ]
    )

    assert rc == 0
    assert captured["conn"] is fake_cli_connect
    assert captured["gold_set"] == cli_dataset_path / "context_eval.gold.jsonl"
    assert captured["json_path"] == output
    assert captured["compiled"] == {"rendered_context": "context"}


# ---------------------------------------------------------------------------
# segment
# ---------------------------------------------------------------------------


def test_segment_wires_batch_size_limit_and_source_id(
    monkeypatch: pytest.MonkeyPatch,
    fake_connect: Any,
) -> None:
    captured: dict[str, Any] = {}

    def fake_run_segment_batches(connection: Any, **kwargs: Any) -> SimpleNamespace:
        captured["conn"] = connection
        captured.update(kwargs)
        return _make_segment_result()

    monkeypatch.setattr(cli, "run_segment_batches", fake_run_segment_batches)
    monkeypatch.setattr(
        cli,
        "apply_reclassification_invalidations",
        lambda _conn: 0,
    )

    rc = cli.main(
        [
            "segment",
            "--batch-size",
            "7",
            "--limit",
            "21",
            "--source-id",
            "src-abc",
            "--retries",
            "4",
        ]
    )

    assert rc == 0
    assert captured["batch_size"] == 7
    assert captured["limit"] == 21
    assert captured["source_id"] == "src-abc"
    assert captured["retries"] == 4


def test_segment_returns_nonzero_when_failures_present(
    monkeypatch: pytest.MonkeyPatch,
    fake_connect: Any,
) -> None:
    monkeypatch.setattr(
        cli,
        "run_segment_batches",
        lambda _conn, **_kw: _make_segment_result(failed=2),
    )
    monkeypatch.setattr(cli, "apply_reclassification_invalidations", lambda _conn: 0)

    rc = cli.main(["segment"])
    assert rc == 1


# ---------------------------------------------------------------------------
# embed
# ---------------------------------------------------------------------------


def test_embed_wires_batch_size_limit_and_model_version(
    monkeypatch: pytest.MonkeyPatch,
    fake_connect: Any,
) -> None:
    captured: dict[str, Any] = {}

    def fake_run_embed_batches(connection: Any, **kwargs: Any) -> SimpleNamespace:
        captured["conn"] = connection
        captured.update(kwargs)
        return _make_embed_result()

    monkeypatch.setattr(cli, "run_embed_batches", fake_run_embed_batches)

    rc = cli.main(
        [
            "embed",
            "--batch-size",
            "50",
            "--limit",
            "200",
            "--model-version",
            "embed-vX",
        ]
    )

    assert rc == 0
    assert captured["batch_size"] == 50
    assert captured["limit"] == 200
    assert captured["model_version"] == "embed-vX"


# ---------------------------------------------------------------------------
# Phase 2 run / generic pipeline fail-closed behavior
# ---------------------------------------------------------------------------


def test_phase2_run_wires_distinct_segment_and_embed_batch_sizes(
    monkeypatch: pytest.MonkeyPatch,
    fake_cli_connect: Any,
) -> None:
    seg_kwargs: dict[str, Any] = {}
    embed_kwargs: dict[str, Any] = {}

    def fake_run_segment_batches(connection: Any, **kwargs: Any) -> SimpleNamespace:
        seg_kwargs.update(kwargs)
        return _make_segment_result()

    def fake_run_embed_batches(connection: Any, **kwargs: Any) -> SimpleNamespace:
        embed_kwargs.update(kwargs)
        return _make_embed_result()

    monkeypatch.setattr(cli, "run_segment_batches", fake_run_segment_batches)
    monkeypatch.setattr(cli, "run_embed_batches", fake_run_embed_batches)
    monkeypatch.setattr(cli, "apply_reclassification_invalidations", lambda _conn: 0)

    rc = cli.main(
        [
            "phase2",
            "run",
            "--segment-batch-size",
            "11",
            "--embed-batch-size",
            "33",
            "--limit",
            "5",
            "--source-id",
            "src-xyz",
            "--model-version",
            "embed-Y",
            "--segment-retries",
            "2",
        ]
    )

    assert rc == 0
    assert seg_kwargs["batch_size"] == 11
    assert seg_kwargs["limit"] == 5
    assert seg_kwargs["source_id"] == "src-xyz"
    assert seg_kwargs["retries"] == 2
    assert embed_kwargs["batch_size"] == 33
    assert embed_kwargs["limit"] == 5
    assert embed_kwargs["model_version"] == "embed-Y"


def test_phase2_run_returns_nonzero_when_embed_fails(
    monkeypatch: pytest.MonkeyPatch,
    fake_cli_connect: Any,
) -> None:
    monkeypatch.setattr(
        cli,
        "run_segment_batches",
        lambda _conn, **_kw: _make_segment_result(),
    )
    monkeypatch.setattr(
        cli,
        "run_embed_batches",
        lambda _conn, **_kw: _make_embed_result(failed=3),
    )
    monkeypatch.setattr(cli, "apply_reclassification_invalidations", lambda _conn: 0)

    rc = cli.main(["phase2", "run"])
    assert rc == 1


def test_pipeline_fails_closed_before_database_connection(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def fail_connect() -> None:
        raise AssertionError("pipeline should fail before connect()")

    monkeypatch.setattr(cli, "connect", fail_connect)

    rc = cli.main(["pipeline"])

    assert rc == 2
    captured = capsys.readouterr()
    assert "ambiguous command: pipeline" in captured.err
    assert "engram phase2 run" in captured.err
    assert "engram phase3 run" in captured.err
    assert "engram phase4 smoke" in captured.err


def test_pipeline_help_points_to_phase_scoped_commands(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as excinfo:
        cli.main(["pipeline", "--help"])

    assert excinfo.value.code == 0
    captured = capsys.readouterr()
    assert "ambiguous command: pipeline" in captured.out
    assert "engram phase2 run" in captured.out
    assert "engram phase3 run" in captured.out
    assert "engram phase4 smoke" in captured.out
    assert "--limit" not in captured.out


# ---------------------------------------------------------------------------
# extract / consolidate (Phase 3 dispatch surface)
# ---------------------------------------------------------------------------


def test_extract_wires_batch_size_and_limit(
    monkeypatch: pytest.MonkeyPatch,
    fake_connect: Any,
) -> None:
    captured: dict[str, Any] = {}

    def fake_run_extract_batches(connection: Any, **kwargs: Any) -> SimpleNamespace:
        captured.update(kwargs)
        return SimpleNamespace(processed=1, created=2, skipped=0, failed=0)

    monkeypatch.setattr(cli, "run_extract_batches", fake_run_extract_batches)
    monkeypatch.setattr(cli, "apply_phase3_reclassification_invalidations", lambda _conn: None)

    rc = cli.main(
        [
            "extract",
            "--batch-size",
            "9",
            "--limit",
            "18",
            "--prompt-version",
            "ev-test",
            "--concurrency",
            "3",
        ]
    )

    assert rc == 0
    assert captured["batch_size"] == 9
    assert captured["limit"] == 18
    assert captured["prompt_version"] == "ev-test"
    assert captured["concurrency"] == 3


def test_consolidate_wires_batch_size_and_limit(
    monkeypatch: pytest.MonkeyPatch,
    fake_connect: Any,
) -> None:
    captured: dict[str, Any] = {}

    def fake_run_consolidate_batches(connection: Any, **kwargs: Any) -> SimpleNamespace:
        captured.update(kwargs)
        return SimpleNamespace(processed=1, created=1, superseded=0, contradictions=0)

    monkeypatch.setattr(cli, "run_consolidate_batches", fake_run_consolidate_batches)
    monkeypatch.setattr(cli, "apply_phase3_reclassification_invalidations", lambda _conn: None)

    rc = cli.main(
        [
            "consolidate",
            "--batch-size",
            "13",
            "--limit",
            "26",
            "--prompt-version",
            "cv-test",
        ]
    )

    assert rc == 0
    assert captured["batch_size"] == 13
    assert captured["limit"] == 26
    assert captured["prompt_version"] == "cv-test"


def test_legacy_consolidate_command_prints_replacement_warning(
    monkeypatch: pytest.MonkeyPatch,
    fake_cli_connect: Any,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        cli,
        "run_consolidate_batches",
        lambda _conn, **_kw: SimpleNamespace(
            processed=1,
            created=1,
            superseded=0,
            contradictions=0,
        ),
    )
    monkeypatch.setattr(cli, "apply_phase3_reclassification_invalidations", lambda _conn: None)

    rc = cli.main(["consolidate"])

    assert rc == 0
    captured = capsys.readouterr()
    assert "warning: `engram consolidate` is deprecated" in captured.err
    assert "engram phase3 consolidate" in captured.err


def test_phase1_ingest_chatgpt_dispatches_to_current_ingest_path(
    monkeypatch: pytest.MonkeyPatch,
    fake_cli_connect: Any,
    tmp_path: Path,
) -> None:
    captured: dict[str, Any] = {}

    def fake_ingest(connection: Any, path: Path) -> SimpleNamespace:
        captured["conn"] = connection
        captured["path"] = path
        return _make_ingest_result()

    monkeypatch.setattr(cli, "ingest_chatgpt_export", fake_ingest)

    rc = cli.main(["phase1", "ingest-chatgpt", str(tmp_path)])

    assert rc == 0
    assert captured["conn"] is fake_cli_connect
    assert captured["path"] == tmp_path


def test_phase3_run_accepts_limit_without_claiming_phase2(
    monkeypatch: pytest.MonkeyPatch,
    fake_cli_connect: Any,
) -> None:
    captured: dict[str, Any] = {}

    monkeypatch.setattr(cli, "phase3_schema_preflight", lambda _conn: None)
    monkeypatch.setattr(
        cli,
        "apply_phase3_reclassification_invalidations",
        lambda _conn: None,
    )
    monkeypatch.setattr(
        cli,
        "active_beliefs_with_other_consolidator_version",
        lambda _conn: [],
    )

    def fake_fetch_phase3_conversation_batch(connection: Any, limit: int | None) -> list[str]:
        captured["conn"] = connection
        captured["limit"] = limit
        return []

    monkeypatch.setattr(
        cli,
        "fetch_phase3_conversation_batch",
        fake_fetch_phase3_conversation_batch,
    )

    rc = cli.main(["phase3", "run", "--limit", "7"])

    assert rc == 0
    assert captured["conn"] is fake_cli_connect
    assert captured["limit"] == 7


def test_phase4_smoke_dispatches_to_current_smoke_path(
    monkeypatch: pytest.MonkeyPatch,
    fake_cli_connect: Any,
) -> None:
    captured: dict[str, Any] = {}

    def fake_run_phase4_smoke(connection: Any, *, limit: int) -> SimpleNamespace:
        captured["conn"] = connection
        captured["limit"] = limit
        return SimpleNamespace(
            current_beliefs=1,
            review_queue_items=2,
            beliefs_processed=3,
            entities_created=4,
            entities_reused=5,
            edges_created=6,
            edges_reused=7,
            neighborhood_rows=8,
        )

    monkeypatch.setattr(cli, "run_phase4_smoke", fake_run_phase4_smoke)

    rc = cli.main(["phase4", "smoke", "--limit", "9"])

    assert rc == 0
    assert captured["conn"] is fake_cli_connect
    assert captured["limit"] == 9


def test_phase4_run_is_not_a_command() -> None:
    with pytest.raises(SystemExit) as excinfo:
        cli.main(["phase4", "run"])

    assert excinfo.value.code != 0


def test_phase3_re_extract_dispatches_to_current_re_extract_path(
    monkeypatch: pytest.MonkeyPatch,
    fake_cli_connect: Any,
) -> None:
    captured: dict[str, Any] = {}

    def fake_re_extract(connection: Any, target_version: str, **kwargs: Any) -> Any:
        captured["conn"] = connection
        captured["target_version"] = target_version
        captured.update(kwargs)
        return SimpleNamespace(
            target_version=target_version,
            plan=SimpleNamespace(
                current_version="extractor.v1.test",
                segment_count=0,
                prior_version_counts={},
                source_kind_counts={},
            ),
            processed=0,
            created=0,
            skipped=0,
            failed=0,
            dry_run=True,
            coverage_gaps=[],
            diff_samples=[],
        )

    monkeypatch.setattr(cli, "re_extract", fake_re_extract)
    monkeypatch.setattr(
        cli,
        "apply_phase3_reclassification_invalidations",
        lambda _conn: 0,
    )

    rc = cli.main(
        [
            "phase3",
            "re-extract",
            "--version",
            "extractor.v9.d999.phase-scoped",
            "--batch-size",
            "7",
            "--limit",
            "11",
            "--source-id",
            "src-abc",
            "--diff-sample",
            "3",
            "--dry-run",
        ]
    )

    assert rc == 0
    assert captured["conn"] is fake_cli_connect
    assert captured["target_version"] == "extractor.v9.d999.phase-scoped"
    assert captured["batch_size"] == 7
    assert captured["limit"] == 11
    assert captured["source_id"] == "src-abc"
    assert captured["diff_sample"] == 3
    assert captured["dry_run"] is True


def test_legacy_segment_command_prints_replacement_warning(
    monkeypatch: pytest.MonkeyPatch,
    fake_cli_connect: Any,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        cli,
        "run_segment_batches",
        lambda _conn, **_kw: _make_segment_result(created=0),
    )
    monkeypatch.setattr(
        cli,
        "apply_reclassification_invalidations",
        lambda _conn: 0,
    )

    rc = cli.main(["segment"])

    assert rc == 0
    captured = capsys.readouterr()
    assert "warning: `engram segment` is deprecated" in captured.err
    assert "engram phase2 segment" in captured.err


def test_makefile_has_phase_scoped_targets_and_pipeline_fail_closed() -> None:
    makefile = Path("Makefile").read_text()

    for target in (
        "phase1-ingest-chatgpt:",
        "phase2-run:",
        "phase2-run-docker:",
        "phase2-run-isolated:",
        "phase3-run:",
        "phase3-run-docker:",
        "phase3-re-extract:",
        "phase4-smoke:",
        "e2e-entity-grounding:",
    ):
        assert target in makefile

    assert "ambiguous target: pipeline" in makefile
    assert "ambiguous target: pipeline-docker" in makefile
    assert "ambiguous target: pipeline-isolated" in makefile
    assert "engram.cli phase2 run $(if $(LIMIT),--limit $(LIMIT),)" in makefile
    assert "engram.cli phase3 run $(if $(LIMIT),--limit $(LIMIT),)" in makefile
    assert "$(wildcard tests/test_entity_grounding_workflow.py)" in makefile
    assert "$(wildcard tests/test_entity_grounding_materialization.py)" in makefile
