from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from types import SimpleNamespace
from typing import Any
from uuid import uuid4

import pytest

from engram import entity_grounding_daemon
from engram.entity_grounding_materialization import (
    ApprovedGrantMaterializationResult,
    ProcessedApprovedGrant,
)


class _FakeCursor:
    def __init__(self, row: tuple[object, ...] | None) -> None:
        self.row = row

    def fetchone(self) -> tuple[object, ...] | None:
        return self.row


class _FakeConnection:
    def __init__(self, *, lock_row: tuple[object, ...] | None = (True,)) -> None:
        self.lock_row = lock_row
        self.commit_count = 0
        self.executed: list[tuple[str, tuple[object, ...] | None]] = []

    def execute(
        self,
        query: str,
        params: tuple[object, ...] | None = None,
    ) -> _FakeCursor:
        self.executed.append((query, params))
        return _FakeCursor(self.lock_row)

    def commit(self) -> None:
        self.commit_count += 1


def test_broker_daemon_processes_bounded_iterations(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    connections: list[_FakeConnection] = []
    process_calls: list[dict[str, object]] = []
    sleep_calls: list[float] = []

    @contextmanager
    def connect_factory() -> Iterator[_FakeConnection]:
        connection = _FakeConnection()
        connections.append(connection)
        yield connection

    def fake_process_approved_grounding_grants(
        conn: _FakeConnection,
        **kwargs: Any,
    ) -> ApprovedGrantMaterializationResult:
        process_calls.append({"conn": conn, **kwargs})
        return ApprovedGrantMaterializationResult(
            processed=(
                ProcessedApprovedGrant(
                    request_id="request-1",
                    grant_id="grant-1",
                    status="resolved",
                    evidence_ids=(uuid4(),),
                    response_id=uuid4(),
                    adapter_invoked=True,
                ),
            ),
            skipped=(),
        )

    monkeypatch.setattr(
        entity_grounding_daemon,
        "process_approved_grounding_grants",
        fake_process_approved_grounding_grants,
    )

    result = entity_grounding_daemon.run_entity_grounding_broker_daemon(
        connect_factory,
        tenant_id="personal",
        corpus_id="personal",
        limit=3,
        interval_seconds=0.25,
        target_adapter="internet_search",
        max_iterations=2,
        sleep=sleep_calls.append,
        use_advisory_lock=False,
    )

    assert result.iterations == 2
    assert result.processed_count == 2
    assert result.materialized_evidence_count == 2
    assert result.lock_skipped_count == 0
    assert result.stopped_reason == "max_iterations"
    assert result.last_iteration is not None
    assert result.last_iteration.statuses == ("resolved",)
    assert sleep_calls == [0.25]
    assert len(connections) == 2
    assert [connection.commit_count for connection in connections] == [1, 1]
    assert [call["tenant_id"] for call in process_calls] == ["personal", "personal"]
    assert [call["limit"] for call in process_calls] == [3, 3]
    assert [call["target_adapter"] for call in process_calls] == [
        "internet_search",
        "internet_search",
    ]


def test_broker_daemon_skips_iteration_when_lock_is_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    connection = _FakeConnection(lock_row=(False,))

    @contextmanager
    def connect_factory() -> Iterator[_FakeConnection]:
        yield connection

    def fail_process_approved_grounding_grants(
        conn: _FakeConnection,
        **kwargs: Any,
    ) -> ApprovedGrantMaterializationResult:
        raise AssertionError("materializer must not run without the advisory lock")

    monkeypatch.setattr(
        entity_grounding_daemon,
        "process_approved_grounding_grants",
        fail_process_approved_grounding_grants,
    )

    result = entity_grounding_daemon.run_entity_grounding_broker_daemon(
        connect_factory,
        max_iterations=1,
    )

    assert result.iterations == 1
    assert result.processed_count == 0
    assert result.materialized_evidence_count == 0
    assert result.lock_skipped_count == 1
    assert result.last_iteration is not None
    assert result.last_iteration.lock_acquired is False
    assert result.last_iteration.statuses == ("lock_unavailable",)
    assert connection.commit_count == 1
    assert "pg_try_advisory_xact_lock" in connection.executed[0][0]


def test_broker_daemon_rejects_invalid_options() -> None:
    @contextmanager
    def connect_factory() -> Iterator[SimpleNamespace]:
        yield SimpleNamespace(commit=lambda: None)

    with pytest.raises(entity_grounding_daemon.EntityGroundingBrokerDaemonError):
        entity_grounding_daemon.run_entity_grounding_broker_daemon(
            connect_factory,
            interval_seconds=-1,
            max_iterations=1,
        )
