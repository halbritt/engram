"""Tier metadata, threshold sets, and verdicts for segmentation benchmarks."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from benchmarks.segmentation.fixtures import BenchmarkValidationError


THRESHOLD_SCHEMA_VERSION = "segmentation-benchmark-early-signal-thresholds.v1"
VERDICT_SCHEMA_VERSION = "segmentation-benchmark-early-signal-verdict.v1"
SUPPORTED_BENCHMARK_TIERS = ("smoke", "early_signal", "decision")
SELECTION_CAVEATS = {
    "smoke": "smoke_only",
    "early_signal": "early_signal_not_decision_grade",
    "decision": "decision_grade",
}
CURRENT_OPERATIONAL_MODEL_STRATEGY = "qwen_35b_a3b_iq4_xs_d034"
DETERMINISTIC_STRATEGY_KINDS = {"fixed_window", "message_group"}


@dataclass(frozen=True)
class EarlySignalThresholdSet:
    schema_version: str
    threshold_set_id: str
    source: str
    status: str | None
    created_at: str | None
    schema_valid_rate_min: float
    provenance_valid_rate_min: float
    forbidden_backend_error_kinds: tuple[str, ...]
    no_boundary_false_split_rate_max: float
    segment_count_ratio_max: float
    sub_100_fragment_rate_max: float
    adjacent_tiny_fragment_rate_max: float
    duplicate_adjacent_rate_max: float
    raw: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        payload = dict(self.raw)
        payload["schema_version"] = self.schema_version
        payload["threshold_set_id"] = self.threshold_set_id
        payload["source"] = self.source
        if self.status is not None:
            payload["status"] = self.status
        if self.created_at is not None:
            payload["created_at"] = self.created_at
        payload["hard_gates"] = {
            "schema_valid_rate_min": self.schema_valid_rate_min,
            "provenance_valid_rate_min": self.provenance_valid_rate_min,
            "forbidden_backend_error_kinds": list(self.forbidden_backend_error_kinds),
        }
        payload["fragmentation"] = {
            "no_boundary_false_split_rate_max": self.no_boundary_false_split_rate_max,
            "segment_count_ratio_max": self.segment_count_ratio_max,
            "sub_100_fragment_rate_max": self.sub_100_fragment_rate_max,
            "adjacent_tiny_fragment_rate_max": self.adjacent_tiny_fragment_rate_max,
            "duplicate_adjacent_rate_max": self.duplicate_adjacent_rate_max,
        }
        return payload


def selection_caveat_for_tier(benchmark_tier: str) -> str:
    if benchmark_tier not in SELECTION_CAVEATS:
        raise ValueError(
            f"unsupported benchmark tier {benchmark_tier!r}; expected one of "
            f"{', '.join(SUPPORTED_BENCHMARK_TIERS)}"
        )
    return SELECTION_CAVEATS[benchmark_tier]


def load_threshold_set(path: str | Path) -> EarlySignalThresholdSet:
    path = Path(path)
    if not path.exists():
        raise BenchmarkValidationError([f"{path}: threshold set does not exist"])
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise BenchmarkValidationError([f"{path}: invalid JSON: {exc}"]) from exc
    if not isinstance(payload, dict):
        raise BenchmarkValidationError([f"{path}: threshold set must be a JSON object"])
    errors: list[str] = []
    threshold = threshold_set_from_dict(payload, errors, str(path))
    if errors:
        raise BenchmarkValidationError(errors)
    return threshold


def threshold_set_from_dict(
    payload: dict[str, Any],
    errors: list[str] | None = None,
    label: str = "threshold_set",
) -> EarlySignalThresholdSet:
    errors = errors if errors is not None else []
    schema_version = required_string(payload, "schema_version", errors, label)
    if schema_version and schema_version != THRESHOLD_SCHEMA_VERSION:
        errors.append(
            f"{label}: unsupported schema_version {schema_version!r}; expected "
            f"{THRESHOLD_SCHEMA_VERSION}"
        )
    threshold_set_id = required_string(payload, "threshold_set_id", errors, label)
    source = required_string(payload, "source", errors, label)
    status = optional_string(payload, "status", errors, label)
    created_at = optional_string(payload, "created_at", errors, label)
    if not status and not created_at:
        errors.append(f"{label}: threshold set must include either status or created_at")

    hard_gates = payload.get("hard_gates")
    if not isinstance(hard_gates, dict):
        errors.append(f"{label}.hard_gates: must be an object")
        hard_gates = {}
    fragmentation = payload.get("fragmentation")
    if not isinstance(fragmentation, dict):
        errors.append(f"{label}.fragmentation: must be an object")
        fragmentation = {}

    forbidden = hard_gates.get("forbidden_backend_error_kinds")
    if not isinstance(forbidden, list) or not all(isinstance(item, str) for item in forbidden):
        errors.append(
            f"{label}.hard_gates.forbidden_backend_error_kinds: "
            "must be a list of strings"
        )
        forbidden = []

    threshold = EarlySignalThresholdSet(
        schema_version=str(schema_version or ""),
        threshold_set_id=str(threshold_set_id or ""),
        source=str(source or ""),
        status=status,
        created_at=created_at,
        schema_valid_rate_min=required_number(
            hard_gates, "schema_valid_rate_min", errors, f"{label}.hard_gates"
        ),
        provenance_valid_rate_min=required_number(
            hard_gates, "provenance_valid_rate_min", errors, f"{label}.hard_gates"
        ),
        forbidden_backend_error_kinds=tuple(str(item) for item in forbidden),
        no_boundary_false_split_rate_max=required_number(
            fragmentation,
            "no_boundary_false_split_rate_max",
            errors,
            f"{label}.fragmentation",
        ),
        segment_count_ratio_max=required_number(
            fragmentation, "segment_count_ratio_max", errors, f"{label}.fragmentation"
        ),
        sub_100_fragment_rate_max=required_number(
            fragmentation,
            "sub_100_fragment_rate_max",
            errors,
            f"{label}.fragmentation",
        ),
        adjacent_tiny_fragment_rate_max=required_number(
            fragmentation,
            "adjacent_tiny_fragment_rate_max",
            errors,
            f"{label}.fragmentation",
        ),
        duplicate_adjacent_rate_max=required_number(
            fragmentation,
            "duplicate_adjacent_rate_max",
            errors,
            f"{label}.fragmentation",
        ),
        raw=payload,
    )
    if errors and label == "threshold_set":
        raise BenchmarkValidationError(errors)
    return threshold


def generate_early_signal_verdicts(
    *,
    benchmark_tier: str,
    selection_caveat: str,
    metrics_by_strategy: dict[str, dict[str, Any]],
    strategy_kinds: dict[str, str],
    threshold_set: EarlySignalThresholdSet | None,
    operational_model_strategy: str = CURRENT_OPERATIONAL_MODEL_STRATEGY,
) -> dict[str, dict[str, Any]]:
    if benchmark_tier != "early_signal":
        return {}
    return {
        strategy_name: build_strategy_verdict(
            strategy_name=strategy_name,
            selection_caveat=selection_caveat,
            metrics=metrics,
            metrics_by_strategy=metrics_by_strategy,
            strategy_kinds=strategy_kinds,
            threshold_set=threshold_set,
            operational_model_strategy=operational_model_strategy,
        )
        for strategy_name, metrics in metrics_by_strategy.items()
    }


def build_strategy_verdict(
    *,
    strategy_name: str,
    selection_caveat: str,
    metrics: dict[str, Any],
    metrics_by_strategy: dict[str, dict[str, Any]],
    strategy_kinds: dict[str, str],
    threshold_set: EarlySignalThresholdSet | None,
    operational_model_strategy: str,
) -> dict[str, Any]:
    metric_reasons: dict[str, dict[str, Any]] = {}
    hard_warnings: list[str] = []
    blocking_failures: list[str] = []
    operational = metrics.get("operational", {})
    fragmentation = metrics.get("fragmentation", {})
    schema_threshold = threshold_set.schema_valid_rate_min if threshold_set else 1.0
    provenance_threshold = (
        threshold_set.provenance_valid_rate_min if threshold_set else 1.0
    )
    forbidden_backend_kinds = (
        threshold_set.forbidden_backend_error_kinds
        if threshold_set
        else ("backend_wedge_post_smoke", "cuda_oom")
    )

    add_min_gate(
        metric_reasons,
        blocking_failures,
        "schema_valid_rate",
        operational.get("schema_valid_rate"),
        schema_threshold,
    )
    add_min_gate(
        metric_reasons,
        blocking_failures,
        "provenance_valid_rate",
        operational.get("provenance_valid_rate"),
        provenance_threshold,
    )
    backend_counts = operational.get("backend_error_counts", {})
    if isinstance(backend_counts, dict):
        for kind in forbidden_backend_kinds:
            count = int(backend_counts.get(kind, 0) or 0)
            metric_reasons[f"backend_error_{kind}_count"] = {
                "value": count,
                "threshold": 0,
                "passed": count == 0,
            }
            if count:
                blocking_failures.append(f"forbidden backend error {kind}: {count}")
    runaway_count = int(operational.get("runaway_count", 0) or 0)
    metric_reasons["runaway_count"] = {
        "value": runaway_count,
        "threshold": 0,
        "passed": runaway_count == 0,
    }
    if runaway_count:
        blocking_failures.append(f"runaway completions: {runaway_count}")

    if threshold_set is None:
        threshold_payload: dict[str, Any] = {
            "schema_version": THRESHOLD_SCHEMA_VERSION,
            "status": "missing",
            "source": "explicit --early-signal-thresholds file required for candidate verdicts",
        }
    else:
        threshold_payload = threshold_set.to_dict()
        add_max_gate(
            metric_reasons,
            hard_warnings,
            "no_boundary_false_split_rate",
            fragmentation.get("no_boundary_false_split_rate"),
            threshold_set.no_boundary_false_split_rate_max,
        )
        add_max_gate(
            metric_reasons,
            hard_warnings,
            "segment_count_ratio",
            fragmentation.get("predicted_expected_segment_count_ratio_average"),
            threshold_set.segment_count_ratio_max,
        )
        add_max_gate(
            metric_reasons,
            hard_warnings,
            "sub_100_fragment_rate",
            fragmentation.get("sub_100_fragment_rate"),
            threshold_set.sub_100_fragment_rate_max,
        )
        add_max_gate(
            metric_reasons,
            hard_warnings,
            "adjacent_tiny_fragment_rate",
            fragmentation.get("adjacent_tiny_fragment_rate"),
            threshold_set.adjacent_tiny_fragment_rate_max,
        )
        add_max_gate(
            metric_reasons,
            hard_warnings,
            "duplicate_adjacent_rate",
            fragmentation.get("duplicate_adjacent_rate"),
            threshold_set.duplicate_adjacent_rate_max,
        )

    strict_f1 = strict_f1_for(metrics)
    baseline_f1 = best_strict_f1_for_kind(
        metrics_by_strategy, strategy_kinds, DETERMINISTIC_STRATEGY_KINDS
    )
    operational_f1 = strict_f1_for(metrics_by_strategy.get(operational_model_strategy, {}))
    is_deterministic = strategy_kinds.get(strategy_name) in DETERMINISTIC_STRATEGY_KINDS
    baseline_unavailable = baseline_f1 == "not_applicable"
    comparison_unavailable = operational_model_strategy not in metrics_by_strategy
    if baseline_unavailable and not is_deterministic:
        hard_warnings.append(
            "deterministic baselines unavailable; cannot evaluate challenger "
            "without a cheap anchor"
        )
    if comparison_unavailable and not is_deterministic:
        hard_warnings.append(
            f"comparison to operational model {operational_model_strategy} unavailable"
        )
    metric_reasons["strict_f1_vs_best_deterministic"] = {
        "value": strict_f1,
        "threshold": baseline_f1,
        "passed": (
            numeric(strict_f1)
            and numeric(baseline_f1)
            and float(strict_f1) > float(baseline_f1)
        ),
    }
    metric_reasons["strict_f1_vs_operational_model"] = {
        "value": strict_f1,
        "threshold": operational_f1,
        "passed": (
            numeric(strict_f1)
            and numeric(operational_f1)
            and float(strict_f1) > float(operational_f1)
        ),
    }

    if blocking_failures:
        verdict = "reject"
        summary = "Blocking safety or reliability failures were detected."
    elif is_deterministic:
        verdict = "defer"
        summary = "Deterministic baseline scored for comparison; it is not a model candidate."
    elif threshold_set is None:
        verdict = "longer_run"
        summary = "No explicit threshold set was supplied, so candidate verdicts are disabled."
    elif comparison_unavailable:
        verdict = "longer_run"
        summary = "Promising runs need the current operational model in the same run before candidate status."
    elif baseline_unavailable:
        verdict = "longer_run"
        summary = "Promising runs need deterministic baselines in the same run before candidate status."
    elif hard_warnings:
        verdict = "longer_run" if passes_comparison(metric_reasons) else "defer"
        summary = "Fragmentation or comparison warnings require a longer run before candidate status."
    elif passes_comparison(metric_reasons):
        verdict = "candidate"
        summary = "Tier 1 metrics clear configured gates and beat available comparisons."
    else:
        verdict = "defer"
        summary = "Run is valid but does not beat deterministic and operational comparisons."

    return {
        "schema_version": VERDICT_SCHEMA_VERSION,
        "strategy_name": strategy_name,
        "verdict": verdict,
        "selection_caveat": selection_caveat,
        "operational_model_strategy": operational_model_strategy,
        "summary": summary,
        "hard_warnings": hard_warnings,
        "blocking_failures": blocking_failures,
        "metric_reasons": metric_reasons,
        "threshold_set": threshold_payload,
    }


def add_min_gate(
    metric_reasons: dict[str, dict[str, Any]],
    blocking_failures: list[str],
    name: str,
    value: Any,
    threshold: float,
) -> None:
    if value == "not_applicable":
        passed = True
    else:
        passed = numeric(value) and float(value) >= threshold
    metric_reasons[name] = {"value": value, "threshold": threshold, "passed": passed}
    if not passed:
        blocking_failures.append(f"{name} below threshold: {value} < {threshold}")


def add_max_gate(
    metric_reasons: dict[str, dict[str, Any]],
    hard_warnings: list[str],
    name: str,
    value: Any,
    threshold: float,
) -> None:
    if value == "not_applicable":
        passed = True
    else:
        passed = numeric(value) and float(value) <= threshold
    metric_reasons[name] = {"value": value, "threshold": threshold, "passed": passed}
    if not passed:
        hard_warnings.append(f"{name} above threshold: {value} > {threshold}")


def passes_comparison(metric_reasons: dict[str, dict[str, Any]]) -> bool:
    return bool(
        metric_reasons.get("strict_f1_vs_best_deterministic", {}).get("passed")
        and metric_reasons.get("strict_f1_vs_operational_model", {}).get("passed")
    )


def strict_f1_for(metrics: dict[str, Any]) -> Any:
    strict = metrics.get("segmentation", {}).get("strict_boundary")
    if isinstance(strict, dict):
        return strict.get("f1")
    return strict or "not_applicable"


def best_strict_f1_for_kind(
    metrics_by_strategy: dict[str, dict[str, Any]],
    strategy_kinds: dict[str, str],
    kinds: set[str],
) -> Any:
    values = [
        strict_f1_for(metrics)
        for strategy_name, metrics in metrics_by_strategy.items()
        if strategy_kinds.get(strategy_name) in kinds and numeric(strict_f1_for(metrics))
    ]
    if not values:
        return "not_applicable"
    return max(float(value) for value in values)


def numeric(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def required_string(
    payload: dict[str, Any],
    key: str,
    errors: list[str],
    label: str,
) -> str | None:
    value = payload.get(key)
    if not isinstance(value, str) or not value:
        errors.append(f"{label}.{key}: must be a non-empty string")
        return None
    return value


def optional_string(
    payload: dict[str, Any],
    key: str,
    errors: list[str],
    label: str,
) -> str | None:
    value = payload.get(key)
    if value is None:
        return None
    if not isinstance(value, str) or not value:
        errors.append(f"{label}.{key}: must be a non-empty string or omitted")
        return None
    return value


def required_number(
    payload: dict[str, Any],
    key: str,
    errors: list[str],
    label: str,
) -> float:
    value = payload.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        errors.append(f"{label}.{key}: must be a number")
        return 0.0
    return float(value)
