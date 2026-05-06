from __future__ import annotations

import json
import os
import signal
import time
from collections import Counter
from collections.abc import Callable
from contextlib import contextmanager
from dataclasses import dataclass, replace
from typing import Any, Protocol

import psycopg
from psycopg.types.json import Jsonb

from engram.consolidator import apply_phase3_reclassification_invalidations
from engram.progress import upsert_progress
from engram.segmenter import (
    IK_LLAMA_BASE_URL,
    SegmenterContextBudgetError,
    assert_context_budget,
    default_segmenter_probe,
    ensure_local_base_url,
    error_summary,
    http_json,
    sanitize_model_json,
    sanitize_model_string,
)


EXTRACTION_PROMPT_VERSION = "extractor.v6.d063.null-object-repair"
EXTRACTION_REQUEST_PROFILE_VERSION = (
    "ik-llama-json-schema.d034.v8.extractor-8192-null-object-repair"
)
EXTRACTION_SYSTEM_PROMPT = (
    "You are a deterministic claim extractor for a local-first personal memory "
    "pipeline. Return only schema-valid JSON."
)
EXTRACTOR_HEALTH_SMOKE_PROMPT = (
    'Health check only. Return exactly one schema-valid JSON object: {"claims":[]}.'
)
DEFAULT_EXTRACTION_MAX_TOKENS = int(os.environ.get("ENGRAM_EXTRACTOR_MAX_TOKENS", "8192"))
EXTRACTION_REQUEST_TIMEOUT_SECONDS = int(
    os.environ.get("ENGRAM_EXTRACTOR_TIMEOUT_SECONDS", "600")
)
EXTRACTION_RETRIES = int(os.environ.get("ENGRAM_EXTRACTOR_RETRIES", "1"))
EXTRACTOR_INFLIGHT_TIMEOUT_SECONDS = int(
    os.environ.get("ENGRAM_EXTRACTOR_INFLIGHT_TIMEOUT_SECONDS", "900")
)
MAX_EXTRACTION_ERROR_COUNT = int(os.environ.get("ENGRAM_EXTRACTOR_MAX_ERROR_COUNT", "3"))
DEFAULT_EXTRACTION_CHUNK_MAX_MESSAGES = int(
    os.environ.get("ENGRAM_EXTRACTOR_CHUNK_MAX_MESSAGES", "12")
)
DEFAULT_EXTRACTION_CHUNK_MAX_CONTENT_CHARS = int(
    os.environ.get("ENGRAM_EXTRACTOR_CHUNK_MAX_CONTENT_CHARS", "6000")
)
EXTRACTION_ADAPTIVE_SPLIT_MAX_DEPTH = int(
    os.environ.get("ENGRAM_EXTRACTOR_ADAPTIVE_SPLIT_MAX_DEPTH", "4")
)


STABILITY_CLASSES = [
    "identity",
    "preference",
    "project_status",
    "goal",
    "task",
    "mood",
    "relationship",
]


PREDICATE_VOCABULARY: list[dict[str, Any]] = [
    {"predicate": "has_name", "stability_class": "identity", "cardinality_class": "single_current", "object_kind": "text", "group_object_keys": [], "required_object_keys": []},
    {"predicate": "has_pronouns", "stability_class": "identity", "cardinality_class": "single_current", "object_kind": "text", "group_object_keys": [], "required_object_keys": []},
    {"predicate": "born_on", "stability_class": "identity", "cardinality_class": "single_current", "object_kind": "text", "group_object_keys": [], "required_object_keys": []},
    {"predicate": "lives_at", "stability_class": "identity", "cardinality_class": "single_current", "object_kind": "json", "group_object_keys": [], "required_object_keys": ["address_line1"]},
    {"predicate": "holds_role_at", "stability_class": "identity", "cardinality_class": "single_current", "object_kind": "json", "group_object_keys": [], "required_object_keys": ["role", "employer"]},
    {"predicate": "has_pet", "stability_class": "identity", "cardinality_class": "multi_current", "object_kind": "json", "group_object_keys": ["name", "species"], "required_object_keys": ["species"]},
    {"predicate": "is_related_to", "stability_class": "relationship", "cardinality_class": "multi_current", "object_kind": "json", "group_object_keys": ["name"], "required_object_keys": ["name", "kind"]},
    {"predicate": "is_friends_with", "stability_class": "relationship", "cardinality_class": "multi_current", "object_kind": "text", "group_object_keys": ["text"], "required_object_keys": []},
    {"predicate": "works_with", "stability_class": "relationship", "cardinality_class": "multi_current", "object_kind": "text", "group_object_keys": ["text"], "required_object_keys": []},
    {"predicate": "prefers", "stability_class": "preference", "cardinality_class": "multi_current", "object_kind": "text", "group_object_keys": ["text"], "required_object_keys": []},
    {"predicate": "dislikes", "stability_class": "preference", "cardinality_class": "multi_current", "object_kind": "text", "group_object_keys": ["text"], "required_object_keys": []},
    {"predicate": "believes", "stability_class": "preference", "cardinality_class": "multi_current", "object_kind": "text", "group_object_keys": ["text"], "required_object_keys": []},
    {"predicate": "uses_tool", "stability_class": "preference", "cardinality_class": "multi_current", "object_kind": "text", "group_object_keys": ["text"], "required_object_keys": []},
    {"predicate": "drives", "stability_class": "preference", "cardinality_class": "single_current", "object_kind": "text", "group_object_keys": [], "required_object_keys": []},
    {"predicate": "eats_diet", "stability_class": "preference", "cardinality_class": "single_current", "object_kind": "text", "group_object_keys": [], "required_object_keys": []},
    {"predicate": "working_on", "stability_class": "project_status", "cardinality_class": "multi_current", "object_kind": "text", "group_object_keys": ["text"], "required_object_keys": []},
    {"predicate": "project_status_is", "stability_class": "project_status", "cardinality_class": "single_current_per_object", "object_kind": "json", "group_object_keys": ["project"], "required_object_keys": ["project", "status"]},
    {"predicate": "owns_repo", "stability_class": "project_status", "cardinality_class": "multi_current", "object_kind": "text", "group_object_keys": ["text"], "required_object_keys": []},
    {"predicate": "wants_to", "stability_class": "goal", "cardinality_class": "multi_current", "object_kind": "text", "group_object_keys": ["text"], "required_object_keys": []},
    {"predicate": "plans_to", "stability_class": "goal", "cardinality_class": "multi_current", "object_kind": "json", "group_object_keys": ["action"], "required_object_keys": ["action"]},
    {"predicate": "intends_to", "stability_class": "goal", "cardinality_class": "multi_current", "object_kind": "text", "group_object_keys": ["text"], "required_object_keys": []},
    {"predicate": "must_do", "stability_class": "task", "cardinality_class": "event", "object_kind": "text", "group_object_keys": ["text"], "required_object_keys": []},
    {"predicate": "committed_to", "stability_class": "task", "cardinality_class": "event", "object_kind": "json", "group_object_keys": ["action", "with_party"], "required_object_keys": ["action"]},
    {"predicate": "feels", "stability_class": "mood", "cardinality_class": "multi_current", "object_kind": "text", "group_object_keys": ["text"], "required_object_keys": []},
    {"predicate": "relationship_with", "stability_class": "relationship", "cardinality_class": "single_current_per_object", "object_kind": "json", "group_object_keys": ["name"], "required_object_keys": ["name", "status"]},
    {"predicate": "met_with", "stability_class": "relationship", "cardinality_class": "event", "object_kind": "json", "group_object_keys": ["name", "when"], "required_object_keys": ["name"]},
    {"predicate": "talked_about", "stability_class": "preference", "cardinality_class": "event", "object_kind": "text", "group_object_keys": ["text"], "required_object_keys": []},
    {"predicate": "studied", "stability_class": "identity", "cardinality_class": "multi_current", "object_kind": "text", "group_object_keys": ["text"], "required_object_keys": []},
    {"predicate": "traveled_to", "stability_class": "identity", "cardinality_class": "event", "object_kind": "json", "group_object_keys": ["place", "when"], "required_object_keys": ["place"]},
]
PREDICATE_ENUM = [row["predicate"] for row in PREDICATE_VOCABULARY]
PREDICATE_BY_NAME = {row["predicate"]: row for row in PREDICATE_VOCABULARY}


class ExtractionError(RuntimeError):
    """Raised when the local extractor returns unusable output."""


class ExtractorResponseError(ExtractionError):
    def __init__(self, message: str, *, response: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.response = response


class ExtractorRequestTimeout(ExtractionError):
    """Raised when one extraction request exceeds the configured deadline."""


@dataclass(frozen=True)
class ClaimDraft:
    subject_text: str
    predicate: str
    object_text: str | None
    object_json: dict[str, Any] | None
    stability_class: str
    confidence: float
    evidence_message_ids: list[str]
    rationale: str
    raw: dict[str, Any] | None = None


@dataclass(frozen=True)
class ExtractorModelOutput:
    claims: list[ClaimDraft]
    model_response: str
    parse_metadata: dict[str, Any]
    relaxed_schema: bool = False


@dataclass(frozen=True)
class SegmentMessage:
    id: str
    sequence_index: int
    role: str | None
    content_text: str | None


@dataclass(frozen=True)
class SegmentPayload:
    id: str
    generation_id: str
    conversation_id: str
    source_kind: str
    message_ids: list[str]
    content_text: str
    summary_text: str | None
    privacy_tier: int
    messages: list[SegmentMessage]


@dataclass(frozen=True)
class ExtractionResult:
    extraction_id: str
    segment_id: str
    claim_count: int
    status: str
    dropped_count: int = 0
    noop: bool = False


@dataclass(frozen=True)
class ExtractionBatchResult:
    processed: int
    created: int
    skipped: int
    failed: int


class ExtractorClient(Protocol):
    def extract(
        self,
        prompt: str,
        *,
        model_id: str,
        max_tokens: int,
        allowed_message_ids: list[str] | None = None,
        relaxed_schema: bool = False,
    ) -> ExtractorModelOutput | list[ClaimDraft]:
        ...


def default_extractor_model_id() -> str:
    configured = os.environ.get("ENGRAM_EXTRACTOR_MODEL") or os.environ.get(
        "ENGRAM_SEGMENTER_MODEL"
    )
    if configured:
        return configured
    return default_segmenter_probe().model_id


class IkLlamaExtractorClient:
    def __init__(
        self,
        base_url: str = IK_LLAMA_BASE_URL,
        *,
        context_window: int | None = None,
    ) -> None:
        ensure_local_base_url(base_url)
        self.base_url = base_url.rstrip("/")
        self._context_window = context_window

    def context_window(self) -> int | None:
        if self._context_window is not None:
            return self._context_window
        self._context_window = default_segmenter_probe().context_window
        return self._context_window

    def extract(
        self,
        prompt: str,
        *,
        model_id: str,
        max_tokens: int,
        allowed_message_ids: list[str] | None = None,
        relaxed_schema: bool = False,
    ) -> ExtractorModelOutput:
        payload = {
            "model": model_id,
            "messages": [
                {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            "stream": False,
            "temperature": 0,
            "top_p": 1,
            "max_tokens": max_tokens,
            "chat_template_kwargs": {"enable_thinking": False},
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "ClaimExtractionResult",
                    "strict": True,
                    "schema": extraction_json_schema(
                        allowed_message_ids,
                        relaxed_schema=relaxed_schema,
                    ),
                },
            },
        }
        assert_context_budget(
            prompt,
            max_tokens=max_tokens,
            context_window=self.context_window(),
        )
        response = http_json(
            "POST",
            f"{self.base_url}/v1/chat/completions",
            payload=payload,
            timeout=EXTRACTION_REQUEST_TIMEOUT_SECONDS,
        )
        return parse_extraction_response(response, relaxed_schema=relaxed_schema)


def extraction_json_schema(
    allowed_message_ids: list[str] | None = None,
    *,
    relaxed_schema: bool = False,
) -> dict[str, Any]:
    message_id_items: dict[str, Any] = {"type": "string"}
    if allowed_message_ids is not None:
        if not relaxed_schema:
            message_id_items["enum"] = list(dict.fromkeys(allowed_message_ids))
        else:
            message_id_items["pattern"] = (
                "^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-"
                "[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
            )
    predicate_schema: dict[str, Any] = {"type": "string", "enum": PREDICATE_ENUM}
    claim_item: dict[str, Any] = {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "subject_text",
            "predicate",
            "object_text",
            "object_json",
            "stability_class",
            "confidence",
            "evidence_message_ids",
            "rationale",
        ],
        "properties": {
            "subject_text": {"type": "string", "minLength": 1},
            "predicate": predicate_schema,
            "object_text": {"type": ["string", "null"], "minLength": 1},
            "object_json": {"type": ["object", "null"], "additionalProperties": True},
            "stability_class": {"type": "string", "enum": STABILITY_CLASSES},
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
            "evidence_message_ids": {
                "type": "array",
                "minItems": 1,
                "items": message_id_items,
            },
            "rationale": {"type": "string"},
        },
    }
    if not relaxed_schema:
        # The shared schema-construction fallback drops both the message-id enum
        # and this oneOf branch; prompt rules plus Python validation remain
        # authoritative in relaxed mode.
        claim_item["oneOf"] = [
            {
                "required": ["object_text", "object_json"],
                "properties": {
                    "object_text": {"type": "string", "minLength": 1},
                    "object_json": {"type": "null"},
                },
            },
            {
                "required": ["object_text", "object_json"],
                "properties": {
                    "object_text": {"type": "null"},
                    "object_json": {"type": "object", "additionalProperties": True},
                },
            },
        ]
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["claims"],
        "properties": {
            "claims": {
                "type": "array",
                "items": claim_item,
            }
        },
    }


def parse_extraction_response(
    response: dict[str, Any],
    *,
    relaxed_schema: bool = False,
) -> ExtractorModelOutput:
    choices = response.get("choices")
    if not isinstance(choices, list) or not choices:
        raise ExtractorResponseError("extractor response missing choices", response=response)
    message = choices[0].get("message") if isinstance(choices[0], dict) else None
    if not isinstance(message, dict):
        raise ExtractorResponseError("extractor response missing choices[0].message", response=response)
    content = message.get("content")
    if not isinstance(content, str) or not content.strip():
        if message.get("reasoning_content"):
            raise ExtractorResponseError(
                "extractor returned payload only in reasoning_content",
                response=response,
            )
        raise ExtractorResponseError("extractor returned empty message content", response=response)
    stripped = content.strip()
    if stripped.startswith("```"):
        raise ExtractorResponseError("extractor returned Markdown-fenced JSON", response=response)
    try:
        payload = json.loads(stripped)
    except json.JSONDecodeError as exc:
        raise ExtractorResponseError(
            f"extractor returned invalid JSON: {exc}",
            response=response,
        ) from exc
    claims = parse_extraction_payload(payload, relaxed_schema=relaxed_schema)
    usage = response.get("usage") if isinstance(response.get("usage"), dict) else {}
    return ExtractorModelOutput(
        claims=claims,
        model_response=stripped,
        parse_metadata={"usage": usage, "relaxed_schema": relaxed_schema},
        relaxed_schema=relaxed_schema,
    )


def parse_extraction_payload(payload: Any, *, relaxed_schema: bool = False) -> list[ClaimDraft]:
    if not isinstance(payload, dict) or set(payload) != {"claims"}:
        raise ExtractionError("extraction payload must contain only claims")
    claims = payload["claims"]
    if not isinstance(claims, list):
        raise ExtractionError("extraction payload claims must be a list")
    drafts: list[ClaimDraft] = []
    required = {
        "subject_text",
        "predicate",
        "object_text",
        "object_json",
        "stability_class",
        "confidence",
        "evidence_message_ids",
        "rationale",
    }
    for index, item in enumerate(claims):
        if not isinstance(item, dict) or set(item) != required:
            raise ExtractionError(f"claim {index} does not match the schema")
        if not isinstance(item["subject_text"], str) or not item["subject_text"].strip():
            raise ExtractionError(f"claim {index} has empty subject_text")
        predicate = item["predicate"]
        if not isinstance(predicate, str) or (not relaxed_schema and predicate not in PREDICATE_ENUM):
            raise ExtractionError(f"claim {index} has invalid predicate")
        object_text = item["object_text"]
        object_json = item["object_json"]
        if object_text is not None and (not isinstance(object_text, str) or not object_text.strip()):
            raise ExtractionError(f"claim {index} has empty object_text")
        if object_json is not None and not isinstance(object_json, dict):
            raise ExtractionError(f"claim {index} has invalid object_json")
        stability_class = item["stability_class"]
        if stability_class not in STABILITY_CLASSES:
            raise ExtractionError(f"claim {index} has invalid stability_class")
        confidence = item["confidence"]
        if not isinstance(confidence, int | float) or not 0 <= float(confidence) <= 1:
            raise ExtractionError(f"claim {index} has invalid confidence")
        evidence_ids = item["evidence_message_ids"]
        if (
            not isinstance(evidence_ids, list)
            or not evidence_ids
            or not all(isinstance(value, str) and value for value in evidence_ids)
        ):
            raise ExtractionError(f"claim {index} has invalid evidence_message_ids")
        rationale = item["rationale"]
        if not isinstance(rationale, str):
            raise ExtractionError(f"claim {index} has invalid rationale")
        drafts.append(
            ClaimDraft(
                subject_text=item["subject_text"],
                predicate=predicate,
                object_text=object_text,
                object_json=object_json,
                stability_class=stability_class,
                confidence=float(confidence),
                evidence_message_ids=evidence_ids,
                rationale=rationale,
            )
        )
    return drafts


def extract_claims_from_segment(
    conn: psycopg.Connection,
    segment_id: str,
    *,
    model_version: str | None = None,
    prompt_version: str = EXTRACTION_PROMPT_VERSION,
    client: ExtractorClient | None = None,
    max_tokens: int = DEFAULT_EXTRACTION_MAX_TOKENS,
    force: bool = False,
    retries: int = EXTRACTION_RETRIES,
) -> ExtractionResult:
    apply_phase3_reclassification_invalidations(conn)
    reap_stale_extractions(conn)
    model_id = model_version or default_extractor_model_id()
    segment = fetch_segment_payload(conn, segment_id)

    existing = find_existing_extraction(
        conn,
        segment_id=segment_id,
        prompt_version=prompt_version,
        model_version=model_id,
    )
    if existing and existing["status"] == "extracted" and not force:
        return ExtractionResult(
            extraction_id=existing["id"],
            segment_id=segment_id,
            claim_count=existing["claim_count"],
            status="extracted",
            noop=True,
        )
    if existing and existing["status"] == "extracting":
        extraction_id = existing["id"]
    else:
        extraction_id = create_extraction_row(
            conn,
            segment,
            prompt_version=prompt_version,
            model_version=model_id,
        )

    chunks = extraction_prompt_chunks(segment)
    extractor = client or IkLlamaExtractorClient()
    try:
        output = extract_segment_chunks(
            extractor,
            chunks,
            model_id=model_id,
            max_tokens=max_tokens,
            retries=retries,
        )
    except Exception as exc:
        mark_extraction_failed(
            conn,
            extraction_id,
            failure_kind=failure_kind_for_exception(exc),
            error=exc,
            model_response=response_text_from_exception(exc),
        )
        upsert_progress(
            conn,
            stage="extractor",
            scope=f"conversation:{segment.conversation_id}",
            status="failed",
            position={"conversation_id": segment.conversation_id, "segment_id": segment.id},
            last_error=error_summary(exc),
            increment_error=True,
        )
        return ExtractionResult(extraction_id, segment_id, 0, "failed")

    valid, dropped = salvage_claims(output.claims, segment)
    dropped = chunk_dropped_claims(output) + dropped
    if not valid and dropped:
        output, valid, dropped = retry_after_trigger_violation(
            extractor,
            segment,
            chunks,
            prior_output=output,
            prior_dropped=dropped,
            model_id=model_id,
            max_tokens=max_tokens,
            retries=retries,
        )
    if not valid and dropped:
        payload = {
            "model_response": output.model_response,
            "parse_metadata": output.parse_metadata,
            "dropped_claims": dropped,
            "failure_kind": "trigger_violation",
            "last_error": "all extracted claims failed pre-validation",
        }
        copy_validation_repair_payload(payload, output)
        conn.execute(
            """
            UPDATE claim_extractions
            SET status = 'failed',
                completed_at = now(),
                claim_count = 0,
                raw_payload = %s
            WHERE id = %s
            """,
            (Jsonb(payload), extraction_id),
        )
        upsert_progress(
            conn,
            stage="extractor",
            scope=f"conversation:{segment.conversation_id}",
            status="failed",
            position={"conversation_id": segment.conversation_id, "segment_id": segment.id},
            last_error="all extracted claims failed pre-validation",
            increment_error=True,
        )
        return ExtractionResult(extraction_id, segment_id, 0, "failed", dropped_count=len(dropped))

    inserted = insert_valid_claims(
        conn,
        extraction_id,
        segment,
        valid,
        prompt_version=prompt_version,
        model_version=model_id,
    )
    raw_payload = {
        "model_response": output.model_response,
        "parse_metadata": output.parse_metadata,
        "dropped_claims": dropped,
        "failure_kind": None,
    }
    copy_validation_repair_payload(raw_payload, output)
    with conn.transaction():
        conn.execute(
            """
            UPDATE claim_extractions
            SET status = 'extracted',
                completed_at = now(),
                claim_count = %s,
                raw_payload = %s
            WHERE id = %s
            """,
            (inserted, Jsonb(raw_payload), extraction_id),
        )
        conn.execute(
            """
            UPDATE claim_extractions
            SET status = 'superseded',
                completed_at = COALESCE(completed_at, now()),
                raw_payload = raw_payload || jsonb_build_object(
                    'superseded_by_extraction_id',
                    %s::text
                )
            WHERE segment_id = %s
              AND id <> %s
              AND status = 'extracted'
            """,
            (extraction_id, segment.id, extraction_id),
        )
    upsert_progress(
        conn,
        stage="extractor",
        scope=f"conversation:{segment.conversation_id}",
        status="completed",
        position={
            "conversation_id": segment.conversation_id,
            "segment_id": segment.id,
            "segment_index_within_conversation": segment_index_within_conversation(conn, segment.id),
        },
    )
    return ExtractionResult(
        extraction_id=extraction_id,
        segment_id=segment_id,
        claim_count=inserted,
        status="extracted",
        dropped_count=len(dropped),
    )


def run_extractor_health_smoke(
    client: ExtractorClient | None = None,
    *,
    model_id: str | None = None,
    max_tokens: int = 128,
) -> None:
    extractor = client or IkLlamaExtractorClient()
    resolved_model_id = model_id or default_extractor_model_id()
    call_extractor_with_retries(
        extractor,
        EXTRACTOR_HEALTH_SMOKE_PROMPT,
        model_id=resolved_model_id,
        max_tokens=max_tokens,
        allowed_message_ids=None,
        retries=0,
    )


def call_extractor_with_retries(
    client: ExtractorClient,
    prompt: str,
    *,
    model_id: str,
    max_tokens: int,
    allowed_message_ids: list[str] | None,
    retries: int,
) -> ExtractorModelOutput:
    errors: list[str] = []
    relaxed_schema_only = False
    for attempt in range(retries + 1):
        try:
            with extractor_request_deadline(EXTRACTION_REQUEST_TIMEOUT_SECONDS):
                return coerce_client_output(
                    client.extract(
                        prompt,
                        model_id=model_id,
                        max_tokens=max_tokens,
                        allowed_message_ids=allowed_message_ids,
                        relaxed_schema=relaxed_schema_only,
                    )
                )
        except Exception as exc:
            errors.append(error_summary(exc))
            if is_schema_construction_error(exc) and not relaxed_schema_only:
                relaxed_schema_only = True
                try:
                    with extractor_request_deadline(EXTRACTION_REQUEST_TIMEOUT_SECONDS):
                        return coerce_client_output(
                            client.extract(
                                prompt,
                                model_id=model_id,
                                max_tokens=max_tokens,
                                allowed_message_ids=allowed_message_ids,
                                relaxed_schema=True,
                            )
                        )
                except Exception as relaxed_exc:
                    errors.append(error_summary(relaxed_exc))
                    if attempt >= retries:
                        attach_attempt_diagnostics(
                            relaxed_exc,
                            errors,
                            max_tokens=max_tokens,
                        )
                        raise
                    continue
            if attempt >= retries:
                attach_attempt_diagnostics(exc, errors, max_tokens=max_tokens)
                raise
            continue
    raise ExtractionError("extractor retry loop exhausted unexpectedly")


def coerce_client_output(output: ExtractorModelOutput | list[ClaimDraft]) -> ExtractorModelOutput:
    if isinstance(output, ExtractorModelOutput):
        return output
    claims_payload = [
        {
            "subject_text": claim.subject_text,
            "predicate": claim.predicate,
            "object_text": claim.object_text,
            "object_json": claim.object_json,
            "stability_class": claim.stability_class,
            "confidence": claim.confidence,
            "evidence_message_ids": claim.evidence_message_ids,
            "rationale": claim.rationale,
        }
        for claim in output
    ]
    return ExtractorModelOutput(
        claims=list(output),
        model_response=json.dumps({"claims": claims_payload}, sort_keys=True),
        parse_metadata={"fake_client": True},
    )


def extract_segment_chunks(
    client: ExtractorClient,
    chunks: list[SegmentPayload],
    *,
    model_id: str,
    max_tokens: int,
    retries: int,
    validation_feedback: str | None = None,
    adaptive_split: bool = True,
) -> ExtractorModelOutput:
    outputs: list[ExtractorModelOutput] = []
    chunk_metadata: list[dict[str, Any]] = []
    for index, chunk in enumerate(chunks, start=1):
        extract_chunk_adaptively(
            client,
            chunk,
            model_id=model_id,
            max_tokens=max_tokens,
            retries=retries,
            validation_feedback=validation_feedback,
            adaptive_split=adaptive_split,
            root_chunk_index=index,
            root_chunk_count=len(chunks),
            split_path=[index],
            split_depth=0,
            outputs=outputs,
            chunk_metadata=chunk_metadata,
        )

    if len(outputs) == 1:
        output = outputs[0]
        return ExtractorModelOutput(
            claims=output.claims,
            model_response=output.model_response,
            parse_metadata={
                **output.parse_metadata,
                "chunked": False,
                "chunk_count": 1,
                "chunks": chunk_metadata,
            },
            relaxed_schema=output.relaxed_schema,
        )

    claims = [claim for output in outputs for claim in output.claims]
    dropped = [drop for output in outputs for drop in chunk_dropped_claims(output)]
    return ExtractorModelOutput(
        claims=claims,
        model_response=json.dumps(
            {"chunks": [output.model_response for output in outputs]},
            sort_keys=True,
        ),
        parse_metadata={
            "chunked": True,
            "chunk_count": len(outputs),
            "chunks": chunk_metadata,
            "chunk_dropped_claims": dropped,
        },
        relaxed_schema=any(output.relaxed_schema for output in outputs),
    )


def extract_chunk_adaptively(
    client: ExtractorClient,
    chunk: SegmentPayload,
    *,
    model_id: str,
    max_tokens: int,
    retries: int,
    validation_feedback: str | None,
    adaptive_split: bool,
    root_chunk_index: int,
    root_chunk_count: int,
    split_path: list[int],
    split_depth: int,
    outputs: list[ExtractorModelOutput],
    chunk_metadata: list[dict[str, Any]],
) -> None:
    try:
        output = call_extractor_with_retries(
            client,
            build_extraction_prompt(chunk, validation_feedback=validation_feedback),
            model_id=model_id,
            max_tokens=max_tokens,
            allowed_message_ids=chunk.message_ids,
            retries=retries,
        )
    except Exception as exc:
        subchunks = split_extraction_chunk(chunk)
        if adaptive_split and split_depth < EXTRACTION_ADAPTIVE_SPLIT_MAX_DEPTH and len(subchunks) > 1:
            child_retries = max(0, retries - 1)
            for subindex, subchunk in enumerate(subchunks, start=1):
                extract_chunk_adaptively(
                    client,
                    subchunk,
                    model_id=model_id,
                    max_tokens=max_tokens,
                    retries=child_retries,
                    validation_feedback=validation_feedback,
                    adaptive_split=adaptive_split,
                    root_chunk_index=root_chunk_index,
                    root_chunk_count=root_chunk_count,
                    split_path=[*split_path, subindex],
                    split_depth=split_depth + 1,
                    outputs=outputs,
                    chunk_metadata=chunk_metadata,
                )
            return
        attach_chunk_diagnostics(
            exc,
            chunk_index=root_chunk_index,
            chunk_count=root_chunk_count,
            split_depth=split_depth,
            split_path=split_path,
            message_count=len(chunk.message_ids),
        )
        raise

    output = validate_chunk_output(output, chunk, split_path=split_path)
    outputs.append(output)
    chunk_metadata.append(
        {
            "root_chunk_index": root_chunk_index,
            "root_chunk_count": root_chunk_count,
            "split_path": split_path,
            "split_depth": split_depth,
            "message_count": len(chunk.message_ids),
            "claim_count": len(output.claims),
            "parse_metadata": output.parse_metadata,
        }
    )


def retry_after_trigger_violation(
    client: ExtractorClient,
    segment: SegmentPayload,
    chunks: list[SegmentPayload],
    *,
    prior_output: ExtractorModelOutput,
    prior_dropped: list[dict[str, Any]],
    model_id: str,
    max_tokens: int,
    retries: int,
) -> tuple[ExtractorModelOutput, list[ClaimDraft], list[dict[str, Any]]]:
    feedback = build_validation_repair_feedback(prior_dropped)
    try:
        repaired = extract_segment_chunks(
            client,
            chunks,
            model_id=model_id,
            max_tokens=max_tokens,
            retries=0,
            validation_feedback=feedback,
            adaptive_split=False,
        )
    except Exception as exc:
        return (
            replace(
                prior_output,
                parse_metadata={
                    **prior_output.parse_metadata,
                    "validation_repair": {
                        "attempted": True,
                        "result": "failed",
                        "prior_dropped_count": len(prior_dropped),
                        "prior_error_counts": dropped_error_counts(prior_dropped),
                        "prior_dropped_claims": redact_dropped_claims(prior_dropped),
                        "last_error": error_summary(exc),
                    },
                },
            ),
            [],
            prior_dropped,
        )

    valid, dropped = salvage_claims(repaired.claims, segment)
    dropped = chunk_dropped_claims(repaired) + dropped
    return (
        replace(
            repaired,
            parse_metadata={
                **repaired.parse_metadata,
                "validation_repair": {
                    "attempted": True,
                    "result": "accepted" if (valid or not dropped) else "still_invalid",
                    "prior_dropped_count": len(prior_dropped),
                    "prior_error_counts": dropped_error_counts(prior_dropped),
                    "prior_dropped_claims": redact_dropped_claims(prior_dropped),
                    "final_dropped_count": len(dropped),
                    "final_error_counts": dropped_error_counts(dropped),
                },
            },
        ),
        valid,
        dropped,
    )


def build_validation_repair_feedback(dropped: list[dict[str, Any]]) -> str:
    error_counts = dropped_error_counts(dropped)
    rendered_counts = "\n".join(
        f"- {error}: {count}" for error, count in error_counts.items()
    )
    if not rendered_counts:
        rendered_counts = "- unknown validation error: 1"
    null_sweep_section = render_null_object_repair_feedback(dropped)
    repair_details = rendered_counts
    if null_sweep_section:
        repair_details = f"{repair_details}\n{null_sweep_section}"
    return f"""
Validation repair retry:
The previous extraction response was schema-valid JSON but failed local
pre-insert validation, so no claims survived. Error classes:
{repair_details}

Return a complete corrected extraction for the same segment. Do not copy invalid
claims from the previous attempt. For text predicates, object_text must be a
non-empty directly evidenced string and object_json must be null. For JSON
predicates, object_text must be null and object_json must contain every required
object key listed above. If the evidence does not support the required object
value, omit that claim. If no valid claims remain, return exactly {{"claims":[]}}.
""".strip()


def render_null_object_repair_feedback(dropped: list[dict[str, Any]]) -> str:
    redacted = redact_dropped_claims(dropped)
    null_drops = [
        drop
        for drop in redacted
        if drop.get("error") == "exactly one of object_text or object_json is required"
        and drop.get("object_text_type") == "null"
        and drop.get("object_json_type") == "null"
    ]
    if not null_drops:
        return ""

    predicates = sorted(
        {
            str(drop["predicate"])
            for drop in null_drops
            if isinstance(drop.get("predicate"), str)
        }
    )
    predicate_list = ", ".join(predicates) if predicates else "(none)"
    label = (
        "full null-object sweep"
        if len(null_drops) == len(redacted)
        else "mixed null-object drops"
    )
    return f"""
Null-object repair diagnostics ({label}):
- total null-object drops: {len(null_drops)}
- distinct predicate count: {len(predicates)}
- predicates: {predicate_list}
- object-shape class: object_text=null, object_json=null
- repair instruction: provide directly evidenced objects for these claims or
  omit them.
- empty-output instruction: if no valid claims remain, return exactly
  {{"claims":[]}}.
""".rstrip()


def dropped_error_counts(dropped: list[dict[str, Any]]) -> dict[str, int]:
    counts = Counter(
        str(drop.get("error") or "unknown validation error")
        for drop in dropped
        if isinstance(drop, dict)
    )
    return dict(sorted(counts.items()))


def redact_dropped_claims(dropped: list[dict[str, Any]]) -> list[dict[str, Any]]:
    redacted: list[dict[str, Any]] = []
    for drop in dropped:
        if not isinstance(drop, dict):
            continue
        item: dict[str, Any] = {}
        for key in ("reason", "index", "error", "split_path"):
            if key in drop:
                item[key] = drop[key]
        claim = drop.get("claim")
        if isinstance(claim, dict):
            item.update(redacted_claim_shape(claim))
        redacted.append(item)
    return redacted


def redacted_claim_shape(claim: dict[str, Any]) -> dict[str, Any]:
    shape: dict[str, Any] = {}
    for key in ("predicate", "stability_class"):
        value = claim.get(key)
        if isinstance(value, str):
            shape[key] = value
    shape["object_text_type"] = json_shape_type(claim, "object_text")
    shape["object_json_type"] = json_shape_type(claim, "object_json")
    object_json = claim.get("object_json")
    if isinstance(object_json, dict):
        shape["object_json_keys"] = sorted(str(key) for key in object_json)
    evidence_ids = claim.get("evidence_message_ids")
    if isinstance(evidence_ids, list):
        shape["evidence_message_count"] = len(evidence_ids)
    return shape


def json_shape_type(payload: dict[str, Any], key: str) -> str:
    if key not in payload:
        return "missing"
    value = payload[key]
    if value is None:
        return "null"
    if isinstance(value, str):
        return "string"
    if isinstance(value, dict):
        return "object"
    if isinstance(value, list):
        return "array"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int | float):
        return "number"
    return type(value).__name__


def copy_validation_repair_payload(
    raw_payload: dict[str, Any],
    output: ExtractorModelOutput,
) -> None:
    repair = output.parse_metadata.get("validation_repair")
    if isinstance(repair, dict):
        raw_payload["validation_repair"] = repair


def validate_chunk_output(
    output: ExtractorModelOutput,
    chunk: SegmentPayload,
    *,
    split_path: list[int],
) -> ExtractorModelOutput:
    valid, dropped = salvage_claims(
        output.claims,
        chunk,
        allowed_evidence_label="chunk message_ids",
    )
    if not dropped:
        return output
    chunk_drops = [
        {
            **drop,
            "split_path": list(split_path),
        }
        for drop in dropped
    ]
    return replace(
        output,
        claims=valid,
        parse_metadata={
            **output.parse_metadata,
            "chunk_dropped_claims": chunk_dropped_claims(output) + chunk_drops,
        },
    )


def chunk_dropped_claims(output: ExtractorModelOutput) -> list[dict[str, Any]]:
    dropped = output.parse_metadata.get("chunk_dropped_claims", [])
    if not isinstance(dropped, list):
        return []
    return [drop for drop in dropped if isinstance(drop, dict)]


def attach_attempt_diagnostics(
    exc: BaseException,
    errors: list[str],
    *,
    max_tokens: int,
) -> None:
    setattr(
        exc,
        "extractor_attempt_diagnostics",
        {
            "attempts": len(errors),
            "attempt_errors": list(errors),
            "attempt_max_tokens": [max_tokens for _ in errors],
            "decode_counts": [],
        },
    )


def attach_chunk_diagnostics(
    exc: BaseException,
    *,
    chunk_index: int,
    chunk_count: int,
    split_depth: int,
    split_path: list[int],
    message_count: int,
) -> None:
    diagnostics = getattr(exc, "extractor_attempt_diagnostics", {})
    if not isinstance(diagnostics, dict):
        diagnostics = {}
    diagnostics.update(
        {
            "chunk_index": chunk_index,
            "chunk_count": chunk_count,
            "split_depth": split_depth,
            "split_path": split_path,
            "chunk_message_count": message_count,
        }
    )
    setattr(exc, "extractor_attempt_diagnostics", diagnostics)


def is_schema_construction_error(exc: BaseException) -> bool:
    text = str(exc).lower()
    return (
        "grammar" in text
        or "schema construction" in text
        or "schema-construction" in text
        or "grammar-state" in text
    )


def response_text_from_exception(exc: BaseException) -> str | None:
    response = getattr(exc, "response", None)
    if isinstance(response, dict):
        try:
            return json.dumps(response, sort_keys=True)
        except TypeError:
            return str(response)
    return None


def failure_kind_for_exception(exc: BaseException) -> str:
    if isinstance(exc, SegmenterContextBudgetError):
        return "context_guard"
    if isinstance(exc, ExtractorRequestTimeout):
        return "service_unavailable"
    if isinstance(exc, ExtractorResponseError):
        text = str(exc).lower()
        if "json" in text or "markdown" in text or "empty" in text or "reasoning_content" in text:
            return "parse_error"
        return "schema_invalid"
    return "service_unavailable" if "unavailable" in str(exc).lower() else "retry_exhausted"


def mark_extraction_failed(
    conn: psycopg.Connection,
    extraction_id: str,
    *,
    failure_kind: str,
    error: BaseException,
    model_response: str | None = None,
) -> None:
    payload: dict[str, Any] = {
        "failure_kind": failure_kind,
        "last_error": error_summary(error),
        "model_response": model_response,
        "dropped_claims": [],
    }
    diagnostics = getattr(error, "extractor_attempt_diagnostics", None)
    if isinstance(diagnostics, dict):
        payload.update(diagnostics)
    conn.execute(
        """
        UPDATE claim_extractions
        SET status = 'failed',
            completed_at = now(),
            claim_count = 0,
            raw_payload = raw_payload || %s
        WHERE id = %s
        """,
        (Jsonb(payload), extraction_id),
    )


def salvage_claims(
    claims: list[ClaimDraft],
    segment: SegmentPayload,
    *,
    allowed_evidence_label: str = "segment message_ids",
) -> tuple[list[ClaimDraft], list[dict[str, Any]]]:
    valid: list[ClaimDraft] = []
    dropped: list[dict[str, Any]] = []
    allowed_evidence = set(segment.message_ids)
    for index, claim in enumerate(claims):
        claim, normalizations = normalize_claim_draft(claim)
        reason = validate_claim_draft(
            claim,
            allowed_evidence,
            allowed_evidence_label=allowed_evidence_label,
        )
        if reason:
            dropped.append(
                {
                    "reason": "trigger_violation",
                    "index": index,
                    "error": reason,
                    "claim": claim_to_payload(claim),
                }
            )
            continue
        valid.append(claim)
    return valid, dropped


def normalize_claim_draft(claim: ClaimDraft) -> tuple[ClaimDraft, list[dict[str, Any]]]:
    vocab = PREDICATE_BY_NAME.get(claim.predicate)
    if vocab is None:
        return claim, []

    normalizations: list[dict[str, Any]] = []
    normalized = claim
    if claim.stability_class != vocab["stability_class"]:
        normalizations.append(
            {
                "field": "stability_class",
                "from": claim.stability_class,
                "to": vocab["stability_class"],
            }
        )
        normalized = replace(normalized, stability_class=vocab["stability_class"])

    if (
        vocab["object_kind"] == "text"
        and normalized.object_text is not None
        and normalized.object_text.strip()
        and normalized.object_json is not None
    ):
        normalizations.append({"field": "object_json", "action": "dropped_for_text_predicate"})
        normalized = replace(normalized, object_json=None)
    elif (
        vocab["object_kind"] == "json"
        and isinstance(normalized.object_json, dict)
        and normalized.object_text is not None
    ):
        normalizations.append({"field": "object_text", "action": "dropped_for_json_predicate"})
        normalized = replace(normalized, object_text=None)

    if not normalizations:
        return normalized, []
    return replace(
        normalized,
        raw={
            **(normalized.raw or {}),
            "normalizations": normalizations,
        },
    ), normalizations


def validate_claim_draft(
    claim: ClaimDraft,
    allowed_evidence: set[str],
    *,
    allowed_evidence_label: str,
) -> str | None:
    if not claim.subject_text.strip():
        return "subject_text is empty"
    vocab = PREDICATE_BY_NAME.get(claim.predicate)
    if vocab is None:
        return f"unknown predicate: {claim.predicate}"
    if claim.stability_class != vocab["stability_class"]:
        return "stability_class does not match predicate vocabulary"
    if not claim.evidence_message_ids:
        return "evidence_message_ids is empty"
    if not set(claim.evidence_message_ids).issubset(allowed_evidence):
        return f"evidence_message_ids must be a subset of {allowed_evidence_label}"
    if (claim.object_text is None) == (claim.object_json is None):
        return "exactly one of object_text or object_json is required"
    if vocab["object_kind"] == "text":
        if claim.object_text is None or not claim.object_text.strip():
            return "predicate requires non-empty object_text"
    if vocab["object_kind"] == "json":
        if not isinstance(claim.object_json, dict):
            return "predicate requires object_json"
        for key in vocab["required_object_keys"]:
            if key not in claim.object_json:
                return f"object_json missing required key: {key}"
    return None


def insert_valid_claims(
    conn: psycopg.Connection,
    extraction_id: str,
    segment: SegmentPayload,
    claims: list[ClaimDraft],
    *,
    prompt_version: str,
    model_version: str,
) -> int:
    inserted = 0
    for claim in claims:
        subject_text, _ = sanitize_model_string(claim.subject_text)
        object_text, _ = sanitize_model_string(claim.object_text)
        object_json, _ = sanitize_model_json(claim.object_json)
        raw, _ = sanitize_model_json(
            {
                **(claim.raw or {}),
                "rationale": claim.rationale,
            }
        )
        conn.execute(
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
            VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s::uuid[], %s, %s, %s, %s, %s
            )
            """,
            (
                segment.id,
                segment.generation_id,
                segment.conversation_id,
                extraction_id,
                subject_text,
                claim.predicate,
                object_text,
                Jsonb(object_json) if object_json is not None else None,
                claim.stability_class,
                claim.confidence,
                claim.evidence_message_ids,
                prompt_version,
                model_version,
                EXTRACTION_REQUEST_PROFILE_VERSION,
                segment.privacy_tier,
                Jsonb(raw),
            ),
        )
        inserted += 1
    return inserted


def fetch_segment_payload(conn: psycopg.Connection, segment_id: str) -> SegmentPayload:
    row = conn.execute(
        """
        SELECT
            s.id::text,
            s.generation_id::text,
            s.conversation_id::text,
            s.source_kind::text,
            s.message_ids::text[],
            s.content_text,
            s.summary_text,
            s.privacy_tier
        FROM segments s
        JOIN segment_generations sg ON sg.id = s.generation_id
        WHERE s.id = %s
          AND s.is_active = true
          AND sg.status = 'active'
          AND s.source_kind IN ('chatgpt', 'claude', 'gemini')
          AND s.conversation_id IS NOT NULL
        """,
        (segment_id,),
    ).fetchone()
    if not row:
        raise ExtractionError(f"active AI-conversation segment not found: {segment_id}")
    messages = fetch_segment_messages(conn, row[4])
    return SegmentPayload(
        id=row[0],
        generation_id=row[1],
        conversation_id=row[2],
        source_kind=row[3],
        message_ids=list(row[4]),
        content_text=row[5],
        summary_text=row[6],
        privacy_tier=int(row[7]),
        messages=messages,
    )


def fetch_segment_messages(conn: psycopg.Connection, message_ids: list[str]) -> list[SegmentMessage]:
    rows = conn.execute(
        """
        SELECT id::text, sequence_index, role, content_text
        FROM messages
        WHERE id = ANY(%s::uuid[])
        ORDER BY sequence_index
        """,
        (message_ids,),
    ).fetchall()
    return [SegmentMessage(row[0], row[1], row[2], row[3]) for row in rows]


def find_existing_extraction(
    conn: psycopg.Connection,
    *,
    segment_id: str,
    prompt_version: str,
    model_version: str,
) -> dict[str, Any] | None:
    row = conn.execute(
        """
        SELECT id::text, status, claim_count
        FROM claim_extractions
        WHERE segment_id = %s
          AND extraction_prompt_version = %s
          AND extraction_model_version = %s
          AND status IN ('extracting', 'extracted')
        ORDER BY created_at DESC
        LIMIT 1
        """,
        (segment_id, prompt_version, model_version),
    ).fetchone()
    if not row:
        return None
    return {"id": row[0], "status": row[1], "claim_count": int(row[2])}


def create_extraction_row(
    conn: psycopg.Connection,
    segment: SegmentPayload,
    *,
    prompt_version: str,
    model_version: str,
) -> str:
    return conn.execute(
        """
        INSERT INTO claim_extractions (
            segment_id,
            generation_id,
            extraction_prompt_version,
            extraction_model_version,
            request_profile_version,
            status
        )
        VALUES (%s, %s, %s, %s, %s, 'extracting')
        RETURNING id::text
        """,
        (
            segment.id,
            segment.generation_id,
            prompt_version,
            model_version,
            EXTRACTION_REQUEST_PROFILE_VERSION,
        ),
    ).fetchone()[0]


def extraction_prompt_chunks(segment: SegmentPayload) -> list[SegmentPayload]:
    if not should_chunk_segment(segment):
        return [segment]

    chunks: list[SegmentPayload] = []
    current: list[SegmentMessage] = []
    current_chars = 0
    for message in segment.messages:
        message_chars = len(message.content_text or "")
        if current and (
            len(current) >= DEFAULT_EXTRACTION_CHUNK_MAX_MESSAGES
            or current_chars + message_chars > DEFAULT_EXTRACTION_CHUNK_MAX_CONTENT_CHARS
        ):
            chunks.append(chunk_segment_payload(segment, current))
            current = []
            current_chars = 0
        current.append(message)
        current_chars += message_chars

    if current:
        chunks.append(chunk_segment_payload(segment, current))
    return chunks or [segment]


def should_chunk_segment(segment: SegmentPayload) -> bool:
    content_chars = sum(len(message.content_text or "") for message in segment.messages)
    return (
        len(segment.messages) > DEFAULT_EXTRACTION_CHUNK_MAX_MESSAGES
        or content_chars > DEFAULT_EXTRACTION_CHUNK_MAX_CONTENT_CHARS
    )


def chunk_segment_payload(
    segment: SegmentPayload,
    messages: list[SegmentMessage],
) -> SegmentPayload:
    message_ids = [message.id for message in messages]
    rendered_content = "\n".join(message.content_text or "" for message in messages)
    return replace(
        segment,
        message_ids=message_ids,
        content_text=rendered_content,
        summary_text=None,
        messages=list(messages),
    )


def split_extraction_chunk(chunk: SegmentPayload) -> list[SegmentPayload]:
    if len(chunk.messages) > 1:
        midpoint = max(1, len(chunk.messages) // 2)
        return [
            chunk_segment_payload(chunk, chunk.messages[:midpoint]),
            chunk_segment_payload(chunk, chunk.messages[midpoint:]),
        ]

    if not chunk.messages:
        return []

    message = chunk.messages[0]
    content = message.content_text or ""
    if len(content) < 2:
        return []

    midpoint = len(content) // 2
    left = replace(message, content_text=content[:midpoint])
    right = replace(message, content_text=content[midpoint:])
    return [
        chunk_segment_payload(chunk, [left]),
        chunk_segment_payload(chunk, [right]),
    ]


def build_extraction_prompt(
    segment: SegmentPayload,
    *,
    validation_feedback: str | None = None,
) -> str:
    rendered_messages = "\n".join(format_message_for_prompt(message) for message in segment.messages)
    vocabulary = "\n".join(
        f"- {row['predicate']}: stability={row['stability_class']}, "
        f"cardinality={row['cardinality_class']}, object_kind={row['object_kind']}, "
        f"required_object_keys={row['required_object_keys'] or 'none'}"
        for row in PREDICATE_VOCABULARY
    )
    summary = segment.summary_text or "(none)"
    repair_section = f"\n\n{validation_feedback}" if validation_feedback else ""
    return f"""
Extract atomic, evidence-backed claims from this active AI-conversation segment.

Return one JSON object with key "claims" and no other keys. Each claim must use:
subject_text, predicate, object_text, object_json, stability_class, confidence,
evidence_message_ids, rationale. Exactly one of object_text/object_json must be
non-null. Cite only message ids shown below.

Predicate vocabulary:
{vocabulary}

Emission rules:
- Use `feels` for "experiencing" wording; `experiencing` is not a predicate.
- `lives_at` is JSON-only, with at least address_line1.
- `talked_about` is event-class.
- For JSON predicates, emit object_json only when every required_object_key
  listed above is directly supported by the message evidence.
- For text predicates, emit object_text and set object_json to null.
- If a required object value is unknown, omit the claim instead of emitting a
  partial or null object.
- Treat the segment summary as context only; extract and cite claims only from
  the `<messages>` block.
- Prefer omitting uncertain or low-salience details over emitting invalid JSON
  or claims without direct evidence.
- Tool and null messages may be cited if they are the evidence, even when their
  body is shown as a placeholder.
- Do not enumerate the predicate vocabulary as output.
- Do not create skeleton claims to show possible predicates.
- If no valid claims remain, return exactly {{"claims":[]}}.
{repair_section}

Segment summary:
{summary}

<messages>
{rendered_messages}
</messages>
""".strip()


def format_message_for_prompt(message: SegmentMessage) -> str:
    role = message.role or "unknown"
    content = message.content_text
    if role.lower() == "tool":
        content = f"[tool message {message.id} omitted]"
    elif content is None:
        content = f"[null-content message {message.id}]"
    return (
        f'<message id="{message.id}" sequence="{message.sequence_index}" role="{role}">\n'
        f"{content}\n"
        "</message>"
    )


def extract_pending_claims(
    conn: psycopg.Connection,
    batch_size: int,
    *,
    model_version: str | None = None,
    prompt_version: str = EXTRACTION_PROMPT_VERSION,
    client: ExtractorClient | None = None,
    max_tokens: int = DEFAULT_EXTRACTION_MAX_TOKENS,
    limit: int | None = None,
    conversation_id: str | None = None,
    progress_callback: Callable[[str, dict[str, Any]], None] | None = None,
) -> ExtractionBatchResult:
    apply_phase3_reclassification_invalidations(conn)
    reap_stale_extractions(conn)
    model_id = model_version or default_extractor_model_id()
    candidates = fetch_pending_segments(
        conn,
        prompt_version=prompt_version,
        model_version=model_id,
        limit=min(batch_size, limit) if limit is not None else batch_size,
        conversation_id=conversation_id,
    )
    processed = created = skipped = failed = 0
    for index, segment_id in enumerate(candidates, start=1):
        started_at = time.monotonic()
        if progress_callback:
            progress_callback("extract_start", {"index": index, "segment_id": segment_id})
        result = extract_claims_from_segment(
            conn,
            segment_id,
            model_version=model_id,
            prompt_version=prompt_version,
            client=client,
            max_tokens=max_tokens,
        )
        processed += 1
        if result.noop:
            skipped += 1
        elif result.status == "failed":
            failed += 1
        else:
            created += result.claim_count
        if progress_callback:
            progress_callback(
                "extract_done" if result.status != "failed" else "extract_failed",
                {
                    "index": index,
                    "segment_id": segment_id,
                    "claim_count": result.claim_count,
                    "status": result.status,
                    "elapsed": time.monotonic() - started_at,
                },
            )
        if result.status == "failed":
            break
    return ExtractionBatchResult(processed, created, skipped, failed)


def fetch_pending_segments(
    conn: psycopg.Connection,
    *,
    prompt_version: str,
    model_version: str,
    limit: int,
    conversation_id: str | None = None,
) -> list[str]:
    rows = conn.execute(
        """
        SELECT s.id::text
        FROM segments s
        JOIN segment_generations sg ON sg.id = s.generation_id
        LEFT JOIN consolidation_progress p
          ON p.stage = 'extractor'
         AND p.scope = 'conversation:' || s.conversation_id::text
        WHERE s.is_active = true
          AND sg.status = 'active'
          AND s.source_kind IN ('chatgpt', 'claude', 'gemini')
          AND s.conversation_id IS NOT NULL
          AND (%s::uuid IS NULL OR s.conversation_id = %s::uuid)
          AND COALESCE(p.error_count, 0) < %s
          AND NOT EXISTS (
              SELECT 1
              FROM claim_extractions ce
              WHERE ce.segment_id = s.id
                AND ce.extraction_prompt_version = %s
                AND ce.extraction_model_version = %s
                AND ce.status IN ('extracting', 'extracted')
          )
        ORDER BY s.conversation_id, s.sequence_index, s.id
        LIMIT %s
        """,
        (
            conversation_id,
            conversation_id,
            MAX_EXTRACTION_ERROR_COUNT,
            prompt_version,
            model_version,
            limit,
        ),
    ).fetchall()
    return [row[0] for row in rows]


def requeue_extraction_conversation(
    conn: psycopg.Connection,
    conversation_id: str,
) -> int:
    rows = conn.execute(
        """
        UPDATE claim_extractions ce
        SET status = 'failed',
            completed_at = now(),
            raw_payload = ce.raw_payload || jsonb_build_object(
                'failure_kind', 'manual_requeue'
            )
        FROM segments s
        WHERE ce.segment_id = s.id
          AND s.conversation_id = %s
          AND ce.status = 'extracting'
        RETURNING ce.id
        """,
        (conversation_id,),
    ).fetchall()
    conn.execute(
        """
        INSERT INTO consolidation_progress (
            stage,
            scope,
            status,
            updated_at,
            position,
            error_count,
            last_error
        )
        VALUES ('extractor', 'conversation:' || %s::text, 'pending', now(), %s, 0, NULL)
        ON CONFLICT (stage, scope) DO UPDATE SET
            status = 'pending',
            updated_at = now(),
            position = EXCLUDED.position,
            error_count = 0,
            last_error = NULL
        """,
        (conversation_id, Jsonb({"conversation_id": conversation_id, "requeued": True})),
    )
    return len(rows)


def reap_stale_extractions(
    conn: psycopg.Connection,
    *,
    timeout_seconds: int = EXTRACTOR_INFLIGHT_TIMEOUT_SECONDS,
) -> int:
    rows = conn.execute(
        """
        UPDATE claim_extractions
        SET status = 'failed',
            completed_at = now(),
            raw_payload = raw_payload || jsonb_build_object(
                'failure_kind', 'inflight_timeout'
            )
        WHERE status = 'extracting'
          AND created_at < now() - (%s::text || ' seconds')::interval
        RETURNING id
        """,
        (timeout_seconds,),
    ).fetchall()
    return len(rows)


def segment_index_within_conversation(conn: psycopg.Connection, segment_id: str) -> int | None:
    row = conn.execute(
        "SELECT sequence_index FROM segments WHERE id = %s",
        (segment_id,),
    ).fetchone()
    return int(row[0]) if row else None


def claim_to_payload(claim: ClaimDraft) -> dict[str, Any]:
    return {
        "subject_text": claim.subject_text,
        "predicate": claim.predicate,
        "object_text": claim.object_text,
        "object_json": claim.object_json,
        "stability_class": claim.stability_class,
        "confidence": claim.confidence,
        "evidence_message_ids": claim.evidence_message_ids,
        "rationale": claim.rationale,
    }


@contextmanager
def extractor_request_deadline(seconds: int):
    if seconds <= 0:
        yield
        return
    old_handler = signal.getsignal(signal.SIGALRM)
    old_timer = signal.setitimer(signal.ITIMER_REAL, 0)

    def handle_timeout(signum, frame):
        raise ExtractorRequestTimeout(f"local extractor request exceeded {seconds}s deadline")

    signal.signal(signal.SIGALRM, handle_timeout)
    signal.setitimer(signal.ITIMER_REAL, seconds)
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, old_handler)
        if old_timer[0] > 0:
            signal.setitimer(signal.ITIMER_REAL, old_timer[0], old_timer[1])
