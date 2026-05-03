"""Scoring placeholders for the segmentation benchmark.

The real scorer will be implemented after fixture and metric review. These
names are anchors for the SPEC.md scoring plan.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


SCORING_IMPLEMENTATION_VERSION = "segmentation-benchmark-scoring.v0"


@dataclass(frozen=True)
class MetricBundle:
    operational: dict[str, Any] = field(default_factory=dict)
    segmentation: dict[str, Any] = field(default_factory=dict)
    claim_utility: dict[str, Any] = field(default_factory=dict)
    denominators: dict[str, Any] = field(default_factory=dict)


def validate_provenance(*args: Any, **kwargs: Any) -> None:
    raise NotImplementedError("provenance validation is specified but not implemented")


def score_boundaries(*args: Any, **kwargs: Any) -> MetricBundle:
    raise NotImplementedError("boundary scoring is specified but not implemented")


def score_claim_utility(*args: Any, **kwargs: Any) -> MetricBundle:
    raise NotImplementedError("claim utility scoring is specified but not implemented")
