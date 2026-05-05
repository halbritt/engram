from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from psycopg.errors import CheckViolation, RaiseException, UniqueViolation
from psycopg.types.json import Jsonb

import engram.consolidator as consolidator_module
from engram import cli, extractor
from engram.consolidator import (
    CONSOLIDATOR_MODEL_VERSION,
    CONSOLIDATOR_PROMPT_VERSION,
    active_beliefs_with_other_consolidator_version,
    apply_phase3_reclassification_invalidations,
    consolidate_beliefs,
    normalize_subject,
)
from engram.consolidator.transitions import BeliefPayload, insert_belief
from engram.extractor import (
    EXTRACTION_PROMPT_VERSION,
    EXTRACTION_REQUEST_PROFILE_VERSION,
    ClaimDraft,
    ExtractorModelOutput,
    ExtractorResponseError,
    extract_claims_from_segment,
    parse_extraction_response,
    reap_stale_extractions,
    run_extractor_health_smoke,
)
from test_phase2_segments import insert_conversation, insert_generation, insert_segment_row


class StaticExtractor:
    def __init__(self, drafts: list[ClaimDraft] | None = None) -> None:
        self.drafts = drafts if drafts is not None else []
        self.calls: list[dict] = []

    def extract(
        self,
        prompt: str,
        *,
        model_id: str,
        max_tokens: int,
        allowed_message_ids: list[str] | None = None,
        relaxed_schema: bool = False,
    ):
        self.calls.append(
            {
                "prompt": prompt,
                "model_id": model_id,
                "max_tokens": max_tokens,
                "allowed_message_ids": allowed_message_ids,
                "relaxed_schema": relaxed_schema,
            }
        )
        return self.drafts


class SequenceExtractor(StaticExtractor):
    def __init__(self, outputs) -> None:
        super().__init__([])
        self.outputs = list(outputs)

    def extract(self, *args, **kwargs):
        self.calls.append({"args": args, **kwargs})
        if not self.outputs:
            raise AssertionError("no extractor outputs left")
        output = self.outputs.pop(0)
        if isinstance(output, BaseException):
            raise output
        return output


class RelaxedFallbackExtractor(StaticExtractor):
    def extract(self, *args, **kwargs):
        self.calls.append(kwargs)
        if not kwargs.get("relaxed_schema"):
            raise RuntimeError("grammar-state schema construction failed")
        return self.drafts


class FlakyExtractor(StaticExtractor):
    def __init__(self, drafts: list[ClaimDraft], failures: int) -> None:
        super().__init__(drafts)
        self.failures = failures

    def extract(self, *args, **kwargs):
        self.calls.append(kwargs)
        if len(self.calls) <= self.failures:
            raise ExtractorResponseError("extractor returned invalid JSON")
        return self.drafts


class AlwaysFailExtractor(StaticExtractor):
    def extract(self, *args, **kwargs):
        self.calls.append(kwargs)
        raise ExtractorResponseError("extractor returned invalid JSON")


def active_segment(conn, messages, *, status="active"):
    conv_id, msg_ids = insert_conversation(conn, messages)
    gen_id = insert_generation(conn, conv_id, status=status)
    seg_id = insert_segment_row(conn, gen_id, conv_id, msg_ids, active=True)
    return conv_id, gen_id, seg_id, msg_ids


def insert_extracted_claim(
    conn,
    *,
    segment_id: str,
    generation_id: str,
    conversation_id: str,
    evidence_ids: list[str],
    predicate: str,
    object_text: str | None = None,
    object_json: dict | None = None,
    subject_text: str = "user",
    stability_class: str | None = None,
    confidence: float = 0.9,
    prompt_version: str = EXTRACTION_PROMPT_VERSION,
    model_version: str = "model-a",
):
    if stability_class is None:
        stability_class = {
            "drives": "preference",
            "prefers": "preference",
            "works_with": "relationship",
            "relationship_with": "relationship",
            "project_status_is": "project_status",
            "lives_at": "identity",
        }.get(predicate, "preference")
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
            segment_id,
            generation_id,
            prompt_version,
            model_version,
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
            object_json,
            stability_class,
            confidence,
            evidence_message_ids,
            extraction_prompt_version,
            extraction_model_version,
            request_profile_version,
            privacy_tier,
            raw_payload
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::uuid[], %s, %s, %s, 1, %s)
        RETURNING id::text
        """,
        (
            segment_id,
            generation_id,
            conversation_id,
            extraction_id,
            subject_text,
            predicate,
            object_text,
            Jsonb(object_json) if object_json is not None else None,
            stability_class,
            confidence,
            evidence_ids,
            prompt_version,
            model_version,
            EXTRACTION_REQUEST_PROFILE_VERSION,
            Jsonb({"rationale": "fixture"}),
        ),
    ).fetchone()[0]
    return extraction_id, claim_id


def test_predicate_vocabulary_and_extractor_schema_parity(conn):
    db_predicates = [
        row[0]
        for row in conn.execute(
            "SELECT predicate FROM predicate_vocabulary ORDER BY predicate"
        ).fetchall()
    ]
    assert db_predicates == sorted(extractor.PREDICATE_ENUM)
    assert "experiencing" not in db_predicates
    assert "lives_in" not in db_predicates
    schema_enum = extractor.extraction_json_schema(["00000000-0000-0000-0000-000000000000"])[
        "properties"
    ]["claims"]["items"]["properties"]["predicate"]["enum"]
    assert sorted(schema_enum) == db_predicates
    relaxed = extractor.extraction_json_schema(
        ["00000000-0000-0000-0000-000000000000"],
        relaxed_schema=True,
    )["properties"]["claims"]["items"]["properties"]
    assert sorted(relaxed["predicate"]["enum"]) == db_predicates
    assert "pattern" in relaxed["evidence_message_ids"]["items"]
    assert "enum" not in relaxed["evidence_message_ids"]["items"]


def test_claim_schema_guards_and_rationale(conn):
    conv_id, gen_id, seg_id, msg_ids = active_segment(conn, [("user", "I live at 1 Main", 1)])
    extraction_id, claim_id = insert_extracted_claim(
        conn,
        segment_id=seg_id,
        generation_id=gen_id,
        conversation_id=conv_id,
        evidence_ids=[msg_ids[0]],
        predicate="lives_at",
        object_json={"address_line1": "1 Main"},
        stability_class="identity",
    )
    row = conn.execute(
        """
        SELECT raw_payload->>'rationale',
               extraction_prompt_version,
               extraction_model_version,
               request_profile_version
        FROM claims
        WHERE id = %s
        """,
        (claim_id,),
    ).fetchone()
    parent = conn.execute(
        """
        SELECT extraction_prompt_version, extraction_model_version, request_profile_version
        FROM claim_extractions
        WHERE id = %s
        """,
        (extraction_id,),
    ).fetchone()
    assert row[0] == "fixture"
    assert row[1:] == parent

    with pytest.raises(CheckViolation, match="derivation columns"):
        conn.execute(
            """
            INSERT INTO claims (
                segment_id, generation_id, conversation_id, extraction_id, subject_text,
                predicate, object_json, stability_class, confidence, evidence_message_ids,
                extraction_prompt_version, extraction_model_version, request_profile_version,
                privacy_tier, raw_payload
            )
            VALUES (%s, %s, %s, %s, 'user', 'lives_at', %s, 'identity', 1,
                    %s::uuid[], 'wrong-prompt', 'model-a', %s, 1, '{}')
            """,
            (
                seg_id,
                gen_id,
                conv_id,
                extraction_id,
                Jsonb({"address_line1": "1 Main"}),
                [msg_ids[0]],
                EXTRACTION_REQUEST_PROFILE_VERSION,
            ),
        )
    conn.rollback()

    with pytest.raises(RaiseException, match="insert-only"):
        conn.execute("UPDATE claims SET subject_text = 'other' WHERE id = %s", (claim_id,))
    conn.rollback()

    with pytest.raises(CheckViolation):
        conn.execute(
            """
            INSERT INTO claims (
                segment_id, generation_id, conversation_id, extraction_id, subject_text,
                predicate, object_text, stability_class, confidence, evidence_message_ids,
                extraction_prompt_version, extraction_model_version, request_profile_version,
                privacy_tier, raw_payload
            )
            VALUES (%s, %s, %s, %s, 'user', 'prefers', 'tea', 'preference', 1,
                    '{}'::uuid[], 'p', 'm', 'r', 1, '{}')
            """,
            (seg_id, gen_id, conv_id, extraction_id),
        )
    conn.rollback()

    with pytest.raises(CheckViolation, match="subset of segment message_ids"):
        conn.execute(
            """
            INSERT INTO claims (
                segment_id, generation_id, conversation_id, extraction_id, subject_text,
                predicate, object_text, stability_class, confidence, evidence_message_ids,
                extraction_prompt_version, extraction_model_version, request_profile_version,
                privacy_tier, raw_payload
            )
            VALUES (%s, %s, %s, %s, 'user', 'prefers', 'tea', 'preference', 1,
                    ARRAY['00000000-0000-0000-0000-000000000000']::uuid[],
                    'p', 'm', 'r', 1, '{}')
            """,
            (seg_id, gen_id, conv_id, extraction_id),
        )
    conn.rollback()

    with pytest.raises(CheckViolation, match="missing required key"):
        insert_extracted_claim(
            conn,
            segment_id=seg_id,
            generation_id=gen_id,
            conversation_id=conv_id,
            evidence_ids=msg_ids,
            predicate="lives_at",
            object_json={"city": "Berlin"},
            stability_class="identity",
            prompt_version="bad-required-key",
        )
    conn.rollback()


def test_belief_transition_guard_audit_and_guc(conn):
    conv_id, gen_id, seg_id, msg_ids = active_segment(conn, [("user", "I drive a Subaru", 1)])
    _, claim_id = insert_extracted_claim(
        conn,
        segment_id=seg_id,
        generation_id=gen_id,
        conversation_id=conv_id,
        evidence_ids=msg_ids,
        predicate="drives",
        object_text="Subaru",
    )
    with pytest.raises(RaiseException, match="transition_in_progress"):
        conn.execute(
            """
            INSERT INTO beliefs (
                subject_text, predicate, object_text, valid_from, observed_at, extracted_at,
                status, confidence, evidence_ids, claim_ids, prompt_version,
                model_version, privacy_tier, raw_payload
            )
            VALUES ('user', 'drives', 'Subaru', now(), now(), now(), 'candidate', 1,
                    %s::uuid[], %s::uuid[], 'p', 'm', 1, '{}')
            """,
            (msg_ids, [claim_id]),
        )
    conn.rollback()

    payload = BeliefPayload(
        subject_text="User!!",
        predicate="drives",
        object_text="Subaru",
        object_json=None,
        valid_from=datetime.now(timezone.utc),
        valid_to=None,
        observed_at=datetime.now(timezone.utc),
        extracted_at=datetime.now(timezone.utc),
        status="candidate",
        confidence=0.9,
        evidence_ids=[msg_ids[0]],
        claim_ids=[claim_id],
        prompt_version=CONSOLIDATOR_PROMPT_VERSION,
        model_version=CONSOLIDATOR_MODEL_VERSION,
        privacy_tier=1,
        raw_payload={},
        score_breakdown={"mean": 0.9, "max": 0.9, "min": 0.9, "count": 1, "stddev": 0},
    )
    belief_id = insert_belief(conn, payload)
    audit = conn.execute(
        """
        SELECT ba.transition_kind, ba.request_uuid::text, b.subject_normalized, b.group_object_key
        FROM belief_audit ba
        JOIN beliefs b ON b.id = ba.belief_id
        WHERE b.id = %s
        """,
        (belief_id,),
    ).fetchone()
    assert audit[0] == "insert"
    assert audit[1]
    assert audit[2] == "user"
    assert audit[3] == ""
    guc = conn.execute(
        "SELECT current_setting('engram.transition_in_progress', true)"
    ).fetchone()[0]
    assert guc in (None, "")

    with pytest.raises(RaiseException, match="append-only"):
        conn.execute("UPDATE belief_audit SET new_status = 'accepted'")
    conn.rollback()


def test_contradiction_update_limits(conn):
    conv_id, gen_id, seg_id, msg_ids = active_segment(conn, [("user", "I drive a Subaru", 1)])
    _, claim_id = insert_extracted_claim(
        conn,
        segment_id=seg_id,
        generation_id=gen_id,
        conversation_id=conv_id,
        evidence_ids=msg_ids,
        predicate="drives",
        object_text="Subaru",
    )
    payload = BeliefPayload(
        subject_text="user",
        predicate="drives",
        object_text="Subaru",
        object_json=None,
        valid_from=datetime.now(timezone.utc),
        valid_to=datetime.now(timezone.utc),
        observed_at=datetime.now(timezone.utc),
        extracted_at=datetime.now(timezone.utc),
        status="candidate",
        confidence=0.9,
        evidence_ids=[msg_ids[0]],
        claim_ids=[claim_id],
        prompt_version=CONSOLIDATOR_PROMPT_VERSION,
        model_version=CONSOLIDATOR_MODEL_VERSION,
        privacy_tier=1,
        raw_payload={},
        score_breakdown={"mean": 0.9, "max": 0.9, "min": 0.9, "count": 1, "stddev": 0},
    )
    a = insert_belief(conn, payload)
    b = insert_belief(
        conn,
        BeliefPayload(**{**payload.__dict__, "object_text": "Volvo", "valid_to": None}),
    )
    contradiction_id = conn.execute(
        """
        INSERT INTO contradictions (belief_a_id, belief_b_id, detection_kind, privacy_tier)
        VALUES (%s, %s, 'same_subject_predicate', 1)
        RETURNING id::text
        """,
        (a, b),
    ).fetchone()[0]
    conn.execute(
        """
        UPDATE contradictions
        SET resolution_status = 'auto_resolved',
            resolution_kind = 'temporal_ordering',
            resolved_at = now()
        WHERE id = %s
        """,
        (contradiction_id,),
    )
    with pytest.raises(RaiseException, match="resolution fields"):
        conn.execute("UPDATE contradictions SET detection_kind = 'reclassification_recompute'")
    conn.rollback()
    with pytest.raises(CheckViolation):
        conn.execute(
            """
            INSERT INTO contradictions (belief_a_id, belief_b_id, detection_kind, privacy_tier)
            VALUES (%s, %s, 'same_subject_predicate', 1)
            """,
            (a, a),
        )


def test_extractor_request_shape_parse_rejections_and_salvage(conn, monkeypatch):
    captured = {}

    def fake_http(method, url, *, payload=None, timeout=30):
        captured.update({"method": method, "url": url, "payload": payload, "timeout": timeout})
        message_id = payload["response_format"]["json_schema"]["schema"]["properties"]["claims"][
            "items"
        ]["properties"]["evidence_message_ids"]["items"]["enum"][0]
        return {
            "choices": [
                {
                    "message": {
                        "content": (
                            '{"claims":[{"subject_text":"user","predicate":"has_name",'
                            '"object_text":"Hal","object_json":null,'
                            '"stability_class":"identity","confidence":1,'
                            f'"evidence_message_ids":["{message_id}"],"rationale":"direct"}}]}}'
                        )
                    }
                }
            ],
            "usage": {"completion_tokens": 12},
        }

    monkeypatch.setattr(extractor, "http_json", fake_http)
    client = extractor.IkLlamaExtractorClient(context_window=65536)
    result = client.extract("prompt", model_id="model-a", max_tokens=8192, allowed_message_ids=["00000000-0000-0000-0000-000000000000"])
    assert result.claims[0].predicate == "has_name"
    payload = captured["payload"]
    assert payload["stream"] is False
    assert payload["temperature"] == 0
    assert payload["top_p"] == 1
    assert payload["max_tokens"] == 8192
    assert payload["chat_template_kwargs"]["enable_thinking"] is False
    assert payload["response_format"]["type"] == "json_schema"

    for response, match in [
        ({"choices": [{"message": {"content": "", "reasoning_content": "{}"}}]}, "reasoning_content"),
        ({"choices": [{"message": {"content": "```json\n{}\n```"}}]}, "Markdown-fenced"),
        ({"choices": [{"message": {"content": "not-json"}}]}, "invalid JSON"),
    ]:
        with pytest.raises(ExtractorResponseError, match=match):
            parse_extraction_response(response)

    conv_id, gen_id, seg_id, msg_ids = active_segment(conn, [("user", "I use Postgres", 1)])
    client = StaticExtractor(
        [
            ClaimDraft("user", "uses_tool", "Postgres", None, "preference", 0.9, msg_ids, "direct"),
            ClaimDraft("user", "lives_at", None, {"city": "Berlin"}, "identity", 0.9, msg_ids, "missing required"),
        ]
    )
    extraction = extract_claims_from_segment(conn, seg_id, model_version="model-a", client=client)
    assert extraction.status == "extracted"
    assert extraction.claim_count == 1
    raw = conn.execute("SELECT raw_payload FROM claim_extractions WHERE id = %s", (extraction.extraction_id,)).fetchone()[0]
    assert raw["model_response"]
    assert len(raw["dropped_claims"]) == 1

    conv2, gen2, seg2, msg2 = active_segment(conn, [("user", "I use SQLite", 1)])
    bad_shape = StaticExtractor(
        [
            ClaimDraft(
                "user",
                "uses_tool",
                None,
                {"unexpected": "extra object channel"},
                "preference",
                0.9,
                msg2,
                "bad shape",
            )
        ]
    )
    failed = extract_claims_from_segment(conn, seg2, model_version="model-a", client=bad_shape)
    assert failed.status == "failed"
    raw_failed = conn.execute(
        "SELECT raw_payload FROM claim_extractions WHERE id = %s",
        (failed.extraction_id,),
    ).fetchone()[0]
    assert raw_failed["failure_kind"] == "trigger_violation"
    assert raw_failed["model_response"]
    assert raw_failed["dropped_claims"][0]["error"] == "predicate requires non-empty object_text"


def test_extractor_normalizes_vocab_derivable_claim_fields(conn):
    conv_id, gen_id, seg_id, msg_ids = active_segment(conn, [("user", "I use SQLite and DuckDB", 1)])
    client = StaticExtractor(
        [
            ClaimDraft(
                "user",
                "uses_tool",
                "SQLite",
                None,
                "identity",
                0.9,
                msg_ids,
                "stability repair",
            ),
            ClaimDraft(
                "user",
                "uses_tool",
                "DuckDB",
                {"unexpected": "extra object channel"},
                "preference",
                0.9,
                msg_ids,
                "object channel repair",
            ),
        ]
    )

    result = extract_claims_from_segment(conn, seg_id, model_version="model-a", client=client)

    assert result.status == "extracted"
    assert result.claim_count == 2
    rows = conn.execute(
        """
        SELECT object_text, object_json, stability_class, raw_payload->'normalizations'
        FROM claims
        WHERE segment_id = %s
        ORDER BY object_text
        """,
        (seg_id,),
    ).fetchall()
    assert rows[0][0] == "DuckDB"
    assert rows[0][1] is None
    assert rows[0][2] == "preference"
    assert rows[0][3] == [{"field": "object_json", "action": "dropped_for_text_predicate"}]
    assert rows[1][0] == "SQLite"
    assert rows[1][2] == "preference"
    assert rows[1][3] == [{"field": "stability_class", "from": "identity", "to": "preference"}]


def test_extractor_validation_repair_retry_can_produce_empty_success(conn):
    conv_id, gen_id, seg_id, msg_ids = active_segment(conn, [("user", "call me by my handle", 1)])
    client = SequenceExtractor(
        [
            [
                ClaimDraft(
                    "user",
                    "has_name",
                    None,
                    None,
                    "identity",
                    0.8,
                    msg_ids,
                    "missing object value",
                )
            ],
            [],
        ]
    )

    result = extract_claims_from_segment(conn, seg_id, model_version="model-a", client=client)

    assert result.status == "extracted"
    assert result.claim_count == 0
    assert len(client.calls) == 2
    assert "Validation repair retry" in client.calls[1]["args"][0]
    row = conn.execute(
        """
        SELECT claim_count, raw_payload
        FROM claim_extractions
        WHERE id = %s
        """,
        (result.extraction_id,),
    ).fetchone()
    assert row[0] == 0
    assert row[1]["failure_kind"] is None
    repair = row[1]["validation_repair"]
    assert row[1]["dropped_claims"] == []
    assert row[1]["parse_metadata"]["validation_repair"] == repair
    assert repair["attempted"] is True
    assert repair["result"] == "accepted"
    assert repair["prior_dropped_count"] == 1
    assert repair["prior_error_counts"] == {
        "exactly one of object_text or object_json is required": 1,
    }
    assert repair["final_dropped_count"] == 0
    assert repair["final_error_counts"] == {}
    prior_drop = repair["prior_dropped_claims"][0]
    assert prior_drop["reason"] == "trigger_violation"
    assert prior_drop["index"] == 0
    assert prior_drop["error"] == "exactly one of object_text or object_json is required"
    assert prior_drop["predicate"] == "has_name"
    assert prior_drop["stability_class"] == "identity"
    assert prior_drop["object_text_type"] == "null"
    assert prior_drop["object_json_type"] == "null"
    assert prior_drop["evidence_message_count"] == 1
    assert "subject_text" not in prior_drop
    assert "object_text" not in prior_drop
    assert conn.execute(
        """
        SELECT count(*)
        FROM consolidation_progress
        WHERE stage = 'extractor' AND status = 'failed'
        """
    ).fetchone()[0] == 0


def test_extractor_validation_repair_preserves_prior_drops_when_valid_claims_survive(conn):
    conv_id, gen_id, seg_id, msg_ids = active_segment(conn, [("user", "I use a local database", 1)])
    client = SequenceExtractor(
        [
            [
                ClaimDraft(
                    "user",
                    "uses_tool",
                    None,
                    None,
                    "preference",
                    0.8,
                    msg_ids,
                    "missing object value",
                )
            ],
            [
                ClaimDraft(
                    "user",
                    "uses_tool",
                    "local database",
                    None,
                    "preference",
                    0.8,
                    msg_ids,
                    "direct",
                )
            ],
        ]
    )

    result = extract_claims_from_segment(conn, seg_id, model_version="model-a", client=client)

    assert result.status == "extracted"
    assert result.claim_count == 1
    raw = conn.execute(
        "SELECT raw_payload FROM claim_extractions WHERE id = %s",
        (result.extraction_id,),
    ).fetchone()[0]
    assert raw["dropped_claims"] == []
    assert raw["validation_repair"]["prior_dropped_count"] == 1
    assert raw["validation_repair"]["prior_dropped_claims"][0]["predicate"] == "uses_tool"
    assert raw["validation_repair"]["prior_dropped_claims"][0]["object_text_type"] == "null"
    assert "subject_text" not in raw["validation_repair"]["prior_dropped_claims"][0]
    assert "object_text" not in raw["validation_repair"]["prior_dropped_claims"][0]
    assert raw["validation_repair"]["final_dropped_count"] == 0


def test_extractor_validation_repair_still_invalid_remains_failed(conn):
    conv_id, gen_id, seg_id, msg_ids = active_segment(conn, [("user", "call me by my handle", 1)])
    invalid = [
        ClaimDraft(
            "user",
            "has_name",
            None,
            None,
            "identity",
            0.8,
            msg_ids,
            "missing object value",
        )
    ]
    client = SequenceExtractor([invalid, invalid])

    result = extract_claims_from_segment(conn, seg_id, model_version="model-a", client=client)

    assert result.status == "failed"
    assert len(client.calls) == 2
    raw = conn.execute(
        "SELECT raw_payload FROM claim_extractions WHERE id = %s",
        (result.extraction_id,),
    ).fetchone()[0]
    assert raw["failure_kind"] == "trigger_violation"
    assert raw["validation_repair"]["result"] == "still_invalid"
    assert raw["validation_repair"]["prior_dropped_count"] == 1
    assert raw["validation_repair"]["final_dropped_count"] == 1
    assert len(raw["dropped_claims"]) == 1


def test_extractor_validation_repair_uses_one_attempt_even_with_extra_retries(conn):
    conv_id, gen_id, seg_id, msg_ids = active_segment(conn, [("user", "call me by my handle", 1)])
    client = SequenceExtractor(
        [
            [
                ClaimDraft(
                    "user",
                    "has_name",
                    None,
                    None,
                    "identity",
                    0.8,
                    msg_ids,
                    "missing object value",
                )
            ],
            ExtractorResponseError("extractor returned invalid JSON"),
        ]
    )

    result = extract_claims_from_segment(
        conn,
        seg_id,
        model_version="model-a",
        client=client,
        retries=3,
    )

    assert result.status == "failed"
    assert len(client.calls) == 2
    raw = conn.execute(
        "SELECT raw_payload FROM claim_extractions WHERE id = %s",
        (result.extraction_id,),
    ).fetchone()[0]
    assert raw["validation_repair"]["result"] == "failed"
    assert raw["validation_repair"]["prior_dropped_count"] == 1
    assert raw["validation_repair"]["last_error"] == "extractor returned invalid JSON"


def test_extractor_empty_failure_replacement_and_reaping(conn):
    conv_id, gen_id, seg_id, msg_ids = active_segment(conn, [("user", "nothing durable", 1)])
    old_extraction, _ = insert_extracted_claim(
        conn,
        segment_id=seg_id,
        generation_id=gen_id,
        conversation_id=conv_id,
        evidence_ids=msg_ids,
        predicate="uses_tool",
        object_text="Python",
        prompt_version="old",
    )
    extracting = conn.execute(
        """
        INSERT INTO claim_extractions (
            segment_id, generation_id, extraction_prompt_version, extraction_model_version,
            request_profile_version, status, created_at
        )
        VALUES (%s, %s, 'new', 'model-a', %s, 'extracting', now() - interval '1 hour')
        RETURNING id::text
        """,
        (seg_id, gen_id, EXTRACTION_REQUEST_PROFILE_VERSION),
    ).fetchone()[0]
    assert reap_stale_extractions(conn, timeout_seconds=1) == 1
    assert conn.execute("SELECT status, raw_payload->>'failure_kind' FROM claim_extractions WHERE id = %s", (extracting,)).fetchone() == ("failed", "inflight_timeout")
    assert conn.execute("SELECT status FROM claim_extractions WHERE id = %s", (old_extraction,)).fetchone()[0] == "extracted"

    empty = extract_claims_from_segment(
        conn,
        seg_id,
        model_version="model-a",
        prompt_version="newer",
        client=StaticExtractor([]),
    )
    assert empty.status == "extracted"
    assert empty.claim_count == 0
    statuses = dict(conn.execute("SELECT extraction_prompt_version, status FROM claim_extractions").fetchall())
    assert statuses["old"] == "superseded"
    assert statuses["newer"] == "extracted"


def test_relaxed_schema_fallback_is_reactive(conn):
    conv_id, gen_id, seg_id, msg_ids = active_segment(conn, [("user", "I use SQLite", 1)])
    client = RelaxedFallbackExtractor(
        [ClaimDraft("user", "uses_tool", "SQLite", None, "preference", 0.8, msg_ids, "direct")]
    )
    result = extract_claims_from_segment(conn, seg_id, model_version="model-a", client=client)
    assert result.claim_count == 1
    assert [call["relaxed_schema"] for call in client.calls] == [False, True]


def test_large_segment_extraction_uses_bounded_message_chunks(conn):
    messages = [("user", f"I use local tool {index}", 1) for index in range(25)]
    conv_id, gen_id, seg_id, msg_ids = active_segment(conn, messages)

    class ChunkAwareExtractor:
        def __init__(self) -> None:
            self.calls = []

        def extract(self, prompt, *, model_id, max_tokens, allowed_message_ids, **kwargs):
            self.calls.append(
                {
                    "prompt": prompt,
                    "allowed_message_ids": allowed_message_ids,
                    "max_tokens": max_tokens,
                }
            )
            return [
                ClaimDraft(
                    "user",
                    "uses_tool",
                    f"local tool chunk {len(self.calls)}",
                    None,
                    "preference",
                    0.8,
                    [allowed_message_ids[0]],
                    "direct",
                )
            ]

    client = ChunkAwareExtractor()
    result = extract_claims_from_segment(conn, seg_id, model_version="model-a", client=client)

    assert result.status == "extracted"
    assert result.claim_count == 3
    assert [len(call["allowed_message_ids"]) for call in client.calls] == [12, 12, 1]
    assert all("Segment summary:\n(none)" in call["prompt"] for call in client.calls)
    assert "required_object_keys=['project', 'status']" in client.calls[0]["prompt"]
    assert "For JSON predicates, emit object_json only when every required_object_key" in client.calls[0]["prompt"]
    raw = conn.execute(
        "SELECT raw_payload FROM claim_extractions WHERE id = %s",
        (result.extraction_id,),
    ).fetchone()[0]
    assert raw["parse_metadata"]["chunked"] is True
    assert raw["parse_metadata"]["chunk_count"] == 3


def test_chunked_relaxed_schema_output_is_salvaged_against_chunk_ids(conn):
    messages = [("user", f"I use local tool {index}", 1) for index in range(13)]
    conv_id, gen_id, seg_id, msg_ids = active_segment(conn, messages)

    class CrossChunkRelaxedExtractor:
        def __init__(self) -> None:
            self.calls = []

        def extract(self, prompt, *, allowed_message_ids, relaxed_schema, **kwargs):
            self.calls.append(
                {
                    "allowed_message_ids": allowed_message_ids,
                    "relaxed_schema": relaxed_schema,
                }
            )
            if not relaxed_schema:
                raise RuntimeError("grammar-state schema construction failed")
            if msg_ids[-1] not in allowed_message_ids:
                return [
                    ClaimDraft(
                        "user",
                        "uses_tool",
                        "cross chunk citation",
                        None,
                        "preference",
                        0.8,
                        [msg_ids[-1]],
                        "invalid cross-chunk evidence",
                    )
                ]
            return [
                ClaimDraft(
                    "user",
                    "uses_tool",
                    "last chunk citation",
                    None,
                    "preference",
                    0.8,
                    [allowed_message_ids[0]],
                    "direct",
                )
            ]

    result = extract_claims_from_segment(
        conn,
        seg_id,
        model_version="model-a",
        client=CrossChunkRelaxedExtractor(),
        retries=0,
    )

    assert result.status == "extracted"
    assert result.claim_count == 1
    raw = conn.execute(
        "SELECT raw_payload FROM claim_extractions WHERE id = %s",
        (result.extraction_id,),
    ).fetchone()[0]
    assert len(raw["dropped_claims"]) == 1
    assert raw["dropped_claims"][0]["error"] == (
        "evidence_message_ids must be a subset of chunk message_ids"
    )
    assert raw["parse_metadata"]["chunk_dropped_claims"] == raw["dropped_claims"]


def test_chunked_extraction_failure_writes_chunk_diagnostics_without_claims(conn):
    messages = [("user", f"I use local tool {index}", 1) for index in range(13)]
    conv_id, gen_id, seg_id, msg_ids = active_segment(conn, messages)

    class FailsOnSecondChunk:
        def __init__(self) -> None:
            self.calls = 0

        def extract(self, prompt, *, allowed_message_ids, **kwargs):
            self.calls += 1
            if msg_ids[-1] in allowed_message_ids:
                raise ExtractorResponseError("extractor returned invalid JSON")
            return [
                ClaimDraft(
                    "user",
                    "uses_tool",
                    "local tool first chunk",
                    None,
                    "preference",
                    0.8,
                    [allowed_message_ids[0]],
                    "direct",
                )
            ]

    result = extract_claims_from_segment(
        conn,
        seg_id,
        model_version="model-a",
        client=FailsOnSecondChunk(),
        retries=0,
    )

    assert result.status == "failed"
    assert conn.execute("SELECT count(*) FROM claims WHERE segment_id = %s", (seg_id,)).fetchone()[0] == 0
    raw = conn.execute(
        "SELECT raw_payload FROM claim_extractions WHERE id = %s",
        (result.extraction_id,),
    ).fetchone()[0]
    assert raw["failure_kind"] == "parse_error"
    assert raw["chunk_index"] == 2
    assert raw["chunk_count"] == 2


def test_adaptive_chunk_split_recovers_from_oversized_chunk_parse_error(conn):
    messages = [("user", f"I use local tool {index}", 1) for index in range(13)]
    conv_id, gen_id, seg_id, msg_ids = active_segment(conn, messages)

    class SplitRecoveringExtractor:
        def __init__(self) -> None:
            self.allowed_lengths = []

        def extract(self, prompt, *, allowed_message_ids, **kwargs):
            self.allowed_lengths.append(len(allowed_message_ids))
            if len(allowed_message_ids) > 6:
                raise ExtractorResponseError("extractor returned invalid JSON")
            return [
                ClaimDraft(
                    "user",
                    "uses_tool",
                    f"local tool leaf {len(self.allowed_lengths)}",
                    None,
                    "preference",
                    0.8,
                    [allowed_message_ids[0]],
                    "direct",
                )
            ]

    client = SplitRecoveringExtractor()
    result = extract_claims_from_segment(
        conn,
        seg_id,
        model_version="model-a",
        client=client,
        retries=0,
    )

    assert result.status == "extracted"
    assert result.claim_count == 3
    assert client.allowed_lengths == [12, 6, 6, 1]
    raw = conn.execute(
        "SELECT raw_payload FROM claim_extractions WHERE id = %s",
        (result.extraction_id,),
    ).fetchone()[0]
    assert raw["parse_metadata"]["chunked"] is True
    assert [chunk["split_depth"] for chunk in raw["parse_metadata"]["chunks"]] == [1, 1, 0]


def test_adaptive_chunk_split_reduces_child_retry_budget(conn):
    messages = [("user", f"I use local tool {index}", 1) for index in range(13)]
    conv_id, gen_id, seg_id, msg_ids = active_segment(conn, messages)

    class FailsLargeChunks:
        def __init__(self) -> None:
            self.allowed_lengths = []

        def extract(self, prompt, *, allowed_message_ids, **kwargs):
            self.allowed_lengths.append(len(allowed_message_ids))
            if len(allowed_message_ids) > 3:
                raise ExtractorResponseError("extractor returned invalid JSON")
            return [
                ClaimDraft(
                    "user",
                    "uses_tool",
                    f"local tool leaf {len(self.allowed_lengths)}",
                    None,
                    "preference",
                    0.8,
                    [allowed_message_ids[0]],
                    "direct",
                )
            ]

    client = FailsLargeChunks()
    result = extract_claims_from_segment(
        conn,
        seg_id,
        model_version="model-a",
        client=client,
        retries=1,
    )

    assert result.status == "extracted"
    assert result.claim_count == 5
    assert client.allowed_lengths.count(12) == 2
    assert client.allowed_lengths.count(6) == 2


def test_extractor_retry_budget_and_failure_diagnostics(conn):
    conv_id, gen_id, seg_id, msg_ids = active_segment(conn, [("user", "I use DuckDB", 1)])
    flaky = FlakyExtractor(
        [ClaimDraft("user", "uses_tool", "DuckDB", None, "preference", 0.8, msg_ids, "direct")],
        failures=2,
    )
    result = extract_claims_from_segment(
        conn,
        seg_id,
        model_version="model-a",
        prompt_version="retry-success",
        client=flaky,
        retries=2,
    )
    assert result.status == "extracted"
    assert result.claim_count == 1
    assert len(flaky.calls) == 3

    conv2, gen2, seg2, msg2 = active_segment(conn, [("user", "x", 1)])
    always_fail = AlwaysFailExtractor()
    failed = extract_claims_from_segment(
        conn,
        seg2,
        model_version="model-a",
        prompt_version="retry-failure",
        client=always_fail,
        retries=1,
    )
    assert failed.status == "failed"
    raw = conn.execute(
        "SELECT raw_payload FROM claim_extractions WHERE id = %s",
        (failed.extraction_id,),
    ).fetchone()[0]
    assert raw["failure_kind"] == "parse_error"
    assert raw["attempts"] == 2
    assert len(raw["attempt_errors"]) == 2


def test_extract_pending_claims_stops_internal_batch_after_failure(monkeypatch):
    calls = []

    class DummyConn:
        pass

    monkeypatch.setattr(extractor, "apply_phase3_reclassification_invalidations", lambda conn: None)
    monkeypatch.setattr(extractor, "reap_stale_extractions", lambda conn: None)
    monkeypatch.setattr(extractor, "default_extractor_model_id", lambda: "model-a")
    monkeypatch.setattr(
        extractor,
        "fetch_pending_segments",
        lambda *args, **kwargs: ["seg-a", "seg-b"],
    )

    def fake_extract_claims_from_segment(conn, segment_id, **kwargs):
        calls.append(segment_id)
        return extractor.ExtractionResult("extract-a", segment_id, 0, "failed")

    monkeypatch.setattr(
        extractor,
        "extract_claims_from_segment",
        fake_extract_claims_from_segment,
    )

    result = extractor.extract_pending_claims(DummyConn(), 2, client=object())

    assert result.processed == 1
    assert result.failed == 1
    assert calls == ["seg-a"]


def test_extractor_health_smoke_uses_empty_claim_schema():
    client = StaticExtractor([])

    run_extractor_health_smoke(client, model_id="model-a")

    assert client.calls == [
        {
            "prompt": extractor.EXTRACTOR_HEALTH_SMOKE_PROMPT,
            "model_id": "model-a",
            "max_tokens": 128,
            "allowed_message_ids": None,
            "relaxed_schema": False,
        }
    ]


def test_consolidator_insert_same_value_and_contradiction(conn):
    conv_id, msg_ids = insert_conversation(
        conn,
        [
            ("user", "I drive a Subaru", 1),
            ("user", "Still driving a Subaru", 1),
            ("user", "Now I drive a Volvo", 1),
        ],
    )
    gen_id = insert_generation(conn, conv_id, status="active")
    seg1 = insert_segment_row(conn, gen_id, conv_id, [msg_ids[0]], sequence_index=0, active=True)
    seg2 = insert_segment_row(conn, gen_id, conv_id, [msg_ids[1]], sequence_index=1, active=True)
    seg3 = insert_segment_row(conn, gen_id, conv_id, [msg_ids[2]], sequence_index=2, active=True)
    insert_extracted_claim(
        conn,
        segment_id=seg1,
        generation_id=gen_id,
        conversation_id=conv_id,
        evidence_ids=[msg_ids[0]],
        predicate="drives",
        object_text="Subaru",
        confidence=0.8,
        prompt_version="p1",
    )
    first = consolidate_beliefs(conn, batch_size=10, conversation_id=conv_id)
    assert first.created == 1
    belief1 = conn.execute("SELECT id::text, status, valid_to FROM beliefs").fetchone()
    assert belief1[1:] == ("candidate", None)

    insert_extracted_claim(
        conn,
        segment_id=seg2,
        generation_id=gen_id,
        conversation_id=conv_id,
        evidence_ids=[msg_ids[1]],
        predicate="drives",
        object_text="Subaru",
        confidence=1.0,
        prompt_version="p2",
    )
    second = consolidate_beliefs(conn, batch_size=10, conversation_id=conv_id)
    assert second.created == 1
    assert second.superseded == 1
    prior = conn.execute("SELECT status, valid_to, superseded_by IS NOT NULL FROM beliefs WHERE id = %s", (belief1[0],)).fetchone()
    assert prior == ("superseded", None, True)

    insert_extracted_claim(
        conn,
        segment_id=seg3,
        generation_id=gen_id,
        conversation_id=conv_id,
        evidence_ids=[msg_ids[2]],
        predicate="drives",
        object_text="Volvo",
        confidence=0.9,
        prompt_version="p3",
    )
    third = consolidate_beliefs(conn, batch_size=10, conversation_id=conv_id)
    assert third.contradictions == 1
    contradiction = conn.execute(
        """
        SELECT detection_kind, resolution_status, resolution_kind
        FROM contradictions
        """
    ).fetchone()
    assert contradiction == ("same_subject_predicate", "auto_resolved", "temporal_ordering")
    closed, new = conn.execute(
        """
        SELECT a.valid_to, b.valid_from
        FROM contradictions c
        JOIN beliefs a ON a.id = c.belief_a_id
        JOIN beliefs b ON b.id = c.belief_b_id
        """
    ).fetchone()
    assert closed == new


def test_contradiction_retry_rolls_back_partial_close(conn, monkeypatch):
    conv_id, msg_ids = insert_conversation(
        conn,
        [
            ("user", "I drive a Subaru", 1),
            ("user", "Now I drive a Volvo", 1),
        ],
    )
    gen_id = insert_generation(conn, conv_id, status="active")
    seg1 = insert_segment_row(conn, gen_id, conv_id, [msg_ids[0]], sequence_index=0, active=True)
    seg2 = insert_segment_row(conn, gen_id, conv_id, [msg_ids[1]], sequence_index=1, active=True)
    insert_extracted_claim(
        conn,
        segment_id=seg1,
        generation_id=gen_id,
        conversation_id=conv_id,
        evidence_ids=[msg_ids[0]],
        predicate="drives",
        object_text="Subaru",
        prompt_version="car-1",
    )
    consolidate_beliefs(conn, batch_size=10, conversation_id=conv_id)
    insert_extracted_claim(
        conn,
        segment_id=seg2,
        generation_id=gen_id,
        conversation_id=conv_id,
        evidence_ids=[msg_ids[1]],
        predicate="drives",
        object_text="Volvo",
        prompt_version="car-2",
    )

    real_insert_belief = consolidator_module.insert_belief
    raised = {"done": False}

    def flaky_insert_belief(conn_arg, payload, *args, **kwargs):
        if payload.object_text == "Volvo" and not raised["done"]:
            raised["done"] = True
            raise UniqueViolation("simulated active belief conflict")
        return real_insert_belief(conn_arg, payload, *args, **kwargs)

    monkeypatch.setattr(consolidator_module, "insert_belief", flaky_insert_belief)

    result = consolidate_beliefs(conn, batch_size=10, conversation_id=conv_id)

    assert raised["done"] is True
    assert result.contradictions == 1
    assert (
        conn.execute(
            "SELECT count(*) FROM belief_audit WHERE transition_kind = 'close'"
        ).fetchone()[0]
        == 1
    )
    assert conn.execute("SELECT count(*) FROM contradictions").fetchone()[0] == 1


def test_multi_current_and_scoped_current_grouping(conn):
    conv_id, msg_ids = insert_conversation(conn, [("user", "I work with Alice", 1), ("user", "I work with Bob", 1)])
    gen_id = insert_generation(conn, conv_id, status="active")
    seg1 = insert_segment_row(conn, gen_id, conv_id, [msg_ids[0]], sequence_index=0, active=True)
    seg2 = insert_segment_row(conn, gen_id, conv_id, [msg_ids[1]], sequence_index=1, active=True)
    insert_extracted_claim(
        conn,
        segment_id=seg1,
        generation_id=gen_id,
        conversation_id=conv_id,
        evidence_ids=[msg_ids[0]],
        predicate="works_with",
        object_text="Alice",
        prompt_version="p1",
    )
    insert_extracted_claim(
        conn,
        segment_id=seg2,
        generation_id=gen_id,
        conversation_id=conv_id,
        evidence_ids=[msg_ids[1]],
        predicate="works_with",
        object_text="Bob",
        prompt_version="p2",
    )
    result = consolidate_beliefs(conn, batch_size=10, conversation_id=conv_id)
    assert result.created == 2
    assert conn.execute("SELECT count(*) FROM contradictions").fetchone()[0] == 0

    conv2, msg2 = insert_conversation(conn, [("user", "Alice is close", 1), ("user", "Alice is strained", 1)])
    gen2 = insert_generation(conn, conv2, status="active")
    rel_seg1 = insert_segment_row(conn, gen2, conv2, [msg2[0]], sequence_index=0, active=True)
    rel_seg2 = insert_segment_row(conn, gen2, conv2, [msg2[1]], sequence_index=1, active=True)
    insert_extracted_claim(
        conn,
        segment_id=rel_seg1,
        generation_id=gen2,
        conversation_id=conv2,
        evidence_ids=[msg2[0]],
        predicate="relationship_with",
        object_json={"name": "Alice", "status": "close"},
        prompt_version="p3",
    )
    insert_extracted_claim(
        conn,
        segment_id=rel_seg2,
        generation_id=gen2,
        conversation_id=conv2,
        evidence_ids=[msg2[1]],
        predicate="relationship_with",
        object_json={"name": "Alice", "status": "strained"},
        prompt_version="p4",
    )
    result2 = consolidate_beliefs(conn, batch_size=10, conversation_id=conv2)
    assert result2.contradictions == 1


def test_decision_rule_0_rejects_orphan_and_reclassification_hook(conn):
    conv_id, gen_id, seg_id, msg_ids = active_segment(conn, [("user", "I use Python", 1)])
    extraction_id, claim_id = insert_extracted_claim(
        conn,
        segment_id=seg_id,
        generation_id=gen_id,
        conversation_id=conv_id,
        evidence_ids=msg_ids,
        predicate="uses_tool",
        object_text="Python",
    )
    consolidate_beliefs(conn, batch_size=10, conversation_id=conv_id)
    conn.execute(
        "UPDATE segments SET is_active = false, invalidated_at = now(), invalidation_reason = %s WHERE id = %s",
        (f"privacy reclassification of message:{msg_ids[0]}", seg_id),
    )
    assert apply_phase3_reclassification_invalidations(conn) == 1
    assert conn.execute("SELECT status FROM claim_extractions WHERE id = %s", (extraction_id,)).fetchone()[0] == "superseded"
    result = consolidate_beliefs(conn, batch_size=10, conversation_id=conv_id)
    assert result.rejected == 1
    audit = conn.execute(
        "SELECT transition_kind, score_breakdown->>'cause' FROM belief_audit ORDER BY created_at DESC LIMIT 1"
    ).fetchone()
    assert audit == ("reject", "orphan_after_reclassification")


def test_reclassification_recompute_multi_current_same_group_is_not_contradiction(conn):
    conv_id, msg_ids = insert_conversation(
        conn,
        [
            ("user", "I have a cat named Milo since 2020", 1),
            ("user", "Milo is my cat", 1),
        ],
    )
    gen_id = insert_generation(conn, conv_id, status="active")
    seg1 = insert_segment_row(conn, gen_id, conv_id, [msg_ids[0]], sequence_index=0, active=True)
    seg2 = insert_segment_row(conn, gen_id, conv_id, [msg_ids[1]], sequence_index=1, active=True)
    extraction1, claim1 = insert_extracted_claim(
        conn,
        segment_id=seg1,
        generation_id=gen_id,
        conversation_id=conv_id,
        evidence_ids=[msg_ids[0]],
        predicate="has_pet",
        object_json={"name": "Milo", "species": "cat", "since": "2020"},
        stability_class="identity",
        prompt_version="pet-1",
    )
    _, claim2 = insert_extracted_claim(
        conn,
        segment_id=seg2,
        generation_id=gen_id,
        conversation_id=conv_id,
        evidence_ids=[msg_ids[1]],
        predicate="has_pet",
        object_json={"name": "Milo", "species": "cat"},
        stability_class="identity",
        prompt_version="pet-2",
    )
    first = consolidate_beliefs(conn, batch_size=10, conversation_id=conv_id)
    assert first.created == 2
    active = conn.execute(
        """
        SELECT claim_ids::text[]
        FROM beliefs
        WHERE status = 'candidate'
          AND valid_to IS NULL
        """
    ).fetchone()[0]
    assert set(active) == {claim1, claim2}

    conn.execute(
        "UPDATE segments SET is_active = false, invalidated_at = now(), invalidation_reason = %s WHERE id = %s",
        (f"privacy reclassification of message:{msg_ids[0]}", seg1),
    )
    assert apply_phase3_reclassification_invalidations(conn) == 1
    assert conn.execute("SELECT status FROM claim_extractions WHERE id = %s", (extraction1,)).fetchone()[0] == "superseded"

    result = consolidate_beliefs(conn, batch_size=10, conversation_id=conv_id)

    assert result.superseded == 1
    assert result.contradictions == 0
    assert conn.execute("SELECT count(*) FROM contradictions").fetchone()[0] == 0
    active_after = conn.execute(
        """
        SELECT claim_ids::text[], object_json
        FROM beliefs
        WHERE status = 'candidate'
          AND valid_to IS NULL
        """
    ).fetchone()
    assert active_after[0] == [claim2]
    assert dict(active_after[1]) == {"name": "Milo", "species": "cat"}


def test_rebuild_structural_equivalence_and_lineage(conn):
    conv_id, gen_id, seg_id, msg_ids = active_segment(conn, [("user", "I use Postgres", 1)])
    insert_extracted_claim(
        conn,
        segment_id=seg_id,
        generation_id=gen_id,
        conversation_id=conv_id,
        evidence_ids=msg_ids,
        predicate="uses_tool",
        object_text="Postgres",
    )
    consolidate_beliefs(conn, batch_size=10, conversation_id=conv_id)
    before = active_belief_structure(conn)
    consolidate_beliefs(conn, batch_size=10, rebuild=True, conversation_id=conv_id)
    after = active_belief_structure(conn)
    assert after == before
    audit = conn.execute(
        """
        SELECT transition_kind, previous_status, new_status
        FROM belief_audit
        WHERE transition_kind = 'close'
        ORDER BY created_at DESC
        LIMIT 1
        """
    ).fetchone()
    assert audit == ("close", "candidate", "superseded")


def active_belief_structure(conn):
    return conn.execute(
        """
        SELECT subject_normalized, predicate, group_object_key, object_text, object_json,
               evidence_ids::text[], claim_ids::text[], valid_from, valid_to, status
        FROM beliefs
        WHERE valid_to IS NULL
          AND status = 'candidate'
        ORDER BY subject_normalized, predicate, group_object_key
        """
    ).fetchall()


def test_sql_python_subject_normalization_parity(conn):
    fixtures = [" User!! ", "Ａlice\tSmith...", "Project  Engram?"]
    for value in fixtures:
        sql = conn.execute("SELECT engram_normalize_subject(%s)", (value,)).fetchone()[0]
        assert sql == normalize_subject(value)


def test_cli_pipeline_is_phase2_only_and_pipeline3_warns(monkeypatch, capsys):
    calls = []

    class DummyConn:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def commit(self):
            calls.append("commit")

    monkeypatch.setattr(cli, "connect", lambda: DummyConn())
    monkeypatch.setattr(cli, "apply_reclassification_invalidations", lambda conn: 0)
    monkeypatch.setattr(cli, "run_segment_batches", lambda *a, **k: type("R", (), {"processed": 0, "created": 0, "skipped": 0, "failed": 0})())
    monkeypatch.setattr(cli, "run_embed_batches", lambda *a, **k: type("R", (), {"processed": 0, "created": 0, "cache_hits": 0, "activated": 0, "failed": 0})())
    monkeypatch.setattr(cli, "run_extract_batches", lambda *a, **k: (_ for _ in ()).throw(AssertionError("phase3 should not run")))
    assert cli.main(["pipeline", "--limit", "1"]) == 0

    monkeypatch.setattr(cli, "phase3_schema_preflight", lambda conn: None)
    monkeypatch.setattr(cli, "apply_phase3_reclassification_invalidations", lambda conn: 0)
    monkeypatch.setattr(cli, "active_beliefs_with_other_consolidator_version", lambda conn: 1)
    monkeypatch.setattr(cli, "fetch_phase3_conversation_batch", lambda conn, limit: [])
    assert cli.main(["pipeline-3", "--limit", "0"]) == 0
    assert "different consolidator prompt_version" in capsys.readouterr().err


def test_pipeline3_preflight_stops_before_model_work(monkeypatch, capsys):
    calls = []

    class DummyConn:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

    monkeypatch.setattr(cli, "connect", lambda: DummyConn())
    monkeypatch.setattr(
        cli,
        "phase3_schema_preflight",
        lambda conn: (_ for _ in ()).throw(
            cli.Phase3SchemaPreflightError("claims.extraction_id is missing")
        ),
    )
    monkeypatch.setattr(
        cli,
        "run_extractor_health_smoke",
        lambda *args, **kwargs: calls.append("smoke"),
    )

    assert cli.main(["pipeline-3", "--limit", "1"]) == 1
    assert calls == []
    assert "claims.extraction_id is missing" in capsys.readouterr().err


def test_phase3_schema_preflight_accepts_current_schema(conn):
    cli.phase3_schema_preflight(conn)


@pytest.mark.parametrize(
    ("sql", "match"),
    [
        (
            "DELETE FROM schema_migrations WHERE filename = '006_claims_beliefs.sql'",
            "006_claims_beliefs\\.sql is not recorded",
        ),
        (
            """
            UPDATE predicate_vocabulary
            SET cardinality_class = 'multi_current'
            WHERE predicate = 'project_status_is'
            """,
            "project_status_is\\.cardinality_class",
        ),
        (
            "DROP INDEX beliefs_active_group_unique_idx",
            "beliefs_active_group_unique_idx index is missing",
        ),
        (
            "DROP TRIGGER claims_insert_prepare_validate ON claims",
            "claims_insert_prepare_validate trigger is missing",
        ),
        (
            "DROP FUNCTION fn_contradictions_mutation_guard() CASCADE",
            "fn_contradictions_mutation_guard",
        ),
    ],
)
def test_phase3_schema_preflight_detects_semantic_schema_drift(conn, sql, match):
    conn.execute(sql)

    with pytest.raises(cli.Phase3SchemaPreflightError, match=match):
        cli.phase3_schema_preflight(conn)


def test_pipeline3_extracts_selected_conversations_to_completion(monkeypatch):
    calls = []

    class DummyConn:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def commit(self):
            calls.append(("commit",))

    monkeypatch.setattr(cli, "connect", lambda: DummyConn())
    monkeypatch.setattr(cli, "phase3_schema_preflight", lambda conn: None)
    monkeypatch.setattr(cli, "apply_phase3_reclassification_invalidations", lambda conn: 0)
    monkeypatch.setattr(cli, "active_beliefs_with_other_consolidator_version", lambda conn: 0)
    monkeypatch.setattr(cli, "fetch_phase3_conversation_batch", lambda conn, limit: ["conv-a"])
    monkeypatch.setattr(cli, "default_extractor_model_id", lambda: "model-a")
    monkeypatch.setattr(cli, "IkLlamaExtractorClient", lambda: object())
    monkeypatch.setattr(
        cli,
        "run_extractor_health_smoke",
        lambda client, *, model_id: calls.append(("smoke", model_id)),
    )
    monkeypatch.setattr(
        cli,
        "upsert_progress",
        lambda conn, **kwargs: calls.append(("progress", kwargs)),
    )

    def fake_extract(
        conn,
        *,
        batch_size,
        limit,
        conversation_id,
        model_version,
        client,
        health_smoke,
        **kwargs,
    ):
        calls.append(("extract", batch_size, limit, conversation_id, model_version, health_smoke))
        return SimpleNamespace(processed=3, created=5, skipped=0, failed=0)

    def fake_consolidate(conn, *, batch_size, limit, conversation_id, **kwargs):
        calls.append(("consolidate", batch_size, limit, conversation_id))
        return SimpleNamespace(processed=1, created=2, superseded=0, contradictions=0)

    monkeypatch.setattr(cli, "run_extract_batches", fake_extract)
    monkeypatch.setattr(cli, "run_consolidate_batches", fake_consolidate)

    assert cli.main(["pipeline-3", "--extract-batch-size", "1", "--limit", "1"]) == 0
    assert ("extract", 1, None, "conv-a", "model-a", False) in calls
    assert ("consolidate", 10, 1, "conv-a") in calls
    assert calls.count(("smoke", "model-a")) == 2


def test_pipeline3_skips_consolidation_after_extraction_failure(monkeypatch, capsys):
    calls = []

    class DummyConn:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def commit(self):
            calls.append(("commit",))

    monkeypatch.setattr(cli, "connect", lambda: DummyConn())
    monkeypatch.setattr(cli, "phase3_schema_preflight", lambda conn: None)
    monkeypatch.setattr(cli, "apply_phase3_reclassification_invalidations", lambda conn: 0)
    monkeypatch.setattr(cli, "active_beliefs_with_other_consolidator_version", lambda conn: 0)
    monkeypatch.setattr(
        cli,
        "fetch_phase3_conversation_batch",
        lambda conn, limit: ["conv-failed", "conv-ok"],
    )
    monkeypatch.setattr(cli, "default_extractor_model_id", lambda: "model-a")
    monkeypatch.setattr(cli, "IkLlamaExtractorClient", lambda: object())
    monkeypatch.setattr(
        cli,
        "run_extractor_health_smoke",
        lambda client, *, model_id: calls.append(("smoke", model_id)),
    )
    monkeypatch.setattr(
        cli,
        "upsert_progress",
        lambda conn, **kwargs: calls.append(("progress", kwargs)),
    )

    def fake_extract(conn, *, conversation_id, **kwargs):
        calls.append(("extract", conversation_id))
        if conversation_id == "conv-failed":
            return SimpleNamespace(processed=2, created=1, skipped=0, failed=1)
        return SimpleNamespace(processed=1, created=3, skipped=0, failed=0)

    def fake_consolidate(conn, *, conversation_id, **kwargs):
        calls.append(("consolidate", conversation_id))
        return SimpleNamespace(processed=1, created=3, superseded=0, contradictions=0)

    monkeypatch.setattr(cli, "run_extract_batches", fake_extract)
    monkeypatch.setattr(cli, "run_consolidate_batches", fake_consolidate)

    assert cli.main(["pipeline-3", "--limit", "2"]) == 1
    assert ("consolidate", "conv-failed") not in calls
    assert ("consolidate", "conv-ok") in calls
    progress_calls = [call for call in calls if call[0] == "progress"]
    assert progress_calls[0][1]["stage"] == "consolidator"
    assert progress_calls[0][1]["status"] == "failed"
    assert progress_calls[0][1]["scope"] == "conversation:conv-failed"
    assert "consolidate skipped conversation=conv-failed" in capsys.readouterr().err


def test_run_extract_batches_wraps_batch_in_health_smoke(monkeypatch):
    calls = []

    class DummyConn:
        def commit(self):
            calls.append(("commit",))

    monkeypatch.setattr(cli, "default_extractor_model_id", lambda: "model-a")
    monkeypatch.setattr(cli, "IkLlamaExtractorClient", lambda: object())
    monkeypatch.setattr(
        cli,
        "run_extractor_health_smoke",
        lambda client, *, model_id: calls.append(("smoke", model_id)),
    )
    results = [
        SimpleNamespace(processed=1, created=2, skipped=0, failed=0),
        SimpleNamespace(processed=0, created=0, skipped=0, failed=0),
    ]

    def fake_extract_pending(*args, **kwargs):
        calls.append(("extract_pending", kwargs["model_version"], kwargs["client"] is not None))
        return results.pop(0)

    monkeypatch.setattr(cli, "extract_pending_claims", fake_extract_pending)

    result = cli.run_extract_batches(DummyConn(), batch_size=10, limit=None)

    assert result.processed == 1
    assert calls[0] == ("smoke", "model-a")
    assert calls[-1] == ("smoke", "model-a")
    assert ("extract_pending", "model-a", True) in calls


def test_run_extract_batches_stops_after_failed_batch(monkeypatch):
    calls = []

    class DummyConn:
        def commit(self):
            calls.append(("commit",))

    monkeypatch.setattr(cli, "default_extractor_model_id", lambda: "model-a")
    monkeypatch.setattr(cli, "IkLlamaExtractorClient", lambda: object())
    monkeypatch.setattr(
        cli,
        "run_extractor_health_smoke",
        lambda client, *, model_id: calls.append(("smoke", model_id)),
    )

    def fake_extract_pending(*args, **kwargs):
        calls.append(("extract_pending", kwargs["conversation_id"]))
        return SimpleNamespace(processed=1, created=0, skipped=0, failed=1)

    monkeypatch.setattr(cli, "extract_pending_claims", fake_extract_pending)

    result = cli.run_extract_batches(
        DummyConn(),
        batch_size=1,
        limit=3,
        conversation_id="conv-a",
    )

    assert result.processed == 1
    assert result.failed == 1
    assert calls.count(("extract_pending", "conv-a")) == 1
    assert calls.count(("smoke", "model-a")) == 2
