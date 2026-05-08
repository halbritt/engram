"""Tests for the RFC 0021 ``engram phase3 interview`` CLI surface.

Mirrors the dispatch-style tests in ``tests/test_cli.py``: synthetic argv
plus monkeypatch on the driver functions in ``engram.cli``. No live DB
required for the help/dispatch checks.
"""

from __future__ import annotations

from contextlib import contextmanager
from collections.abc import Iterator
from types import SimpleNamespace
from typing import Any

import pytest

from engram import cli


@pytest.fixture()
def fake_cli_connect(monkeypatch: pytest.MonkeyPatch) -> Any:
    """Stub ``cli.connect`` so dispatch tests need no live DB."""

    conn = SimpleNamespace(commit=lambda: None)

    @contextmanager
    def _fake_connect(*args: Any, **kwargs: Any) -> Iterator[Any]:
        yield conn

    monkeypatch.setattr(cli, "connect", _fake_connect)
    return conn


def test_phase3_interview_help_exits_zero(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as excinfo:
        cli.main(["phase3", "interview", "--help"])
    assert excinfo.value.code == 0
    captured = capsys.readouterr()
    text = captured.out + captured.err
    for sub in (
        "start",
        "resume",
        "history",
        "export",
        "list-sessions",
        "coverage",
        "enable-active-learning",
    ):
        assert sub in text


def test_bare_engram_interview_is_rejected(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as excinfo:
        cli.main(["interview", "--help"])
    # argparse uses exit code 2 for parse errors.
    assert excinfo.value.code != 0


def test_phase3_interview_export_default_privacy_tier_max_is_one(
    monkeypatch: pytest.MonkeyPatch,
    fake_cli_connect: Any,
) -> None:
    captured: dict[str, Any] = {}

    def fake_export(args: Any) -> int:
        captured["args"] = args
        return 0

    monkeypatch.setattr(cli, "run_phase3_interview_export", fake_export)

    rc = cli.main(["phase3", "interview", "export"])
    assert rc == 0
    args = captured["args"]
    assert args.privacy_tier_max == 1
    assert args.format == "jsonl"
    assert args.output is None


def test_phase3_interview_export_explicit_tier_max_passthrough(
    monkeypatch: pytest.MonkeyPatch,
    fake_cli_connect: Any,
) -> None:
    captured: dict[str, Any] = {}

    def fake_export(args: Any) -> int:
        captured["tier_max"] = args.privacy_tier_max
        return 0

    monkeypatch.setattr(cli, "run_phase3_interview_export", fake_export)
    rc = cli.main(["phase3", "interview", "export", "--privacy-tier-max", "3"])
    assert rc == 0
    assert captured["tier_max"] == 3


def test_phase3_interview_start_dispatches_to_start_driver(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}

    def fake_start(args: Any) -> int:
        captured["args"] = args
        return 0

    monkeypatch.setattr(cli, "run_phase3_interview_start", fake_start)
    rc = cli.main(["phase3", "interview", "start", "--n", "3", "--seed", "42"])
    assert rc == 0
    args = captured["args"]
    assert args.n == 3
    assert args.seed == 42
    assert args.include_superseded is False
    assert args.ignore_cooldown is False


def test_phase3_interview_start_passes_include_superseded_and_ignore_cooldown(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}

    def fake_start(args: Any) -> int:
        captured["args"] = args
        return 0

    monkeypatch.setattr(cli, "run_phase3_interview_start", fake_start)
    rc = cli.main(
        [
            "phase3",
            "interview",
            "start",
            "--include-superseded",
            "--ignore-cooldown",
        ]
    )
    assert rc == 0
    args = captured["args"]
    assert args.include_superseded is True
    assert args.ignore_cooldown is True


def test_phase3_interview_resume_dispatches_with_session_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}

    def fake_resume(args: Any) -> int:
        captured["session_id"] = args.session_id
        return 0

    monkeypatch.setattr(cli, "run_phase3_interview_resume", fake_resume)
    rc = cli.main(["phase3", "interview", "resume", "--session-id", "abc"])
    assert rc == 0
    assert captured["session_id"] == "abc"


def test_phase3_interview_history_dispatches_with_target(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}

    def fake_history(args: Any) -> int:
        captured["target"] = args.target
        return 0

    monkeypatch.setattr(cli, "run_phase3_interview_history", fake_history)
    rc = cli.main(["phase3", "interview", "history", "--target", "deadbeef"])
    assert rc == 0
    assert captured["target"] == "deadbeef"


def test_phase3_interview_list_sessions_dispatches_with_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}

    def fake_list(args: Any) -> int:
        captured["state"] = args.state
        return 0

    monkeypatch.setattr(cli, "run_phase3_interview_list_sessions", fake_list)
    rc = cli.main(["phase3", "interview", "list-sessions", "--state", "open"])
    assert rc == 0
    assert captured["state"] == "open"


def test_phase3_interview_coverage_requires_strata(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as excinfo:
        cli.main(["phase3", "interview", "coverage"])
    assert excinfo.value.code != 0


def test_phase3_interview_coverage_dispatches_with_strata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}

    def fake_coverage(args: Any) -> int:
        captured["strata"] = args.strata
        return 0

    monkeypatch.setattr(cli, "run_phase3_interview_coverage", fake_coverage)
    rc = cli.main(["phase3", "interview", "coverage", "--strata", "stability_class"])
    assert rc == 0
    assert captured["strata"] == "stability_class"


def test_phase3_interview_enable_active_learning_requires_signal_version(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as excinfo:
        cli.main(["phase3", "interview", "enable-active-learning"])
    assert excinfo.value.code != 0


def test_phase3_interview_enable_active_learning_dispatches(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}

    def fake_active(args: Any) -> int:
        captured["signal_version"] = args.signal_version
        return 0

    monkeypatch.setattr(cli, "run_phase3_interview_enable_active_learning", fake_active)
    rc = cli.main(
        [
            "phase3",
            "interview",
            "enable-active-learning",
            "--signal-version",
            "rfc0018.reviewer.v1",
        ]
    )
    assert rc == 0
    assert captured["signal_version"] == "rfc0018.reviewer.v1"
