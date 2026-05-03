"""Scoring for deterministic segmentation benchmark outputs."""

from __future__ import annotations

import math
import re
import unicodedata
from dataclasses import dataclass, field
from typing import Any

from benchmarks.segmentation.fixtures import ExpectedClaim, ExpectedSegment
from benchmarks.segmentation.strategies import (
    BenchmarkParent,
    SegmentProposal,
    StrategyOutput,
    estimate_text_tokens,
)


SCORING_IMPLEMENTATION_VERSION = "segmentation-benchmark-scoring.v1"
BACKEND_ERROR_CLASSES = (
    "connect_refused",
    "read_timeout",
    "http_5xx",
    "grammar_stack_empty",
    "cuda_oom",
    "backend_wedge_post_smoke",
    "unknown",
)


@dataclass(frozen=True)
class MetricBundle:
    operational: dict[str, Any] = field(default_factory=dict)
    segmentation: dict[str, Any] = field(default_factory=dict)
    claim_utility: dict[str, Any] = field(default_factory=dict)
    denominators: dict[str, Any] = field(default_factory=dict)


def score_strategy_outputs(
    parents: tuple[BenchmarkParent, ...],
    outputs_by_parent: dict[str, StrategyOutput],
    *,
    expected_segments_by_fixture: dict[str, tuple[ExpectedSegment, ...]] | None = None,
    expected_claims_by_fixture: dict[str, tuple[ExpectedClaim, ...]] | None = None,
    durations_by_parent: dict[str, float] | None = None,
) -> MetricBundle:
    expected_segments_by_fixture = expected_segments_by_fixture or {}
    expected_claims_by_fixture = expected_claims_by_fixture or {}
    durations_by_parent = durations_by_parent or {}
    all_message_owner = {
        message.id: parent.parent_id for parent in parents for message in parent.messages
    }

    provenance_failures: list[dict[str, Any]] = []
    token_lengths: list[int] = []
    segment_counts: dict[str, int] = {}
    subfloor_counts = {50: 0, 100: 0, 200: 0}
    backend_error_counts = {kind: 0 for kind in BACKEND_ERROR_CLASSES}
    timeout_count = 0
    runaway_count = 0
    schema_valid_count = 0
    provenance_valid_count = 0
    parent_count = len(parents)
    labeled_parent_count = 0
    strict_parent_scores: list[dict[str, float]] = []
    tolerant_1_scores: list[dict[str, float]] = []
    tolerant_2_scores: list[dict[str, float]] = []
    pk_values: list[float] = []
    windowdiff_values: list[float] = []
    oversplit_total = 0
    undersplit_total = 0

    for parent in parents:
        output = outputs_by_parent.get(parent.parent_id)
        segments = output.segments if output else ()
        parent_failures = list(output.failures if output else ())
        segment_counts[parent.parent_id] = len(segments)
        if not any(failure.get("kind") == "schema_invalid" for failure in parent_failures):
            schema_valid_count += 1

        for failure in parent_failures:
            kind = str(failure.get("kind", "unknown"))
            if kind == "timeout":
                timeout_count += 1
            elif kind == "runaway":
                runaway_count += 1
            elif kind in backend_error_counts:
                backend_error_counts[kind] += 1
            elif kind == "backend_error":
                backend_error_counts["unknown"] += 1

        failures = validate_provenance(parent, segments, all_message_owner)
        provenance_failures.extend(failures)
        if not failures:
            provenance_valid_count += 1

        for segment in segments:
            tokens = estimate_text_tokens(segment.content_text)
            token_lengths.append(tokens)
            for floor in subfloor_counts:
                if tokens < floor:
                    subfloor_counts[floor] += 1

        expected_segments = ()
        if parent.fixture_id:
            expected_segments = expected_segments_by_fixture.get(parent.fixture_id, ())
        expected_boundaries = expected_boundaries_for_parent(parent, expected_segments)
        if expected_boundaries is not None:
            labeled_parent_count += 1
            predicted_boundaries = predicted_boundaries_for_parent(parent, segments)
            strict = boundary_precision_recall_f1(
                set(expected_boundaries), set(predicted_boundaries)
            )
            tolerant_1 = window_tolerant_boundary_f1(
                expected_boundaries, predicted_boundaries, tolerance=1
            )
            tolerant_2 = window_tolerant_boundary_f1(
                expected_boundaries, predicted_boundaries, tolerance=2
            )
            strict_parent_scores.append(strict)
            tolerant_1_scores.append(tolerant_1)
            tolerant_2_scores.append(tolerant_2)
            pk_values.append(pk_score(expected_boundaries, predicted_boundaries, len(parent.messages)))
            windowdiff_values.append(
                windowdiff_score(expected_boundaries, predicted_boundaries, len(parent.messages))
            )
            oversplit_total += strict["false_positives"]
            undersplit_total += strict["false_negatives"]

    expected_claim_count = sum(
        len(claims) for claims in expected_claims_by_fixture.values()
    )
    total_duration = sum(durations_by_parent.values())
    throughput = parent_count / total_duration if total_duration > 0 else None

    operational = {
        "schema_valid_rate": safe_rate(schema_valid_count, parent_count),
        "provenance_valid_rate": safe_rate(provenance_valid_count, parent_count),
        "unknown_message_id_count": count_failure(provenance_failures, "provenance_unknown_id"),
        "cross_parent_message_id_count": count_failure(
            provenance_failures, "provenance_cross_parent_id"
        ),
        "unordered_message_id_count": count_failure(provenance_failures, "provenance_unordered"),
        "empty_embeddable_segment_count": count_failure(
            provenance_failures, "empty_embeddable_text"
        ),
        "sub_floor_fragment_counts": {str(key): value for key, value in subfloor_counts.items()},
        "timeout_count": timeout_count,
        "runaway_count": runaway_count,
        "backend_error_counts": backend_error_counts,
        "parent_throughput_per_second": throughput,
        "token_throughput": "not_applicable",
        "peak_vram": "not_applicable",
        "steady_vram": "not_applicable",
    }

    if labeled_parent_count:
        segmentation: dict[str, Any] = {
            "segment_count_by_parent": segment_counts,
            "segment_count_average": safe_average(list(segment_counts.values())),
            "segment_token_length_p10": percentile(token_lengths, 10),
            "segment_token_length_p50": percentile(token_lengths, 50),
            "segment_token_length_p90": percentile(token_lengths, 90),
            "strict_boundary": macro_boundary_scores(strict_parent_scores),
            "window_tolerant_f1": {
                "plus_minus_1": macro_boundary_scores(tolerant_1_scores),
                "plus_minus_2": macro_boundary_scores(tolerant_2_scores),
            },
            "pk": safe_average(pk_values),
            "windowdiff": safe_average(windowdiff_values),
            "boundary_over_split_count": oversplit_total,
            "boundary_under_split_count": undersplit_total,
        }
    else:
        segmentation = {
            "segment_count_by_parent": segment_counts,
            "segment_count_average": safe_average(list(segment_counts.values())),
            "segment_token_length_p10": percentile(token_lengths, 10),
            "segment_token_length_p50": percentile(token_lengths, 50),
            "segment_token_length_p90": percentile(token_lengths, 90),
            "strict_boundary": "not_applicable",
            "window_tolerant_f1": "not_applicable",
            "pk": "not_applicable",
            "windowdiff": "not_applicable",
            "boundary_over_split_count": "not_applicable",
            "boundary_under_split_count": "not_applicable",
        }

    claim_utility = {
        "status": "not_run",
        "claim_precision": "not_run",
        "claim_recall": "not_run",
        "unsupported_claim_count": "not_run",
        "duplicate_claim_count": "not_run",
        "privacy_tier_leakage_count": "not_run",
        "expected_claim_denominator": expected_claim_count,
        "predicted_claim_denominator": 0,
    }

    return MetricBundle(
        operational=operational,
        segmentation=segmentation,
        claim_utility=claim_utility,
        denominators={
            "parents": parent_count,
            "labeled_parents": labeled_parent_count,
            "segments": sum(segment_counts.values()),
            "expected_claims": expected_claim_count,
        },
    )


def validate_provenance(
    parent: BenchmarkParent,
    segments: tuple[SegmentProposal, ...],
    all_message_owner: dict[str, str] | None = None,
) -> list[dict[str, Any]]:
    all_message_owner = all_message_owner or {}
    sequence_by_id = {message.id: message.sequence_index for message in parent.messages}
    failures: list[dict[str, Any]] = []
    for segment_index, segment in enumerate(segments):
        previous_sequence = -1
        for message_id in segment.message_ids:
            owner = all_message_owner.get(message_id)
            if message_id not in sequence_by_id:
                if owner and owner != parent.parent_id:
                    failures.append(
                        {
                            "kind": "provenance_cross_parent_id",
                            "segment_index": segment_index,
                            "message_id": message_id,
                            "owner_parent_id": owner,
                        }
                    )
                else:
                    failures.append(
                        {
                            "kind": "provenance_unknown_id",
                            "segment_index": segment_index,
                            "message_id": message_id,
                        }
                    )
                continue
            sequence = sequence_by_id[message_id]
            if sequence < previous_sequence:
                failures.append(
                    {
                        "kind": "provenance_unordered",
                        "segment_index": segment_index,
                        "message_id": message_id,
                    }
                )
            previous_sequence = sequence
        if not segment.content_text.strip():
            failures.append(
                {"kind": "empty_embeddable_text", "segment_index": segment_index}
            )
    return failures


def predicted_boundaries_for_parent(
    parent: BenchmarkParent, segments: tuple[SegmentProposal, ...]
) -> tuple[int, ...]:
    sequence_by_id = {message.id: message.sequence_index for message in parent.messages}
    boundaries: list[int] = []
    for segment in segments[1:]:
        known_sequences = [
            sequence_by_id[message_id]
            for message_id in segment.message_ids
            if message_id in sequence_by_id
        ]
        if known_sequences:
            boundaries.append(min(known_sequences))
    return tuple(sorted(set(boundaries)))


def expected_boundaries_for_parent(
    parent: BenchmarkParent,
    expected_segments: tuple[ExpectedSegment, ...] = (),
) -> tuple[int, ...] | None:
    if parent.expected_boundaries is not None:
        return parent.expected_boundaries
    if not expected_segments:
        return None
    sequence_by_id = {message.id: message.sequence_index for message in parent.messages}
    boundaries: list[int] = []
    for segment in expected_segments[1:]:
        known_sequences = [
            sequence_by_id[message_id]
            for message_id in segment.message_ids
            if message_id in sequence_by_id
        ]
        if known_sequences:
            boundaries.append(min(known_sequences))
    return tuple(sorted(set(boundaries)))


def boundary_precision_recall_f1(
    expected: set[int], predicted: set[int]
) -> dict[str, float | int]:
    true_positives = len(expected & predicted)
    false_positives = len(predicted - expected)
    false_negatives = len(expected - predicted)
    precision = safe_rate(true_positives, true_positives + false_positives)
    recall = safe_rate(true_positives, true_positives + false_negatives)
    f1 = f1_score(precision, recall)
    return {
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "true_positives": true_positives,
        "false_positives": false_positives,
        "false_negatives": false_negatives,
    }


def window_tolerant_boundary_f1(
    expected: tuple[int, ...],
    predicted: tuple[int, ...],
    *,
    tolerance: int,
) -> dict[str, float | int]:
    unmatched_expected = list(expected)
    true_positives = 0
    false_positives = 0
    for boundary in predicted:
        match_index = next(
            (
                index
                for index, expected_boundary in enumerate(unmatched_expected)
                if abs(boundary - expected_boundary) <= tolerance
            ),
            None,
        )
        if match_index is None:
            false_positives += 1
        else:
            true_positives += 1
            unmatched_expected.pop(match_index)
    false_negatives = len(unmatched_expected)
    precision = safe_rate(true_positives, true_positives + false_positives)
    recall = safe_rate(true_positives, true_positives + false_negatives)
    return {
        "precision": precision,
        "recall": recall,
        "f1": f1_score(precision, recall),
        "true_positives": true_positives,
        "false_positives": false_positives,
        "false_negatives": false_negatives,
    }


def pk_score(
    expected_boundaries: tuple[int, ...],
    predicted_boundaries: tuple[int, ...],
    message_count: int,
) -> float:
    if message_count < 2:
        return 0.0
    window_size = boundary_window_size(expected_boundaries, message_count)
    total = 0
    disagreements = 0
    for start in range(0, message_count - window_size):
        end = start + window_size
        expected_same = same_segment(start, end, expected_boundaries)
        predicted_same = same_segment(start, end, predicted_boundaries)
        disagreements += int(expected_same != predicted_same)
        total += 1
    return safe_rate(disagreements, total)


def windowdiff_score(
    expected_boundaries: tuple[int, ...],
    predicted_boundaries: tuple[int, ...],
    message_count: int,
) -> float:
    if message_count < 2:
        return 0.0
    window_size = boundary_window_size(expected_boundaries, message_count)
    total = 0
    disagreements = 0
    for start in range(0, message_count - window_size):
        end = start + window_size
        expected_count = boundaries_in_window(expected_boundaries, start, end)
        predicted_count = boundaries_in_window(predicted_boundaries, start, end)
        disagreements += int(expected_count != predicted_count)
        total += 1
    return safe_rate(disagreements, total)


def boundary_window_size(boundaries: tuple[int, ...], message_count: int) -> int:
    segment_count = len(boundaries) + 1
    average_segment_length = message_count / segment_count
    return max(1, min(message_count - 1, round(average_segment_length / 2)))


def same_segment(start: int, end: int, boundaries: tuple[int, ...]) -> bool:
    return boundaries_in_window(boundaries, start, end) == 0


def boundaries_in_window(boundaries: tuple[int, ...], start: int, end: int) -> int:
    return sum(1 for boundary in boundaries if start < boundary <= end)


def normalize_claim_text(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", text).casefold()
    return re.sub(r"\s+", " ", normalized).strip()


def claim_matches(expected_claim: ExpectedClaim, candidate_text: str) -> bool:
    normalized_candidate = normalize_claim_text(candidate_text)
    candidates = (expected_claim.claim_text, *expected_claim.match_aliases)
    return any(normalize_claim_text(candidate) == normalized_candidate for candidate in candidates)


def macro_boundary_scores(scores: list[dict[str, float | int]]) -> dict[str, float]:
    return {
        "precision": safe_average([float(score["precision"]) for score in scores]),
        "recall": safe_average([float(score["recall"]) for score in scores]),
        "f1": safe_average([float(score["f1"]) for score in scores]),
    }


def count_failure(failures: list[dict[str, Any]], kind: str) -> int:
    return sum(1 for failure in failures if failure.get("kind") == kind)


def safe_rate(numerator: int | float, denominator: int | float) -> float:
    if denominator == 0:
        return 0.0
    return float(numerator) / float(denominator)


def f1_score(precision: float, recall: float) -> float:
    if precision + recall == 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)


def safe_average(values: list[int | float]) -> float | None:
    if not values:
        return None
    return float(sum(values)) / len(values)


def percentile(values: list[int], percentile_value: int) -> int | None:
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    rank = (percentile_value / 100) * (len(ordered) - 1)
    lower = math.floor(rank)
    upper = math.ceil(rank)
    if lower == upper:
        return ordered[int(rank)]
    interpolated = ordered[lower] + (ordered[upper] - ordered[lower]) * (rank - lower)
    return round(interpolated)
