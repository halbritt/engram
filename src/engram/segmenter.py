from __future__ import annotations

import json
import math
import os
import re
import signal
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Protocol

import psycopg
from psycopg.types.json import Jsonb

from engram.progress import upsert_progress


IK_LLAMA_BASE_URL = os.environ.get("ENGRAM_IK_LLAMA_BASE_URL", "http://127.0.0.1:8081")
SEGMENTER_PROMPT_VERSION = os.environ.get(
    "ENGRAM_SEGMENTER_PROMPT_VERSION",
    "segmenter.v2.d034.enum-ids.tool-placeholders",
)
SEGMENTER_REQUEST_PROFILE_VERSION = "ik-llama-json-schema.d034.v2"
DEFAULT_MAX_TOKENS = int(os.environ.get("ENGRAM_SEGMENTER_MAX_TOKENS", "16384"))
RETRY_MAX_TOKENS = int(os.environ.get("ENGRAM_SEGMENTER_RETRY_MAX_TOKENS", "32768"))
DEFAULT_RETRIES = int(os.environ.get("ENGRAM_SEGMENTER_RETRIES", "1"))
SEGMENTER_REQUEST_TIMEOUT_SECONDS = int(
    os.environ.get("ENGRAM_SEGMENTER_TIMEOUT_SECONDS", "600")
)
DEFAULT_WINDOW_CHAR_BUDGET = int(
    os.environ.get("ENGRAM_SEGMENTER_WINDOW_CHAR_BUDGET", "60000")
)
CONTEXT_GUARD_MARGIN_TOKENS = int(
    os.environ.get("ENGRAM_SEGMENTER_CONTEXT_GUARD_MARGIN_TOKENS", "1024")
)
CONTEXT_GUARD_CHARS_PER_TOKEN = float(
    os.environ.get("ENGRAM_SEGMENTER_CONTEXT_GUARD_CHARS_PER_TOKEN", "2.5")
)
MIN_CONTEXT_SAFE_WINDOW_CHAR_BUDGET = int(
    os.environ.get("ENGRAM_SEGMENTER_MIN_WINDOW_CHAR_BUDGET", "4000")
)
WINDOW_OVERLAP_MESSAGES = max(0, int(os.environ.get("ENGRAM_SEGMENTER_WINDOW_OVERLAP", "0")))
MAX_SEGMENTER_ERROR_COUNT = int(os.environ.get("ENGRAM_SEGMENTER_MAX_ERROR_COUNT", "3"))
ADAPTIVE_SPLIT_MAX_DEPTH = int(
    os.environ.get("ENGRAM_SEGMENTER_ADAPTIVE_SPLIT_MAX_DEPTH", "8")
)

_SEGMENTER_MODEL_ID_CACHE: str | None = None
_SEGMENTER_PROBE_CACHE: SegmenterProbe | None = None
SEGMENTER_SYSTEM_PROMPT = (
    "You are a deterministic topic segmenter for a local-first "
    "personal memory pipeline. Return only schema-valid JSON."
)

MARKER_ONLY_RE = re.compile(
    r"^\s*(?:"
    r"\[(?:image_asset_pointer|image|tool_use|tool_result|attachment|audio|video|file|"
    r"input_image|output_image|computer_call|computer_call_output|reasoning)[^\]]*\]"
    r"|\[tool artifact omitted[^\]]*\]"
    r"|<\|[^>]+\|>"
    r")\s*$",
    re.IGNORECASE,
)
FILECITE_RE = re.compile(r"filecite|turn\d+file\d+|Content source:\s*Source\.file")
URL_RE = re.compile(r"https?://\S+")


class SegmentationError(RuntimeError):
    """Raised when the local segmenter returns unusable output."""


class SegmenterServiceUnavailable(SegmentationError):
    """Raised when the local segmenter endpoint is unreachable."""


class SegmenterRequestTimeout(SegmentationError):
    """Raised when one parent/window exceeds the configured request deadline."""


class SegmenterResponseError(SegmentationError):
    """Raised when ik-llama returns a response object with unusable content."""

    def __init__(self, message: str, *, response: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.response = response
        self.decoded_tokens = decoded_token_count_from_response(response)


class SegmenterContextBudgetError(SegmentationError):
    """Raised before a structured request can reach ik-llama context shift."""


@dataclass(frozen=True)
class SegmenterProbe:
    model_id: str
    context_window: int | None
    raw_models: dict[str, Any]
    raw_props: dict[str, Any]


@dataclass(frozen=True)
class ConversationMessage:
    id: str
    sequence_index: int
    role: str | None
    content_text: str | None
    privacy_tier: int


@dataclass(frozen=True)
class SegmentDraft:
    message_ids: list[str]
    summary: str | None
    content_text: str
    raw: dict[str, Any]


@dataclass(frozen=True)
class MessageWindow:
    index: int
    messages: list[ConversationMessage]
    truncated_message_ids: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class SegmentationResult:
    generation_id: str | None
    parent_id: str
    segments_inserted: int
    windows_processed: int
    skipped_windows: int
    status: str
    noop: bool = False


@dataclass(frozen=True)
class WindowSegmentation:
    window: MessageWindow
    drafts: list[SegmentDraft]
    retry_count: int
    adaptive_split_depth: int = 0


@dataclass(frozen=True)
class BatchResult:
    processed: int
    created: int
    skipped: int
    failed: int


class SegmenterClient(Protocol):
    def segment(
        self,
        prompt: str,
        *,
        model_id: str,
        max_tokens: int,
    ) -> list[SegmentDraft]:
        ...


def probe_segmenter(base_url: str = IK_LLAMA_BASE_URL) -> SegmenterProbe:
    ensure_local_base_url(base_url)
    models_payload = http_json("GET", f"{base_url}/v1/models")
    props_payload = http_json("GET", f"{base_url}/props")
    models = models_payload.get("data") or []
    if not models:
        raise SegmentationError("ik-llama /v1/models returned no models")
    model = models[0]
    model_id = str(model.get("id") or props_payload.get("model_alias") or "")
    if not model_id:
        raise SegmentationError("ik-llama model id could not be determined")
    context_window = model.get("max_model_len") or props_payload.get("n_ctx")
    if context_window is None:
        settings = props_payload.get("default_generation_settings") or {}
        context_window = settings.get("n_ctx")
    return SegmenterProbe(
        model_id=model_id,
        context_window=int(context_window) if context_window is not None else None,
        raw_models=models_payload,
        raw_props=props_payload,
    )


def default_segmenter_model_id() -> str:
    configured = os.environ.get("ENGRAM_SEGMENTER_MODEL")
    if configured:
        return configured
    return default_segmenter_probe().model_id


def default_segmenter_probe() -> SegmenterProbe:
    global _SEGMENTER_MODEL_ID_CACHE, _SEGMENTER_PROBE_CACHE
    if _SEGMENTER_PROBE_CACHE:
        return _SEGMENTER_PROBE_CACHE
    if _SEGMENTER_MODEL_ID_CACHE:
        probe = probe_segmenter()
        _SEGMENTER_PROBE_CACHE = probe
        return probe
    _SEGMENTER_PROBE_CACHE = probe_segmenter()
    _SEGMENTER_MODEL_ID_CACHE = _SEGMENTER_PROBE_CACHE.model_id
    return _SEGMENTER_PROBE_CACHE


def configured_segmenter_context_window() -> int | None:
    raw = os.environ.get("ENGRAM_SEGMENTER_CONTEXT_WINDOW")
    if not raw:
        return None
    value = int(raw)
    if value <= 0:
        raise SegmentationError("ENGRAM_SEGMENTER_CONTEXT_WINDOW must be positive")
    return value


class IkLlamaSegmenterClient:
    def __init__(
        self,
        base_url: str = IK_LLAMA_BASE_URL,
        *,
        context_window: int | None = None,
    ) -> None:
        ensure_local_base_url(base_url)
        self.base_url = base_url.rstrip("/")
        self._context_window = context_window or configured_segmenter_context_window()

    def context_window(self) -> int | None:
        if self._context_window is not None:
            return self._context_window
        probe = probe_segmenter(self.base_url)
        self._context_window = probe.context_window
        return self._context_window

    def segment(
        self,
        prompt: str,
        *,
        model_id: str,
        max_tokens: int,
        allowed_message_ids: list[str] | None = None,
    ) -> list[SegmentDraft]:
        payload = {
            "model": model_id,
            "messages": [
                {
                    "role": "system",
                    "content": SEGMENTER_SYSTEM_PROMPT,
                },
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
                    "name": "SegmentationResult",
                    "strict": True,
                    "schema": segmentation_json_schema(allowed_message_ids),
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
            timeout=SEGMENTER_REQUEST_TIMEOUT_SECONDS,
        )
        return parse_segmentation_response(response)


def segmentation_json_schema(
    allowed_message_ids: list[str] | None = None,
) -> dict[str, Any]:
    message_id_items: dict[str, Any] = {"type": "string"}
    if allowed_message_ids is not None:
        if not allowed_message_ids:
            raise SegmentationError("cannot constrain segmenter schema to zero message ids")
        message_id_items["enum"] = list(dict.fromkeys(allowed_message_ids))
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["segments"],
        "properties": {
            "segments": {
                "type": "array",
                "minItems": 1,
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["message_ids", "summary", "content_text", "raw"],
                    "properties": {
                        "message_ids": {
                            "type": "array",
                            "minItems": 1,
                            "items": message_id_items,
                        },
                        "summary": {"type": ["string", "null"]},
                        "content_text": {"type": "string", "minLength": 1},
                        "raw": {"type": "object", "additionalProperties": True},
                    },
                },
            }
        },
    }


def assert_context_budget(
    prompt: str,
    *,
    max_tokens: int,
    context_window: int | None,
) -> None:
    if context_window is None:
        return
    estimated_prompt_tokens = estimate_segmenter_prompt_tokens(prompt)
    requested_tokens = estimated_prompt_tokens + max_tokens + CONTEXT_GUARD_MARGIN_TOKENS
    if requested_tokens >= context_window:
        raise SegmenterContextBudgetError(
            "segmenter request would reach context shift: "
            f"estimated_prompt_tokens={estimated_prompt_tokens}, "
            f"max_tokens={max_tokens}, "
            f"margin_tokens={CONTEXT_GUARD_MARGIN_TOKENS}, "
            f"context_window={context_window}"
        )


def estimate_segmenter_prompt_tokens(prompt: str) -> int:
    chars_per_token = max(CONTEXT_GUARD_CHARS_PER_TOKEN, 1.0)
    # The schema is enforced as a grammar, not prompt text. Count the rendered
    # chat messages plus a small template overhead so the guard fails closed.
    rendered_chars = len(SEGMENTER_SYSTEM_PROMPT) + len(prompt) + 512
    return math.ceil(rendered_chars / chars_per_token)


def context_safe_window_char_budget(
    configured_budget: int,
    *,
    context_window: int | None,
    max_tokens: int,
) -> int:
    if context_window is None:
        return configured_budget
    prompt_token_budget = context_window - max_tokens - CONTEXT_GUARD_MARGIN_TOKENS
    if prompt_token_budget <= 0:
        return MIN_CONTEXT_SAFE_WINDOW_CHAR_BUDGET
    prompt_scaffold_tokens = estimate_segmenter_prompt_tokens(
        build_segmenter_prompt(MessageWindow(index=0, messages=[]), "windowed")
    )
    content_token_budget = max(0, prompt_token_budget - prompt_scaffold_tokens)
    safe_budget = int(content_token_budget * max(CONTEXT_GUARD_CHARS_PER_TOKEN, 1.0) * 0.6)
    if safe_budget <= 0:
        safe_budget = MIN_CONTEXT_SAFE_WINDOW_CHAR_BUDGET
    return min(configured_budget, safe_budget)


def parse_segmentation_response(response: dict[str, Any]) -> list[SegmentDraft]:
    choices = response.get("choices")
    if not isinstance(choices, list) or not choices:
        raise SegmenterResponseError("segmenter response missing choices", response=response)
    message = choices[0].get("message") if isinstance(choices[0], dict) else None
    if not isinstance(message, dict):
        raise SegmenterResponseError(
            "segmenter response missing choices[0].message",
            response=response,
        )

    content = message.get("content")
    if not isinstance(content, str) or not content.strip():
        if message.get("reasoning_content"):
            raise SegmenterResponseError(
                "segmenter returned payload only in reasoning_content",
                response=response,
            )
        raise SegmenterResponseError(
            "segmenter returned empty message content",
            response=response,
        )

    stripped = content.strip()
    if stripped.startswith("```"):
        raise SegmenterResponseError(
            "segmenter returned Markdown-fenced JSON",
            response=response,
        )

    try:
        payload = json.loads(stripped)
    except json.JSONDecodeError as exc:
        raise SegmenterResponseError(
            f"segmenter returned invalid JSON: {exc}",
            response=response,
        ) from exc

    try:
        return parse_segmentation_payload(payload)
    except SegmentationError as exc:
        raise SegmenterResponseError(str(exc), response=response) from exc


def parse_segmentation_payload(payload: Any) -> list[SegmentDraft]:
    if not isinstance(payload, dict) or set(payload) != {"segments"}:
        raise SegmentationError("segmentation payload must contain only segments")
    segments = payload["segments"]
    if not isinstance(segments, list) or not segments:
        raise SegmentationError("segmentation payload must contain at least one segment")

    drafts: list[SegmentDraft] = []
    expected_keys = {"message_ids", "summary", "content_text", "raw"}
    for index, item in enumerate(segments):
        if not isinstance(item, dict) or set(item) != expected_keys:
            raise SegmentationError(f"segment {index} does not match the schema")
        message_ids = item["message_ids"]
        if (
            not isinstance(message_ids, list)
            or not message_ids
            or not all(isinstance(value, str) and value for value in message_ids)
        ):
            raise SegmentationError(f"segment {index} has invalid message_ids")
        summary = item["summary"]
        if summary is not None and not isinstance(summary, str):
            raise SegmentationError(f"segment {index} has invalid summary")
        summary, summary_sanitized = sanitize_model_string(summary)
        content_text = item["content_text"]
        if not isinstance(content_text, str) or not content_text.strip():
            raise SegmentationError(f"segment {index} has empty content_text")
        content_text, content_sanitized = sanitize_model_string(content_text)
        raw = item["raw"]
        if not isinstance(raw, dict):
            raise SegmentationError(f"segment {index} has invalid raw metadata")
        raw, raw_sanitized = sanitize_model_json(raw)
        if summary_sanitized or content_sanitized or raw_sanitized:
            raw = dict(raw)
            raw["invalid_utf8_surrogates_replaced"] = True
        drafts.append(
            SegmentDraft(
                message_ids=message_ids,
                summary=summary,
                content_text=content_text,
                raw=raw,
            )
        )
    return drafts


def sanitize_model_string(value: str | None) -> tuple[str | None, bool]:
    if value is None:
        return None, False
    try:
        value.encode("utf-8")
    except UnicodeEncodeError:
        return value.encode("utf-8", "replace").decode("utf-8"), True
    return value, False


def sanitize_segment_draft(draft: SegmentDraft) -> SegmentDraft:
    summary, summary_sanitized = sanitize_model_string(draft.summary)
    content_text, content_sanitized = sanitize_model_string(draft.content_text)
    raw, raw_sanitized = sanitize_model_json(draft.raw)
    if summary_sanitized or content_sanitized or raw_sanitized:
        raw = dict(raw)
        raw["invalid_utf8_surrogates_replaced"] = True
    return SegmentDraft(
        message_ids=draft.message_ids,
        summary=summary,
        content_text=str(content_text),
        raw=raw,
    )


def sanitize_model_json(value: Any) -> tuple[Any, bool]:
    if isinstance(value, str):
        return sanitize_model_string(value)
    if isinstance(value, list):
        changed = False
        items: list[Any] = []
        for item in value:
            sanitized, item_changed = sanitize_model_json(item)
            changed = changed or item_changed
            items.append(sanitized)
        return items, changed
    if isinstance(value, dict):
        changed = False
        sanitized_dict: dict[str, Any] = {}
        for key, item in value.items():
            sanitized_key, key_changed = sanitize_model_string(str(key))
            sanitized_item, item_changed = sanitize_model_json(item)
            changed = changed or key_changed or item_changed
            sanitized_dict[str(sanitized_key)] = sanitized_item
        return sanitized_dict, changed
    return value, False


def segment_conversation(
    conn: psycopg.Connection,
    conversation_id: str,
    *,
    model_version: str | None = None,
    prompt_version: str = SEGMENTER_PROMPT_VERSION,
    client: SegmenterClient | None = None,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    window_char_budget: int = DEFAULT_WINDOW_CHAR_BUDGET,
    force: bool = False,
    retries: int = DEFAULT_RETRIES,
) -> SegmentationResult:
    try:
        model_id = model_version or default_segmenter_model_id()
    except SegmenterServiceUnavailable as exc:
        upsert_progress(
            conn,
            stage="segmenter",
            scope=f"conversation:{conversation_id}",
            status="pending",
            position={"conversation_id": conversation_id, "failure_stage": "model_probe"},
            last_error=str(exc),
            increment_error=True,
        )
        raise
    conversation = fetch_conversation(conn, conversation_id)
    existing = find_existing_generation(
        conn,
        parent_kind="conversation",
        parent_id=conversation_id,
        prompt_version=prompt_version,
        model_version=model_id,
    )
    if existing and existing["status"] in {"segmented", "embedding", "active"} and not force:
        return SegmentationResult(
            generation_id=str(existing["id"]),
            parent_id=conversation_id,
            segments_inserted=0,
            windows_processed=0,
            skipped_windows=0,
            status=str(existing["status"]),
            noop=True,
        )

    segmenter = client or IkLlamaSegmenterClient()
    try:
        context_window = (
            segmenter.context_window()
            if isinstance(segmenter, IkLlamaSegmenterClient)
            else None
        )
    except SegmenterServiceUnavailable as exc:
        upsert_progress(
            conn,
            stage="segmenter",
            scope=f"conversation:{conversation_id}",
            status="pending",
            position={
                "conversation_id": conversation_id,
                "failure_stage": "context_probe",
            },
            last_error=str(exc),
            increment_error=True,
        )
        raise
    effective_window_char_budget = context_safe_window_char_budget(
        window_char_budget,
        context_window=context_window,
        max_tokens=max_tokens,
    )
    messages = fetch_messages(conn, conversation_id)
    windows = build_windows(messages, effective_window_char_budget)
    window_strategy = "windowed" if len(windows) > 1 else "whole"
    generation_id = (
        str(existing["id"])
        if existing and existing["status"] == "segmenting"
        else create_generation(
            conn,
            parent_kind="conversation",
            parent_id=conversation_id,
            prompt_version=prompt_version,
            model_version=model_id,
            raw_payload={
                "request_profile_version": SEGMENTER_REQUEST_PROFILE_VERSION,
                "max_tokens": max_tokens,
                "context_window": context_window,
                "window_char_budget": window_char_budget,
                "effective_window_char_budget": effective_window_char_budget,
                "window_count": len(windows),
            },
        )
    )
    message_by_id = {message.id: message for message in messages}
    sequence_by_id = {message.id: message.sequence_index for message in messages}
    next_sequence_index = next_segment_sequence_index(conn, generation_id)
    start_window_index = next_window_index(conn, generation_id)
    inserted = 0
    skipped = 0

    for window in windows:
        if window.index < start_window_index:
            continue
        upsert_progress(
            conn,
            stage="segmenter",
            scope=f"conversation:{conversation_id}",
            status="in_progress",
            position={"conversation_id": conversation_id, "window_index": window.index},
        )

        if not window_has_embeddable_text(window):
            skipped += 1
            append_generation_metadata(
                conn,
                generation_id,
                {
                    f"window_{window.index}_skip": {
                        "reason": "no_embeddable_text",
                        "message_ids": [message.id for message in window.messages],
                    }
                },
            )
            continue

        try:
            window_results = segment_window_adaptively(
                segmenter,
                window,
                window_strategy=window_strategy,
                model_id=model_id,
                max_tokens=max_tokens,
                retries=retries,
            )
        except SegmenterServiceUnavailable as exc:
            mark_generation_failed(
                conn,
                generation_id,
                failure_kind="service_unavailable",
                error=exc,
            )
            upsert_progress(
                conn,
                stage="segmenter",
                scope=f"conversation:{conversation_id}",
                status="pending",
                position={
                    "conversation_id": conversation_id,
                    "window_index": window.index,
                    "retryable_failure_kind": "service_unavailable",
                },
                last_error=str(exc),
                increment_error=True,
            )
            raise
        except SegmenterRequestTimeout as exc:
            mark_generation_failed(
                conn,
                generation_id,
                failure_kind="segmenter_timeout",
                error=exc,
            )
            upsert_progress(
                conn,
                stage="segmenter",
                scope=f"conversation:{conversation_id}",
                status="failed",
                position={"conversation_id": conversation_id, "window_index": window.index},
                last_error=str(exc),
                increment_error=True,
            )
            raise
        except Exception as exc:
            mark_generation_failed(
                conn,
                generation_id,
                failure_kind="segmenter_error",
                error=exc,
            )
            upsert_progress(
                conn,
                stage="segmenter",
                scope=f"conversation:{conversation_id}",
                status="failed",
                position={"conversation_id": conversation_id, "window_index": window.index},
                last_error=str(exc),
                increment_error=True,
            )
            raise

        for window_result in window_results:
            result_window = window_result.window
            result_window_strategy = (
                "windowed"
                if window_strategy == "windowed" or window_result.adaptive_split_depth > 0
                else window_strategy
            )
            for draft in window_result.drafts:
                draft = sanitize_segment_draft(draft)
                expanded_message_ids = expand_message_span(draft.message_ids, sequence_by_id)
                content_text = canonicalize_embeddable_text(draft.content_text)
                if not content_text:
                    skipped += 1
                    append_generation_metadata(
                        conn,
                        generation_id,
                        {
                            f"window_{result_window.index}_segment_{next_sequence_index}_skip": {
                                "reason": "empty_embeddable_text_after_canonicalization",
                                "message_ids": expanded_message_ids,
                                "raw": draft.raw,
                            }
                        },
                    )
                    continue
                privacy_tier = max(
                    [int(conversation["privacy_tier"])]
                    + [
                        message_by_id[message_id].privacy_tier
                        for message_id in expanded_message_ids
                    ]
                )
                insert_segment(
                    conn,
                    generation_id=generation_id,
                    source_id=str(conversation["source_id"]),
                    source_kind=str(conversation["source_kind"]),
                    conversation_id=conversation_id,
                    message_ids=expanded_message_ids,
                    sequence_index=next_sequence_index,
                    content_text=content_text,
                    summary_text=draft.summary,
                    window_strategy=result_window_strategy,
                    window_index=(
                        result_window.index if result_window_strategy == "windowed" else None
                    ),
                    prompt_version=prompt_version,
                    model_version=model_id,
                    privacy_tier=privacy_tier,
                    raw_payload={
                        "segment": draft.raw,
                        "model_output": {
                            "message_ids": draft.message_ids,
                            "summary": draft.summary,
                            "content_text": draft.content_text,
                        },
                        "expanded_message_ids": expanded_message_ids,
                        "span_expansion_added": [
                            message_id
                            for message_id in expanded_message_ids
                            if message_id not in draft.message_ids
                        ],
                        "window_index": result_window.index,
                        "parent_window_index": window.index,
                        "retry_count": window_result.retry_count,
                        "adaptive_split_depth": window_result.adaptive_split_depth,
                        "truncated_message_ids": result_window.truncated_message_ids,
                        "request_profile_version": SEGMENTER_REQUEST_PROFILE_VERSION,
                    },
                )
                next_sequence_index += 1
                inserted += 1

    status = "segmented"
    conn.execute(
        "UPDATE segment_generations SET status = %s WHERE id = %s",
        (status, generation_id),
    )
    upsert_progress(
        conn,
        stage="segmenter",
        scope=f"conversation:{conversation_id}",
        status="completed",
        position={
            "conversation_id": conversation_id,
            "window_index": windows[-1].index if windows else None,
        },
    )
    return SegmentationResult(
        generation_id=generation_id,
        parent_id=conversation_id,
        segments_inserted=inserted,
        windows_processed=max(0, len(windows) - start_window_index),
        skipped_windows=skipped,
        status=status,
    )


def segment_pending(
    conn: psycopg.Connection,
    batch_size: int,
    model_version: str | None = None,
    *,
    source_id: str | None = None,
    limit: int | None = None,
    prompt_version: str = SEGMENTER_PROMPT_VERSION,
    client: SegmenterClient | None = None,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    window_char_budget: int = DEFAULT_WINDOW_CHAR_BUDGET,
    retries: int = DEFAULT_RETRIES,
    progress_callback: Callable[[str, dict[str, Any]], None] | None = None,
) -> BatchResult:
    try:
        model_id = model_version or default_segmenter_model_id()
    except SegmenterServiceUnavailable as exc:
        upsert_progress(
            conn,
            stage="segmenter",
            scope="probe",
            status="failed",
            position={"failure_stage": "model_probe"},
            last_error=str(exc),
            increment_error=True,
        )
        upsert_progress(
            conn,
            stage="segmenter",
            scope="batch",
            status="failed",
            position={"processed": 0, "created": 0, "failed": 1},
            last_error=str(exc),
            increment_error=True,
        )
        if progress_callback:
            progress_callback(
                "segment_probe_failed",
                {"elapsed_seconds": 0.0, "error": str(exc)},
            )
        return BatchResult(processed=0, created=0, skipped=0, failed=1)
    candidates = fetch_pending_conversations(
        conn,
        prompt_version=prompt_version,
        model_version=model_id,
        source_id=source_id,
        limit=min(batch_size, limit) if limit is not None else batch_size,
    )
    processed = created = skipped = failed = 0
    for conversation_id, force in candidates:
        if limit is not None and processed >= limit:
            break
        processed += 1
        started_at = time.monotonic()
        if progress_callback:
            progress_callback(
                "segment_start",
                {
                    "index": processed,
                    "batch_size": len(candidates),
                    "conversation_id": conversation_id,
                    "force": force,
                },
            )
        try:
            result = segment_conversation(
                conn,
                conversation_id,
                model_version=model_id,
                prompt_version=prompt_version,
                client=client,
                max_tokens=max_tokens,
                window_char_budget=window_char_budget,
                force=force,
                retries=retries,
            )
        except SegmenterServiceUnavailable:
            failed += 1
            if progress_callback:
                progress_callback(
                    "segment_service_unavailable",
                    {
                        "index": processed,
                        "batch_size": len(candidates),
                        "conversation_id": conversation_id,
                        "elapsed_seconds": time.monotonic() - started_at,
                    },
                )
            continue
        except Exception as exc:
            mark_parent_segmenting_generations_failed(
                conn,
                parent_kind="conversation",
                parent_id=conversation_id,
                prompt_version=prompt_version,
                model_version=model_id,
                failure_kind="segmenter_error",
                error=exc,
            )
            failed += 1
            if progress_callback:
                progress_callback(
                    "segment_failed",
                    {
                        "index": processed,
                        "batch_size": len(candidates),
                        "conversation_id": conversation_id,
                        "elapsed_seconds": time.monotonic() - started_at,
                    },
                )
            continue
        if result.noop:
            skipped += 1
        else:
            created += result.segments_inserted
        if progress_callback:
            progress_callback(
                "segment_done",
                {
                    "index": processed,
                    "batch_size": len(candidates),
                    "conversation_id": conversation_id,
                    "segments_inserted": result.segments_inserted,
                    "windows_processed": result.windows_processed,
                    "skipped_windows": result.skipped_windows,
                    "noop": result.noop,
                    "elapsed_seconds": time.monotonic() - started_at,
                },
            )

    upsert_progress(
        conn,
        stage="segmenter",
        scope="batch",
        status="completed" if failed == 0 else "failed",
        position={"processed": processed, "created": created, "failed": failed},
        last_error=None if failed == 0 else f"{failed} conversation(s) failed",
        increment_error=failed > 0,
    )
    return BatchResult(processed=processed, created=created, skipped=skipped, failed=failed)


def fetch_pending_conversations(
    conn: psycopg.Connection,
    *,
    prompt_version: str,
    model_version: str,
    source_id: str | None,
    limit: int,
) -> list[tuple[str, bool]]:
    rows = conn.execute(
        """
        SELECT c.id::text, (p.status = 'pending') AS force
        FROM conversations c
        LEFT JOIN consolidation_progress p
          ON p.stage = 'segmenter'
         AND p.scope = 'conversation:' || c.id::text
        WHERE (%s::uuid IS NULL OR c.source_id = %s::uuid)
          AND (
              p.status IS DISTINCT FROM 'pending'
              OR p.position ? 'queued_by'
              OR COALESCE(p.error_count, 0) < %s
          )
          AND (
              p.status = 'pending'
              OR NOT EXISTS (
                  SELECT 1
                  FROM segment_generations sg
                  WHERE sg.parent_kind = 'conversation'
                    AND sg.parent_id = c.id
                    AND sg.segmenter_prompt_version = %s
                    AND sg.segmenter_model_version = %s
                    AND sg.status IN ('segmenting', 'segmented', 'embedding', 'active', 'failed')
              )
          )
        ORDER BY c.imported_at, c.id
        LIMIT %s
        """,
        (
            source_id,
            source_id,
            MAX_SEGMENTER_ERROR_COUNT,
            prompt_version,
            model_version,
            limit,
        ),
    ).fetchall()
    return [(row[0], bool(row[1])) for row in rows]


def mark_generation_failed(
    conn: psycopg.Connection,
    generation_id: str,
    *,
    failure_kind: str,
    error: BaseException | None = None,
) -> None:
    conn.execute(
        """
        UPDATE segment_generations
        SET status = 'failed',
            raw_payload = raw_payload || %s
        WHERE id = %s
        """,
        (Jsonb(segmenter_failure_payload(failure_kind, error)), generation_id),
    )


def mark_parent_segmenting_generations_failed(
    conn: psycopg.Connection,
    *,
    parent_kind: str,
    parent_id: str,
    prompt_version: str,
    model_version: str,
    failure_kind: str,
    error: BaseException | None = None,
) -> None:
    conn.execute(
        """
        UPDATE segment_generations
        SET status = 'failed',
            raw_payload = raw_payload || %s
        WHERE parent_kind = %s
          AND parent_id = %s
          AND segmenter_prompt_version = %s
          AND segmenter_model_version = %s
          AND status = 'segmenting'
        """,
        (
            Jsonb(segmenter_failure_payload(failure_kind, error)),
            parent_kind,
            parent_id,
            prompt_version,
            model_version,
        ),
    )


def segment_window_adaptively(
    client: SegmenterClient,
    window: MessageWindow,
    *,
    window_strategy: str,
    model_id: str,
    max_tokens: int,
    retries: int,
    split_depth: int = 0,
) -> list[WindowSegmentation]:
    prompt = build_segmenter_prompt(window, window_strategy)
    try:
        drafts, retry_count = segment_window_with_retries(
            client,
            prompt,
            model_id=model_id,
            max_tokens=max_tokens,
            retries=retries,
            allowed_message_ids=[message.id for message in window.messages],
        )
        return [
            WindowSegmentation(
                window=window,
                drafts=drafts,
                retry_count=retry_count,
                adaptive_split_depth=split_depth,
            )
        ]
    except (SegmenterServiceUnavailable, SegmenterRequestTimeout):
        raise
    except Exception as exc:
        if not should_adaptively_split_window(exc, window, split_depth):
            raise
        results: list[WindowSegmentation] = []
        for child in split_message_window(window):
            results.extend(
                segment_window_adaptively(
                    client,
                    child,
                    window_strategy="windowed",
                    model_id=model_id,
                    max_tokens=max_tokens,
                    retries=retries,
                    split_depth=split_depth + 1,
                )
            )
        return results


def should_adaptively_split_window(
    exc: BaseException,
    window: MessageWindow,
    split_depth: int,
) -> bool:
    if split_depth >= ADAPTIVE_SPLIT_MAX_DEPTH or len(window.messages) <= 1:
        return False
    if isinstance(exc, SegmenterContextBudgetError):
        return True
    diagnostics = getattr(exc, "segmenter_attempt_diagnostics", None)
    if isinstance(diagnostics, dict):
        attempt_errors = diagnostics.get("attempt_errors")
        if isinstance(attempt_errors, list):
            if any("context shift" in str(error).lower() for error in attempt_errors):
                return True
            if any(is_likely_truncation_text(str(error)) for error in attempt_errors):
                return True
    return is_likely_truncation_error(exc)


def split_message_window(window: MessageWindow) -> list[MessageWindow]:
    if len(window.messages) <= 1:
        return [window]
    return [
        MessageWindow(
            index=window.index,
            messages=[message],
            truncated_message_ids=[
                message_id
                for message_id in window.truncated_message_ids
                if message.id == message_id
            ],
        )
        for message in window.messages
    ]


def segment_window_with_retries(
    client: SegmenterClient,
    prompt: str,
    *,
    model_id: str,
    max_tokens: int,
    retries: int,
    allowed_message_ids: list[str] | None = None,
) -> tuple[list[SegmentDraft], int]:
    attempt_prompt = prompt
    attempt_max_tokens = max_tokens
    attempt_max_tokens_used: list[int] = []
    decode_counts: list[int | None] = []
    attempt_errors: list[str] = []
    for attempt in range(retries + 1):
        attempt_max_tokens_used.append(attempt_max_tokens)
        try:
            with segmenter_request_deadline(SEGMENTER_REQUEST_TIMEOUT_SECONDS):
                return (
                    call_segmenter_client(
                        client,
                        attempt_prompt,
                        model_id=model_id,
                        max_tokens=attempt_max_tokens,
                        allowed_message_ids=allowed_message_ids,
                    ),
                    attempt,
                )
        except (SegmenterServiceUnavailable, SegmenterRequestTimeout) as exc:
            decode_counts.append(decoded_token_count_from_exception(exc))
            attempt_errors.append(error_summary(exc))
            attach_attempt_diagnostics(
                exc,
                attempt_max_tokens=attempt_max_tokens_used,
                decode_counts=decode_counts,
                attempt_errors=attempt_errors,
            )
            raise
        except SegmentationError as exc:
            decode_counts.append(decoded_token_count_from_exception(exc))
            attempt_errors.append(error_summary(exc))
            if isinstance(exc, SegmenterContextBudgetError):
                attach_attempt_diagnostics(
                    exc,
                    attempt_max_tokens=attempt_max_tokens_used,
                    decode_counts=decode_counts,
                    attempt_errors=attempt_errors,
                )
                raise
            if attempt >= retries:
                attach_attempt_diagnostics(
                    exc,
                    attempt_max_tokens=attempt_max_tokens_used,
                    decode_counts=decode_counts,
                    attempt_errors=attempt_errors,
                )
                raise
            attempt_max_tokens = retry_max_tokens(max_tokens, attempt + 1)
            if is_likely_truncation_error(exc):
                attempt_prompt = prompt
            else:
                attempt_prompt = retry_segmenter_prompt(prompt, exc)
        except Exception as exc:
            decode_counts.append(decoded_token_count_from_exception(exc))
            attempt_errors.append(error_summary(exc))
            attach_attempt_diagnostics(
                exc,
                attempt_max_tokens=attempt_max_tokens_used,
                decode_counts=decode_counts,
                attempt_errors=attempt_errors,
            )
            raise
    raise SegmentationError("segmenter retry loop exhausted unexpectedly")


def call_segmenter_client(
    client: SegmenterClient,
    prompt: str,
    *,
    model_id: str,
    max_tokens: int,
    allowed_message_ids: list[str] | None,
) -> list[SegmentDraft]:
    if isinstance(client, IkLlamaSegmenterClient):
        return client.segment(
            prompt,
            model_id=model_id,
            max_tokens=max_tokens,
            allowed_message_ids=allowed_message_ids,
        )
    return client.segment(prompt, model_id=model_id, max_tokens=max_tokens)


def attach_attempt_diagnostics(
    exc: BaseException,
    *,
    attempt_max_tokens: list[int],
    decode_counts: list[int | None],
    attempt_errors: list[str],
) -> None:
    setattr(
        exc,
        "segmenter_attempt_diagnostics",
        {
            "attempts": len(attempt_max_tokens),
            "attempt_max_tokens": list(attempt_max_tokens),
            "decode_counts": list(decode_counts),
            "attempt_errors": list(attempt_errors),
        },
    )


def segmenter_failure_payload(
    failure_kind: str,
    error: BaseException | None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {"failure_kind": failure_kind}
    if error is not None:
        payload["last_error"] = error_summary(error)
    diagnostics = getattr(error, "segmenter_attempt_diagnostics", None)
    if isinstance(diagnostics, dict):
        payload.update(
            {
                "attempts": diagnostics.get("attempts"),
                "attempt_max_tokens": diagnostics.get("attempt_max_tokens", []),
                "decode_counts": diagnostics.get("decode_counts", []),
                "attempt_errors": diagnostics.get("attempt_errors", []),
            }
        )
    return payload


def decoded_token_count_from_exception(exc: BaseException) -> int | None:
    decoded = getattr(exc, "decoded_tokens", None)
    return int(decoded) if isinstance(decoded, int) else None


def decoded_token_count_from_response(response: dict[str, Any] | None) -> int | None:
    if not isinstance(response, dict):
        return None
    usage = response.get("usage")
    if isinstance(usage, dict):
        for key in ("completion_tokens", "completion_tokens_details", "predicted_tokens"):
            value = usage.get(key)
            if isinstance(value, int):
                return value
            if isinstance(value, dict):
                nested = value.get("accepted_prediction_tokens")
                if isinstance(nested, int):
                    return nested
    for container_key in ("timings", "generation_settings"):
        container = response.get(container_key)
        if isinstance(container, dict):
            for key in ("n_decoded", "predicted_n", "tokens_predicted"):
                value = container.get(key)
                if isinstance(value, int):
                    return value
    for key in ("n_decoded", "predicted_n", "tokens_predicted"):
        value = response.get(key)
        if isinstance(value, int):
            return value
    return None


def error_summary(error: BaseException, *, limit: int = 2000) -> str:
    text = str(error)
    if len(text) <= limit:
        return text
    return text[: limit - 3] + "..."


def retry_max_tokens(base_max_tokens: int, retry_number: int) -> int:
    return max(base_max_tokens, min(RETRY_MAX_TOKENS, base_max_tokens * (2**retry_number)))


def is_likely_truncation_error(exc: Exception) -> bool:
    return is_likely_truncation_text(str(exc))


def is_likely_truncation_text(message: str) -> bool:
    message = message.lower()
    return (
        "unterminated string" in message
        or "truncated" in message
        or "unexpected end" in message
    )


@contextmanager
def segmenter_request_deadline(seconds: int):
    if seconds <= 0:
        yield
        return
    old_handler = signal.getsignal(signal.SIGALRM)
    old_timer = signal.setitimer(signal.ITIMER_REAL, 0)

    def handle_timeout(signum, frame):
        raise SegmenterRequestTimeout(
            f"local segmenter request exceeded {seconds}s deadline"
        )

    signal.signal(signal.SIGALRM, handle_timeout)
    signal.setitimer(signal.ITIMER_REAL, seconds)
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, old_handler)
        if old_timer[0] > 0:
            signal.setitimer(signal.ITIMER_REAL, old_timer[0], old_timer[1])


def retry_segmenter_prompt(prompt: str, last_error: Exception | None) -> str:
    return f"""
The previous segmentation attempt failed to produce parseable schema-valid JSON.

Failure:
{last_error}

Retry with a more compact response:
- Return exactly one JSON object.
- Do not use Markdown fences.
- Keep each segment `content_text` concise enough to avoid response truncation.
- Preserve the correct ordered `message_ids`.
- Put uncertainty in `raw`.

Original task and conversation window:
{prompt}
""".strip()


def fetch_conversation(conn: psycopg.Connection, conversation_id: str) -> dict[str, Any]:
    row = conn.execute(
        """
        SELECT id::text, source_id::text, source_kind::text, privacy_tier
        FROM conversations
        WHERE id = %s
        """,
        (conversation_id,),
    ).fetchone()
    if not row:
        raise SegmentationError(f"conversation not found: {conversation_id}")
    return {
        "id": row[0],
        "source_id": row[1],
        "source_kind": row[2],
        "privacy_tier": row[3],
    }


def fetch_messages(conn: psycopg.Connection, conversation_id: str) -> list[ConversationMessage]:
    return [
        ConversationMessage(
            id=row[0],
            sequence_index=row[1],
            role=row[2],
            content_text=row[3],
            privacy_tier=row[4],
        )
        for row in conn.execute(
            """
            SELECT id::text, sequence_index, role, content_text, privacy_tier
            FROM messages
            WHERE conversation_id = %s
            ORDER BY sequence_index
            """,
            (conversation_id,),
        ).fetchall()
    ]


def find_existing_generation(
    conn: psycopg.Connection,
    *,
    parent_kind: str,
    parent_id: str,
    prompt_version: str,
    model_version: str,
) -> dict[str, Any] | None:
    row = conn.execute(
        """
        SELECT id::text, status
        FROM segment_generations
        WHERE parent_kind = %s
          AND parent_id = %s
          AND segmenter_prompt_version = %s
          AND segmenter_model_version = %s
          AND status IN ('segmenting', 'segmented', 'embedding', 'active')
        ORDER BY created_at DESC
        LIMIT 1
        """,
        (parent_kind, parent_id, prompt_version, model_version),
    ).fetchone()
    if not row:
        return None
    return {"id": row[0], "status": row[1]}


def create_generation(
    conn: psycopg.Connection,
    *,
    parent_kind: str,
    parent_id: str,
    prompt_version: str,
    model_version: str,
    raw_payload: dict[str, Any],
) -> str:
    row = conn.execute(
        """
        INSERT INTO segment_generations (
            parent_kind,
            parent_id,
            segmenter_prompt_version,
            segmenter_model_version,
            status,
            raw_payload
        )
        VALUES (%s, %s, %s, %s, 'segmenting', %s)
        RETURNING id::text
        """,
        (parent_kind, parent_id, prompt_version, model_version, Jsonb(raw_payload)),
    ).fetchone()
    return row[0]


def append_generation_metadata(
    conn: psycopg.Connection,
    generation_id: str,
    payload: dict[str, Any],
) -> None:
    conn.execute(
        """
        UPDATE segment_generations
        SET raw_payload = raw_payload || %s
        WHERE id = %s
        """,
        (Jsonb(payload), generation_id),
    )


def next_segment_sequence_index(conn: psycopg.Connection, generation_id: str) -> int:
    row = conn.execute(
        "SELECT COALESCE(MAX(sequence_index) + 1, 0) FROM segments WHERE generation_id = %s",
        (generation_id,),
    ).fetchone()
    return int(row[0])


def next_window_index(conn: psycopg.Connection, generation_id: str) -> int:
    row = conn.execute(
        """
        SELECT COALESCE(MAX(window_index) + 1, 0)
        FROM segments
        WHERE generation_id = %s
          AND window_index IS NOT NULL
        """,
        (generation_id,),
    ).fetchone()
    return int(row[0])


def insert_segment(
    conn: psycopg.Connection,
    *,
    generation_id: str,
    source_id: str,
    source_kind: str,
    conversation_id: str,
    message_ids: list[str],
    sequence_index: int,
    content_text: str,
    summary_text: str | None,
    window_strategy: str,
    window_index: int | None,
    prompt_version: str,
    model_version: str,
    privacy_tier: int,
    raw_payload: dict[str, Any],
) -> str:
    row = conn.execute(
        """
        INSERT INTO segments (
            generation_id,
            source_id,
            source_kind,
            conversation_id,
            message_ids,
            sequence_index,
            content_text,
            summary_text,
            window_strategy,
            window_index,
            segmenter_prompt_version,
            segmenter_model_version,
            privacy_tier,
            raw_payload
        )
        VALUES (
            %s, %s, %s, %s, %s::uuid[], %s, %s, %s, %s, %s, %s, %s, %s, %s
        )
        RETURNING id::text
        """,
        (
            generation_id,
            source_id,
            source_kind,
            conversation_id,
            message_ids,
            sequence_index,
            content_text,
            summary_text,
            window_strategy,
            window_index,
            prompt_version,
            model_version,
            privacy_tier,
            Jsonb(raw_payload),
        ),
    ).fetchone()
    return row[0]


def build_windows(
    messages: list[ConversationMessage],
    window_char_budget: int,
) -> list[MessageWindow]:
    if not messages:
        return []
    total = sum(prompt_message_length(message) for message in messages)
    if total <= window_char_budget:
        return [MessageWindow(index=0, messages=messages)]

    windows: list[MessageWindow] = []
    start = 0
    while start < len(messages):
        char_count = 0
        end = start
        truncated: list[str] = []
        while end < len(messages):
            message_len = prompt_message_length(messages[end])
            if end > start and char_count + message_len > window_char_budget:
                break
            if message_len > window_char_budget:
                truncated.append(messages[end].id)
            char_count += min(message_len, window_char_budget)
            end += 1
        windows.append(
            MessageWindow(
                index=len(windows),
                messages=messages[start:end],
                truncated_message_ids=truncated,
            )
        )
        if end >= len(messages):
            break
        start = max(start + 1, end - WINDOW_OVERLAP_MESSAGES)
    return windows


def prompt_message_length(message: ConversationMessage) -> int:
    return len(prompt_content_for_message(message)) + len(message.id) + len(message.role or "") + 80


def window_has_embeddable_text(window: MessageWindow) -> bool:
    for message in window.messages:
        if embeddable_content_for_message(message):
            return True
    return False


def build_segmenter_prompt(window: MessageWindow, window_strategy: str) -> str:
    messages = "\n".join(
        format_message_for_prompt(
            message,
            truncated=message.id in set(window.truncated_message_ids),
        )
        for message in window.messages
    )
    return f"""
Segment the conversation window into topic-coherent segments.

Return one JSON object matching this exact shape:
{{"segments":[{{"message_ids":["uuid"],"summary":"string or null","content_text":"non-empty string","raw":{{}}}}]}}

Rules:
- Use only message ids shown in this window.
- `message_ids` must be in the original message order.
- Include null-content message ids when they are inside a covered span.
- `content_text` is the exact text that will be embedded, so omit image/tool-only placeholders unless they carry semantic content.
- Tool/file artifact placeholders are provenance markers, not embeddable text; do not copy them into `content_text`.
- Short or single-topic windows may produce one segment.
- Put uncertainty about window boundaries or overlap inside `raw`.
- Return JSON only. No Markdown fences and no explanatory text.

window_strategy={window_strategy}
window_index={window.index}

<conversation_window>
{messages}
</conversation_window>
""".strip()


def format_message_for_prompt(
    message: ConversationMessage,
    *,
    truncated: bool = False,
) -> str:
    content = prompt_content_for_message(message)
    max_chars = 1000 if truncated else max(4000, DEFAULT_WINDOW_CHAR_BUDGET // 2)
    if len(content) > max_chars:
        content = content[:max_chars] + "\n[message truncated for bounded segmentation prompt]"
    role = message.role or "unknown"
    return (
        f'<message id="{message.id}" sequence="{message.sequence_index}" role="{role}">\n'
        f"{content}\n"
        "</message>"
    )


def prompt_content_for_message(message: ConversationMessage) -> str:
    content = message.content_text or ""
    if is_non_embeddable_tool_artifact(message):
        return tool_artifact_placeholder(message)
    return content or "[no text content]"


def embeddable_content_for_message(message: ConversationMessage) -> str:
    if is_non_embeddable_tool_artifact(message):
        return ""
    return canonicalize_embeddable_text(message.content_text or "")


def is_non_embeddable_tool_artifact(message: ConversationMessage) -> bool:
    role = (message.role or "").lower()
    if role != "tool":
        return False
    return True


def tool_artifact_placeholder(message: ConversationMessage) -> str:
    content = message.content_text or ""
    markers: list[str] = ["tool"]
    if FILECITE_RE.search(content):
        markers.append("filecite")
    if URL_RE.search(content):
        markers.append("urls")
    if "Role Profiles Export" in content:
        markers.append("role_profile_export")
    return (
        "[tool artifact omitted: "
        f"chars={len(content)}, markers={','.join(dict.fromkeys(markers))}]"
    )


def canonicalize_embeddable_text(text: str) -> str:
    lines: list[str] = []
    for line in text.splitlines():
        if MARKER_ONLY_RE.match(line):
            continue
        lines.append(line.rstrip())
    collapsed = "\n".join(lines)
    collapsed = re.sub(r"\n{3,}", "\n\n", collapsed)
    return collapsed.strip()


def expand_message_span(
    message_ids: list[str],
    sequence_by_id: dict[str, int],
) -> list[str]:
    for message_id in message_ids:
        if message_id not in sequence_by_id:
            raise SegmentationError(f"segmenter returned unknown message id: {message_id}")
    ordered = sorted(message_ids, key=lambda message_id: sequence_by_id[message_id])
    min_sequence = sequence_by_id[ordered[0]]
    max_sequence = sequence_by_id[ordered[-1]]
    return [
        message_id
        for message_id, sequence in sorted(sequence_by_id.items(), key=lambda item: item[1])
        if min_sequence <= sequence <= max_sequence
    ]


def apply_reclassification_invalidations(conn: psycopg.Connection) -> int:
    rows = conn.execute(
        """
        SELECT c.id::text, c.raw_payload
        FROM captures c
        WHERE c.capture_type = 'reclassification'
          AND NOT EXISTS (
              SELECT 1
              FROM consolidation_progress p
              WHERE p.stage = 'privacy_reclassification'
                AND p.scope = 'capture:' || c.id::text
                AND p.status = 'completed'
          )
        ORDER BY c.imported_at, c.id
        """
    ).fetchall()
    invalidated = 0
    for capture_id, payload in rows:
        target_kind, target_id = parse_reclassification_target(payload)
        if not target_kind or not target_id:
            upsert_progress(
                conn,
                stage="privacy_reclassification",
                scope=f"capture:{capture_id}",
                status="failed",
                position={},
                last_error="missing reclassification target",
                increment_error=True,
            )
            continue
        parent = find_reclassification_parent(conn, target_kind, target_id)
        if not parent:
            upsert_progress(
                conn,
                stage="privacy_reclassification",
                scope=f"capture:{capture_id}",
                status="failed",
                position={"target_kind": target_kind, "target_id": target_id},
                last_error="target raw row not found",
                increment_error=True,
            )
            continue
        invalidated += invalidate_parent_segments(
            conn,
            parent_kind=parent[0],
            parent_id=parent[1],
            target_kind=target_kind,
            target_id=target_id,
        )
        upsert_progress(
            conn,
            stage="segmenter",
            scope=f"{parent[0]}:{parent[1]}",
            status="pending",
            position={"queued_by": f"capture:{capture_id}"},
        )
        upsert_progress(
            conn,
            stage="privacy_reclassification",
            scope=f"capture:{capture_id}",
            status="completed",
            position={
                "target_kind": target_kind,
                "target_id": target_id,
                "parent_kind": parent[0],
                "parent_id": parent[1],
            },
        )
    return invalidated


def parse_reclassification_target(payload: dict[str, Any]) -> tuple[str | None, str | None]:
    target_kind = (
        payload.get("target_kind")
        or payload.get("target_table")
        or payload.get("row_kind")
        or payload.get("kind")
    )
    target_id = payload.get("target_id") or payload.get("row_id") or payload.get("id")
    if isinstance(target_kind, str):
        target_kind = target_kind.removesuffix("s")
    return (
        target_kind if isinstance(target_kind, str) else None,
        target_id if isinstance(target_id, str) else None,
    )


def find_reclassification_parent(
    conn: psycopg.Connection,
    target_kind: str,
    target_id: str,
) -> tuple[str, str] | None:
    if target_kind == "message":
        row = conn.execute(
            "SELECT conversation_id::text FROM messages WHERE id = %s",
            (target_id,),
        ).fetchone()
        return ("conversation", row[0]) if row else None
    if target_kind == "conversation":
        row = conn.execute("SELECT id::text FROM conversations WHERE id = %s", (target_id,)).fetchone()
        return ("conversation", row[0]) if row else None
    if target_kind == "note":
        row = conn.execute("SELECT id::text FROM notes WHERE id = %s", (target_id,)).fetchone()
        return ("note", row[0]) if row else None
    if target_kind == "capture":
        row = conn.execute("SELECT id::text FROM captures WHERE id = %s", (target_id,)).fetchone()
        return ("capture", row[0]) if row else None
    return None


def invalidate_parent_segments(
    conn: psycopg.Connection,
    *,
    parent_kind: str,
    parent_id: str,
    target_kind: str,
    target_id: str,
) -> int:
    if parent_kind == "conversation":
        if target_kind == "message":
            segment_rows = conn.execute(
                """
                SELECT id::text
                FROM segments
                WHERE is_active = true
                  AND conversation_id = %s
                  AND %s::uuid = ANY(message_ids)
                """,
                (parent_id, target_id),
            ).fetchall()
        else:
            segment_rows = conn.execute(
                """
                SELECT id::text
                FROM segments
                WHERE is_active = true
                  AND conversation_id = %s
                """,
                (parent_id,),
            ).fetchall()
    elif parent_kind == "note":
        segment_rows = conn.execute(
            "SELECT id::text FROM segments WHERE is_active = true AND note_id = %s",
            (parent_id,),
        ).fetchall()
    else:
        segment_rows = conn.execute(
            "SELECT id::text FROM segments WHERE is_active = true AND capture_id = %s",
            (parent_id,),
        ).fetchall()

    segment_ids = [row[0] for row in segment_rows]
    if not segment_ids:
        return 0
    reason = f"privacy reclassification of {target_kind}:{target_id}"
    conn.execute(
        """
        UPDATE segments
        SET is_active = false,
            invalidated_at = now(),
            invalidation_reason = %s
        WHERE id = ANY(%s::uuid[])
        """,
        (reason, segment_ids),
    )
    conn.execute(
        """
        UPDATE segment_embeddings
        SET is_active = false
        WHERE segment_id = ANY(%s::uuid[])
        """,
        (segment_ids,),
    )
    return len(segment_ids)


def http_json(
    method: str,
    url: str,
    *,
    payload: dict[str, Any] | None = None,
    timeout: int = 30,
) -> dict[str, Any]:
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={"Content-Type": "application/json"} if payload is not None else {},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read().decode("utf-8")
    except urllib.error.URLError as exc:
        reason = getattr(exc, "reason", None)
        if isinstance(reason, OSError):
            raise SegmenterServiceUnavailable(
                f"local segmenter unavailable: {reason}"
            ) from exc
        raise SegmentationError(f"local segmenter request failed: {exc}") from exc
    except ConnectionResetError as exc:
        raise SegmenterServiceUnavailable(
            f"local segmenter unavailable: {exc}"
        ) from exc
    except TimeoutError as exc:
        raise SegmenterServiceUnavailable(
            f"local segmenter unavailable: {exc}"
        ) from exc
    try:
        parsed = json.loads(body)
    except json.JSONDecodeError as exc:
        raise SegmentationError(f"local segmenter returned non-JSON response: {exc}") from exc
    if not isinstance(parsed, dict):
        raise SegmentationError("local segmenter returned a non-object JSON response")
    return parsed


def ensure_local_base_url(url: str) -> None:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise SegmentationError(f"invalid local segmenter URL scheme: {url}")
    if parsed.hostname not in {"127.0.0.1", "localhost", "::1"}:
        raise SegmentationError(f"segmenter URL must be local-only: {url}")
