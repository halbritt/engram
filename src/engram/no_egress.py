from __future__ import annotations

import errno
import json
import os
import platform
import shutil
import socket
import subprocess
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import TypeAlias

JsonValue: TypeAlias = (
    str | int | float | bool | None | list["JsonValue"] | dict[str, "JsonValue"]
)

ENGRAM_NO_EGRESS_PROBE_TIMEOUT_SECONDS = float(
    os.environ.get("ENGRAM_NO_EGRESS_PROBE_TIMEOUT_SECONDS", "3.0")
)
ENGRAM_NO_EGRESS_CONNECT_TIMEOUT_SECONDS = float(
    os.environ.get("ENGRAM_NO_EGRESS_CONNECT_TIMEOUT_SECONDS", "0.25")
)

NO_EGRESS_UNSUPPORTED_RETURN_CODE = 125
NO_EGRESS_CHILD_SETUP_RETURN_CODE = 126

_BLOCKED_ERRNOS: frozenset[int] = frozenset(
    {
        errno.EACCES,
        errno.EHOSTUNREACH,
        errno.ENETDOWN,
        errno.ENETUNREACH,
        errno.EPERM,
    }
)


class NoEgressError(RuntimeError):
    """Raised when the no-egress wrapper cannot construct a valid request."""


@dataclass(frozen=True)
class Mechanism:
    """Executable OS mechanism that may provide a no-egress boundary."""

    name: str
    executable: str

    def to_dict(self) -> dict[str, JsonValue]:
        """Return a JSON-serializable mechanism summary."""
        return {"name": self.name, "executable": self.executable}


@dataclass(frozen=True)
class SupportResult:
    """Platform and executable discovery result for no-egress enforcement."""

    status: str
    platform: str
    mechanisms: tuple[Mechanism, ...]
    reason: str | None = None

    def to_dict(self) -> dict[str, JsonValue]:
        """Return a JSON-serializable support result."""
        return {
            "status": self.status,
            "platform": self.platform,
            "mechanisms": [mechanism.to_dict() for mechanism in self.mechanisms],
            "reason": self.reason,
        }


@dataclass(frozen=True)
class ProbeAttempt:
    """Single mechanism probe attempt."""

    mechanism: str
    status: str
    command: tuple[str, ...]
    returncode: int | None = None
    reason: str | None = None
    child: dict[str, JsonValue] | None = None

    def to_dict(self) -> dict[str, JsonValue]:
        """Return a JSON-serializable attempt result."""
        return {
            "mechanism": self.mechanism,
            "status": self.status,
            "command": list(self.command),
            "returncode": self.returncode,
            "reason": self.reason,
            "child": self.child,
        }


@dataclass(frozen=True)
class ProbeResult:
    """No-egress enforcement probe result."""

    status: str
    platform: str
    mechanism: str | None
    reason: str | None
    support: SupportResult
    attempts: tuple[ProbeAttempt, ...]
    loopback_ok: bool | None = None
    non_loopback_blocked: bool | None = None
    namespace_isolated: bool | None = None

    def to_dict(self) -> dict[str, JsonValue]:
        """Return a JSON-serializable probe result."""
        return {
            "status": self.status,
            "platform": self.platform,
            "mechanism": self.mechanism,
            "reason": self.reason,
            "support": self.support.to_dict(),
            "loopback_ok": self.loopback_ok,
            "non_loopback_blocked": self.non_loopback_blocked,
            "namespace_isolated": self.namespace_isolated,
            "attempts": [attempt.to_dict() for attempt in self.attempts],
        }


@dataclass(frozen=True)
class RunResult:
    """Result from launching a subprocess through the no-egress wrapper."""

    status: str
    returncode: int
    mechanism: str | None
    reason: str | None
    probe: ProbeResult

    def to_dict(self) -> dict[str, JsonValue]:
        """Return a JSON-serializable run result."""
        return {
            "status": self.status,
            "returncode": self.returncode,
            "mechanism": self.mechanism,
            "reason": self.reason,
            "probe": self.probe.to_dict(),
        }


def detect_support(
    *,
    which: Callable[[str], str | None] = shutil.which,
    system_name: str | None = None,
) -> SupportResult:
    """Detect whether this host has known no-egress enforcement candidates."""
    current_platform = system_name if system_name is not None else platform.system()
    if current_platform != "Linux":
        return SupportResult(
            status="unsupported",
            platform=current_platform,
            mechanisms=(),
            reason="no-egress OS enforcement is currently implemented for Linux only",
        )

    mechanisms: list[Mechanism] = []
    unshare_path = which("unshare")
    if unshare_path is not None:
        mechanisms.append(Mechanism("unshare-netns", unshare_path))
    bwrap_path = which("bwrap")
    if bwrap_path is not None:
        mechanisms.append(Mechanism("bubblewrap-netns", bwrap_path))

    if not mechanisms:
        return SupportResult(
            status="unsupported",
            platform=current_platform,
            mechanisms=(),
            reason="neither unshare nor bwrap is installed",
        )
    return SupportResult(
        status="available",
        platform=current_platform,
        mechanisms=tuple(mechanisms),
    )


def build_wrapped_command(command: Sequence[str], mechanism: Mechanism) -> list[str]:
    """Build a command line that executes a subprocess inside a no-egress boundary."""
    if not command:
        raise NoEgressError("no-egress run requires a command")
    child_args = ["_child", "exec", "--", *command]
    return _wrap_child_args(child_args, mechanism)


def build_probe_command(mechanism: Mechanism, *, parent_netns: str | None = None) -> list[str]:
    """Build a command line that probes one no-egress mechanism."""
    args = ["_child", "probe"]
    if parent_netns is not None:
        args.extend(["--parent-netns", parent_netns])
    return _wrap_child_args(args, mechanism)


def probe_enforcement(
    *,
    which: Callable[[str], str | None] = shutil.which,
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
    system_name: str | None = None,
) -> ProbeResult:
    """Probe available mechanisms and return the first honestly enforced boundary."""
    support = detect_support(which=which, system_name=system_name)
    if support.status != "available":
        return ProbeResult(
            status="unsupported",
            platform=support.platform,
            mechanism=None,
            reason=support.reason,
            support=support,
            attempts=(),
        )

    parent_netns = _read_current_netns()
    attempts: list[ProbeAttempt] = []
    for mechanism in support.mechanisms:
        attempt = _probe_mechanism(
            mechanism,
            parent_netns=parent_netns,
            runner=runner,
        )
        attempts.append(attempt)
        child = attempt.child or {}
        loopback_ok = _json_bool(child.get("loopback_ok"))
        non_loopback_blocked = _json_bool(child.get("non_loopback_blocked"))
        namespace_isolated = _json_bool(child.get("namespace_isolated"))
        if (
            attempt.status == "egress_enforced"
            and loopback_ok is True
            and non_loopback_blocked is True
            and namespace_isolated is True
        ):
            return ProbeResult(
                status="egress_enforced",
                platform=support.platform,
                mechanism=mechanism.name,
                reason=None,
                support=support,
                attempts=tuple(attempts),
                loopback_ok=True,
                non_loopback_blocked=True,
                namespace_isolated=True,
            )

    reason = attempts[-1].reason if attempts else "no mechanism was probed"
    return ProbeResult(
        status="unsupported",
        platform=support.platform,
        mechanism=None,
        reason=reason,
        support=support,
        attempts=tuple(attempts),
    )


def run_under_no_egress(
    command: Sequence[str],
    *,
    which: Callable[[str], str | None] = shutil.which,
    probe_runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
    run_runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
    system_name: str | None = None,
) -> RunResult:
    """Run a subprocess under the best available no-egress mechanism."""
    if not command:
        raise NoEgressError("no-egress run requires a command")
    probe = probe_enforcement(which=which, runner=probe_runner, system_name=system_name)
    if probe.status != "egress_enforced" or probe.mechanism is None:
        return RunResult(
            status="unsupported",
            returncode=NO_EGRESS_UNSUPPORTED_RETURN_CODE,
            mechanism=None,
            reason=probe.reason,
            probe=probe,
        )

    mechanism = _mechanism_by_name(probe.support.mechanisms, probe.mechanism)
    if mechanism is None:
        return RunResult(
            status="unsupported",
            returncode=NO_EGRESS_UNSUPPORTED_RETURN_CODE,
            mechanism=None,
            reason=f"probed mechanism {probe.mechanism!r} is no longer available",
            probe=probe,
        )
    completed = run_runner(build_wrapped_command(command, mechanism), check=False)
    return RunResult(
        status="egress_enforced",
        returncode=int(completed.returncode),
        mechanism=mechanism.name,
        reason=None,
        probe=probe,
    )


def _wrap_child_args(child_args: Sequence[str], mechanism: Mechanism) -> list[str]:
    child_command = [sys.executable, "-m", "engram.no_egress", *child_args]
    if mechanism.name == "unshare-netns":
        return [
            mechanism.executable,
            "--user",
            "--map-root-user",
            "--net",
            "--fork",
            "--kill-child",
            *child_command,
        ]
    if mechanism.name == "bubblewrap-netns":
        return [
            mechanism.executable,
            "--unshare-net",
            "--die-with-parent",
            "--bind",
            "/",
            "/",
            "--dev",
            "/dev",
            "--proc",
            "/proc",
            *child_command,
        ]
    raise NoEgressError(f"unknown no-egress mechanism: {mechanism.name}")


def _probe_mechanism(
    mechanism: Mechanism,
    *,
    parent_netns: str | None,
    runner: Callable[..., subprocess.CompletedProcess[str]],
) -> ProbeAttempt:
    command = build_probe_command(mechanism, parent_netns=parent_netns)
    try:
        completed = runner(
            command,
            capture_output=True,
            text=True,
            timeout=ENGRAM_NO_EGRESS_PROBE_TIMEOUT_SECONDS,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return ProbeAttempt(
            mechanism=mechanism.name,
            status="unsupported",
            command=tuple(command),
            reason="probe timed out",
        )
    except OSError as exc:
        return ProbeAttempt(
            mechanism=mechanism.name,
            status="unsupported",
            command=tuple(command),
            reason=str(exc),
        )

    child = _parse_probe_stdout(completed.stdout)
    status = "unsupported"
    reason = _stderr_reason(completed.stderr)
    if completed.returncode == 0 and child is not None:
        loopback_ok = _json_bool(child.get("loopback_ok"))
        non_loopback_blocked = _json_bool(child.get("non_loopback_blocked"))
        namespace_isolated = _json_bool(child.get("namespace_isolated"))
        if loopback_ok is True and non_loopback_blocked is True and namespace_isolated is True:
            status = "egress_enforced"
            reason = None
        else:
            reason = _child_unsupported_reason(child)
    elif reason is None:
        reason = f"probe exited with status {completed.returncode}"
    return ProbeAttempt(
        mechanism=mechanism.name,
        status=status,
        command=tuple(command),
        returncode=int(completed.returncode),
        reason=reason,
        child=child,
    )


def _parse_probe_stdout(stdout: str) -> dict[str, JsonValue] | None:
    stripped = stdout.strip()
    if not stripped:
        return None
    try:
        payload = json.loads(stripped)
    except json.JSONDecodeError:
        return None
    if isinstance(payload, dict):
        return payload
    return None


def _child_unsupported_reason(child: dict[str, JsonValue]) -> str:
    reasons: list[str] = []
    if _json_bool(child.get("namespace_isolated")) is not True:
        reasons.append("network namespace did not change")
    if _json_bool(child.get("loopback_ok")) is not True:
        reasons.append("loopback probe failed")
    if _json_bool(child.get("non_loopback_blocked")) is not True:
        reasons.append("non-loopback socket was not conclusively blocked")
    setup_error = child.get("setup_error")
    if isinstance(setup_error, str) and setup_error:
        reasons.append(setup_error)
    return "; ".join(reasons) if reasons else "probe did not prove enforcement"


def _stderr_reason(stderr: str | None) -> str | None:
    if stderr is None:
        return None
    stripped = stderr.strip()
    if not stripped:
        return None
    return stripped.splitlines()[-1]


def _mechanism_by_name(mechanisms: Sequence[Mechanism], name: str) -> Mechanism | None:
    for mechanism in mechanisms:
        if mechanism.name == name:
            return mechanism
    return None


def _read_current_netns() -> str | None:
    try:
        return os.readlink("/proc/self/ns/net")
    except OSError:
        return None


def _json_bool(value: JsonValue | None) -> bool | None:
    if isinstance(value, bool):
        return value
    return None


def _child_main(argv: Sequence[str]) -> int:
    args = list(argv)
    if not args:
        print("no-egress child: missing mode", file=sys.stderr)
        return 2
    mode = args[0]
    if mode not in {"probe", "exec"}:
        print(f"no-egress child: unknown mode {mode!r}", file=sys.stderr)
        return 2

    setup_error = _bring_loopback_up()
    if mode == "probe":
        parent_netns = _parse_probe_child_args(args[1:])
        payload = _run_child_probe(parent_netns=parent_netns, setup_error=setup_error)
        print(json.dumps(payload, sort_keys=True))
        return 0

    command = _normalize_remainder(args[1:])
    if not command:
        print("no-egress child: missing command", file=sys.stderr)
        return 2
    if setup_error is not None:
        print(f"no-egress child: {setup_error}", file=sys.stderr)
        return NO_EGRESS_CHILD_SETUP_RETURN_CODE
    os.execvp(command[0], command)
    raise AssertionError("os.execvp returned unexpectedly")


def _parse_probe_child_args(args: Sequence[str]) -> str | None:
    parent_netns: str | None = None
    remaining = list(args)
    while remaining:
        arg = remaining.pop(0)
        if arg != "--parent-netns":
            print(f"no-egress child: ignoring unexpected probe arg {arg!r}", file=sys.stderr)
            continue
        if not remaining:
            print("no-egress child: --parent-netns requires a value", file=sys.stderr)
            return None
        parent_netns = remaining.pop(0)
    return parent_netns


def _normalize_remainder(command: Sequence[str]) -> list[str]:
    normalized = list(command)
    if normalized and normalized[0] == "--":
        return normalized[1:]
    return normalized


def _run_child_probe(
    *,
    parent_netns: str | None,
    setup_error: str | None,
) -> dict[str, JsonValue]:
    child_netns = _read_current_netns()
    namespace_isolated = (
        parent_netns is not None and child_netns is not None and child_netns != parent_netns
    )
    loopback_ok, loopback_error = _probe_loopback()
    non_loopback_blocked, non_loopback_errno, non_loopback_error = _probe_non_loopback_blocked()
    return {
        "status": (
            "egress_enforced"
            if namespace_isolated and loopback_ok and non_loopback_blocked
            else "unsupported"
        ),
        "parent_netns": parent_netns,
        "child_netns": child_netns,
        "namespace_isolated": namespace_isolated,
        "loopback_ok": loopback_ok,
        "loopback_error": loopback_error,
        "non_loopback_blocked": non_loopback_blocked,
        "non_loopback_errno": non_loopback_errno,
        "non_loopback_error": non_loopback_error,
        "setup_error": setup_error,
    }


def _bring_loopback_up() -> str | None:
    if platform.system() != "Linux":
        return "loopback setup is implemented for Linux only"
    try:
        import fcntl
        import struct
    except ImportError as exc:
        return f"loopback setup unavailable: {exc}"

    ifname = b"lo"
    siocgifflags = 0x8913
    siocsifflags = 0x8914
    iff_up = 0x1
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            ifreq = struct.pack("16sH14s", ifname, 0, b"")
            flags_payload = fcntl.ioctl(sock.fileno(), siocgifflags, ifreq)
            _, flags, _ = struct.unpack("16sH14s", flags_payload)
            fcntl.ioctl(
                sock.fileno(),
                siocsifflags,
                struct.pack("16sH14s", ifname, flags | iff_up, b""),
            )
    except OSError as exc:
        return f"failed to bring loopback up: {exc}"
    return None


def _probe_loopback() -> tuple[bool, str | None]:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
            server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server.bind(("127.0.0.1", 0))
            server.listen(1)
            port = int(server.getsockname()[1])
            with socket.create_connection(
                ("127.0.0.1", port),
                timeout=ENGRAM_NO_EGRESS_CONNECT_TIMEOUT_SECONDS,
            ) as client:
                conn, _ = server.accept()
                with conn:
                    client.sendall(b"x")
                    conn.recv(1)
        return True, None
    except OSError as exc:
        return False, str(exc)


def _probe_non_loopback_blocked() -> tuple[bool, int | None, str | None]:
    try:
        with socket.create_connection(
            ("198.51.100.1", 9),
            timeout=ENGRAM_NO_EGRESS_CONNECT_TIMEOUT_SECONDS,
        ):
            return False, None, "non-loopback connection unexpectedly succeeded"
    except TimeoutError as exc:
        return False, None, f"non-loopback connection timed out: {exc}"
    except OSError as exc:
        blocked = exc.errno in _BLOCKED_ERRNOS
        return blocked, exc.errno, str(exc)


def main(argv: Sequence[str] | None = None) -> int:
    """Internal entrypoint used by namespace wrapper subprocesses."""
    args = list(sys.argv[1:] if argv is None else argv)
    if not args or args[0] != "_child":
        print("engram.no_egress is an internal helper; use `engram no-egress`", file=sys.stderr)
        return 2
    return _child_main(args[1:])


if __name__ == "__main__":
    raise SystemExit(main())
