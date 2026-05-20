"""Local broker daemon workflow for RFC 0055 entity-grounding materialization."""

from __future__ import annotations

import os
import threading
import time
from collections.abc import Callable
from contextlib import AbstractContextManager
from dataclasses import dataclass

import psycopg

from engram.entity_grounding_materialization import (
    ApprovedGrantMaterializationResult,
    process_approved_grounding_grants,
)

ENTITY_GROUNDING_BROKER_DAEMON_VERSION = "entity_grounding_broker_daemon.v1"
ENTITY_GROUNDING_BROKER_DAEMON_INTERVAL_SECONDS_ENV = (
    "ENGRAM_ENTITY_GROUNDING_BROKER_DAEMON_INTERVAL_SECONDS"
)
ENTITY_GROUNDING_BROKER_DAEMON_BATCH_SIZE_ENV = (
    "ENGRAM_ENTITY_GROUNDING_BROKER_DAEMON_BATCH_SIZE"
)

DEFAULT_ENTITY_GROUNDING_BROKER_DAEMON_INTERVAL_SECONDS = float(
    os.environ.get(ENTITY_GROUNDING_BROKER_DAEMON_INTERVAL_SECONDS_ENV, "10")
)
DEFAULT_ENTITY_GROUNDING_BROKER_DAEMON_BATCH_SIZE = int(
    os.environ.get(ENTITY_GROUNDING_BROKER_DAEMON_BATCH_SIZE_ENV, "20")
)

_ENTITY_GROUNDING_BROKER_DAEMON_LOCK_KEY_1 = 1_701_005_500
_ENTITY_GROUNDING_BROKER_DAEMON_LOCK_KEY_2 = 1


class EntityGroundingBrokerDaemonError(RuntimeError):
    """Raised when the local broker daemon workflow is misconfigured."""


@dataclass(frozen=True)
class BrokerDaemonIteration:
    """Summary for one daemon polling iteration."""

    processed_count: int
    materialized_evidence_count: int
    statuses: tuple[str, ...]
    lock_acquired: bool

    def to_json(self) -> dict[str, object]:
        """Return a JSON-compatible iteration summary."""
        return {
            "processed_count": self.processed_count,
            "materialized_evidence_count": self.materialized_evidence_count,
            "statuses": list(self.statuses),
            "lock_acquired": self.lock_acquired,
        }


@dataclass(frozen=True)
class BrokerDaemonRunResult:
    """Summary for a bounded or interrupted daemon workflow run."""

    iterations: int
    processed_count: int
    materialized_evidence_count: int
    lock_skipped_count: int
    stopped_reason: str
    last_iteration: BrokerDaemonIteration | None

    def to_json(self) -> dict[str, object]:
        """Return a JSON-compatible daemon summary."""
        return {
            "workflow_version": ENTITY_GROUNDING_BROKER_DAEMON_VERSION,
            "iterations": self.iterations,
            "processed_count": self.processed_count,
            "materialized_evidence_count": self.materialized_evidence_count,
            "lock_skipped_count": self.lock_skipped_count,
            "stopped_reason": self.stopped_reason,
            "last_iteration": (
                self.last_iteration.to_json() if self.last_iteration is not None else None
            ),
        }


def run_entity_grounding_broker_daemon(
    connect_factory: Callable[[], AbstractContextManager[psycopg.Connection]],
    *,
    tenant_id: str = "personal",
    corpus_id: str = "personal",
    limit: int = DEFAULT_ENTITY_GROUNDING_BROKER_DAEMON_BATCH_SIZE,
    interval_seconds: float = DEFAULT_ENTITY_GROUNDING_BROKER_DAEMON_INTERVAL_SECONDS,
    target_adapter: str | None = None,
    max_iterations: int | None = None,
    stop_event: threading.Event | None = None,
    sleep: Callable[[float], None] = time.sleep,
    use_advisory_lock: bool = True,
) -> BrokerDaemonRunResult:
    """Poll approved grants and materialize local grounding evidence."""
    _validate_daemon_options(
        limit=limit,
        interval_seconds=interval_seconds,
        max_iterations=max_iterations,
    )

    iterations = 0
    processed_count = 0
    materialized_evidence_count = 0
    lock_skipped_count = 0
    last_iteration: BrokerDaemonIteration | None = None

    while True:
        if stop_event is not None and stop_event.is_set():
            return BrokerDaemonRunResult(
                iterations=iterations,
                processed_count=processed_count,
                materialized_evidence_count=materialized_evidence_count,
                lock_skipped_count=lock_skipped_count,
                stopped_reason="stop_event",
                last_iteration=last_iteration,
            )

        try:
            iteration = _run_daemon_iteration(
                connect_factory,
                tenant_id=tenant_id,
                corpus_id=corpus_id,
                limit=limit,
                target_adapter=target_adapter,
                use_advisory_lock=use_advisory_lock,
            )
        except KeyboardInterrupt:
            return BrokerDaemonRunResult(
                iterations=iterations,
                processed_count=processed_count,
                materialized_evidence_count=materialized_evidence_count,
                lock_skipped_count=lock_skipped_count,
                stopped_reason="keyboard_interrupt",
                last_iteration=last_iteration,
            )

        iterations += 1
        last_iteration = iteration
        if not iteration.lock_acquired:
            lock_skipped_count += 1
        processed_count += iteration.processed_count
        materialized_evidence_count += iteration.materialized_evidence_count

        if max_iterations is not None and iterations >= max_iterations:
            return BrokerDaemonRunResult(
                iterations=iterations,
                processed_count=processed_count,
                materialized_evidence_count=materialized_evidence_count,
                lock_skipped_count=lock_skipped_count,
                stopped_reason="max_iterations",
                last_iteration=last_iteration,
            )

        if stop_event is not None and stop_event.is_set():
            return BrokerDaemonRunResult(
                iterations=iterations,
                processed_count=processed_count,
                materialized_evidence_count=materialized_evidence_count,
                lock_skipped_count=lock_skipped_count,
                stopped_reason="stop_event",
                last_iteration=last_iteration,
            )

        try:
            sleep(interval_seconds)
        except KeyboardInterrupt:
            return BrokerDaemonRunResult(
                iterations=iterations,
                processed_count=processed_count,
                materialized_evidence_count=materialized_evidence_count,
                lock_skipped_count=lock_skipped_count,
                stopped_reason="keyboard_interrupt",
                last_iteration=last_iteration,
            )


def _run_daemon_iteration(
    connect_factory: Callable[[], AbstractContextManager[psycopg.Connection]],
    *,
    tenant_id: str,
    corpus_id: str,
    limit: int,
    target_adapter: str | None,
    use_advisory_lock: bool,
) -> BrokerDaemonIteration:
    with connect_factory() as conn:
        lock_acquired = True
        if use_advisory_lock:
            lock_acquired = _try_daemon_advisory_lock(conn)
        if not lock_acquired:
            conn.commit()
            return BrokerDaemonIteration(
                processed_count=0,
                materialized_evidence_count=0,
                statuses=("lock_unavailable",),
                lock_acquired=False,
            )

        result = process_approved_grounding_grants(
            conn,
            tenant_id=tenant_id,
            corpus_id=corpus_id,
            limit=limit,
            target_adapter=target_adapter,
        )
        conn.commit()
        return _iteration_from_materialization_result(result, lock_acquired=True)


def _try_daemon_advisory_lock(conn: psycopg.Connection) -> bool:
    row = conn.execute(
        "SELECT pg_try_advisory_xact_lock(%s, %s)",
        (
            _ENTITY_GROUNDING_BROKER_DAEMON_LOCK_KEY_1,
            _ENTITY_GROUNDING_BROKER_DAEMON_LOCK_KEY_2,
        ),
    ).fetchone()
    if row is None:
        return False
    return bool(row[0])


def _iteration_from_materialization_result(
    result: ApprovedGrantMaterializationResult,
    *,
    lock_acquired: bool,
) -> BrokerDaemonIteration:
    evidence_count = 0
    statuses: list[str] = []
    for processed in result.processed:
        evidence_count += len(processed.evidence_ids)
        statuses.append(processed.status)
    return BrokerDaemonIteration(
        processed_count=len(result.processed),
        materialized_evidence_count=evidence_count,
        statuses=tuple(statuses),
        lock_acquired=lock_acquired,
    )


def _validate_daemon_options(
    *,
    limit: int,
    interval_seconds: float,
    max_iterations: int | None,
) -> None:
    if limit < 1 or limit > 100:
        raise EntityGroundingBrokerDaemonError("limit must be between 1 and 100")
    if interval_seconds < 0:
        raise EntityGroundingBrokerDaemonError("interval_seconds must be non-negative")
    if max_iterations is not None and max_iterations < 1:
        raise EntityGroundingBrokerDaemonError("max_iterations must be at least 1")
