"""Segmentation strategies for the benchmark harness.

This module does not import production segmenter code or write production
state. Local model strategies are benchmark-only and require an explicit
``--allow-local-models`` opt-in.
"""

from __future__ import annotations

import json
import math
import re
import socket
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from hashlib import sha256
from pathlib import Path
from typing import Any, Literal, Protocol


# Benchmark-internal classifier only. This is not production
# segments.window_strategy and does not introduce deferred P-FRAG schema values.
StrategyKind = Literal["llm", "fixed_window", "message_group"]

STRATEGY_IMPLEMENTATION_VERSION = "segmentation-benchmark-strategy.v1"
TOKEN_ESTIMATOR_VERSION = "segmentation-benchmark-token-estimator.v2"
TOKEN_ESTIMATOR_CHARS_PER_TOKEN = 2.5
LOCAL_MODEL_REQUEST_PROFILE_VERSION = "ik-llama-json-schema.d034.benchmark.v1"
LOCAL_MODEL_DEFAULT_BASE_URL = "http://127.0.0.1:8081"
LOCAL_MODEL_DEFAULT_TIMEOUT_SECONDS = 600
LOCAL_MODEL_DEFAULT_MAX_TOKENS = 4096
LOCAL_MODEL_CONTEXT_GUARD_MARGIN_TOKENS = 1024
LOCAL_MODEL_PROMPT_VERSION = "segmentation-benchmark-local-model-prompt.d034.v1"
LOCAL_MODEL_SERVER_ARGS = (
    "--host",
    "127.0.0.1",
    "--port",
    "8081",
    "--gpu-layers",
    "99",
    "--ctx-size",
    "49152",
    "--flash-attn",
    "on",
    "--threads",
    "8",
    "--parallel",
    "1",
    "--batch-size",
    "2048",
    "--ubatch-size",
    "512",
    "--cache-type-k",
    "q8_0",
    "--cache-type-v",
    "q8_0",
    "--jinja",
)
LOCAL_MODEL_SYSTEM_PROMPT = (
    "You are a local-only segmentation benchmark worker. Segment the supplied "
    "public dialogue window into topic-coherent segments and return JSON only."
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


@dataclass(frozen=True)
class BenchmarkMessage:
    id: str
    sequence_index: int
    role: str | None
    content_text: str | None
    privacy_tier: int
    placeholders: tuple[str, ...] = ()


@dataclass(frozen=True)
class BenchmarkParent:
    fixture_id: str | None
    source_kind: str
    parent_id: str
    title: str | None
    privacy_tier: int
    messages: tuple[BenchmarkMessage, ...]
    dataset_kind: str = "synthetic"
    dataset_name: str | None = None
    dataset_split: str | None = None
    expected_boundaries: tuple[int, ...] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SegmentProposal:
    message_ids: tuple[str, ...]
    summary: str | None
    content_text: str
    raw: dict[str, Any] = field(default_factory=dict)
    embeddable_message_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class RunConfig:
    run_id: str
    strategy_config: dict[str, Any] = field(default_factory=dict)
    fixture_version: str | None = None
    allow_local_models: bool = False


@dataclass(frozen=True)
class StrategyOutput:
    strategy_name: str
    strategy_kind: StrategyKind
    parent_id: str
    segments: tuple[SegmentProposal, ...]
    metadata: dict[str, Any] = field(default_factory=dict)
    failures: tuple[dict[str, Any], ...] = ()


class SegmenterStrategy(Protocol):
    name: str
    kind: StrategyKind

    def segment(self, parent: BenchmarkParent, config: RunConfig) -> StrategyOutput:
        """Return proposed segments for one in-memory benchmark parent."""


class StrategyUnavailable(RuntimeError):
    """Raised when a configured benchmark strategy must not run."""


class LocalModelError(RuntimeError):
    """Raised when a local model request cannot produce benchmark output."""

    def __init__(
        self,
        message: str,
        *,
        kind: str = "backend_error",
        response: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.kind = kind
        self.response = response


@dataclass(frozen=True)
class LocalModelProfile:
    strategy_name: str
    model_path: str
    request_profile_version: str = LOCAL_MODEL_REQUEST_PROFILE_VERSION
    prompt_version: str = LOCAL_MODEL_PROMPT_VERSION
    server_args: tuple[str, ...] = LOCAL_MODEL_SERVER_ARGS


class LocalModelClient(Protocol):
    def get_json(self, path: str, *, timeout_seconds: int) -> dict[str, Any]:
        """Read JSON from a local OpenAI-compatible endpoint."""

    def post_json(
        self,
        path: str,
        *,
        payload: dict[str, Any],
        timeout_seconds: int,
    ) -> dict[str, Any]:
        """Write JSON to a local OpenAI-compatible endpoint and parse JSON."""


class UrlLibLocalModelClient:
    def __init__(self, base_url: str) -> None:
        self.base_url = normalize_local_base_url(base_url)

    def get_json(self, path: str, *, timeout_seconds: int) -> dict[str, Any]:
        return self._request_json("GET", path, payload=None, timeout_seconds=timeout_seconds)

    def post_json(
        self,
        path: str,
        *,
        payload: dict[str, Any],
        timeout_seconds: int,
    ) -> dict[str, Any]:
        return self._request_json("POST", path, payload=payload, timeout_seconds=timeout_seconds)

    def _request_json(
        self,
        method: str,
        path: str,
        *,
        payload: dict[str, Any] | None,
        timeout_seconds: int,
    ) -> dict[str, Any]:
        body = None
        headers = {"Accept": "application/json"}
        if payload is not None:
            body = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"
        request = urllib.request.Request(
            f"{self.base_url}{path}",
            data=body,
            headers=headers,
            method=method,
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
                raw = response.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode("utf-8", "replace")
            raise LocalModelError(
                f"HTTP {exc.code} from local model endpoint: {raw[:500]}",
                kind=classify_backend_error(raw, status=exc.code),
            ) from exc
        except (TimeoutError, socket.timeout) as exc:
            raise LocalModelError("local model request timed out", kind="read_timeout") from exc
        except urllib.error.URLError as exc:
            message = str(exc.reason or exc)
            raise LocalModelError(
                f"local model endpoint unavailable: {message}",
                kind=classify_backend_error(message),
            ) from exc

        try:
            decoded = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise LocalModelError(
                f"local model endpoint returned invalid JSON: {exc}",
                kind="schema_invalid",
            ) from exc
        if not isinstance(decoded, dict):
            raise LocalModelError(
                "local model endpoint returned non-object JSON",
                kind="schema_invalid",
            )
        return decoded


class LocalModelStrategy:
    """Benchmark-only local OpenAI-compatible segmentation strategy."""

    name: str
    kind: StrategyKind = "llm"

    def __init__(
        self,
        profile: LocalModelProfile,
        *,
        client: LocalModelClient | None = None,
    ) -> None:
        self.profile = profile
        self.name = profile.strategy_name
        self.client = client
        self._file_metadata_cache: dict[tuple[str, bool], dict[str, Any]] = {}

    def segment(self, parent: BenchmarkParent, config: RunConfig) -> StrategyOutput:
        if not config.allow_local_models:
            raise StrategyUnavailable(
                f"{self.name} requires --allow-local-models; no model call was made"
            )
        base_url = string_config(
            config.strategy_config,
            "local_model_base_url",
            LOCAL_MODEL_DEFAULT_BASE_URL,
        )
        base_url = normalize_local_base_url(base_url)
        timeout_seconds = positive_int_config(
            config.strategy_config,
            "local_model_timeout_seconds",
            LOCAL_MODEL_DEFAULT_TIMEOUT_SECONDS,
        )
        max_tokens = positive_int_config(
            config.strategy_config,
            "local_model_max_tokens",
            LOCAL_MODEL_DEFAULT_MAX_TOKENS,
        )
        client = self.client or UrlLibLocalModelClient(base_url)
        model_metadata = self.model_metadata(
            client,
            base_url=base_url,
            timeout_seconds=timeout_seconds,
            compute_sha256=bool(config.strategy_config.get("compute_model_sha256", False)),
        )
        metadata: dict[str, Any] = {
            "implementation_version": STRATEGY_IMPLEMENTATION_VERSION,
            "prompt_version": self.profile.prompt_version,
            "request_profile_version": self.profile.request_profile_version,
            "model": model_metadata,
            "request": {
                "base_url": base_url,
                "endpoint": f"{base_url}/v1/chat/completions",
                "stream": False,
                "temperature": 0,
                "top_p": 1,
                "max_tokens": max_tokens,
                "timeout_seconds": timeout_seconds,
                "chat_template_kwargs": {"enable_thinking": False},
                "response_format_type": "json_schema",
                "retries": 0,
            },
        }
        prompt = build_local_model_prompt(parent)
        allowed_message_ids = [message.id for message in ordered_messages(parent)]
        estimated_prompt_tokens = estimate_local_model_prompt_tokens(prompt)
        metadata["request"]["estimated_prompt_tokens"] = estimated_prompt_tokens
        metadata["request"]["context_guard_margin_tokens"] = (
            LOCAL_MODEL_CONTEXT_GUARD_MARGIN_TOKENS
        )

        started = time.perf_counter()
        try:
            response = client.post_json(
                "/v1/chat/completions",
                payload=local_model_payload(
                    model_path=expanded_model_path(self.profile.model_path),
                    prompt=prompt,
                    max_tokens=max_tokens,
                    allowed_message_ids=allowed_message_ids,
                ),
                timeout_seconds=timeout_seconds,
            )
            segments = parse_local_model_response(response, parent)
        except LocalModelError as exc:
            latency_seconds = time.perf_counter() - started
            metadata["request"]["latency_seconds"] = latency_seconds
            metadata["request"]["status"] = "failed"
            metadata["request"]["failure_kind"] = exc.kind
            metadata["request"]["failure_error"] = str(exc)
            return StrategyOutput(
                strategy_name=self.name,
                strategy_kind=self.kind,
                parent_id=parent.parent_id,
                segments=(),
                metadata=metadata,
                failures=(
                    {
                        "kind": exc.kind,
                        "stage": "local_model_request",
                        "error": str(exc),
                        "latency_seconds": latency_seconds,
                    },
                ),
            )
        latency_seconds = time.perf_counter() - started
        metadata["request"]["latency_seconds"] = latency_seconds
        metadata["request"]["status"] = "ok"
        metadata["request"]["returned_segment_count"] = len(segments)
        return StrategyOutput(
            strategy_name=self.name,
            strategy_kind=self.kind,
            parent_id=parent.parent_id,
            segments=tuple(segments),
            metadata=metadata,
        )

    def model_metadata(
        self,
        client: LocalModelClient,
        *,
        base_url: str,
        timeout_seconds: int,
        compute_sha256: bool,
    ) -> dict[str, Any]:
        path = expanded_model_path(self.profile.model_path)
        file_metadata = self.model_file_metadata(
            path,
            compute_sha256=compute_sha256,
        )
        metadata: dict[str, Any] = {
            "model_id": path,
            "model_path": path,
            "request_profile": self.profile.request_profile_version,
            "endpoint": f"{base_url}/v1/chat/completions",
            "server_args": [
                "--model",
                path,
                *self.profile.server_args,
            ],
            "models_response": None,
            "props_response": None,
            **file_metadata,
        }
        for endpoint, key in (("/v1/models", "models_response"), ("/props", "props_response")):
            try:
                metadata[key] = client.get_json(endpoint, timeout_seconds=timeout_seconds)
            except LocalModelError as exc:
                metadata[f"{key}_error"] = {"kind": exc.kind, "error": str(exc)}
        return metadata

    def model_file_metadata(
        self,
        path: str,
        *,
        compute_sha256: bool,
    ) -> dict[str, Any]:
        key = (path, compute_sha256)
        cached = self._file_metadata_cache.get(key)
        if cached is not None:
            return dict(cached)
        metadata: dict[str, Any] = {
            "model_sha256": "not_computed",
            "model_sha256_sidecar": "not_written",
            "path_exists": Path(path).exists(),
            "size_bytes": model_file_size(path),
        }
        if compute_sha256:
            try:
                metadata["model_sha256"] = model_file_sha256(path)
            except OSError as exc:
                metadata["model_sha256"] = "not_computed"
                metadata["model_sha256_error"] = str(exc)
        self._file_metadata_cache[key] = dict(metadata)
        return metadata


class FixedTokenWindowsStrategy:
    name = "fixed_token_windows"
    kind: StrategyKind = "fixed_window"

    def segment(self, parent: BenchmarkParent, config: RunConfig) -> StrategyOutput:
        target_tokens = positive_int_config(config.strategy_config, "target_tokens", 200)
        overlap_messages = non_negative_int_config(
            config.strategy_config, "overlap_messages", 0
        )
        messages = tuple(sorted(parent.messages, key=lambda message: message.sequence_index))
        segments: list[SegmentProposal] = []
        index = 0

        while index < len(messages):
            start = index
            current: list[BenchmarkMessage] = []
            current_tokens = 0

            while index < len(messages):
                message = messages[index]
                message_tokens = estimate_message_tokens(message)
                if not current:
                    current.append(message)
                    current_tokens += message_tokens
                    index += 1
                    if message_tokens > target_tokens:
                        break
                    continue
                if current_tokens + message_tokens > target_tokens:
                    break
                current.append(message)
                current_tokens += message_tokens
                index += 1

            segments.append(
                build_segment(
                    current,
                    raw={
                        "strategy": self.name,
                        "target_tokens": target_tokens,
                        "estimated_tokens": current_tokens,
                        "single_message_over_target": (
                            len(current) == 1
                            and estimate_message_tokens(current[0]) > target_tokens
                        ),
                    },
                )
            )

            if overlap_messages > 0 and index < len(messages):
                next_index = max(start + 1, index - min(overlap_messages, len(current) - 1))
                index = next_index

        return StrategyOutput(
            strategy_name=self.name,
            strategy_kind=self.kind,
            parent_id=parent.parent_id,
            segments=tuple(segments),
            metadata={
                "implementation_version": STRATEGY_IMPLEMENTATION_VERSION,
                "token_estimator_version": TOKEN_ESTIMATOR_VERSION,
                "target_tokens": target_tokens,
                "overlap_messages": overlap_messages,
            },
        )


class MessageGroupsStrategy:
    name = "message_groups"
    kind: StrategyKind = "message_group"

    def segment(self, parent: BenchmarkParent, config: RunConfig) -> StrategyOutput:
        target_tokens = positive_int_config(config.strategy_config, "target_tokens", 200)
        messages = tuple(sorted(parent.messages, key=lambda message: message.sequence_index))
        units = natural_turn_units(messages)
        segments: list[SegmentProposal] = []
        current_units: list[tuple[BenchmarkMessage, ...]] = []
        current_tokens = 0

        for unit in units:
            unit_tokens = sum(estimate_message_tokens(message) for message in unit)
            if not current_units:
                current_units.append(unit)
                current_tokens += unit_tokens
                if unit_tokens > target_tokens:
                    segments.append(
                        build_segment(
                            flatten_units(current_units),
                            raw={
                                "strategy": self.name,
                                "target_tokens": target_tokens,
                                "estimated_tokens": current_tokens,
                                "unit_over_target": True,
                            },
                        )
                    )
                    current_units = []
                    current_tokens = 0
                continue
            if current_tokens + unit_tokens > target_tokens:
                segments.append(
                    build_segment(
                        flatten_units(current_units),
                        raw={
                            "strategy": self.name,
                            "target_tokens": target_tokens,
                            "estimated_tokens": current_tokens,
                        },
                    )
                )
                current_units = [unit]
                current_tokens = unit_tokens
            else:
                current_units.append(unit)
                current_tokens += unit_tokens

        if current_units:
            segments.append(
                build_segment(
                    flatten_units(current_units),
                    raw={
                        "strategy": self.name,
                        "target_tokens": target_tokens,
                        "estimated_tokens": current_tokens,
                    },
                )
            )

        return StrategyOutput(
            strategy_name=self.name,
            strategy_kind=self.kind,
            parent_id=parent.parent_id,
            segments=tuple(segments),
            metadata={
                "implementation_version": STRATEGY_IMPLEMENTATION_VERSION,
                "token_estimator_version": TOKEN_ESTIMATOR_VERSION,
                "target_tokens": target_tokens,
            },
        )


def positive_int_config(config: dict[str, Any], key: str, default: int) -> int:
    value = int(config.get(key, default))
    if value <= 0:
        raise ValueError(f"{key} must be positive")
    return value


def non_negative_int_config(config: dict[str, Any], key: str, default: int) -> int:
    value = int(config.get(key, default))
    if value < 0:
        raise ValueError(f"{key} must be non-negative")
    return value


def string_config(config: dict[str, Any], key: str, default: str) -> str:
    value = config.get(key, default)
    if not isinstance(value, str) or not value:
        raise ValueError(f"{key} must be a non-empty string")
    return value


def estimate_text_tokens(text: str | None) -> int:
    if not text:
        return 0
    return max(1, math.ceil(len(text) / TOKEN_ESTIMATOR_CHARS_PER_TOKEN))


def estimate_message_tokens(message: BenchmarkMessage) -> int:
    return estimate_text_tokens(embeddable_content_for_message(message))


def normalize_local_base_url(base_url: str) -> str:
    parsed = urllib.parse.urlparse(base_url)
    if parsed.scheme != "http":
        raise StrategyUnavailable("local model base URL must use http")
    if parsed.username or parsed.password:
        raise StrategyUnavailable("local model base URL must not include credentials")
    hostname = parsed.hostname
    if hostname not in {"127.0.0.1", "localhost", "::1"}:
        raise StrategyUnavailable(
            f"local model base URL must be loopback-only, got host {hostname!r}"
        )
    if parsed.params or parsed.query or parsed.fragment:
        raise StrategyUnavailable("local model base URL must not include params/query/fragment")
    path = parsed.path.rstrip("/")
    if path:
        raise StrategyUnavailable("local model base URL must not include a path")
    netloc = parsed.netloc
    return urllib.parse.urlunparse(("http", netloc, "", "", "", ""))


def classify_backend_error(message: str, *, status: int | None = None) -> str:
    lowered = message.casefold()
    if "connection refused" in lowered or "errno 111" in lowered:
        return "connect_refused"
    if "timed out" in lowered or "timeout" in lowered:
        return "read_timeout"
    if "empty grammar stack" in lowered:
        return "grammar_stack_empty"
    if "cuda" in lowered and ("out of memory" in lowered or "oom" in lowered):
        return "cuda_oom"
    if status is not None and status >= 500:
        return "http_5xx"
    return "unknown"


def expanded_model_path(model_path: str) -> str:
    return str(Path(model_path).expanduser())


def model_file_size(model_path: str) -> int | None:
    try:
        return Path(model_path).stat().st_size
    except OSError:
        return None


def model_file_sha256(model_path: str) -> str:
    digest = sha256()
    with Path(model_path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def ordered_messages(parent: BenchmarkParent) -> tuple[BenchmarkMessage, ...]:
    return tuple(sorted(parent.messages, key=lambda message: message.sequence_index))


def build_local_model_prompt(parent: BenchmarkParent) -> str:
    messages = "\n".join(
        format_local_model_message(message) for message in ordered_messages(parent)
    )
    return f"""
Segment the public dialogue window into topic-coherent segments.

Return one JSON object matching this exact shape:
{{"segments":[{{"message_ids":["uuid"],"summary":"string or null","content_text":"non-empty string","raw":{{}}}}]}}

Rules:
- Use only message ids shown in this window.
- `message_ids` must be in the original message order.
- Include messages inside a covered span even if their text is not embeddable.
- `content_text` is the exact text that will be embedded for the segment.
- Tool/file artifact placeholders are provenance markers, not embeddable text; do not copy them into `content_text`.
- Short or single-topic windows may produce one segment.
- Put uncertainty about window boundaries inside `raw`.
- Return JSON only. No Markdown fences and no explanatory text.

benchmark_dataset={parent.dataset_name or parent.dataset_kind}
parent_id={parent.parent_id}

<conversation_window>
{messages}
</conversation_window>
""".strip()


def format_local_model_message(message: BenchmarkMessage) -> str:
    content = prompt_content_for_local_model(message)
    role = message.role or "unknown"
    return (
        f'<message id="{message.id}" sequence="{message.sequence_index}" role="{role}">\n'
        f"{content}\n"
        "</message>"
    )


def prompt_content_for_local_model(message: BenchmarkMessage) -> str:
    if (message.role or "").lower() == "tool":
        return f"[tool artifact omitted: chars={len(message.content_text or '')}]"
    content = message.content_text or ""
    return content or "[no text content]"


def estimate_local_model_prompt_tokens(prompt: str) -> int:
    rendered_chars = len(LOCAL_MODEL_SYSTEM_PROMPT) + len(prompt) + 512
    return math.ceil(rendered_chars / TOKEN_ESTIMATOR_CHARS_PER_TOKEN)


def segmentation_json_schema(allowed_message_ids: list[str]) -> dict[str, Any]:
    if not allowed_message_ids:
        raise LocalModelError(
            "cannot constrain benchmark schema to zero message ids",
            kind="schema_invalid",
        )
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
                            "items": {
                                "type": "string",
                                "enum": list(dict.fromkeys(allowed_message_ids)),
                            },
                        },
                        "summary": {"type": ["string", "null"]},
                        "content_text": {"type": "string", "minLength": 1},
                        "raw": {"type": "object", "additionalProperties": True},
                    },
                },
            }
        },
    }


def local_model_payload(
    *,
    model_path: str,
    prompt: str,
    max_tokens: int,
    allowed_message_ids: list[str],
) -> dict[str, Any]:
    return {
        "model": model_path,
        "messages": [
            {"role": "system", "content": LOCAL_MODEL_SYSTEM_PROMPT},
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


def parse_local_model_response(
    response: dict[str, Any],
    parent: BenchmarkParent,
) -> list[SegmentProposal]:
    choices = response.get("choices")
    if not isinstance(choices, list) or not choices:
        raise LocalModelError(
            "local model response missing choices",
            kind="schema_invalid",
            response=response,
        )
    message = choices[0].get("message") if isinstance(choices[0], dict) else None
    if not isinstance(message, dict):
        raise LocalModelError(
            "local model response missing choices[0].message",
            kind="schema_invalid",
            response=response,
        )
    content = message.get("content")
    if not isinstance(content, str) or not content.strip():
        if message.get("reasoning_content"):
            error = "local model returned payload only in reasoning_content"
        else:
            error = "local model returned empty message content"
        raise LocalModelError(error, kind="schema_invalid", response=response)
    stripped = content.strip()
    if stripped.startswith("```"):
        raise LocalModelError(
            "local model returned Markdown-fenced JSON",
            kind="schema_invalid",
            response=response,
        )
    try:
        payload = json.loads(stripped)
    except json.JSONDecodeError as exc:
        raise LocalModelError(
            f"local model returned invalid JSON: {exc}",
            kind="schema_invalid",
            response=response,
        ) from exc
    return parse_local_model_payload(payload, parent)


def parse_local_model_payload(payload: Any, parent: BenchmarkParent) -> list[SegmentProposal]:
    if not isinstance(payload, dict) or set(payload) != {"segments"}:
        raise LocalModelError(
            "segmentation payload must contain only segments",
            kind="schema_invalid",
        )
    raw_segments = payload["segments"]
    if not isinstance(raw_segments, list) or not raw_segments:
        raise LocalModelError(
            "segmentation payload must contain at least one segment",
            kind="schema_invalid",
        )
    allowed_message_ids = {message.id for message in parent.messages}
    embeddable_message_ids = {
        message.id for message in parent.messages if is_embeddable_message(message)
    }
    segments: list[SegmentProposal] = []
    expected_keys = {"message_ids", "summary", "content_text", "raw"}
    for index, raw_segment in enumerate(raw_segments):
        if not isinstance(raw_segment, dict) or set(raw_segment) != expected_keys:
            raise LocalModelError(
                f"segment {index} does not match the schema",
                kind="schema_invalid",
            )
        message_ids = raw_segment["message_ids"]
        if (
            not isinstance(message_ids, list)
            or not message_ids
            or not all(isinstance(value, str) and value for value in message_ids)
        ):
            raise LocalModelError(
                f"segment {index} has invalid message_ids",
                kind="schema_invalid",
            )
        unknown = [message_id for message_id in message_ids if message_id not in allowed_message_ids]
        if unknown:
            raise LocalModelError(
                f"segment {index} contains message_ids outside this parent: {unknown}",
                kind="schema_invalid",
            )
        summary = raw_segment["summary"]
        if summary is not None and not isinstance(summary, str):
            raise LocalModelError(
                f"segment {index} has invalid summary",
                kind="schema_invalid",
            )
        content_text = raw_segment["content_text"]
        if not isinstance(content_text, str) or not content_text.strip():
            raise LocalModelError(
                f"segment {index} has empty content_text",
                kind="schema_invalid",
            )
        raw = raw_segment["raw"]
        if not isinstance(raw, dict):
            raise LocalModelError(
                f"segment {index} has invalid raw metadata",
                kind="schema_invalid",
            )
        raw = dict(raw)
        raw.setdefault("request_profile_version", LOCAL_MODEL_REQUEST_PROFILE_VERSION)
        segments.append(
            SegmentProposal(
                message_ids=tuple(message_ids),
                embeddable_message_ids=tuple(
                    message_id for message_id in message_ids if message_id in embeddable_message_ids
                ),
                summary=summary,
                content_text=content_text.strip(),
                raw=raw,
            )
        )
    return segments


def is_embeddable_message(message: BenchmarkMessage) -> bool:
    role = (message.role or "").lower()
    if role == "tool":
        return False
    if message.placeholders and not (message.content_text or "").strip():
        return False
    return bool(embeddable_content_for_message(message))


def embeddable_content_for_message(message: BenchmarkMessage) -> str:
    if (message.role or "").lower() == "tool":
        return ""
    lines: list[str] = []
    for line in (message.content_text or "").splitlines():
        if MARKER_ONLY_RE.match(line):
            continue
        lines.append(line.rstrip())
    collapsed = "\n".join(lines)
    collapsed = re.sub(r"\n{3,}", "\n\n", collapsed)
    return collapsed.strip()


def build_segment(messages: list[BenchmarkMessage], *, raw: dict[str, Any]) -> SegmentProposal:
    ordered = tuple(sorted(messages, key=lambda message: message.sequence_index))
    embeddable = tuple(message for message in ordered if is_embeddable_message(message))
    content_parts = [embeddable_content_for_message(message) for message in embeddable]
    content_text = "\n".join(part for part in content_parts if part).strip()
    return SegmentProposal(
        message_ids=tuple(message.id for message in ordered),
        embeddable_message_ids=tuple(message.id for message in embeddable),
        summary=None,
        content_text=content_text,
        raw=raw,
    )


def natural_turn_units(
    messages: tuple[BenchmarkMessage, ...]
) -> list[tuple[BenchmarkMessage, ...]]:
    units: list[tuple[BenchmarkMessage, ...]] = []
    index = 0
    while index < len(messages):
        message = messages[index]
        next_message = messages[index + 1] if index + 1 < len(messages) else None
        if (
            (message.role or "").lower() == "user"
            and next_message is not None
            and (next_message.role or "").lower() == "assistant"
        ):
            units.append((message, next_message))
            index += 2
        else:
            units.append((message,))
            index += 1
    return units


def flatten_units(units: list[tuple[BenchmarkMessage, ...]]) -> list[BenchmarkMessage]:
    return [message for unit in units for message in unit]


DEFAULT_STRATEGIES: dict[str, SegmenterStrategy] = {
    "qwen_35b_a3b_apex_i_compact_d034": LocalModelStrategy(
        LocalModelProfile(
            "qwen_35b_a3b_apex_i_compact_d034",
            "~/models/Qwen3.6-35B-A3B-APEX-I-Compact.gguf",
        )
    ),
    "qwen_35b_a3b_ud_iq4_xs_d034": LocalModelStrategy(
        LocalModelProfile(
            "qwen_35b_a3b_ud_iq4_xs_d034",
            "~/models/Qwen3.6-35B-A3B-UD-IQ4_XS.gguf",
        )
    ),
    "qwen_35b_a3b_ud_q3_k_m_d034": LocalModelStrategy(
        LocalModelProfile(
            "qwen_35b_a3b_ud_q3_k_m_d034",
            "~/models/Qwen3.6-35B-A3B-UD-Q3_K_M.gguf",
        )
    ),
    "qwen_35b_a3b_iq4_xs_d034": LocalModelStrategy(
        LocalModelProfile(
            "qwen_35b_a3b_iq4_xs_d034",
            "~/models/Qwen_Qwen3.6-35B-A3B-IQ4_XS.gguf",
        )
    ),
    "qwen_27b_q5_k_m_d034": LocalModelStrategy(
        LocalModelProfile(
            "qwen_27b_q5_k_m_d034",
            "~/models/Qwen3.6-27B-Q5_K_M.gguf",
        )
    ),
    "gemma_26b_a4b_q4_k_m_d034": LocalModelStrategy(
        LocalModelProfile(
            "gemma_26b_a4b_q4_k_m_d034",
            "~/models/gemma-4-26B-A4B-it-GGUF/gemma-4-26B-A4B-it-Q4_K_M.gguf",
        )
    ),
    "fixed_token_windows": FixedTokenWindowsStrategy(),
    "message_groups": MessageGroupsStrategy(),
}
