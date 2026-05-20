from __future__ import annotations

import uuid

import psycopg
import pytest
from psycopg import errors
from psycopg.types.json import Jsonb

from engram.events import insert_context_feedback, insert_memory_event


def _insert_snapshot(conn: psycopg.Connection, *, memory_epoch: int) -> str:
    row = conn.execute(
        """
        INSERT INTO context_snapshots (
            tenant_id,
            corpus_id,
            scope_type,
            scope_key,
            memory_epoch,
            compiler_version,
            package_json,
            rendered_text,
            source_belief_ids,
            source_segment_ids,
            source_reference_ids,
            omissions
        )
        VALUES (
            'personal',
            'personal',
            'project',
            'engram',
            %s,
            'context.compiler.v1',
            %s,
            'Rendered context',
            %s,
            %s,
            %s,
            %s
        )
        RETURNING id::text
        """,
        (
            memory_epoch,
            Jsonb({"sections": []}),
            [uuid.uuid4()],
            [uuid.uuid4()],
            ["git_commits:abc123"],
            Jsonb([{"reason": "no_data", "lane": "recent_signals"}]),
        ),
    ).fetchone()
    assert row is not None
    return str(row[0])


def _insert_feedback(conn: psycopg.Connection, *, snapshot_id: str) -> str:
    row = conn.execute(
        """
        INSERT INTO context_feedback (
            snapshot_id,
            tenant_id,
            corpus_id,
            feedback_kind,
            source_belief_ids,
            source_segment_ids,
            source_reference_ids,
            correction_note,
            actor,
            request_uuid
        )
        VALUES (%s, 'personal', 'personal', 'wrong', %s, %s, %s, %s, %s, %s)
        RETURNING id::text
        """,
        (
            snapshot_id,
            [uuid.uuid4()],
            [uuid.uuid4()],
            ["markdown_files:README.md"],
            "The rendered fact is stale.",
            "operator",
            uuid.uuid4(),
        ),
    ).fetchone()
    assert row is not None
    return str(row[0])


def test_context_event_tables_exist(conn: psycopg.Connection) -> None:
    for table in ("memory_events", "context_snapshots", "context_feedback"):
        row = conn.execute("SELECT to_regclass(%s) IS NOT NULL", (f"public.{table}",)).fetchone()
        assert row is not None
        assert row[0] is True, f"table missing: {table}"


def test_insert_memory_event_helper_records_epoch_and_payload(
    conn: psycopg.Connection,
) -> None:
    first = insert_memory_event(
        conn,
        event_type="belief_changed",
        aggregate_type="belief",
        aggregate_id=uuid.uuid4(),
        scope_type="project",
        scope_key="engram",
        payload={"transition": "accepted"},
    )
    second = insert_memory_event(
        conn,
        event_type="context_snapshot_invalidated",
        aggregate_type="context_snapshot",
        scope_type="project",
        scope_key="engram",
        payload={"reason": "belief_changed"},
    )

    assert first.id != second.id
    assert second.memory_epoch > first.memory_epoch
    row = conn.execute(
        """
        SELECT tenant_id, corpus_id, event_type, payload
        FROM memory_events
        WHERE id = %s
        """,
        (first.id,),
    ).fetchone()
    assert row == ("personal", "personal", "belief_changed", {"transition": "accepted"})


def test_context_snapshots_store_package_sources_omissions_and_dirty_flag(
    conn: psycopg.Connection,
) -> None:
    event = insert_memory_event(
        conn,
        event_type="context_snapshot_refreshed",
        aggregate_type="context_snapshot",
        scope_type="project",
        scope_key="engram",
    )
    snapshot_id = _insert_snapshot(conn, memory_epoch=event.memory_epoch)

    row = conn.execute(
        """
        SELECT package_json, rendered_text, cardinality(source_belief_ids),
               cardinality(source_segment_ids), source_reference_ids,
               omissions, is_dirty
        FROM context_snapshots
        WHERE id = %s
        """,
        (snapshot_id,),
    ).fetchone()
    assert row is not None
    assert row[0] == {"sections": []}
    assert row[1] == "Rendered context"
    assert row[2] == 1
    assert row[3] == 1
    assert row[4] == ["git_commits:abc123"]
    assert row[5] == [{"reason": "no_data", "lane": "recent_signals"}]
    assert row[6] is False


def test_context_feedback_links_to_snapshot_and_source_ids(
    conn: psycopg.Connection,
) -> None:
    event = insert_memory_event(
        conn,
        event_type="context_snapshot_refreshed",
        aggregate_type="context_snapshot",
        scope_type="project",
        scope_key="engram",
    )
    snapshot_id = _insert_snapshot(conn, memory_epoch=event.memory_epoch)
    feedback_id = _insert_feedback(conn, snapshot_id=snapshot_id)

    row = conn.execute(
        """
        SELECT snapshot_id::text, feedback_kind, cardinality(source_belief_ids),
               cardinality(source_segment_ids), source_reference_ids,
               correction_note, actor, request_uuid IS NOT NULL
        FROM context_feedback
        WHERE id = %s
        """,
        (feedback_id,),
    ).fetchone()
    assert row == (
        snapshot_id,
        "wrong",
        1,
        1,
        ["markdown_files:README.md"],
        "The rendered fact is stale.",
        "operator",
        True,
    )


def test_insert_context_feedback_helper_records_event_and_source_links(
    conn: psycopg.Connection,
) -> None:
    event = insert_memory_event(
        conn,
        event_type="context_snapshot_refreshed",
        aggregate_type="context_snapshot",
        scope_type="project",
        scope_key="engram",
    )
    snapshot_id = _insert_snapshot(conn, memory_epoch=event.memory_epoch)
    belief_id = uuid.uuid4()
    segment_id = uuid.uuid4()

    feedback = insert_context_feedback(
        conn,
        snapshot_id=snapshot_id,
        feedback_kind="stale",
        source_belief_ids=[belief_id],
        source_segment_ids=[segment_id],
        source_reference_ids=["beliefs:stale-marker"],
        correction_note="The snapshot cited stale context.",
        actor="worker-m",
    )

    row = conn.execute(
        """
        SELECT
            cf.snapshot_id::text,
            cf.feedback_kind,
            cf.source_belief_ids,
            cf.source_segment_ids,
            cf.source_reference_ids,
            cf.correction_note,
            cf.actor,
            me.event_type,
            me.aggregate_id::text,
            me.payload->>'feedback_kind'
        FROM context_feedback cf
        JOIN memory_events me ON me.aggregate_id = cf.id
        WHERE cf.id = %s
        """,
        (feedback.id,),
    ).fetchone()
    assert row is not None
    assert row[0] == snapshot_id
    assert row[1] == "stale"
    assert [str(value) for value in row[2]] == [str(belief_id)]
    assert [str(value) for value in row[3]] == [str(segment_id)]
    assert row[4] == ["beliefs:stale-marker"]
    assert row[5] == "The snapshot cited stale context."
    assert row[6] == "worker-m"
    assert row[7] == "context_feedback_captured"
    assert row[8] == feedback.id
    assert row[9] == "stale"
    assert feedback.memory_epoch > event.memory_epoch


@pytest.mark.parametrize(
    ("table", "update_sql", "delete_sql"),
    [
        (
            "memory_events",
            "UPDATE memory_events SET payload = '{}'::jsonb WHERE id = %s",
            "DELETE FROM memory_events WHERE id = %s",
        ),
        (
            "context_snapshots",
            "UPDATE context_snapshots SET is_dirty = true WHERE id = %s",
            "DELETE FROM context_snapshots WHERE id = %s",
        ),
        (
            "context_feedback",
            "UPDATE context_feedback SET feedback_kind = 'useful' WHERE id = %s",
            "DELETE FROM context_feedback WHERE id = %s",
        ),
    ],
)
def test_context_event_tables_are_append_only(
    conn: psycopg.Connection,
    table: str,
    update_sql: str,
    delete_sql: str,
) -> None:
    event = insert_memory_event(
        conn,
        event_type="context_snapshot_refreshed",
        aggregate_type="context_snapshot",
        scope_type="project",
        scope_key=f"engram-{table}",
    )
    ids = {"memory_events": event.id}
    ids["context_snapshots"] = _insert_snapshot(conn, memory_epoch=event.memory_epoch)
    ids["context_feedback"] = _insert_feedback(conn, snapshot_id=ids["context_snapshots"])

    with pytest.raises(errors.RaiseException):
        conn.execute(update_sql, (ids[table],))
    conn.rollback()

    with pytest.raises(errors.RaiseException):
        conn.execute(delete_sql, (ids[table],))
    conn.rollback()


@pytest.mark.parametrize(
    ("sql", "params"),
    [
        (
            """
            INSERT INTO memory_events (
                event_type, aggregate_type, scope_type, scope_key
            )
            VALUES ('made_up', 'belief', 'project', 'engram')
            """,
            (),
        ),
        (
            """
            INSERT INTO memory_events (
                event_type, aggregate_type, scope_type, scope_key
            )
            VALUES ('belief_changed', 'made_up', 'project', 'engram')
            """,
            (),
        ),
        (
            """
            INSERT INTO context_snapshots (
                scope_type, scope_key, memory_epoch, compiler_version
            )
            VALUES ('made_up', 'engram', 1, 'context.compiler.v1')
            """,
            (),
        ),
        (
            """
            INSERT INTO memory_events (
                event_type, aggregate_type, scope_type, scope_key
            )
            VALUES ('belief_changed', 'belief', 'made_up', 'engram')
            """,
            (),
        ),
    ],
)
def test_context_event_and_snapshot_closed_vocabularies_reject_unknown_values(
    conn: psycopg.Connection,
    sql: str,
    params: tuple[object, ...],
) -> None:
    with pytest.raises(errors.CheckViolation):
        conn.execute(sql, params)
    conn.rollback()


def test_context_feedback_closed_vocabulary_rejects_unknown_kind(
    conn: psycopg.Connection,
) -> None:
    event = insert_memory_event(
        conn,
        event_type="context_snapshot_refreshed",
        aggregate_type="context_snapshot",
        scope_type="project",
        scope_key="engram",
    )
    snapshot_id = _insert_snapshot(conn, memory_epoch=event.memory_epoch)

    with pytest.raises(errors.CheckViolation):
        conn.execute(
            """
            INSERT INTO context_feedback (
                snapshot_id,
                feedback_kind
            )
            VALUES (%s, 'made_up')
            """,
            (snapshot_id,),
        )
    conn.rollback()
