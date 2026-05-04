"""Deterministic sample plans for public segmentation benchmark datasets."""

from __future__ import annotations

import hashlib
import json
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from benchmarks.segmentation.datasets import PublicDataset, PublicDatasetManifest
from benchmarks.segmentation.fixtures import BenchmarkValidationError
from benchmarks.segmentation.strategies import BenchmarkParent


SAMPLE_PLAN_SCHEMA_VERSION = "segmentation-benchmark-sample-plan.v1"
SAMPLE_PLAN_IMPLEMENTATION_VERSION = "segmentation-benchmark-sample-plan.v1"
TIER1_MINIMUM_SELECTED_PARENTS = 60
SUPERDIALSEG_TIER1_STRATA = (
    "no_boundary",
    "boundaries_1_2",
    "boundaries_3_5",
    "high_boundary_count",
    "short_dialogue",
    "medium_dialogue",
    "long_dialogue",
    "mixed_role_pattern",
)


@dataclass(frozen=True)
class SamplePlan:
    schema_version: str
    benchmark_tier: str
    dataset_name: str
    dataset_source: str
    dataset_version: str
    dataset_revision: str | None
    split: str | None
    sample_seed: int
    target_sample_size: int
    selected_parent_ids: tuple[str, ...]
    stratum_assignment: dict[str, tuple[str, ...]]
    expected_boundary_count_distribution: dict[str, int]
    message_count_distribution: dict[str, int]
    stratum_target_sizes: dict[str, int]
    stratum_actual_sizes: dict[str, int]
    stratum_shortfalls: dict[str, int]
    implementation_version: str
    path: Path | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "benchmark_tier": self.benchmark_tier,
            "dataset": {
                "name": self.dataset_name,
                "source": self.dataset_source,
                "version": self.dataset_version,
                "revision": self.dataset_revision,
            },
            "split": self.split,
            "sample_seed": self.sample_seed,
            "target_sample_size": self.target_sample_size,
            "selected_parent_ids": list(self.selected_parent_ids),
            "stratum_assignment": {
                parent_id: list(strata)
                for parent_id, strata in sorted(self.stratum_assignment.items())
            },
            "expected_boundary_count_distribution": dict(
                sorted(self.expected_boundary_count_distribution.items())
            ),
            "message_count_distribution": dict(sorted(self.message_count_distribution.items())),
            "stratum_target_sizes": dict(sorted(self.stratum_target_sizes.items())),
            "stratum_actual_sizes": dict(sorted(self.stratum_actual_sizes.items())),
            "stratum_shortfalls": dict(sorted(self.stratum_shortfalls.items())),
            "implementation_version": self.implementation_version,
        }

    def summary_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "benchmark_tier": self.benchmark_tier,
            "path": str(self.path) if self.path else None,
            "dataset": {
                "name": self.dataset_name,
                "source": self.dataset_source,
                "version": self.dataset_version,
                "revision": self.dataset_revision,
            },
            "split": self.split,
            "sample_seed": self.sample_seed,
            "target_sample_size": self.target_sample_size,
            "selected_parent_count": len(self.selected_parent_ids),
            "stratum_target_sizes": dict(sorted(self.stratum_target_sizes.items())),
            "stratum_actual_sizes": dict(sorted(self.stratum_actual_sizes.items())),
            "stratum_shortfalls": dict(sorted(self.stratum_shortfalls.items())),
            "implementation_version": self.implementation_version,
        }


def create_sample_plan(
    dataset: PublicDataset,
    *,
    benchmark_tier: str,
    split: str | None,
    sample_seed: int,
    target_sample_size: int,
    enforce_tier_minimum: bool = True,
) -> SamplePlan:
    if target_sample_size <= 0:
        raise BenchmarkValidationError(["target sample size must be positive"])
    if benchmark_tier == "decision":
        raise NotImplementedError("decision benchmark tier sample plans are pending implementation")
    if dataset.manifest.dataset_name != "superdialseg":
        raise BenchmarkValidationError(
            ["sample plans are currently implemented for superdialseg only"]
        )

    parents = tuple(dataset.parents)
    if not parents:
        raise BenchmarkValidationError(["cannot create a sample plan from zero parents"])
    assignments = {parent.parent_id: classify_superdialseg_parent(parent) for parent in parents}
    targets = target_sizes_for_tier(benchmark_tier, target_sample_size)
    parent_by_id = {parent.parent_id: parent for parent in parents}

    if benchmark_tier == "smoke":
        selected = deterministic_shuffle(
            [parent.parent_id for parent in parents],
            seed_parts=(
                str(sample_seed),
                dataset.manifest.dataset_name,
                dataset.manifest.dataset_source,
                dataset.manifest.dataset_version,
                str(split),
                benchmark_tier,
                str(target_sample_size),
                SAMPLE_PLAN_IMPLEMENTATION_VERSION,
                "smoke",
            ),
        )[:target_sample_size]
    else:
        selected = []
        selected_set: set[str] = set()
        for stratum in SUPERDIALSEG_TIER1_STRATA:
            candidates = [
                parent.parent_id
                for parent in parents
                if stratum in assignments[parent.parent_id]
            ]
            for parent_id in deterministic_shuffle(
                candidates,
                seed_parts=(
                    str(sample_seed),
                    dataset.manifest.dataset_name,
                    dataset.manifest.dataset_source,
                    dataset.manifest.dataset_version,
                    str(split),
                    benchmark_tier,
                    str(target_sample_size),
                    SAMPLE_PLAN_IMPLEMENTATION_VERSION,
                    stratum,
                ),
            ):
                if len(selected) >= target_sample_size:
                    break
                if parent_id in selected_set:
                    continue
                selected.append(parent_id)
                selected_set.add(parent_id)
                if selected_count_for_stratum(selected, assignments, stratum) >= targets[stratum]:
                    break

        if len(selected) < target_sample_size:
            remaining = [parent.parent_id for parent in parents if parent.parent_id not in selected_set]
            for parent_id in deterministic_shuffle(
                remaining,
                seed_parts=(
                    str(sample_seed),
                    dataset.manifest.dataset_name,
                    dataset.manifest.dataset_source,
                    dataset.manifest.dataset_version,
                    str(split),
                    benchmark_tier,
                    str(target_sample_size),
                    SAMPLE_PLAN_IMPLEMENTATION_VERSION,
                    "fill",
                ),
            ):
                selected.append(parent_id)
                selected_set.add(parent_id)
                if len(selected) >= target_sample_size:
                    break

    if (
        enforce_tier_minimum
        and benchmark_tier == "early_signal"
        and len(selected) < TIER1_MINIMUM_SELECTED_PARENTS
    ):
        raise BenchmarkValidationError(
            [
                "early_signal sample plan selected "
                f"{len(selected)} parents; minimum is {TIER1_MINIMUM_SELECTED_PARENTS}"
            ]
        )

    selected_assignments = {
        parent_id: assignments[parent_id]
        for parent_id in selected
    }
    stratum_keys = tuple(targets)
    actuals = {
        stratum: (
            len(selected)
            if stratum == "smoke"
            else selected_count_for_stratum(selected, assignments, stratum)
        )
        for stratum in stratum_keys
    }
    shortfalls = {
        stratum: max(0, targets[stratum] - actuals[stratum])
        for stratum in SUPERDIALSEG_TIER1_STRATA
    }

    return SamplePlan(
        schema_version=SAMPLE_PLAN_SCHEMA_VERSION,
        benchmark_tier=benchmark_tier,
        dataset_name=dataset.manifest.dataset_name,
        dataset_source=dataset.manifest.dataset_source,
        dataset_version=dataset.manifest.dataset_version,
        dataset_revision=dataset.manifest.local_path_sha256,
        split=split,
        sample_seed=sample_seed,
        target_sample_size=target_sample_size,
        selected_parent_ids=tuple(selected),
        stratum_assignment=selected_assignments,
        expected_boundary_count_distribution=boundary_distribution(
            [parent_by_id[parent_id] for parent_id in selected]
        ),
        message_count_distribution=message_count_distribution(
            [parent_by_id[parent_id] for parent_id in selected]
        ),
        stratum_target_sizes=targets,
        stratum_actual_sizes=actuals,
        stratum_shortfalls=shortfalls,
        implementation_version=SAMPLE_PLAN_IMPLEMENTATION_VERSION,
    )


def write_sample_plan(plan: SamplePlan, path: str | Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(plan.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def load_sample_plan(path: str | Path) -> SamplePlan:
    path = Path(path)
    errors: list[str] = []
    if not path.exists():
        raise BenchmarkValidationError([f"{path}: sample plan does not exist"])
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise BenchmarkValidationError([f"{path}: invalid JSON: {exc}"]) from exc
    if not isinstance(payload, dict):
        raise BenchmarkValidationError([f"{path}: sample plan must be a JSON object"])
    plan = parse_sample_plan_payload(payload, errors, str(path), path=path)
    if errors:
        raise BenchmarkValidationError(errors)
    return plan


def validate_sample_plan_for_manifest(
    plan: SamplePlan,
    manifest: PublicDatasetManifest,
    *,
    split: str | None,
) -> None:
    errors: list[str] = []
    if plan.dataset_name != manifest.dataset_name:
        errors.append(
            f"sample plan dataset name {plan.dataset_name!r} does not match "
            f"manifest {manifest.dataset_name!r}"
        )
    if plan.dataset_source != manifest.dataset_source:
        errors.append(
            f"sample plan dataset source {plan.dataset_source!r} does not match "
            f"manifest {manifest.dataset_source!r}"
        )
    if plan.dataset_version != manifest.dataset_version:
        errors.append(
            f"sample plan dataset version {plan.dataset_version!r} does not match "
            f"manifest {manifest.dataset_version!r}"
        )
    if split is not None and plan.split is not None and split != plan.split:
        errors.append(f"sample plan split {plan.split!r} does not match --split {split!r}")
    if errors:
        raise BenchmarkValidationError(errors)


def select_parents_from_plan(
    dataset: PublicDataset,
    plan: SamplePlan,
) -> tuple[BenchmarkParent, ...]:
    parent_by_id = {parent.parent_id: parent for parent in dataset.parents}
    missing = [parent_id for parent_id in plan.selected_parent_ids if parent_id not in parent_by_id]
    if missing:
        raise BenchmarkValidationError(
            [f"sample plan selected parent id missing from dataset: {parent_id}" for parent_id in missing]
        )
    return tuple(parent_by_id[parent_id] for parent_id in plan.selected_parent_ids)


def parse_sample_plan_payload(
    payload: dict[str, Any],
    errors: list[str],
    label: str,
    *,
    path: Path | None,
) -> SamplePlan:
    schema_version = string_field(payload, "schema_version", errors, label)
    if schema_version and schema_version != SAMPLE_PLAN_SCHEMA_VERSION:
        errors.append(
            f"{label}: unsupported schema_version {schema_version!r}; expected "
            f"{SAMPLE_PLAN_SCHEMA_VERSION}"
        )
    dataset = payload.get("dataset")
    if not isinstance(dataset, dict):
        errors.append(f"{label}.dataset: must be an object")
        dataset = {}
    selected_parent_ids = tuple(string_list(payload, "selected_parent_ids", errors, label))
    raw_assignments = payload.get("stratum_assignment")
    assignments: dict[str, tuple[str, ...]] = {}
    if not isinstance(raw_assignments, dict):
        errors.append(f"{label}.stratum_assignment: must be an object")
    else:
        for parent_id, strata in raw_assignments.items():
            if not isinstance(parent_id, str):
                errors.append(f"{label}.stratum_assignment: parent ids must be strings")
                continue
            if not isinstance(strata, list) or not all(isinstance(item, str) for item in strata):
                errors.append(f"{label}.stratum_assignment[{parent_id}]: must be list[str]")
                continue
            assignments[parent_id] = tuple(strata)

    sample_seed = int_field(payload, "sample_seed", errors, label, 0)
    target_sample_size = int_field(payload, "target_sample_size", errors, label, 0)
    implementation_version = string_field(payload, "implementation_version", errors, label)
    if implementation_version and implementation_version != SAMPLE_PLAN_IMPLEMENTATION_VERSION:
        errors.append(
            f"{label}: unsupported implementation_version {implementation_version!r}; "
            f"expected {SAMPLE_PLAN_IMPLEMENTATION_VERSION}"
        )

    return SamplePlan(
        schema_version=str(schema_version or ""),
        benchmark_tier=str(string_field(payload, "benchmark_tier", errors, label) or ""),
        dataset_name=str(string_field(dataset, "name", errors, f"{label}.dataset") or ""),
        dataset_source=str(string_field(dataset, "source", errors, f"{label}.dataset") or ""),
        dataset_version=str(string_field(dataset, "version", errors, f"{label}.dataset") or ""),
        dataset_revision=optional_string(dataset, "revision"),
        split=optional_string(payload, "split"),
        sample_seed=sample_seed,
        target_sample_size=target_sample_size,
        selected_parent_ids=selected_parent_ids,
        stratum_assignment=assignments,
        expected_boundary_count_distribution=int_dict(
            payload, "expected_boundary_count_distribution", errors, label
        ),
        message_count_distribution=int_dict(payload, "message_count_distribution", errors, label),
        stratum_target_sizes=int_dict(payload, "stratum_target_sizes", errors, label),
        stratum_actual_sizes=int_dict(payload, "stratum_actual_sizes", errors, label),
        stratum_shortfalls=int_dict(payload, "stratum_shortfalls", errors, label),
        implementation_version=str(implementation_version or ""),
        path=path,
    )


def classify_superdialseg_parent(parent: BenchmarkParent) -> tuple[str, ...]:
    strata: list[str] = []
    boundary_count = len(parent.expected_boundaries or ())
    if boundary_count == 0:
        strata.append("no_boundary")
    elif boundary_count <= 2:
        strata.append("boundaries_1_2")
    elif boundary_count <= 5:
        strata.append("boundaries_3_5")
    else:
        strata.append("high_boundary_count")

    message_count = len(parent.messages)
    if message_count <= 4:
        strata.append("short_dialogue")
    elif message_count <= 12:
        strata.append("medium_dialogue")
    else:
        strata.append("long_dialogue")

    roles = [message.role for message in parent.messages if message.role]
    if len(set(roles)) > 1:
        strata.append("mixed_role_pattern")
    return tuple(strata)


def target_sizes_for_tier(benchmark_tier: str, target_sample_size: int) -> dict[str, int]:
    if benchmark_tier == "smoke":
        return {"smoke": target_sample_size}
    if benchmark_tier != "early_signal":
        raise ValueError(f"unsupported sample-plan tier {benchmark_tier!r}")
    base = target_sample_size // len(SUPERDIALSEG_TIER1_STRATA)
    remainder = target_sample_size % len(SUPERDIALSEG_TIER1_STRATA)
    return {
        stratum: base + (1 if index < remainder else 0)
        for index, stratum in enumerate(SUPERDIALSEG_TIER1_STRATA)
    }


def selected_count_for_stratum(
    selected_parent_ids: list[str],
    assignments: dict[str, tuple[str, ...]],
    stratum: str,
) -> int:
    return sum(1 for parent_id in selected_parent_ids if stratum in assignments[parent_id])


def deterministic_shuffle(values: list[str], *, seed_parts: tuple[str, ...]) -> list[str]:
    seed_text = "\x1f".join(seed_parts)
    seed_int = int.from_bytes(hashlib.sha256(seed_text.encode("utf-8")).digest()[:8], "big")
    shuffled = list(values)
    random.Random(seed_int).shuffle(shuffled)
    return shuffled


def boundary_distribution(parents: list[BenchmarkParent]) -> dict[str, int]:
    distribution: dict[str, int] = {}
    for parent in parents:
        key = (
            "unlabeled"
            if parent.expected_boundaries is None
            else str(len(parent.expected_boundaries))
        )
        distribution[key] = distribution.get(key, 0) + 1
    return distribution


def message_count_distribution(parents: list[BenchmarkParent]) -> dict[str, int]:
    distribution = {"short_1_4": 0, "medium_5_12": 0, "long_13_plus": 0}
    for parent in parents:
        count = len(parent.messages)
        if count <= 4:
            distribution["short_1_4"] += 1
        elif count <= 12:
            distribution["medium_5_12"] += 1
        else:
            distribution["long_13_plus"] += 1
    return distribution


def string_field(
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


def optional_string(payload: dict[str, Any], key: str) -> str | None:
    value = payload.get(key)
    return value if isinstance(value, str) and value else None


def int_field(
    payload: dict[str, Any],
    key: str,
    errors: list[str],
    label: str,
    default: int,
) -> int:
    value = payload.get(key, default)
    if isinstance(value, bool) or not isinstance(value, int):
        errors.append(f"{label}.{key}: must be an integer")
        return default
    return value


def string_list(
    payload: dict[str, Any],
    key: str,
    errors: list[str],
    label: str,
) -> list[str]:
    value = payload.get(key)
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        errors.append(f"{label}.{key}: must be a list of strings")
        return []
    return list(value)


def int_dict(
    payload: dict[str, Any],
    key: str,
    errors: list[str],
    label: str,
) -> dict[str, int]:
    value = payload.get(key)
    if not isinstance(value, dict):
        errors.append(f"{label}.{key}: must be an object")
        return {}
    parsed: dict[str, int] = {}
    for item_key, item_value in value.items():
        if not isinstance(item_key, str) or isinstance(item_value, bool) or not isinstance(item_value, int):
            errors.append(f"{label}.{key}: values must be integer counts keyed by strings")
            return {}
        parsed[item_key] = item_value
    return parsed
