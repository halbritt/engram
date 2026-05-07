"""Tests for ``engram.cli`` argument parsing and dispatch wiring.

Covers RFC 0015 §1: the CLI module previously had zero test coverage. These
tests drive ``cli.main()`` directly with synthetic argv (rather than spawning
a subprocess) and use ``monkeypatch`` to swap out the heavy worker functions
that ``main`` dispatches to. The intent is to verify *dispatch* — argument
parsing, exit codes, and that flags wire through to the underlying calls —
not the worker behavior, which is exercised in the phase-specific test files.
"""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Iterator

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


def _make_ingest_result() -> SimpleNamespace:
    return SimpleNamespace(
        source_id="src-123",
        conversations_inserted=1,
        conversations_seen=1,
        messages_inserted=2,
        messages_seen=2,
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
    monkeypatch.setattr(
        cli, "apply_reclassification_invalidations", lambda _conn: 0
    )

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
# pipeline
# ---------------------------------------------------------------------------


def test_pipeline_wires_distinct_segment_and_embed_batch_sizes(
    monkeypatch: pytest.MonkeyPatch,
    fake_connect: Any,
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
    monkeypatch.setattr(
        cli, "apply_reclassification_invalidations", lambda _conn: 0
    )

    rc = cli.main(
        [
            "pipeline",
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


def test_pipeline_returns_nonzero_when_embed_fails(
    monkeypatch: pytest.MonkeyPatch,
    fake_connect: Any,
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
    monkeypatch.setattr(
        cli, "apply_reclassification_invalidations", lambda _conn: 0
    )

    rc = cli.main(["pipeline"])
    assert rc == 1


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
    monkeypatch.setattr(
        cli, "apply_phase3_reclassification_invalidations", lambda _conn: None
    )

    rc = cli.main(
        [
            "extract",
            "--batch-size",
            "9",
            "--limit",
            "18",
            "--prompt-version",
            "ev-test",
        ]
    )

    assert rc == 0
    assert captured["batch_size"] == 9
    assert captured["limit"] == 18
    assert captured["prompt_version"] == "ev-test"


def test_consolidate_wires_batch_size_and_limit(
    monkeypatch: pytest.MonkeyPatch,
    fake_connect: Any,
) -> None:
    captured: dict[str, Any] = {}

    def fake_run_consolidate_batches(
        connection: Any, **kwargs: Any
    ) -> SimpleNamespace:
        captured.update(kwargs)
        return SimpleNamespace(
            processed=1, created=1, superseded=0, contradictions=0
        )

    monkeypatch.setattr(
        cli, "run_consolidate_batches", fake_run_consolidate_batches
    )
    monkeypatch.setattr(
        cli, "apply_phase3_reclassification_invalidations", lambda _conn: None
    )

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
