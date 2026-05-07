from __future__ import annotations

import os

import psycopg
import pytest

from engram.progress import upsert_progress


TEST_DATABASE_URL = os.environ.get("ENGRAM_TEST_DATABASE_URL")


def _read_progress_rows(conn: psycopg.Connection) -> list[tuple]:
    return conn.execute(
        """
        SELECT stage, scope, status, position, error_count, last_error
        FROM consolidation_progress
        ORDER BY stage, scope
        """
    ).fetchall()


def test_first_upsert_inserts_row(conn: psycopg.Connection) -> None:
    upsert_progress(
        conn,
        stage="segment",
        scope="conv-001",
        status="pending",
        position={"idx": 0},
    )
    rows = _read_progress_rows(conn)
    assert len(rows) == 1
    stage, scope, status, position, error_count, last_error = rows[0]
    assert stage == "segment"
    assert scope == "conv-001"
    assert status == "pending"
    assert position == {"idx": 0}
    assert error_count == 0
    assert last_error is None


def test_second_upsert_with_same_key_updates_in_place(conn: psycopg.Connection) -> None:
    upsert_progress(
        conn,
        stage="segment",
        scope="conv-001",
        status="pending",
        position={"idx": 0},
    )
    upsert_progress(
        conn,
        stage="segment",
        scope="conv-001",
        status="in_progress",
        position={"idx": 5},
    )
    rows = _read_progress_rows(conn)
    assert len(rows) == 1
    stage, scope, status, position, _error_count, _last_error = rows[0]
    assert (stage, scope, status) == ("segment", "conv-001", "in_progress")
    assert position == {"idx": 5}


def test_status_transitions(conn: psycopg.Connection) -> None:
    upsert_progress(
        conn,
        stage="segment",
        scope="conv-001",
        status="pending",
        position={"idx": 0},
    )
    upsert_progress(
        conn,
        stage="segment",
        scope="conv-001",
        status="in_progress",
        position={"idx": 1},
    )
    upsert_progress(
        conn,
        stage="segment",
        scope="conv-001",
        status="completed",
        position={"idx": 10},
    )
    rows = _read_progress_rows(conn)
    assert len(rows) == 1
    stage, scope, status, position, _error_count, _last_error = rows[0]
    assert (stage, scope, status) == ("segment", "conv-001", "completed")
    assert position == {"idx": 10}
    # started_at should be set once it transitioned through 'in_progress'
    started_at = conn.execute(
        "SELECT started_at FROM consolidation_progress"
    ).fetchone()[0]
    assert started_at is not None


def test_different_scopes_are_independent(conn: psycopg.Connection) -> None:
    upsert_progress(
        conn,
        stage="segment",
        scope="conv-001",
        status="pending",
        position={"idx": 0},
    )
    upsert_progress(
        conn,
        stage="segment",
        scope="conv-002",
        status="pending",
        position={"idx": 0},
    )
    rows = _read_progress_rows(conn)
    assert len(rows) == 2
    scopes = {row[1] for row in rows}
    assert scopes == {"conv-001", "conv-002"}


def test_different_stages_are_independent(conn: psycopg.Connection) -> None:
    upsert_progress(
        conn,
        stage="segment",
        scope="conv-001",
        status="pending",
        position={"idx": 0},
    )
    upsert_progress(
        conn,
        stage="embed",
        scope="conv-001",
        status="pending",
        position={"idx": 0},
    )
    rows = _read_progress_rows(conn)
    assert len(rows) == 2
    stages = {row[0] for row in rows}
    assert stages == {"segment", "embed"}


def test_position_monotonicity_not_enforced(conn: psycopg.Connection) -> None:
    """upsert_progress does not enforce monotonic positions.

    The implementation always overwrites position with EXCLUDED.position. This
    test documents that gap: a regression to a smaller position value is
    accepted silently. If monotonicity is added later, flip this test to
    assert the rejection.
    """
    upsert_progress(
        conn,
        stage="segment",
        scope="conv-001",
        status="in_progress",
        position={"idx": 10},
    )
    upsert_progress(
        conn,
        stage="segment",
        scope="conv-001",
        status="in_progress",
        position={"idx": 3},
    )
    rows = _read_progress_rows(conn)
    assert len(rows) == 1
    position = rows[0][3]
    assert position == {"idx": 3}


def test_concurrent_writes_do_not_duplicate_rows(conn: psycopg.Connection) -> None:
    assert TEST_DATABASE_URL is not None  # conn fixture would have skipped otherwise
    second = psycopg.connect(TEST_DATABASE_URL)
    try:
        second.autocommit = True
        upsert_progress(
            conn,
            stage="segment",
            scope="conv-001",
            status="pending",
            position={"idx": 0},
        )
        upsert_progress(
            second,
            stage="segment",
            scope="conv-001",
            status="in_progress",
            position={"idx": 7},
        )
        upsert_progress(
            conn,
            stage="segment",
            scope="conv-001",
            status="completed",
            position={"idx": 12},
        )
    finally:
        second.close()

    rows = _read_progress_rows(conn)
    assert len(rows) == 1
    stage, scope, status, position, _error_count, _last_error = rows[0]
    # Last writer wins; final state must reflect one of the writes, not be corrupted.
    assert (stage, scope) == ("segment", "conv-001")
    assert status in {"pending", "in_progress", "completed"}
    assert position in ({"idx": 0}, {"idx": 7}, {"idx": 12})
    # The last call in this test was the 'completed' write on `conn`.
    assert status == "completed"
    assert position == {"idx": 12}


def test_idempotent_re_run(conn: psycopg.Connection) -> None:
    kwargs = {
        "stage": "segment",
        "scope": "conv-001",
        "status": "in_progress",
        "position": {"idx": 4},
    }
    upsert_progress(conn, **kwargs)
    upsert_progress(conn, **kwargs)
    rows = _read_progress_rows(conn)
    assert len(rows) == 1
    stage, scope, status, position, error_count, last_error = rows[0]
    assert (stage, scope, status) == ("segment", "conv-001", "in_progress")
    assert position == {"idx": 4}
    assert error_count == 0
    assert last_error is None


def test_increment_error_accumulates_and_records_last_error(
    conn: psycopg.Connection,
) -> None:
    upsert_progress(
        conn,
        stage="segment",
        scope="conv-001",
        status="failed",
        position={"idx": 2},
        last_error="boom",
        increment_error=True,
    )
    upsert_progress(
        conn,
        stage="segment",
        scope="conv-001",
        status="failed",
        position={"idx": 2},
        last_error="boom again",
        increment_error=True,
    )
    rows = _read_progress_rows(conn)
    assert len(rows) == 1
    _stage, _scope, status, _position, error_count, last_error = rows[0]
    assert status == "failed"
    # First insert path sets error_count to 1; second update path increments by 1.
    assert error_count == 2
    assert last_error == "boom again"
