"""Scratch result writing for segmentation benchmark runs."""

from __future__ import annotations

import json
import os
import subprocess
import uuid
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from benchmarks.segmentation.datasets import PublicDataset, PublicDatasetManifest
from benchmarks.segmentation.early_signal import (
    CURRENT_OPERATIONAL_MODEL_STRATEGY,
    EarlySignalThresholdSet,
    generate_early_signal_verdicts,
    threshold_set_from_dict,
)
from benchmarks.segmentation.fixtures import FixtureBundle
from benchmarks.segmentation.scoring import (
    SCORING_IMPLEMENTATION_VERSION,
    MetricBundle,
    score_strategy_outputs,
)
from benchmarks.segmentation.sample_plan import SamplePlan
from benchmarks.segmentation.strategies import (
    BenchmarkMessage,
    BenchmarkParent,
    SegmentProposal,
    StrategyOutput,
    TOKEN_ESTIMATOR_VERSION,
)


RESULT_SCHEMA_VERSION = "segmentation-benchmark-result.v1"


def write_run_results(
    *,
    output_dir: str | Path,
    dataset: PublicDataset,
    strategy_outputs: dict[str, dict[str, StrategyOutput]],
    durations: dict[str, dict[str, float]],
    fixture_bundle: FixtureBundle | None = None,
    benchmark_tier: str = "smoke",
    selection_caveat: str = "smoke_only",
    sample_plan: SamplePlan | None = None,
    threshold_set: EarlySignalThresholdSet | None = None,
    operational_model_strategy: str = CURRENT_OPERATIONAL_MODEL_STRATEGY,
) -> Path:
    run_id = make_run_id(dataset.manifest.dataset_name)
    run_dir = Path(output_dir) / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    parents_path = run_dir / "parents.jsonl"

    metrics: dict[str, MetricBundle] = {}
    with parents_path.open("w", encoding="utf-8") as handle:
        for strategy_name, outputs_by_parent in strategy_outputs.items():
            metrics[strategy_name] = score_strategy_outputs(
                dataset.parents,
                outputs_by_parent,
                expected_segments_by_fixture=(
                    fixture_bundle.expected_segments_by_fixture if fixture_bundle else None
                ),
                expected_claims_by_fixture=(
                    fixture_bundle.expected_claims_by_fixture if fixture_bundle else None
                ),
                durations_by_parent=durations.get(strategy_name, {}),
            )
            for parent in dataset.parents:
                output = outputs_by_parent[parent.parent_id]
                record = parent_result_record(
                    parent=parent,
                    output=output,
                    duration_seconds=durations.get(strategy_name, {}).get(parent.parent_id),
                )
                handle.write(json.dumps(record, sort_keys=True) + "\n")

    metrics_payload = {name: metric_bundle_to_dict(bundle) for name, bundle in metrics.items()}
    strategy_kinds = {
        strategy_name: next(iter(outputs_by_parent.values())).strategy_kind
        for strategy_name, outputs_by_parent in strategy_outputs.items()
        if outputs_by_parent
    }
    verdicts = generate_early_signal_verdicts(
        benchmark_tier=benchmark_tier,
        selection_caveat=selection_caveat,
        metrics_by_strategy=metrics_payload,
        strategy_kinds=strategy_kinds,
        threshold_set=threshold_set,
        operational_model_strategy=operational_model_strategy,
    )

    run_json = {
        "schema_version": RESULT_SCHEMA_VERSION,
        "run_id": run_id,
        "created_at": utc_now(),
        "git_commit": git_commit(),
        "benchmark_tier": benchmark_tier,
        "selection_caveat": selection_caveat,
        "operational_model_strategy": operational_model_strategy,
        "dataset": {
            "kind": "public",
            "name": dataset.manifest.dataset_name,
            "snapshot": dataset.manifest.snapshot,
            "manifest_schema_version": dataset.manifest.schema_version,
            "manifest_path": str(dataset.manifest.manifest_path),
            "source": dataset.manifest.dataset_source,
            "version": dataset.manifest.dataset_version,
            "preprocessing_version": dataset.manifest.preprocessing_version,
            "license_name": dataset.manifest.license_name,
            "license_accepted_at": dataset.manifest.license_accepted_at,
        },
        "fixture_version": fixture_bundle.fixture_version if fixture_bundle else None,
        "fixture_schema_version": (
            fixture_bundle.fixture_schema_version if fixture_bundle else None
        ),
        "expected_claims_schema_version": (
            fixture_bundle.expected_claims_schema_version if fixture_bundle else None
        ),
        "sample_plan": sample_plan.summary_dict() if sample_plan else None,
        "early_signal_thresholds": threshold_set.to_dict() if threshold_set else None,
        "early_signal_verdicts": verdicts,
        "strategy_results": [
            strategy_metadata(strategy_name, outputs_by_parent)
            for strategy_name, outputs_by_parent in strategy_outputs.items()
        ],
        "scoring_implementation_version": SCORING_IMPLEMENTATION_VERSION,
        "benchmark_token_estimator_version": TOKEN_ESTIMATOR_VERSION,
        "environment": relevant_segmenter_environment(),
        "model_sha256_manifest_policy": (
            "Local model strategies record the absolute model path and file size. "
            "SHA256 capture is opt-in with --compute-model-sha256 because hashing "
            "large GGUF files can materially extend a short benchmark run."
        ),
        "parents_path": "parents.jsonl",
        "metrics": metrics_payload,
    }
    run_path = run_dir / "run.json"
    run_path.write_text(json.dumps(run_json, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return run_path


def score_run_file(run_json_path: str | Path) -> dict[str, Any]:
    run_json_path = Path(run_json_path)
    run = json.loads(run_json_path.read_text(encoding="utf-8"))
    parents_path = run_json_path.parent / run["parents_path"]
    records = [
        json.loads(line)
        for line in parents_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    parents_by_strategy: dict[str, list[BenchmarkParent]] = {}
    outputs_by_strategy: dict[str, dict[str, StrategyOutput]] = {}
    durations_by_strategy: dict[str, dict[str, float]] = {}
    for record in records:
        strategy_name = record["strategy_name"]
        parent = parent_from_record(record["parent"])
        output = output_from_record(record)
        parents_by_strategy.setdefault(strategy_name, []).append(parent)
        outputs_by_strategy.setdefault(strategy_name, {})[parent.parent_id] = output
        duration = record.get("duration_seconds")
        if isinstance(duration, (int, float)):
            durations_by_strategy.setdefault(strategy_name, {})[parent.parent_id] = float(duration)

    metrics = {
        strategy_name: metric_bundle_to_dict(
            score_strategy_outputs(
                tuple(parents),
                outputs_by_strategy[strategy_name],
                durations_by_parent=durations_by_strategy.get(strategy_name, {}),
            )
        )
        for strategy_name, parents in parents_by_strategy.items()
    }
    strategy_kinds = {
        item.get("name"): item.get("kind")
        for item in run.get("strategy_results", [])
        if isinstance(item, dict) and item.get("name")
    }
    threshold_payload = run.get("early_signal_thresholds")
    threshold_errors: list[str] = []
    threshold_set = None
    if isinstance(threshold_payload, dict):
        threshold_set = threshold_set_from_dict(
            threshold_payload, threshold_errors, "early_signal_thresholds"
        )
    if threshold_errors:
        raise ValueError("; ".join(threshold_errors))
    operational_model_strategy = (
        run.get("operational_model_strategy") or CURRENT_OPERATIONAL_MODEL_STRATEGY
    )
    verdicts = generate_early_signal_verdicts(
        benchmark_tier=run.get("benchmark_tier", "smoke"),
        selection_caveat=run.get("selection_caveat", "smoke_only"),
        metrics_by_strategy=metrics,
        strategy_kinds=strategy_kinds,
        threshold_set=threshold_set,
        operational_model_strategy=operational_model_strategy,
    )
    score = {
        "schema_version": "segmentation-benchmark-score.v1",
        "run_id": run["run_id"],
        "benchmark_tier": run.get("benchmark_tier"),
        "selection_caveat": run.get("selection_caveat"),
        "operational_model_strategy": operational_model_strategy,
        "sample_plan": run.get("sample_plan"),
        "early_signal_thresholds": threshold_payload,
        "early_signal_verdicts": verdicts,
        "scoring_implementation_version": SCORING_IMPLEMENTATION_VERSION,
        "metrics": metrics,
    }
    score_path = run_json_path.parent / "score.json"
    score_path.write_text(json.dumps(score, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return score


def parent_result_record(
    *,
    parent: BenchmarkParent,
    output: StrategyOutput,
    duration_seconds: float | None,
) -> dict[str, Any]:
    return {
        "strategy_name": output.strategy_name,
        "strategy_kind": output.strategy_kind,
        "parent": parent_to_dict(parent),
        "segments": [segment_to_dict(segment) for segment in output.segments],
        "failures": list(output.failures),
        "metadata": output.metadata,
        "duration_seconds": duration_seconds,
    }


def parent_to_dict(parent: BenchmarkParent) -> dict[str, Any]:
    return {
        "fixture_id": parent.fixture_id,
        "source_kind": parent.source_kind,
        "parent_id": parent.parent_id,
        "title": parent.title,
        "privacy_tier": parent.privacy_tier,
        "messages": [asdict(message) for message in parent.messages],
        "dataset_kind": parent.dataset_kind,
        "dataset_name": parent.dataset_name,
        "dataset_split": parent.dataset_split,
        "expected_boundaries": (
            list(parent.expected_boundaries)
            if parent.expected_boundaries is not None
            else None
        ),
        "metadata": parent.metadata,
    }


def parent_from_record(record: dict[str, Any]) -> BenchmarkParent:
    return BenchmarkParent(
        fixture_id=record.get("fixture_id"),
        source_kind=record["source_kind"],
        parent_id=record["parent_id"],
        title=record.get("title"),
        privacy_tier=int(record["privacy_tier"]),
        messages=tuple(
            BenchmarkMessage(
                id=message["id"],
                sequence_index=int(message["sequence_index"]),
                role=message.get("role"),
                content_text=message.get("content_text"),
                privacy_tier=int(message["privacy_tier"]),
                placeholders=tuple(message.get("placeholders") or ()),
            )
            for message in record["messages"]
        ),
        dataset_kind=record.get("dataset_kind", "public"),
        dataset_name=record.get("dataset_name"),
        dataset_split=record.get("dataset_split"),
        expected_boundaries=(
            tuple(record["expected_boundaries"])
            if record.get("expected_boundaries") is not None
            else None
        ),
        metadata=record.get("metadata") or {},
    )


def segment_to_dict(segment: SegmentProposal) -> dict[str, Any]:
    return {
        "message_ids": list(segment.message_ids),
        "embeddable_message_ids": list(segment.embeddable_message_ids),
        "summary": segment.summary,
        "content_text": segment.content_text,
        "raw": segment.raw,
    }


def output_from_record(record: dict[str, Any]) -> StrategyOutput:
    parent_id = record["parent"]["parent_id"]
    return StrategyOutput(
        strategy_name=record["strategy_name"],
        strategy_kind=record["strategy_kind"],
        parent_id=parent_id,
        segments=tuple(
            SegmentProposal(
                message_ids=tuple(segment["message_ids"]),
                embeddable_message_ids=tuple(segment.get("embeddable_message_ids") or ()),
                summary=segment.get("summary"),
                content_text=segment.get("content_text") or "",
                raw=segment.get("raw") or {},
            )
            for segment in record.get("segments", [])
        ),
        metadata=record.get("metadata") or {},
        failures=tuple(record.get("failures") or ()),
    )


def strategy_metadata(
    strategy_name: str, outputs_by_parent: dict[str, StrategyOutput]
) -> dict[str, Any]:
    first_output = next(iter(outputs_by_parent.values()))
    model_metadata = first_output.metadata.get("model")
    if not isinstance(model_metadata, dict):
        model_metadata = {
            "model_id": None,
            "model_path": None,
            "model_sha256": "not_run",
            "model_sha256_sidecar": "not_run",
            "request_profile": "not_run",
            "endpoint": "not_run",
        }
    return {
        "name": strategy_name,
        "kind": first_output.strategy_kind,
        "config": first_output.metadata,
        "implementation_version": first_output.metadata.get("implementation_version"),
        "model": model_metadata,
    }


def metric_bundle_to_dict(bundle: MetricBundle) -> dict[str, Any]:
    return {
        "operational": bundle.operational,
        "segmentation": bundle.segmentation,
        "fragmentation": bundle.fragmentation,
        "claim_utility": bundle.claim_utility,
        "denominators": bundle.denominators,
    }


def make_run_id(dataset_name: str) -> str:
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    suffix = uuid.uuid4().hex[:8]
    return f"{timestamp}.{dataset_name}.{suffix}"


def utc_now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def git_commit() -> str | None:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def relevant_segmenter_environment() -> dict[str, str]:
    captured = {
        key: value
        for key, value in sorted(os.environ.items())
        if key.startswith("ENGRAM_SEGMENTER_")
    }
    if not captured:
        return {"_note": "no ENGRAM_SEGMENTER_* env vars set"}
    return captured
