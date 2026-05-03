"""Segmentation strategies for the benchmark harness.

This module is intentionally side-effect free. It does not call local models,
open network connections, import production segmenter code, or write
production state.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from typing import Any, Literal, Protocol


# Benchmark-internal classifier only. This is not production
# segments.window_strategy and does not introduce deferred P-FRAG schema values.
StrategyKind = Literal["llm", "fixed_window", "message_group"]

STRATEGY_IMPLEMENTATION_VERSION = "segmentation-benchmark-strategy.v1"
TOKEN_ESTIMATOR_VERSION = "segmentation-benchmark-token-estimator.v2"
TOKEN_ESTIMATOR_CHARS_PER_TOKEN = 2.5

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


class LocalModelStrategy:
    """Safe placeholder for future local-model benchmark strategies."""

    name: str
    kind: StrategyKind = "llm"

    def __init__(self, name: str) -> None:
        self.name = name

    def segment(self, parent: BenchmarkParent, config: RunConfig) -> StrategyOutput:
        if not config.allow_local_models:
            raise StrategyUnavailable(
                f"{self.name} requires --allow-local-models; no model call was made"
            )
        raise NotImplementedError(
            f"{self.name} is registered but local-model execution is not implemented"
        )


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


def estimate_text_tokens(text: str | None) -> int:
    if not text:
        return 0
    return max(1, math.ceil(len(text) / TOKEN_ESTIMATOR_CHARS_PER_TOKEN))


def estimate_message_tokens(message: BenchmarkMessage) -> int:
    return estimate_text_tokens(embeddable_content_for_message(message))


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
    "current_qwen_d034": LocalModelStrategy("current_qwen_d034"),
    "qwen_candidate_d034": LocalModelStrategy("qwen_candidate_d034"),
    "gemma_candidate_d034": LocalModelStrategy("gemma_candidate_d034"),
    "fixed_token_windows": FixedTokenWindowsStrategy(),
    "message_groups": MessageGroupsStrategy(),
}
