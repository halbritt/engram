from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

import psycopg
from psycopg.types.json import Jsonb


CONSOLIDATOR_PROMPT_VERSION = "consolidator.v1.d048-d058.transition-api"
CONSOLIDATOR_MODEL_VERSION = "consolidator.v1.d048-d058.transition-api"


@dataclass(frozen=True)
class BeliefPayload:
    subject_text: str
    predicate: str
    object_text: str | None
    object_json: dict[str, Any] | None
    valid_from: Any
    valid_to: Any | None
    observed_at: Any
    extracted_at: Any
    status: str
    confidence: float
    evidence_ids: list[str]
    claim_ids: list[str]
    prompt_version: str
    model_version: str
    privacy_tier: int
    raw_payload: dict[str, Any]
    score_breakdown: dict[str, Any]


def insert_belief(
    conn: psycopg.Connection,
    payload: BeliefPayload,
    *,
    request_uuid: str | None = None,
) -> str:
    request_uuid = request_uuid or str(uuid.uuid4())
    with conn.transaction():
        _set_transition_request(conn, request_uuid)
        belief_id = _insert_belief_row(conn, payload)
        _insert_audit(
            conn,
            belief_id=belief_id,
            transition_kind="insert",
            previous_status=None,
            new_status=payload.status,
            previous_valid_to=None,
            new_valid_to=payload.valid_to,
            prompt_version=payload.prompt_version,
            model_version=payload.model_version,
            input_claim_ids=payload.claim_ids,
            evidence_message_ids=payload.evidence_ids,
            score_breakdown=payload.score_breakdown,
            request_uuid=request_uuid,
        )
    return belief_id


def supersede_belief(
    conn: psycopg.Connection,
    prior_id: str,
    new_belief_payload: BeliefPayload,
    *,
    request_uuid: str | None = None,
) -> str:
    request_uuid = request_uuid or str(uuid.uuid4())
    with conn.transaction():
        _set_transition_request(conn, request_uuid)
        prior = _fetch_belief_for_update(conn, prior_id)
        conn.execute(
            """
            UPDATE beliefs
            SET status = 'superseded',
                closed_at = now()
            WHERE id = %s
            """,
            (prior_id,),
        )
        new_id = _insert_belief_row(conn, new_belief_payload)
        conn.execute(
            """
            UPDATE beliefs
            SET superseded_by = %s
            WHERE id = %s
            """,
            (new_id, prior_id),
        )
        _insert_audit(
            conn,
            belief_id=prior_id,
            transition_kind="supersede",
            previous_status=prior["status"],
            new_status="superseded",
            previous_valid_to=prior["valid_to"],
            new_valid_to=prior["valid_to"],
            prompt_version=new_belief_payload.prompt_version,
            model_version=new_belief_payload.model_version,
            input_claim_ids=new_belief_payload.claim_ids,
            evidence_message_ids=new_belief_payload.evidence_ids,
            score_breakdown=new_belief_payload.score_breakdown,
            request_uuid=request_uuid,
        )
    return new_id


def close_belief(
    conn: psycopg.Connection,
    prior_id: str,
    reason: dict[str, Any] | str,
    *,
    valid_to: Any | None = None,
    request_uuid: str | None = None,
    prompt_version: str = CONSOLIDATOR_PROMPT_VERSION,
    model_version: str = CONSOLIDATOR_MODEL_VERSION,
    transition_kind: str = "close",
) -> None:
    request_uuid = request_uuid or str(uuid.uuid4())
    score_breakdown = reason if isinstance(reason, dict) else {"cause": reason}
    with conn.transaction():
        _set_transition_request(conn, request_uuid)
        prior = _fetch_belief_for_update(conn, prior_id)
        conn.execute(
            """
            UPDATE beliefs
            SET valid_to = COALESCE(%s, valid_to),
                status = 'superseded',
                closed_at = now()
            WHERE id = %s
            """,
            (valid_to, prior_id),
        )
        _insert_audit(
            conn,
            belief_id=prior_id,
            transition_kind=transition_kind,
            previous_status=prior["status"],
            new_status="superseded",
            previous_valid_to=prior["valid_to"],
            new_valid_to=valid_to if valid_to is not None else prior["valid_to"],
            prompt_version=prompt_version,
            model_version=model_version,
            input_claim_ids=prior["claim_ids"],
            evidence_message_ids=prior["evidence_ids"],
            score_breakdown=score_breakdown,
            request_uuid=request_uuid,
        )


def reject_belief(
    conn: psycopg.Connection,
    prior_id: str,
    cause: dict[str, Any] | str,
    *,
    request_uuid: str | None = None,
    prompt_version: str = CONSOLIDATOR_PROMPT_VERSION,
    model_version: str = CONSOLIDATOR_MODEL_VERSION,
) -> None:
    request_uuid = request_uuid or str(uuid.uuid4())
    score_breakdown = cause if isinstance(cause, dict) else {"cause": cause}
    with conn.transaction():
        _set_transition_request(conn, request_uuid)
        prior = _fetch_belief_for_update(conn, prior_id)
        conn.execute(
            """
            UPDATE beliefs
            SET status = 'rejected',
                closed_at = now()
            WHERE id = %s
            """,
            (prior_id,),
        )
        _insert_audit(
            conn,
            belief_id=prior_id,
            transition_kind="reject",
            previous_status=prior["status"],
            new_status="rejected",
            previous_valid_to=prior["valid_to"],
            new_valid_to=prior["valid_to"],
            prompt_version=prompt_version,
            model_version=model_version,
            input_claim_ids=prior["claim_ids"],
            evidence_message_ids=prior["evidence_ids"],
            score_breakdown=score_breakdown,
            request_uuid=request_uuid,
        )


def _set_transition_request(conn: psycopg.Connection, request_uuid: str) -> None:
    conn.execute("SELECT set_config('engram.transition_in_progress', %s, true)", (request_uuid,))


def _fetch_belief_for_update(conn: psycopg.Connection, belief_id: str) -> dict[str, Any]:
    row = conn.execute(
        """
        SELECT
            status,
            valid_to,
            evidence_ids::text[],
            claim_ids::text[]
        FROM beliefs
        WHERE id = %s
        FOR UPDATE
        """,
        (belief_id,),
    ).fetchone()
    if row is None:
        raise ValueError(f"belief not found: {belief_id}")
    return {
        "status": row[0],
        "valid_to": row[1],
        "evidence_ids": list(row[2]),
        "claim_ids": list(row[3]),
    }


def _insert_belief_row(conn: psycopg.Connection, payload: BeliefPayload) -> str:
    row = conn.execute(
        """
        INSERT INTO beliefs (
            subject_text,
            predicate,
            object_text,
            object_json,
            valid_from,
            valid_to,
            observed_at,
            extracted_at,
            status,
            confidence,
            evidence_ids,
            claim_ids,
            prompt_version,
            model_version,
            privacy_tier,
            raw_payload
        )
        VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
            %s::uuid[], %s::uuid[], %s, %s, %s, %s
        )
        RETURNING id::text
        """,
        (
            payload.subject_text,
            payload.predicate,
            payload.object_text,
            Jsonb(payload.object_json) if payload.object_json is not None else None,
            payload.valid_from,
            payload.valid_to,
            payload.observed_at,
            payload.extracted_at,
            payload.status,
            payload.confidence,
            payload.evidence_ids,
            payload.claim_ids,
            payload.prompt_version,
            payload.model_version,
            payload.privacy_tier,
            Jsonb(payload.raw_payload),
        ),
    ).fetchone()
    return row[0]


def _insert_audit(
    conn: psycopg.Connection,
    *,
    belief_id: str,
    transition_kind: str,
    previous_status: str | None,
    new_status: str,
    previous_valid_to: Any | None,
    new_valid_to: Any | None,
    prompt_version: str,
    model_version: str,
    input_claim_ids: list[str] | None,
    evidence_message_ids: list[str],
    score_breakdown: dict[str, Any],
    request_uuid: str,
) -> None:
    conn.execute(
        """
        INSERT INTO belief_audit (
            belief_id,
            transition_kind,
            previous_status,
            new_status,
            previous_valid_to,
            new_valid_to,
            prompt_version,
            model_version,
            input_claim_ids,
            evidence_message_ids,
            score_breakdown,
            request_uuid
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s::uuid[], %s::uuid[], %s, %s)
        """,
        (
            belief_id,
            transition_kind,
            previous_status,
            new_status,
            previous_valid_to,
            new_valid_to,
            prompt_version,
            model_version,
            input_claim_ids,
            evidence_message_ids,
            Jsonb(score_breakdown),
            request_uuid,
        ),
    )
