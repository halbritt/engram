"""Strategy interfaces for the future segmentation benchmark runner.

This module is intentionally side-effect free. It does not call local models,
open network connections, or write production state.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Protocol


StrategyKind = Literal["llm", "fixed_window", "message_group"]


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
    fixture_id: str
    source_kind: str
    parent_id: str
    title: str | None
    privacy_tier: int
    messages: tuple[BenchmarkMessage, ...]


@dataclass(frozen=True)
class SegmentProposal:
    message_ids: tuple[str, ...]
    summary: str | None
    content_text: str
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RunConfig:
    run_id: str
    fixture_version: str
    strategy_config: dict[str, Any] = field(default_factory=dict)


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


class NotImplementedStrategy:
    """Named strategy placeholder for the spec-only skeleton."""

    name: str
    kind: StrategyKind

    def __init__(self, name: str, kind: StrategyKind) -> None:
        self.name = name
        self.kind = kind

    def segment(self, parent: BenchmarkParent, config: RunConfig) -> StrategyOutput:
        raise NotImplementedError(
            f"{self.name} is specified but not implemented in this skeleton"
        )


DEFAULT_STRATEGIES: dict[str, SegmenterStrategy] = {
    "current_qwen_d034": NotImplementedStrategy("current_qwen_d034", "llm"),
    "qwen_candidate_d034": NotImplementedStrategy("qwen_candidate_d034", "llm"),
    "gemma_candidate_d034": NotImplementedStrategy("gemma_candidate_d034", "llm"),
    "fixed_token_windows": NotImplementedStrategy("fixed_token_windows", "fixed_window"),
    "message_groups": NotImplementedStrategy("message_groups", "message_group"),
}
