from __future__ import annotations

from datetime import UTC, datetime

from test_phase3_claims_beliefs import active_segment, insert_extracted_claim

from engram.consolidator import CONSOLIDATOR_MODEL_VERSION, CONSOLIDATOR_PROMPT_VERSION
from engram.consolidator.transitions import BeliefPayload, insert_belief
from engram.phase4 import (
    accept_belief,
    build_deterministic_entities,
    correct_belief,
    entity_neighborhood,
    promote_to_pinned,
    refresh_current_beliefs,
    reject_review_belief,
    run_phase4_smoke,
)


def insert_candidate_belief(conn, *, object_text: str = "Postgres") -> str:
    conv_id, gen_id, seg_id, msg_ids = active_segment(
        conn,
        [("user", f"I use {object_text}", 1)],
    )
    _, claim_id = insert_extracted_claim(
        conn,
        segment_id=seg_id,
        generation_id=gen_id,
        conversation_id=conv_id,
        evidence_ids=msg_ids,
        predicate="uses_tool",
        object_text=object_text,
    )
    payload = BeliefPayload(
        subject_text="user",
        predicate="uses_tool",
        object_text=object_text,
        object_json=None,
        valid_from=datetime.now(UTC),
        valid_to=None,
        observed_at=datetime.now(UTC),
        extracted_at=datetime.now(UTC),
        status="candidate",
        confidence=0.8,
        evidence_ids=[msg_ids[0]],
        claim_ids=[claim_id],
        prompt_version=CONSOLIDATOR_PROMPT_VERSION,
        model_version=CONSOLIDATOR_MODEL_VERSION,
        privacy_tier=1,
        raw_payload={"source": "phase4-test"},
        score_breakdown={"mean": 0.8, "max": 0.8, "min": 0.8, "count": 1, "stddev": 0},
    )
    return insert_belief(conn, payload)


def test_current_beliefs_and_review_actions_follow_transition_api(conn):
    belief_id = insert_candidate_belief(conn)

    refresh_current_beliefs(conn)
    current = conn.execute(
        "SELECT status FROM current_beliefs WHERE id = %s",
        (belief_id,),
    ).fetchone()
    assert current == ("candidate",)
    assert conn.execute("SELECT count(*) FROM belief_review_queue").fetchone()[0] == 1

    accepted = accept_belief(conn, belief_id, actor="test", note="looks grounded")
    assert accepted.action_status == "applied"
    assert conn.execute(
        "SELECT status FROM current_beliefs WHERE id = %s",
        (belief_id,),
    ).fetchone() == ("accepted",)
    assert conn.execute("SELECT count(*) FROM belief_review_queue").fetchone()[0] == 0
    audit = conn.execute(
        """
        SELECT transition_kind, previous_status, new_status
        FROM belief_audit
        WHERE request_uuid = %s
        """,
        (accepted.request_uuid,),
    ).fetchone()
    assert audit == ("promote", "candidate", "accepted")

    action = conn.execute(
        """
        SELECT action_kind, action_status, actor
        FROM belief_review_actions
        WHERE request_uuid = %s
        """,
        (accepted.request_uuid,),
    ).fetchone()
    assert action == ("accept", "applied", "test")


def test_correction_is_raw_capture_and_reject_exits_current_view(conn):
    belief_id = insert_candidate_belief(conn, object_text="SQLite")

    correction = correct_belief(conn, belief_id, "Actually, I use DuckDB most here.")
    assert correction.action_status == "queued_reprocessing"
    capture = conn.execute(
        """
        SELECT capture_type::text, corrects_belief_id::text, content_text
        FROM captures
        WHERE id = %s
        """,
        (correction.capture_id,),
    ).fetchone()
    assert capture == ("user_correction", belief_id, "Actually, I use DuckDB most here.")

    rejected = reject_review_belief(conn, belief_id, actor="test", note="superseded by correction")
    assert rejected.action_status == "applied"
    assert (
        conn.execute(
            "SELECT count(*) FROM current_beliefs WHERE id = %s",
            (belief_id,),
        ).fetchone()[0]
        == 0
    )


def test_promote_to_pinned_is_idempotent_and_refreshes_review_queue(conn):
    belief_id = insert_candidate_belief(conn)

    refresh_current_beliefs(conn)
    promoted = promote_to_pinned(conn, belief_id, actor="test", note="always include")

    assert promoted.action_status == "applied"
    assert promoted.changed is True
    assert conn.execute(
        "SELECT actor FROM pinned_beliefs WHERE belief_id = %s",
        (belief_id,),
    ).fetchone() == ("test",)
    assert conn.execute(
        "SELECT status FROM current_beliefs WHERE id = %s",
        (belief_id,),
    ).fetchone() == ("accepted",)
    assert conn.execute("SELECT count(*) FROM belief_review_queue").fetchone()[0] == 0

    repeated = promote_to_pinned(conn, belief_id, actor="test")

    assert repeated.action_status == "recorded"
    assert repeated.changed is False
    assert conn.execute(
        "SELECT count(*) FROM pinned_beliefs WHERE belief_id = %s",
        (belief_id,),
    ).fetchone()[0] == 1


def test_deterministic_entity_build_is_idempotent_and_queryable(conn):
    insert_candidate_belief(conn)
    refresh_current_beliefs(conn)

    first = build_deterministic_entities(conn, limit=10)
    assert first.beliefs_processed == 1
    assert first.entities_created == 2
    assert first.entities_reused == 0
    assert first.edges_created == 1
    assert first.edges_reused == 0

    second = build_deterministic_entities(conn, limit=10)
    assert second.beliefs_processed == 1
    assert second.entities_created == 0
    assert second.entities_reused == 2
    assert second.edges_created == 0
    assert second.edges_reused == 1

    subject_entity_id = conn.execute(
        """
        SELECT id::text
        FROM entities
        WHERE canonical_key = 'subject:user'
          AND status = 'active'
        """
    ).fetchone()[0]
    neighborhood = entity_neighborhood(conn, subject_entity_id, max_depth=2)
    assert len(neighborhood) == 1
    assert neighborhood[0].depth == 1


def test_phase4_smoke_runs_bounded_local_pipeline(conn):
    insert_candidate_belief(conn)

    result = run_phase4_smoke(conn, limit=25)

    assert result.current_beliefs == 1
    assert result.review_queue_items == 1
    assert result.beliefs_processed == 1
    assert result.entities_created == 2
    assert result.edges_created == 1
    assert result.neighborhood_rows == 1
