"""Schema-level tests for the RFC 0021 ``gold_labels`` migration.

Skipped automatically when ``ENGRAM_TEST_DATABASE_URL`` is unset (the conftest
``conn`` fixture handles that). Each test is independent and exercises one
trigger or constraint in isolation.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from psycopg import errors
from test_phase2_segments import insert_conversation, insert_generation, insert_segment_row
from test_phase3_claims_beliefs import insert_extracted_claim

from engram.consolidator import CONSOLIDATOR_MODEL_VERSION, CONSOLIDATOR_PROMPT_VERSION
from engram.consolidator.transitions import BeliefPayload, insert_belief
from engram.extractor import EXTRACTION_PROMPT_VERSION, EXTRACTION_REQUEST_PROFILE_VERSION
from engram.interview.errors import GoldLabelStorageError
from engram.interview.storage import (
    get_active_learning_signal_version,
    insert_label,
    insert_active_learning_event,
    insert_session,
    insert_session_targets,
    list_session_targets,
    list_sessions,
    mark_session_completed,
    session_target_to_sampled,
    unanswered_session_targets,
)
from engram.interview.sampler import SampledTarget


def _exec_translated(conn, sql, params=()):  # type: ignore[no-untyped-def]
    """Run SQL and translate ``P0001`` raises into ``GoldLabelStorageError``."""
    try:
        return conn.execute(sql, params)
    except errors.RaiseException as exc:
        raise GoldLabelStorageError(str(exc).strip()) from exc


CLAIM_VERSION_TRIPLE = {
    "extraction_prompt_version": EXTRACTION_PROMPT_VERSION,
    "extraction_model_version": "model-a",
    "request_profile_version": EXTRACTION_REQUEST_PROFILE_VERSION,
}

BELIEF_VERSION_TRIPLE = {
    "consolidation_prompt_version": CONSOLIDATOR_PROMPT_VERSION,
    "consolidation_model_version": CONSOLIDATOR_MODEL_VERSION,
    "request_profile_version": "interview.v1.d079.initial",
}


def _seed_claim(conn) -> str:
    conv_id, msg_ids = insert_conversation(conn, [("user", "I drive a Subaru", 1)])
    gen_id = insert_generation(conn, conv_id)
    seg_id = insert_segment_row(conn, gen_id, conv_id, msg_ids, active=True)
    _, claim_id = insert_extracted_claim(
        conn,
        segment_id=seg_id,
        generation_id=gen_id,
        conversation_id=conv_id,
        evidence_ids=msg_ids,
        predicate="drives",
        object_text="Subaru",
    )
    return claim_id


def _seed_belief(conn, *, privacy_tier: int = 1) -> str:
    conv_id, msg_ids = insert_conversation(conn, [("user", "I prefer vim", 1)])
    gen_id = insert_generation(conn, conv_id)
    seg_id = insert_segment_row(conn, gen_id, conv_id, msg_ids, active=True)
    _, claim_id = insert_extracted_claim(
        conn,
        segment_id=seg_id,
        generation_id=gen_id,
        conversation_id=conv_id,
        evidence_ids=msg_ids,
        predicate="prefers",
        object_text="vim",
    )
    payload = BeliefPayload(
        subject_text="user",
        predicate="prefers",
        object_text="vim",
        object_json=None,
        valid_from=datetime.now(timezone.utc),
        valid_to=None,
        observed_at=datetime.now(timezone.utc),
        extracted_at=datetime.now(timezone.utc),
        status="candidate",
        confidence=0.7,
        evidence_ids=[msg_ids[0]],
        claim_ids=[claim_id],
        prompt_version=BELIEF_VERSION_TRIPLE["consolidation_prompt_version"],
        model_version=BELIEF_VERSION_TRIPLE["consolidation_model_version"],
        privacy_tier=privacy_tier,
        raw_payload={"source": "rfc0021-storage-test"},
        score_breakdown={"mean": 0.7, "max": 0.7, "min": 0.7, "count": 1, "stddev": 0},
    )
    return insert_belief(conn, payload)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _sampled_claim_target(claim_id: str, *, active_signal: str | None = None) -> SampledTarget:
    return SampledTarget(
        target_kind="claim",
        target_id=claim_id,
        stability_class="preference",
        confidence=0.7,
        observed_at=_now(),
        conf_band="0.6-0.8",
        recency_band="<7d",
        belief_status=None,
        candidate_pool_snapshot_id=str(uuid.uuid4()),
        active_learning_signal_version=active_signal,
        extraction_prompt_version=CLAIM_VERSION_TRIPLE["extraction_prompt_version"],
        extraction_model_version=CLAIM_VERSION_TRIPLE["extraction_model_version"],
        consolidation_prompt_version=None,
        consolidation_model_version=None,
        request_profile_version=CLAIM_VERSION_TRIPLE["request_profile_version"],
    )


def test_session_and_label_happy_path(conn) -> None:
    claim_id = _seed_claim(conn)
    session_id = insert_session(
        conn,
        seed=42,
        sampler_id="stratified",
        sampler_version="stratified.v1.d079.initial",
        strata_weights={"stability_class": 1.0},
        operator_note="rfc0021 happy path",
    )

    asked = _now()
    label_id = insert_label(
        conn,
        session_id=session_id,
        target_kind="claim",
        target_id=claim_id,
        version_triple=CLAIM_VERSION_TRIPLE,
        prompt_template_version="interview.claim.v1.d079.initial",
        prompt_template_path="prompts/interview/claim_v1.md",
        prompt_text="Q: Is this an accurate paraphrase of your situation?",
        verdict="true",
        rationale="seed test",
        sampler_id="stratified",
        sampler_version="stratified.v1.d079.initial",
        candidate_pool_snapshot_id=str(uuid.uuid4()),
        active_learning_signal_version=None,
        stability_class="preference",
        conf_band="0.6-0.8",
        recency_band="<7d",
        belief_status=None,
        asked_at=asked,
        answered_at=asked,
    )

    row = conn.execute(
        "SELECT verdict, privacy_tier, target_kind FROM gold_labels WHERE id = %s",
        (label_id,),
    ).fetchone()
    assert row == ("true", 1, "claim")

    mark_session_completed(conn, session_id)
    completed = conn.execute(
        "SELECT completed_at FROM gold_label_sessions WHERE session_id = %s",
        (session_id,),
    ).fetchone()
    assert completed[0] is not None


def test_label_update_is_blocked_by_append_only_trigger(conn) -> None:
    claim_id = _seed_claim(conn)
    session_id = insert_session(
        conn,
        seed=1,
        sampler_id="stratified",
        sampler_version="stratified.v1.d079.initial",
        strata_weights={},
    )
    label_id = insert_label(
        conn,
        session_id=session_id,
        target_kind="claim",
        target_id=claim_id,
        version_triple=CLAIM_VERSION_TRIPLE,
        prompt_template_version="interview.claim.v1.d079.initial",
        prompt_template_path="prompts/interview/claim_v1.md",
        prompt_text="Q",
        verdict="true",
        rationale=None,
        sampler_id="stratified",
        sampler_version="stratified.v1.d079.initial",
        candidate_pool_snapshot_id=str(uuid.uuid4()),
        active_learning_signal_version=None,
        stability_class="preference",
        conf_band="0.6-0.8",
        recency_band="<7d",
        belief_status=None,
        asked_at=_now(),
        answered_at=_now(),
    )

    with pytest.raises(GoldLabelStorageError, match="append-only"):
        _exec_translated(
            conn,
            "UPDATE gold_labels SET rationale = 'x' WHERE id = %s",
            (label_id,),
        )


def test_label_delete_is_blocked_by_append_only_trigger(conn) -> None:
    claim_id = _seed_claim(conn)
    session_id = insert_session(
        conn,
        seed=2,
        sampler_id="stratified",
        sampler_version="stratified.v1.d079.initial",
        strata_weights={},
    )
    insert_label(
        conn,
        session_id=session_id,
        target_kind="claim",
        target_id=claim_id,
        version_triple=CLAIM_VERSION_TRIPLE,
        prompt_template_version="interview.claim.v1.d079.initial",
        prompt_template_path="prompts/interview/claim_v1.md",
        prompt_text="Q",
        verdict="false",
        rationale=None,
        sampler_id="stratified",
        sampler_version="stratified.v1.d079.initial",
        candidate_pool_snapshot_id=str(uuid.uuid4()),
        active_learning_signal_version=None,
        stability_class="preference",
        conf_band="0.6-0.8",
        recency_band="<7d",
        belief_status=None,
        asked_at=_now(),
        answered_at=_now(),
    )
    with pytest.raises(GoldLabelStorageError, match="append-only"):
        _exec_translated(conn, "DELETE FROM gold_labels")


def test_dangling_target_id_is_rejected(conn) -> None:
    session_id = insert_session(
        conn,
        seed=3,
        sampler_id="stratified",
        sampler_version="stratified.v1.d079.initial",
        strata_weights={},
    )
    bogus_target = str(uuid.uuid4())
    with pytest.raises(GoldLabelStorageError, match="not found in claims"):
        insert_label(
            conn,
            session_id=session_id,
            target_kind="claim",
            target_id=bogus_target,
            version_triple=CLAIM_VERSION_TRIPLE,
            prompt_template_version="interview.claim.v1.d079.initial",
            prompt_template_path="prompts/interview/claim_v1.md",
            prompt_text="Q",
            verdict="true",
            rationale=None,
            sampler_id="stratified",
            sampler_version="stratified.v1.d079.initial",
            candidate_pool_snapshot_id=str(uuid.uuid4()),
            active_learning_signal_version=None,
            stability_class="preference",
            conf_band="0.6-0.8",
            recency_band="<7d",
            belief_status=None,
            asked_at=_now(),
            answered_at=_now(),
        )


def test_privacy_tier_mismatch_with_parent_is_rejected(conn) -> None:
    claim_id = _seed_claim(conn)  # privacy_tier=1 by fixture
    session_id = insert_session(
        conn,
        seed=4,
        sampler_id="stratified",
        sampler_version="stratified.v1.d079.initial",
        strata_weights={},
    )
    with pytest.raises(GoldLabelStorageError, match="disagrees with parent"):
        insert_label(
            conn,
            session_id=session_id,
            target_kind="claim",
            target_id=claim_id,
            version_triple=CLAIM_VERSION_TRIPLE,
            prompt_template_version="interview.claim.v1.d079.initial",
            prompt_template_path="prompts/interview/claim_v1.md",
            prompt_text="Q",
            verdict="true",
            rationale=None,
            sampler_id="stratified",
            sampler_version="stratified.v1.d079.initial",
            candidate_pool_snapshot_id=str(uuid.uuid4()),
            active_learning_signal_version=None,
            stability_class="preference",
            conf_band="0.6-0.8",
            recency_band="<7d",
            belief_status=None,
            asked_at=_now(),
            answered_at=_now(),
            privacy_tier=2,
        )


def test_current_gold_label_returns_latest_per_version_triple(conn) -> None:
    claim_id = _seed_claim(conn)
    session_id = insert_session(
        conn,
        seed=5,
        sampler_id="stratified",
        sampler_version="stratified.v1.d079.initial",
        strata_weights={},
    )
    older = _now() - timedelta(hours=2)
    newer = _now()
    insert_label(
        conn,
        session_id=session_id,
        target_kind="claim",
        target_id=claim_id,
        version_triple=CLAIM_VERSION_TRIPLE,
        prompt_template_version="interview.claim.v1.d079.initial",
        prompt_template_path="prompts/interview/claim_v1.md",
        prompt_text="Q",
        verdict="false",
        rationale=None,
        sampler_id="stratified",
        sampler_version="stratified.v1.d079.initial",
        candidate_pool_snapshot_id=str(uuid.uuid4()),
        active_learning_signal_version=None,
        stability_class="preference",
        conf_band="0.6-0.8",
        recency_band="<7d",
        belief_status=None,
        asked_at=older,
        answered_at=older,
    )
    insert_label(
        conn,
        session_id=session_id,
        target_kind="claim",
        target_id=claim_id,
        version_triple=CLAIM_VERSION_TRIPLE,
        prompt_template_version="interview.claim.v1.d079.initial",
        prompt_template_path="prompts/interview/claim_v1.md",
        prompt_text="Q",
        verdict="true",
        rationale=None,
        sampler_id="stratified",
        sampler_version="stratified.v1.d079.initial",
        candidate_pool_snapshot_id=str(uuid.uuid4()),
        active_learning_signal_version=None,
        stability_class="preference",
        conf_band="0.6-0.8",
        recency_band="<7d",
        belief_status=None,
        asked_at=newer,
        answered_at=newer,
    )
    row = conn.execute(
        "SELECT verdict FROM current_gold_label WHERE target_id = %s",
        (claim_id,),
    ).fetchone()
    assert row == ("true",)


def test_list_sessions_filters_by_state(conn) -> None:
    open_id = insert_session(
        conn,
        seed=6,
        sampler_id="stratified",
        sampler_version="stratified.v1.d079.initial",
        strata_weights={},
    )
    closed_id = insert_session(
        conn,
        seed=7,
        sampler_id="stratified",
        sampler_version="stratified.v1.d079.initial",
        strata_weights={},
    )
    mark_session_completed(conn, closed_id)
    open_sessions = list_sessions(conn, state="open")
    completed_sessions = list_sessions(conn, state="completed")
    open_ids = {s.session_id for s in open_sessions}
    completed_ids = {s.session_id for s in completed_sessions}
    assert open_id in open_ids
    assert closed_id in completed_ids
    assert open_id not in completed_ids


def test_active_learning_event_latest_lookup_and_append_only(conn) -> None:
    assert get_active_learning_signal_version(conn) is None
    first = insert_active_learning_event(conn, signal_version="rfc0018.reviewer.v1")
    second = insert_active_learning_event(conn, signal_version="rfc0018.reviewer.v2")
    assert first != second
    assert get_active_learning_signal_version(conn) == "rfc0018.reviewer.v2"

    with pytest.raises(GoldLabelStorageError, match="append-only"):
        _exec_translated(
            conn,
            "UPDATE gold_label_active_learning_events SET signal_version = 'changed'",
        )


def test_session_targets_round_trip_preserves_active_signal_and_confidence(conn) -> None:
    claim_id = _seed_claim(conn)
    session_id = insert_session(
        conn,
        seed=8,
        sampler_id="stratified",
        sampler_version="stratified.v1.d079.initial",
        strata_weights={"stability_class": "preference"},
    )
    sampled = _sampled_claim_target(claim_id, active_signal="rfc0018.reviewer.v1")
    insert_session_targets(conn, session_id=session_id, sampled=[sampled])

    targets = list_session_targets(conn, session_id=session_id)
    assert len(targets) == 1
    target = targets[0]
    assert target.active_learning_signal_version == "rfc0018.reviewer.v1"
    assert target.confidence == 0.7
    assert target.observed_at == sampled.observed_at

    reconstructed = session_target_to_sampled(target)
    assert reconstructed.active_learning_signal_version == "rfc0018.reviewer.v1"
    assert reconstructed.confidence == 0.7
    assert reconstructed.observed_at == sampled.observed_at


def test_unanswered_session_targets_skip_recorded_version(conn) -> None:
    claim_id = _seed_claim(conn)
    session_id = insert_session(
        conn,
        seed=9,
        sampler_id="stratified",
        sampler_version="stratified.v1.d079.initial",
        strata_weights={},
    )
    sampled = _sampled_claim_target(claim_id)
    insert_session_targets(conn, session_id=session_id, sampled=[sampled])
    assert len(unanswered_session_targets(conn, session_id=session_id)) == 1

    insert_label(
        conn,
        session_id=session_id,
        target_kind="claim",
        target_id=claim_id,
        version_triple=CLAIM_VERSION_TRIPLE,
        prompt_template_version="interview.claim.v1.d079.initial",
        prompt_template_path="prompts/interview/claim_v1.md",
        prompt_text="Q",
        verdict="true",
        rationale=None,
        sampler_id="stratified",
        sampler_version="stratified.v1.d079.initial",
        candidate_pool_snapshot_id=sampled.candidate_pool_snapshot_id,
        active_learning_signal_version=None,
        stability_class="preference",
        conf_band="0.6-0.8",
        recency_band="<7d",
        belief_status=None,
        asked_at=_now(),
        answered_at=_now(),
    )
    assert unanswered_session_targets(conn, session_id=session_id) == []
