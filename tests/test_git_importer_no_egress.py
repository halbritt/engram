"""No-egress tests for the RFC 0050 Layer 1 git importer.

These tests pin the importer to its closed git verb allowlist and prove
that no socket is created during a full import.
"""

from __future__ import annotations

import socket
import subprocess
from pathlib import Path

import psycopg
import pytest

from engram.git_import import (
    GIT_VERB_ALLOWLIST,
    GitSubprocessError,
    import_git_repo,
)
from tests.test_git_importer import make_fixture_repo


def test_no_socket_during_import(
    monkeypatch: pytest.MonkeyPatch, conn: psycopg.Connection, tmp_path: Path
) -> None:
    repo = make_fixture_repo(tmp_path)
    seen: list[tuple[object, ...]] = []
    real_socket = socket.socket

    class TrackingSocket(real_socket):
        def __init__(self, *args, **kwargs):  # type: ignore[no-untyped-def]
            seen.append(args)
            super().__init__(*args, **kwargs)

    monkeypatch.setattr(socket, "socket", TrackingSocket)
    import_git_repo(conn, repo)
    # The DB connection in conftest is already open before the monkeypatch.
    # If the importer opens a new socket, the test fails.
    assert seen == [], f"unexpected sockets created during import: {seen}"


def test_subprocess_args_never_include_network_verbs(
    monkeypatch: pytest.MonkeyPatch, conn: psycopg.Connection, tmp_path: Path
) -> None:
    repo = make_fixture_repo(tmp_path)
    recorded: list[str] = []
    real_run = subprocess.run

    def recording_run(cmd, *args, **kwargs):  # type: ignore[no-untyped-def]
        if isinstance(cmd, list) and cmd and cmd[0] == "git":
            recorded.append(cmd[1] if len(cmd) > 1 else "")
        return real_run(cmd, *args, **kwargs)

    monkeypatch.setattr("engram.git_import.subprocess.run", recording_run)
    import_git_repo(conn, repo)
    assert recorded
    forbidden = {"clone", "fetch", "pull", "push", "ls-remote", "remote", "submodule", "archive"}
    assert not (forbidden & set(recorded)), f"network-touching git verbs invoked: {recorded}"


def test_environment_strip_blocks_git_terminal_prompt(
    monkeypatch: pytest.MonkeyPatch, conn: psycopg.Connection, tmp_path: Path
) -> None:
    repo = make_fixture_repo(tmp_path)
    captured_env: list[dict[str, str] | None] = []
    real_run = subprocess.run

    def recording_run(cmd, *args, **kwargs):  # type: ignore[no-untyped-def]
        captured_env.append(kwargs.get("env"))
        return real_run(cmd, *args, **kwargs)

    monkeypatch.setattr("engram.git_import.subprocess.run", recording_run)
    import_git_repo(conn, repo)
    assert captured_env, "expected git subprocess invocations"
    for env in captured_env:
        assert env is not None, "importer must pass an explicit env to subprocess.run"
        assert env.get("GIT_TERMINAL_PROMPT") == "0"
        assert "GIT_DIR" not in env  # no operator GIT_DIR override leaks in
        assert "GIT_WORK_TREE" not in env


def test_verb_allowlist_rejects_unknown_verbs(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # Direct call into the private helper to prove the routing guard fires.
    from engram.git_import import _run_git

    repo = tmp_path
    with pytest.raises(GitSubprocessError):
        _run_git(repo, "clone", "https://example.invalid/x.git")


def test_verb_allowlist_is_closed() -> None:
    # Sanity: if a future change adds a network-touching verb, this test fails.
    network_verbs = {"clone", "fetch", "pull", "push", "ls-remote", "remote", "submodule"}
    assert not (network_verbs & set(GIT_VERB_ALLOWLIST))
