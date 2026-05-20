from __future__ import annotations

from datetime import UTC, datetime

from psycopg.types.json import Jsonb
from test_phase3_claims_beliefs import active_segment, insert_extracted_claim

from engram.consolidator import CONSOLIDATOR_MODEL_VERSION, CONSOLIDATOR_PROMPT_VERSION
from engram.consolidator.transitions import BeliefPayload, insert_belief
from engram.context import CONTEXT_COMPILER_VERSION, ContextForRequest, PersonalContextService
from engram.phase4 import promote_to_pinned, refresh_current_beliefs


def insert_context_belief(
    conn,
    *,
    message_text: str,
    predicate: str,
    object_text: str,
    status: str = "accepted",
    confidence: float = 0.9,
    privacy_tier: int = 1,
    sensitivity_class: str = "routine_project",
    claim_stability_class: str | None = None,
    valid_to: datetime | None = None,
    evidence_message_id: str | None = None,
) -> tuple[str, str, str]:
    conv_id, gen_id, seg_id, msg_ids = active_segment(conn, [("user", message_text, privacy_tier)])
    _, claim_id = insert_extracted_claim(
        conn,
        segment_id=seg_id,
        generation_id=gen_id,
        conversation_id=conv_id,
        evidence_ids=msg_ids,
        predicate=predicate,
        object_text=object_text,
        stability_class=claim_stability_class,
        confidence=confidence,
    )
    now = datetime.now(UTC)
    payload = BeliefPayload(
        subject_text="user",
        predicate=predicate,
        object_text=object_text,
        object_json=None,
        valid_from=now,
        valid_to=valid_to,
        observed_at=now,
        extracted_at=now,
        status=status,
        confidence=confidence,
        evidence_ids=[evidence_message_id or msg_ids[0]],
        claim_ids=[claim_id],
        prompt_version=CONSOLIDATOR_PROMPT_VERSION,
        model_version=CONSOLIDATOR_MODEL_VERSION,
        privacy_tier=privacy_tier,
        raw_payload={
            "source": "context-test",
            "sensitivity_class": sensitivity_class,
        },
        score_breakdown={
            "mean": confidence,
            "max": confidence,
            "min": confidence,
            "count": 1,
            "stddev": 0,
        },
    )
    return insert_belief(conn, payload), msg_ids[0], seg_id


def section_items(result, title: str) -> list[str]:
    for section in result.sections:
        if section.title == title:
            return list(section.items)
    return []


def insert_recent_capture(
    conn,
    content_text: str,
    *,
    privacy_tier: int = 1,
    raw_payload: dict[str, object] | None = None,
) -> str:
    source_id = conn.execute(
        """
        INSERT INTO sources (source_kind, external_id, raw_payload)
        VALUES ('capture', gen_random_uuid()::text, '{}')
        RETURNING id::text
        """
    ).fetchone()[0]
    return conn.execute(
        """
        INSERT INTO captures (
            source_id,
            source_kind,
            external_id,
            raw_payload,
            privacy_tier,
            capture_type,
            content_text,
            observed_at
        )
        VALUES (%s, 'capture', gen_random_uuid()::text, %s, %s, 'observation', %s, now())
        RETURNING id::text
        """,
        (source_id, Jsonb(raw_payload or {}), privacy_tier, content_text),
    ).fetchone()[0]


def insert_cross_tenant_message(conn, content_text: str) -> str:
    source_id = conn.execute(
        """
        INSERT INTO sources (
            source_kind,
            external_id,
            raw_payload,
            tenant_id,
            corpus_id
        )
        VALUES ('chatgpt', gen_random_uuid()::text, '{}', 'striatum', 'striatum')
        RETURNING id
        """
    ).fetchone()[0]
    conversation_id = conn.execute(
        """
        INSERT INTO conversations (
            source_id,
            source_kind,
            external_id,
            raw_payload,
            title,
            tenant_id,
            corpus_id
        )
        VALUES (%s, 'chatgpt', gen_random_uuid()::text, '{}', 'foreign', 'striatum', 'striatum')
        RETURNING id
        """,
        (source_id,),
    ).fetchone()[0]
    return conn.execute(
        """
        INSERT INTO messages (
            source_id,
            source_kind,
            conversation_id,
            external_id,
            raw_payload,
            role,
            content_text,
            sequence_index,
            tenant_id,
            corpus_id
        )
        VALUES (
            %s,
            'chatgpt',
            %s,
            gen_random_uuid()::text,
            %s,
            'user',
            %s,
            0,
            'striatum',
            'striatum'
        )
        RETURNING id::text
        """,
        (
            source_id,
            conversation_id,
            Jsonb({"private_raw_payload_marker": "do-not-cite"}),
            content_text,
        ),
    ).fetchone()[0]


def test_current_belief_is_included_with_citation(conn) -> None:
    belief_id, message_id, segment_id = insert_context_belief(
        conn,
        message_text="I prefer Postgres for local memory work.",
        predicate="prefers",
        object_text="Postgres",
        confidence=0.92,
    )
    refresh_current_beliefs(conn)

    result = PersonalContextService(conn).context_for(
        ContextForRequest(query_text="Postgres database", word_budget=120)
    )

    assert result.status == "ok"
    assert belief_id in result.source_belief_ids
    assert segment_id in result.source_segment_ids
    assert "Postgres" in "\n".join(section_items(result, "Relevant Beliefs"))
    assert "(conf=0.92, src=message:" in result.rendered_context
    assert result.citations[0].target_table == "messages"
    assert result.citations[0].target_id == message_id


def test_cold_context_compile_persists_snapshot_and_event(conn) -> None:
    belief_id, _message_id, segment_id = insert_context_belief(
        conn,
        message_text="SnapshotMarker should persist through context snapshots.",
        predicate="prefers",
        object_text="SnapshotMarker",
    )
    refresh_current_beliefs(conn)

    result = PersonalContextService(conn).context_for(
        ContextForRequest(query_text="SnapshotMarker", word_budget=120)
    )

    assert result.snapshot_id is not None
    assert result.memory_epoch is not None
    assert result.request_hash is not None
    row = conn.execute(
        """
        SELECT
            cs.memory_epoch,
            cs.compiler_version,
            cs.package_json->'snapshot_request'->>'request_hash',
            cs.rendered_text,
            cs.source_belief_ids,
            cs.source_segment_ids,
            me.event_type,
            me.aggregate_id::text
        FROM context_snapshots cs
        JOIN memory_events me ON me.memory_epoch = cs.memory_epoch
        WHERE cs.id = %s
        """,
        (result.snapshot_id,),
    ).fetchone()
    assert row is not None
    assert row[0] == result.memory_epoch
    assert row[1] == CONTEXT_COMPILER_VERSION
    assert row[2] == result.request_hash
    assert row[3] == result.rendered_context
    assert [str(value) for value in row[4]] == [belief_id]
    assert [str(value) for value in row[5]] == [segment_id]
    assert row[6] == "context_snapshot_refreshed"
    assert row[7] == result.snapshot_id


def test_warm_context_lookup_returns_matching_snapshot_without_new_row(conn) -> None:
    insert_context_belief(
        conn,
        message_text="WarmMarker should be served from a warm context snapshot.",
        predicate="prefers",
        object_text="WarmMarker",
    )
    refresh_current_beliefs(conn)
    service = PersonalContextService(conn)
    request = ContextForRequest(query_text="WarmMarker", word_budget=120)

    first = service.context_for(request)
    second = service.context_for(request)

    snapshot_count = conn.execute("SELECT count(*) FROM context_snapshots").fetchone()
    event_count = conn.execute(
        "SELECT count(*) FROM memory_events WHERE event_type = 'context_snapshot_refreshed'"
    ).fetchone()
    assert first.snapshot_id == second.snapshot_id
    assert first.memory_epoch == second.memory_epoch
    assert first.request_hash == second.request_hash
    assert second.rendered_context == first.rendered_context
    assert snapshot_count == (1,)
    assert event_count == (1,)


def test_pinned_belief_appears_in_standing_context_without_query_match(conn) -> None:
    belief_id, _message_id, _segment_id = insert_context_belief(
        conn,
        message_text="I require local-only memory operations.",
        predicate="prefers",
        object_text="local-only memory",
    )
    refresh_current_beliefs(conn)
    promote_to_pinned(conn, belief_id, actor="test")

    result = PersonalContextService(conn).context_for(
        ContextForRequest(query_text="unrelated assistant startup context", word_budget=120)
    )

    standing = "\n".join(section_items(result, "Standing Context"))
    assert "Pinned:" in standing
    assert "local-only memory" in standing
    assert result.status == "ok"


def test_stale_belief_is_historical_not_current(conn) -> None:
    insert_context_belief(
        conn,
        message_text="I used to drive a Volvo.",
        predicate="drives",
        object_text="Volvo",
        valid_to=datetime.now(UTC),
    )
    refresh_current_beliefs(conn)

    result = PersonalContextService(conn).context_for(
        ContextForRequest(query_text="Volvo driving", word_budget=120)
    )

    assert "Volvo" not in "\n".join(section_items(result, "Relevant Beliefs"))
    historical = "\n".join(section_items(result, "Uncertain / Conflicting"))
    assert "Historical, not current" in historical
    assert "Volvo" in historical


def test_no_data_emits_explicit_gap(conn) -> None:
    result = PersonalContextService(conn).context_for(
        ContextForRequest(query_text="favorite fictional database", word_budget=80)
    )

    assert result.status == "no_data"
    gaps = "\n".join(section_items(result, "Missing Data / Gaps"))
    assert "No matching personal memory found" in gaps
    assert result.omissions == ()


def test_policy_withheld_is_distinct_from_no_data(conn) -> None:
    insert_context_belief(
        conn,
        message_text="I prefer SecretDB for private work.",
        predicate="prefers",
        object_text="SecretDB",
        privacy_tier=2,
    )
    refresh_current_beliefs(conn)

    result = PersonalContextService(conn).context_for(
        ContextForRequest(
            query_text="SecretDB",
            word_budget=120,
            privacy_tier_ceiling=1,
        )
    )

    assert result.status == "withheld"
    assert "SecretDB" not in result.rendered_context
    assert "withheld by the requested privacy tier ceiling" in result.rendered_context
    assert [omission.reason for omission in result.omissions] == ["privacy_tier_exceeded"]
    assert [omission.policy_action for omission in result.omissions] == ["withhold"]


def test_sensitivity_withheld_is_distinct_from_privacy_tier_withheld(conn) -> None:
    insert_context_belief(
        conn,
        message_text="My health marker is ContextHealthMarker.",
        predicate="prefers",
        object_text="ContextHealthMarker",
        privacy_tier=1,
        sensitivity_class="health",
    )
    refresh_current_beliefs(conn)

    result = PersonalContextService(conn).context_for(
        ContextForRequest(query_text="ContextHealthMarker", word_budget=120)
    )

    assert result.status == "withheld"
    assert "ContextHealthMarker" not in result.rendered_context
    assert "withheld by context policy" in result.rendered_context
    assert [omission.reason for omission in result.omissions] == ["sensitivity_withheld"]
    assert [omission.sensitivity_class for omission in result.omissions] == ["health"]


def test_cite_only_sensitivity_renders_citation_without_body(conn) -> None:
    belief_id, message_id, _segment_id = insert_context_belief(
        conn,
        message_text="Third-party note says CiteOnlyMarker should not be body-rendered.",
        predicate="talked_about",
        object_text="CiteOnlyMarker",
        privacy_tier=1,
        sensitivity_class="third_party_communication",
    )
    refresh_current_beliefs(conn)

    result = PersonalContextService(conn).context_for(
        ContextForRequest(query_text="CiteOnlyMarker", word_budget=120)
    )

    assert result.status == "ok"
    assert belief_id in result.source_belief_ids
    assert "CiteOnlyMarker" not in result.rendered_context
    assert "Citation only: body withheld by sensitivity policy" in result.rendered_context
    assert "reason=sensitivity_cite_only" in result.rendered_context
    assert result.citations[0].target_id == message_id
    assert [omission.reason for omission in result.omissions] == ["sensitivity_cite_only"]
    assert [omission.policy_action for omission in result.omissions] == ["cite_only"]


def test_recent_capture_citation_does_not_include_raw_payload(conn) -> None:
    insert_recent_capture(
        conn,
        "PayloadMarker recent signal",
        raw_payload={"secret_payload_marker": "must-not-render"},
    )

    result = PersonalContextService(conn).context_for(
        ContextForRequest(query_text="PayloadMarker", word_budget=120)
    )

    assert result.status == "ok"
    assert "PayloadMarker recent signal" in result.rendered_context
    assert result.citations
    assert "secret_payload_marker" not in str(result.to_json())
    assert result.citations[0].provenance["target_table"] == "captures"


def test_belief_message_citation_is_tenant_scoped(conn) -> None:
    foreign_message_id = insert_cross_tenant_message(conn, "Foreign evidence")
    belief_id, _message_id, _segment_id = insert_context_belief(
        conn,
        message_text="ScopedCitationMarker is a personal belief.",
        predicate="prefers",
        object_text="ScopedCitationMarker",
        evidence_message_id=foreign_message_id,
    )
    refresh_current_beliefs(conn)

    result = PersonalContextService(conn).context_for(
        ContextForRequest(query_text="ScopedCitationMarker", word_budget=120)
    )

    assert result.status == "ok"
    assert "ScopedCitationMarker" in result.rendered_context
    assert result.citations == ()
    assert f"message:{foreign_message_id.split('-')[0]}" not in result.rendered_context
    assert f"belief:{belief_id.split('-')[0]}" in result.rendered_context


def test_word_budget_truncates_low_priority_recent_signal(conn) -> None:
    belief_id, _message_id, _segment_id = insert_context_belief(
        conn,
        message_text="Budget topic should remember the durable belief.",
        predicate="prefers",
        object_text="budget topic",
    )
    refresh_current_beliefs(conn)
    promote_to_pinned(conn, belief_id, actor="test")
    insert_recent_capture(
        conn,
        "budget topic "
        + " ".join(
            [
                "low-priority-recent-signal",
                "with",
                "enough",
                "extra",
                "words",
                "to",
                "exceed",
                "the",
                "remaining",
                "budget",
            ]
        ),
    )

    result = PersonalContextService(conn).context_for(
        ContextForRequest(query_text="budget topic", word_budget=16)
    )

    assert "budget topic" in "\n".join(section_items(result, "Standing Context"))
    assert "low-priority-recent-signal" not in result.rendered_context
    assert any(
        omission.reason == "over_budget" and omission.lane == "recent_signals"
        for omission in result.omissions
    )
    assert result.status == "partial"
