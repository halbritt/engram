"""Tests for the RFC 0021 ``engram phase3 interview`` CLI surface.

Mirrors the dispatch-style tests in ``tests/test_cli.py``: synthetic argv
plus monkeypatch on the driver functions in ``engram.cli``. No live DB
required for the help/dispatch checks.
"""

from __future__ import annotations

import uuid
from contextlib import contextmanager
from collections.abc import Iterator
from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Any

import pytest

from engram import cli
from engram.interview.sampler import SampledTarget


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


# ---------------------------------------------------------------------------
# RFC 0027 / Spec 0027: gold_label_session_targets materialization on start
# ---------------------------------------------------------------------------


def _build_sampled_target(
    *,
    target_kind: str,
    target_id: str,
    snapshot_id: str,
    stability_class: str = "identity",
    conf_band: str = "0.6-0.8",
    recency_band: str = "<30d",
    belief_status: str | None = None,
) -> SampledTarget:
    if target_kind == "claim":
        ext_prompt: str | None = "ext-prompt-v1"
        ext_model: str | None = "ext-model-v1"
        cons_prompt: str | None = None
        cons_model: str | None = None
    else:
        ext_prompt = None
        ext_model = None
        cons_prompt = "cons-prompt-v1"
        cons_model = "cons-model-v1"
    return SampledTarget(
        target_kind=target_kind,
        target_id=target_id,
        stability_class=stability_class,
        confidence=0.7,
        observed_at=datetime(2024, 6, 1, 12, 0, tzinfo=timezone.utc),
        conf_band=conf_band,
        recency_band=recency_band,
        belief_status=belief_status,
        candidate_pool_snapshot_id=snapshot_id,
        active_learning_signal_version=None,
        extraction_prompt_version=ext_prompt,
        extraction_model_version=ext_model,
        consolidation_prompt_version=cons_prompt,
        consolidation_model_version=cons_model,
        request_profile_version="profile-v1",
    )


def test_phase3_interview_start_writes_session_targets(
    monkeypatch: pytest.MonkeyPatch,
    conn: Any,
) -> None:
    """Spec 0027 Migration 011: ``run_phase3_interview_start`` writes one
    ``gold_label_session_targets`` row per sampled target before returning,
    even on the non-interactive path."""

    @contextmanager
    def _fake_connect(*args: Any, **kwargs: Any) -> Iterator[Any]:
        yield conn

    monkeypatch.setattr(cli, "connect", _fake_connect)

    snapshot_id = str(uuid.uuid4())
    sampled = [
        _build_sampled_target(
            target_kind="claim",
            target_id=str(uuid.uuid4()),
            snapshot_id=snapshot_id,
            stability_class="identity",
            conf_band="0.6-0.8",
            recency_band="<30d",
        ),
        _build_sampled_target(
            target_kind="belief",
            target_id=str(uuid.uuid4()),
            snapshot_id=snapshot_id,
            stability_class="preference",
            conf_band="0.4-0.6",
            recency_band="<90d",
            belief_status="candidate",
        ),
        _build_sampled_target(
            target_kind="claim",
            target_id=str(uuid.uuid4()),
            snapshot_id=snapshot_id,
            stability_class="task",
            conf_band="0.0-0.2",
            recency_band="<7d",
        ),
    ]

    class _StubSampler:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            pass

        def sample(self, n: int) -> list[SampledTarget]:
            return list(sampled[:n])

    monkeypatch.setattr(cli, "GoldLabelSampler", _StubSampler)

    args = SimpleNamespace(
        n=3,
        seed=99,
        include_superseded=False,
        ignore_cooldown=False,
        non_interactive=True,
    )
    rc = cli.run_phase3_interview_start(args)
    assert rc == 0

    rows = conn.execute(
        """
        SELECT
            idx,
            target_kind,
            target_id::text,
            candidate_pool_snapshot_id::text,
            extraction_prompt_version,
            extraction_model_version,
            consolidation_prompt_version,
            consolidation_model_version,
            request_profile_version,
            stability_class,
            conf_band,
            recency_band,
            belief_status
        FROM gold_label_session_targets
        ORDER BY idx
        """
    ).fetchall()
    assert len(rows) == 3
    assert [row[0] for row in rows] == [0, 1, 2]
    # First row mirrors the claim version triple.
    first = rows[0]
    assert first[1] == "claim"
    assert first[2] == sampled[0].target_id
    assert first[3] == snapshot_id
    assert first[4] == "ext-prompt-v1"
    assert first[5] == "ext-model-v1"
    assert first[6] is None
    assert first[7] is None
    assert first[8] == "profile-v1"
    assert first[9] == "identity"
    assert first[10] == "0.6-0.8"
    assert first[11] == "<30d"
    assert first[12] is None
    # Second row is a belief: extraction columns must be NULL,
    # consolidation columns populated, belief_status preserved.
    belief_row = rows[1]
    assert belief_row[1] == "belief"
    assert belief_row[4] is None
    assert belief_row[5] is None
    assert belief_row[6] == "cons-prompt-v1"
    assert belief_row[7] == "cons-model-v1"
    assert belief_row[12] == "candidate"


# ---------------------------------------------------------------------------
# RFC 0027 / Spec 0027: ``engram phase3 interview serve`` subparser
# ---------------------------------------------------------------------------


def test_phase3_interview_serve_subparser_registered(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Spec 0027 § CLI integration: ``serve`` shows up under ``phase3 interview``."""

    with pytest.raises(SystemExit) as excinfo:
        cli.main(["phase3", "interview", "--help"])
    assert excinfo.value.code == 0
    captured = capsys.readouterr()
    assert "serve" in (captured.out + captured.err)


def test_phase3_interview_serve_default_host_port(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """argparse defaults match the spec: 127.0.0.1 / 8765."""

    captured: dict[str, Any] = {}

    def fake_serve(args: Any) -> int:
        captured["host"] = args.host
        captured["port"] = args.port
        return 0

    monkeypatch.setattr(cli, "run_phase3_interview_serve", fake_serve)
    rc = cli.main(["phase3", "interview", "serve"])
    assert rc == 0
    assert captured["host"] == "127.0.0.1"
    assert captured["port"] == 8765


def test_phase3_interview_serve_refuses_non_loopback(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Spec 0027 § Privacy and security: non-loopback host exits 8 before
    any FastAPI/Uvicorn import runs."""

    with pytest.raises(SystemExit) as excinfo:
        cli.main(["phase3", "interview", "serve", "--host", "0.0.0.0"])
    assert excinfo.value.code == 8
    err = capsys.readouterr().err
    assert "loopback" in err
    assert "0.0.0.0" in err


def test_phase3_interview_serve_pip_install_hint_when_imports_fail(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """When the optional ``engram[serve]`` deps are missing, the driver
    must exit 2 with a ``pip install engram[serve]`` hint rather than
    crashing with an ImportError."""

    import builtins

    real_import = builtins.__import__

    def fake_import(name: str, *args: Any, **kwargs: Any) -> Any:
        if name == "engram.interview.web" or name.startswith("engram.interview.web."):
            raise ImportError("No module named 'engram.interview.web' (test stub)")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    args = SimpleNamespace(host="127.0.0.1", port=8765)
    with pytest.raises(SystemExit) as excinfo:
        cli.run_phase3_interview_serve(args)
    assert excinfo.value.code == 2
    err = capsys.readouterr().err
    assert "pip install engram[serve]" in err
