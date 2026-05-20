from __future__ import annotations

import json
from dataclasses import dataclass
from uuid import uuid4

import psycopg
from psycopg.types.json import Jsonb

from engram.claim_grounding_integration import emit_claim_grounding_requests_for_claims
from engram.extractor import EXTRACTION_REQUEST_PROFILE_VERSION


@dataclass(frozen=True)
class _Segment:
    id: str
    privacy_tier: int


@dataclass(frozen=True)
class _Claim:
    subject_text: str
    object_text: str | None
    object_json: object | None
    evidence_message_ids: list[str]


def test_extraction_grounding_sidecars_are_disabled_by_default(
    conn: psycopg.Connection,
) -> None:
    emitted = emit_claim_grounding_requests_for_claims(
        conn,
        extraction_id=str(uuid4()),
        segment=_Segment(id=str(uuid4()), privacy_tier=1),
        claims=[
            _Claim(
                subject_text="Atlas",
                object_text=None,
                object_json=None,
                evidence_message_ids=[str(uuid4())],
            )
        ],
        prompt_version="extractor.test",
        model_version="local.test",
    )

    assert emitted == ()
    assert conn.execute("SELECT count(*) FROM claim_grounding_requests").fetchone() == (0,)


def test_extraction_grounding_sidecars_emit_requests_without_raw_context(
    conn: psycopg.Connection,
) -> None:
    segment_id, extraction_id, message_id = _seed_extraction(conn)
    private_context = "private sentence around Atlas and PromptForge"

    emitted = emit_claim_grounding_requests_for_claims(
        conn,
        extraction_id=extraction_id,
        segment=_Segment(id=segment_id, privacy_tier=2),
        claims=[
            _Claim(
                subject_text="Atlas",
                object_text=None,
                object_json={"project": "PromptForge", "status": private_context},
                evidence_message_ids=[message_id],
            )
        ],
        prompt_version="extractor.test",
        model_version="local.test",
        requested_at="2026-05-18T00:00:00Z",
        enabled=True,
    )

    assert [(row.surface_form, row.mention_role) for row in emitted] == [
        ("Atlas", "subject"),
        ("PromptForge", "object"),
    ]

    request_rows = conn.execute(
        """
        SELECT surface_form, mention_role, request_payload
        FROM claim_grounding_requests
        ORDER BY created_at, id
        """
    ).fetchall()
    assert [(row[0], row[1]) for row in request_rows] == [
        ("Atlas", "subject"),
        ("PromptForge", "object"),
    ]
    serialized_payloads = json.dumps([row[2] for row in request_rows], sort_keys=True)
    assert private_context not in serialized_payloads
    assert "local_context_capsule" in serialized_payloads
    assert '"text": null' in serialized_payloads
    assert conn.execute("SELECT count(*) FROM claim_grounding_links").fetchone() == (2,)


def _seed_extraction(conn: psycopg.Connection) -> tuple[str, str, str]:
    source_id = conn.execute(
        """
        INSERT INTO sources (source_kind, external_id, raw_payload)
        VALUES ('chatgpt', %s, '{}'::jsonb)
        RETURNING id::text
        """,
        (f"source-{uuid4()}",),
    ).fetchone()[0]
    conversation_id = conn.execute(
        """
        INSERT INTO conversations (source_id, source_kind, external_id, raw_payload)
        VALUES (%s, 'chatgpt', %s, '{}'::jsonb)
        RETURNING id::text
        """,
        (source_id, f"conversation-{uuid4()}"),
    ).fetchone()[0]
    message_id = conn.execute(
        """
        INSERT INTO messages (
            source_id,
            source_kind,
            conversation_id,
            external_id,
            raw_payload,
            role,
            content_text,
            sequence_index
        )
        VALUES (%s, 'chatgpt', %s, %s, '{}'::jsonb, 'user', %s, 0)
        RETURNING id::text
        """,
        (
            source_id,
            conversation_id,
            f"message-{uuid4()}",
            "private sentence around Atlas and PromptForge",
        ),
    ).fetchone()[0]
    generation_id = conn.execute(
        """
        INSERT INTO segment_generations (
            parent_kind,
            parent_id,
            segmenter_prompt_version,
            segmenter_model_version,
            status
        )
        VALUES ('conversation', %s, 'segmenter.test', 'local.test', 'active')
        RETURNING id::text
        """,
        (conversation_id,),
    ).fetchone()[0]
    segment_id = conn.execute(
        """
        INSERT INTO segments (
            generation_id,
            source_id,
            source_kind,
            conversation_id,
            message_ids,
            sequence_index,
            content_text,
            segmenter_prompt_version,
            segmenter_model_version,
            is_active,
            privacy_tier,
            raw_payload
        )
        VALUES (
            %s,
            %s,
            'chatgpt',
            %s,
            ARRAY[%s::uuid],
            0,
            %s,
            'segmenter.test',
            'local.test',
            true,
            2,
            '{}'::jsonb
        )
        RETURNING id::text
        """,
        (
            generation_id,
            source_id,
            conversation_id,
            message_id,
            "private sentence around Atlas and PromptForge",
        ),
    ).fetchone()[0]
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
            raw_payload
        )
        VALUES (%s, %s, 'extractor.test', 'local.test', %s, 'extracting', 0, %s)
        RETURNING id::text
        """,
        (
            segment_id,
            generation_id,
            EXTRACTION_REQUEST_PROFILE_VERSION,
            Jsonb({"model_response": "{\"claims\":[]}"}),
        ),
    ).fetchone()[0]
    return segment_id, extraction_id, message_id
