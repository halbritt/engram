from __future__ import annotations

import json
import subprocess
import sys
from collections.abc import Sequence

import pytest

from engram import cli
from engram.no_egress import (
    NO_EGRESS_UNSUPPORTED_RETURN_CODE,
    Mechanism,
    ProbeResult,
    RunResult,
    SupportResult,
    build_wrapped_command,
    detect_support,
    probe_enforcement,
    run_under_no_egress,
)


def _which_unshare(name: str) -> str | None:
    if name == "unshare":
        return "/usr/bin/unshare"
    return None


def _completed_probe(
    cmd: Sequence[str],
    *,
    child: dict[str, object],
    returncode: int = 0,
    stderr: str = "",
) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(
        args=list(cmd),
        returncode=returncode,
        stdout=json.dumps(child),
        stderr=stderr,
    )


def _unsupported_probe() -> ProbeResult:
    support = SupportResult(
        status="unsupported",
        platform="Darwin",
        mechanisms=(),
        reason="no-egress OS enforcement is currently implemented for Linux only",
    )
    return ProbeResult(
        status="unsupported",
        platform="Darwin",
        mechanism=None,
        reason=support.reason,
        support=support,
        attempts=(),
    )


def test_detect_support_is_honest_on_non_linux() -> None:
    result = detect_support(which=lambda _name: None, system_name="Darwin")

    assert result.status == "unsupported"
    assert result.mechanisms == ()
    assert "Linux only" in (result.reason or "")


def test_build_wrapped_command_uses_unshare_network_namespace() -> None:
    mechanism = Mechanism("unshare-netns", "/usr/bin/unshare")

    command = build_wrapped_command(["python", "-c", "print('ok')"], mechanism)

    assert command[:6] == [
        "/usr/bin/unshare",
        "--user",
        "--map-root-user",
        "--net",
        "--fork",
        "--kill-child",
    ]
    assert command[6:10] == [sys.executable, "-m", "engram.no_egress", "_child"]
    assert command[10:] == ["exec", "--", "python", "-c", "print('ok')"]


def test_probe_enforcement_returns_machine_readable_enforced_shape() -> None:
    recorded: list[list[str]] = []

    def fake_runner(cmd: Sequence[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        recorded.append(list(cmd))
        return _completed_probe(
            cmd,
            child={
                "status": "egress_enforced",
                "namespace_isolated": True,
                "loopback_ok": True,
                "non_loopback_blocked": True,
                "non_loopback_errno": 101,
                "parent_netns": "net:[1]",
                "child_netns": "net:[2]",
                "setup_error": None,
            },
        )

    result = probe_enforcement(
        which=_which_unshare,
        runner=fake_runner,
        system_name="Linux",
    )
    payload = result.to_dict()

    assert result.status == "egress_enforced"
    assert result.mechanism == "unshare-netns"
    assert payload["status"] == "egress_enforced"
    assert payload["loopback_ok"] is True
    assert payload["non_loopback_blocked"] is True
    assert payload["namespace_isolated"] is True
    assert recorded and recorded[0][0] == "/usr/bin/unshare"


def test_probe_enforcement_falls_back_to_unsupported_when_probe_does_not_prove_it() -> None:
    def fake_runner(cmd: Sequence[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        return _completed_probe(
            cmd,
            child={
                "status": "unsupported",
                "namespace_isolated": True,
                "loopback_ok": True,
                "non_loopback_blocked": False,
                "non_loopback_error": "timed out",
                "setup_error": None,
            },
        )

    result = probe_enforcement(
        which=_which_unshare,
        runner=fake_runner,
        system_name="Linux",
    )

    assert result.status == "unsupported"
    assert result.mechanism is None
    assert "non-loopback socket" in (result.reason or "")
    assert result.attempts[0].status == "unsupported"


def test_run_under_no_egress_returns_unsupported_without_running_command() -> None:
    ran: list[list[str]] = []

    def fake_run_runner(cmd: Sequence[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        ran.append(list(cmd))
        return subprocess.CompletedProcess(args=list(cmd), returncode=0)

    result = run_under_no_egress(
        ["python", "-V"],
        which=lambda _name: None,
        run_runner=fake_run_runner,
        system_name="Linux",
    )

    assert result.status == "unsupported"
    assert result.returncode == NO_EGRESS_UNSUPPORTED_RETURN_CODE
    assert ran == []


def test_cli_no_egress_probe_prints_json(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(cli, "probe_enforcement", _unsupported_probe)

    rc = cli.main(["no-egress", "probe"])
    payload = json.loads(capsys.readouterr().out)

    assert rc == 1
    assert payload["status"] == "unsupported"
    assert payload["mechanism"] is None


def test_cli_no_egress_run_strips_separator_and_returns_child_status(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: list[str] = []

    def fake_run(command: Sequence[str]) -> RunResult:
        captured.extend(command)
        return RunResult(
            status="egress_enforced",
            returncode=7,
            mechanism="unshare-netns",
            reason=None,
            probe=_unsupported_probe(),
        )

    monkeypatch.setattr(cli, "run_under_no_egress", fake_run)

    rc = cli.main(["no-egress", "run", "--", "python", "-V"])

    assert rc == 7
    assert captured == ["python", "-V"]
