"""Schema-level tests for the RFC 0018 audit cascade tables.

Reviewer/LLM-calling code is out of scope. These tests exercise the
migration's tables, constraints, and triggers in isolation.
"""

from __future__ import annotations

import uuid

import pytest
from psycopg.errors import (
    CheckViolation,
    ForeignKeyViolation,
    RaiseException,
)
from psycopg.types.json import Jsonb

from engram.extractor import (
    EXTRACTION_PROMPT_VERSION,
    EXTRACTION_REQUEST_PROFILE_VERSION,
)
from test_phase2_segments import (
    insert_conversation,
    insert_generation,
    insert_segment_row,
)


EXPECTED_REASONS: dict[str, int] = {
    "trace_broken": 1,
    "trace_partial": 1,
    "class_overclaim": 1,
    "class_underclaim": 1,
    "predicate_misrouted": 1,
    "scope_inflated": 1,
    "confidence_inflated": 1,
    "evidence_synthesized": 1,
    "value_mismatch": 2,
    "numerical_mismatch": 3,
    "cite_invalid": 3,
    "cite_misapplied": 3,
    "privacy_tier_leak": 3,
}

EXPECTED_PRECLUDES: set[str] = {
    "trace_broken",
    "evidence_synthesized",
    "predicate_misrouted",
}


def _seed_claim(conn) -> str:
    """Insert a real claim and return its id as a string."""
    conv_id, msg_ids = insert_conversation(conn, [("user", "I drive a Subaru", 1)])
    gen_id = insert_generation(conn, conv_id)
    seg_id = insert_segment_row(conn, gen_id, conv_id, msg_ids, active=True)
    extraction_id = conn.execute(
        """
        INSERT INTO claim_extractions (
            segment_id,
            generation_id,
            extraction_prompt_version,
            extraction_model_version,
            request_profile_version,
            status,
            claim_count,
            completed_at,
            raw_payload
        )
        VALUES (%s, %s, %s, %s, %s, 'extracted', 1, now(), %s)
        RETURNING id::text
        """,
        (
            seg_id,
            gen_id,
            EXTRACTION_PROMPT_VERSION,
            "model-a",
            EXTRACTION_REQUEST_PROFILE_VERSION,
            Jsonb({"model_response": '{"claims":[]}', "dropped_claims": []}),
        ),
    ).fetchone()[0]
    claim_id = conn.execute(
        """
        INSERT INTO claims (
            segment_id,
            generation_id,
            conversation_id,
            extraction_id,
            subject_text,
            predicate,
            object_text,
            stability_class,
            confidence,
            evidence_message_ids,
            extraction_prompt_version,
            extraction_model_version,
            request_profile_version,
            privacy_tier,
            raw_payload
        )
        VALUES (%s, %s, %s, %s, 'user', 'drives', 'Subaru', 'preference', 0.9,
                %s::uuid[], %s, %s, %s, 1, %s)
        RETURNING id::text
        """,
        (
            seg_id,
            gen_id,
            conv_id,
            extraction_id,
            [msg_ids[0]],
            EXTRACTION_PROMPT_VERSION,
            "model-a",
            EXTRACTION_REQUEST_PROFILE_VERSION,
            Jsonb({"rationale": "fixture"}),
        ),
    ).fetchone()[0]
    return claim_id


def test_audit_reason_vocabulary_seeded_with_thirteen_rows(conn) -> None:
    rows = conn.execute(
        "SELECT reason, stage FROM audit_reason_vocabulary ORDER BY reason"
    ).fetchall()
    assert len(rows) == 13
    seeded = {reason: stage for reason, stage in rows}
    assert seeded == EXPECTED_REASONS


def test_precludes_supported_set_matches_d070(conn) -> None:
    rows = conn.execute(
        "SELECT reason FROM audit_reason_vocabulary WHERE precludes_supported = TRUE"
    ).fetchall()
    actual = {row[0] for row in rows}
    assert actual == EXPECTED_PRECLUDES


def test_stage1_supported_verdict_rejected(conn) -> None:
    claim_id = _seed_claim(conn)
    with pytest.raises(CheckViolation):
        conn.execute(
            """
            INSERT INTO claim_audits (
                claim_id, stage, verdict, audit_reasons,
                auditor_model_version, auditor_prompt_version
            )
            VALUES (%s, 1, 'supported', '{}', 'aud-m', 'aud-p')
            """,
            (claim_id,),
        )


def test_stage2_null_verdict_rejected(conn) -> None:
    claim_id = _seed_claim(conn)
    with pytest.raises(CheckViolation):
        conn.execute(
            """
            INSERT INTO claim_audits (
                claim_id, stage, verdict, audit_reasons,
                auditor_model_version, auditor_prompt_version
            )
            VALUES (%s, 2, NULL, '{}', 'aud-m', 'aud-p')
            """,
            (claim_id,),
        )


def test_unknown_audit_reason_rejected(conn) -> None:
    claim_id = _seed_claim(conn)
    with pytest.raises(ForeignKeyViolation):
        conn.execute(
            """
            INSERT INTO claim_audits (
                claim_id, stage, verdict, audit_reasons,
                auditor_model_version, auditor_prompt_version
            )
            VALUES (%s, 1, NULL, %s::text[], 'aud-m', 'aud-p')
            """,
            (claim_id, ["totally_made_up_reason"]),
        )


def test_stage2_only_reason_on_stage1_row_rejected(conn) -> None:
    claim_id = _seed_claim(conn)
    with pytest.raises(CheckViolation):
        conn.execute(
            """
            INSERT INTO claim_audits (
                claim_id, stage, verdict, audit_reasons,
                auditor_model_version, auditor_prompt_version
            )
            VALUES (%s, 1, NULL, %s::text[], 'aud-m', 'aud-p')
            """,
            (claim_id, ["value_mismatch"]),
        )


def test_claim_audits_update_rejected(conn) -> None:
    claim_id = _seed_claim(conn)
    audit_id = conn.execute(
        """
        INSERT INTO claim_audits (
            claim_id, stage, verdict, audit_reasons,
            auditor_model_version, auditor_prompt_version
        )
        VALUES (%s, 1, NULL, %s::text[], 'aud-m', 'aud-p')
        RETURNING id::text
        """,
        (claim_id, ["trace_partial"]),
    ).fetchone()[0]
    with pytest.raises(RaiseException):
        conn.execute(
            "UPDATE claim_audits SET auditor_model_version = 'aud-m2' WHERE id = %s",
            (audit_id,),
        )


def test_claim_audits_delete_rejected(conn) -> None:
    claim_id = _seed_claim(conn)
    conn.execute(
        """
        INSERT INTO claim_audits (
            claim_id, stage, verdict, audit_reasons,
            auditor_model_version, auditor_prompt_version
        )
        VALUES (%s, 1, NULL, %s::text[], 'aud-m', 'aud-p')
        """,
        (claim_id, ["trace_partial"]),
    )
    with pytest.raises(RaiseException):
        conn.execute("DELETE FROM claim_audits WHERE claim_id = %s", (claim_id,))


def test_projection_audit_requires_citations(conn) -> None:
    with pytest.raises(CheckViolation):
        conn.execute(
            """
            INSERT INTO projection_audits (
                projection_kind, projection_ref, cited_claim_ids,
                verdict, audit_reasons,
                auditor_model_version, auditor_prompt_version
            )
            VALUES ('context_for', 'ref-1', %s::uuid[], 'clean', '{}', 'aud-m', 'aud-p')
            """,
            ([],),
        )


def test_projection_audit_accepts_stage3_reason(conn) -> None:
    claim_id = _seed_claim(conn)
    audit_id = conn.execute(
        """
        INSERT INTO projection_audits (
            projection_kind, projection_ref, cited_claim_ids,
            verdict, audit_reasons,
            auditor_model_version, auditor_prompt_version
        )
        VALUES ('context_for', 'ref-1', %s::uuid[], 'failed', %s::text[],
                'aud-m', 'aud-p')
        RETURNING id::text
        """,
        ([claim_id], ["cite_invalid"]),
    ).fetchone()[0]
    assert audit_id


def test_projection_audits_update_and_delete_rejected(conn) -> None:
    claim_id = _seed_claim(conn)
    audit_id = conn.execute(
        """
        INSERT INTO projection_audits (
            projection_kind, projection_ref, cited_claim_ids,
            verdict, audit_reasons,
            auditor_model_version, auditor_prompt_version
        )
        VALUES ('context_for', 'ref-1', %s::uuid[], 'clean', '{}', 'aud-m', 'aud-p')
        RETURNING id::text
        """,
        ([claim_id],),
    ).fetchone()[0]
    with pytest.raises(RaiseException):
        conn.execute(
            "UPDATE projection_audits SET verdict = 'failed' WHERE id = %s",
            (audit_id,),
        )
    with pytest.raises(RaiseException):
        conn.execute(
            "DELETE FROM projection_audits WHERE id = %s",
            (audit_id,),
        )


def test_claim_audit_unknown_claim_id_rejected(conn) -> None:
    fake_claim_id = str(uuid.uuid4())
    with pytest.raises(ForeignKeyViolation):
        conn.execute(
            """
            INSERT INTO claim_audits (
                claim_id, stage, verdict, audit_reasons,
                auditor_model_version, auditor_prompt_version
            )
            VALUES (%s, 1, NULL, %s::text[], 'aud-m', 'aud-p')
            """,
            (fake_claim_id, ["trace_partial"]),
        )


def test_audit_reasons_gin_lookup(conn) -> None:
    claim_id = _seed_claim(conn)
    conn.execute(
        """
        INSERT INTO claim_audits (
            claim_id, stage, verdict, audit_reasons,
            auditor_model_version, auditor_prompt_version
        )
        VALUES (%s, 1, NULL, %s::text[], 'aud-m', 'aud-p')
        """,
        (claim_id, ["trace_broken", "scope_inflated"]),
    )
    rows = conn.execute(
        """
        SELECT count(*) FROM claim_audits
        WHERE audit_reasons @> %s::text[]
        """,
        (["trace_broken"],),
    ).fetchone()
    assert rows[0] == 1


def test_latest_audit_per_claim_stage(conn) -> None:
    claim_id = _seed_claim(conn)
    first = conn.execute(
        """
        INSERT INTO claim_audits (
            claim_id, stage, verdict, audit_reasons,
            auditor_model_version, auditor_prompt_version,
            audited_at
        )
        VALUES (%s, 2, 'partial', %s::text[], 'aud-m', 'aud-p',
                '2026-01-01T00:00:00Z')
        RETURNING id::text
        """,
        (claim_id, ["value_mismatch"]),
    ).fetchone()[0]
    second = conn.execute(
        """
        INSERT INTO claim_audits (
            claim_id, stage, verdict, audit_reasons,
            auditor_model_version, auditor_prompt_version,
            audited_at
        )
        VALUES (%s, 2, 'invalidated', %s::text[], 'aud-m2', 'aud-p',
                '2026-03-01T00:00:00Z')
        RETURNING id::text
        """,
        (claim_id, ["value_mismatch"]),
    ).fetchone()[0]
    latest = conn.execute(
        """
        SELECT id::text FROM claim_audits
        WHERE claim_id = %s AND stage = 2
        ORDER BY audited_at DESC
        LIMIT 1
        """,
        (claim_id,),
    ).fetchone()[0]
    assert latest == second
    assert latest != first


def test_vocabulary_is_user_extensible_at_sql_layer(conn) -> None:
    """D073 governs vocabulary growth at the RFC/process level. The SQL
    layer remains permissive: a new reason can be inserted directly,
    matching D057's pattern for predicate_vocabulary.
    """
    conn.execute(
        """
        INSERT INTO audit_reason_vocabulary (reason, stage, description, precludes_supported)
        VALUES ('test_only_reason_xyz', 2, 'Hypothetical Stage 2 reason for tests.', FALSE)
        """,
    )
    row = conn.execute(
        "SELECT stage FROM audit_reason_vocabulary WHERE reason = 'test_only_reason_xyz'"
    ).fetchone()
    assert row[0] == 2
    # And that the new vocabulary row is now usable as an audit reason.
    claim_id = _seed_claim(conn)
    conn.execute(
        """
        INSERT INTO claim_audits (
            claim_id, stage, verdict, audit_reasons,
            auditor_model_version, auditor_prompt_version
        )
        VALUES (%s, 2, 'partial', %s::text[], 'aud-m', 'aud-p')
        """,
        (claim_id, ["test_only_reason_xyz"]),
    )
