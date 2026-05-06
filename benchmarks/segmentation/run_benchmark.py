"""CLI for the local-only segmentation benchmark harness."""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import replace
from pathlib import Path

from benchmarks.segmentation.datasets import PublicDataset, load_public_dataset
from benchmarks.segmentation.early_signal import (
    CURRENT_OPERATIONAL_MODEL_STRATEGY,
    SUPPORTED_BENCHMARK_TIERS,
    load_threshold_set,
    selection_caveat_for_tier,
)
from benchmarks.segmentation.fixtures import BenchmarkValidationError, load_fixtures
from benchmarks.segmentation.llama_bench import (
    LlamaBenchConfig,
    LlamaBenchError,
    model_path_for_strategy,
    run_llama_bench,
)
from benchmarks.segmentation.reporting import write_report_files
from benchmarks.segmentation.results import score_run_file, write_run_results
from benchmarks.segmentation.sample_plan import (
    create_sample_plan,
    load_sample_plan,
    select_parents_from_plan,
    validate_sample_plan_for_manifest,
    write_sample_plan,
)
from benchmarks.segmentation.strategies import (
    DEFAULT_STRATEGIES,
    LOCAL_MODEL_DEFAULT_BASE_URL,
    LOCAL_MODEL_DEFAULT_MAX_TOKENS,
    LOCAL_MODEL_DEFAULT_TIMEOUT_SECONDS,
    RunConfig,
    StrategyOutput,
    StrategyUnavailable,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m benchmarks.segmentation.run_benchmark",
        description="Local-only segmentation benchmark harness.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate_dataset = subparsers.add_parser("validate-dataset")
    validate_dataset.add_argument("--manifest", required=True)
    validate_dataset.add_argument("--split")
    validate_dataset.add_argument("--limit", type=positive_int)

    validate_fixtures = subparsers.add_parser("validate-fixtures")
    validate_fixtures.add_argument("--fixtures", required=True)
    validate_fixtures.add_argument("--expected-claims")

    sample_plan = subparsers.add_parser("sample-plan")
    sample_plan.add_argument("--dataset-manifest", required=True)
    sample_plan.add_argument("--split")
    sample_plan.add_argument(
        "--benchmark-tier",
        choices=SUPPORTED_BENCHMARK_TIERS,
        required=True,
    )
    sample_plan.add_argument("--sample-seed", type=int, required=True)
    sample_plan.add_argument("--target-size", type=positive_int, required=True)
    sample_plan.add_argument("--output", required=True)

    subparsers.add_parser("list-strategies")

    run = subparsers.add_parser("run")
    run.add_argument("--dataset-manifest", required=True)
    run.add_argument("--fixtures")
    run.add_argument("--expected-claims")
    run.add_argument("--strategy", action="append", required=True)
    run.add_argument("--output-dir", required=True)
    run.add_argument("--split")
    run.add_argument("--limit", type=positive_int)
    run.add_argument(
        "--benchmark-tier",
        choices=SUPPORTED_BENCHMARK_TIERS,
        default="smoke",
    )
    run.add_argument("--selection-caveat")
    run.add_argument("--sample-plan")
    run.add_argument("--early-signal-thresholds")
    run.add_argument(
        "--operational-model-strategy",
        default=CURRENT_OPERATIONAL_MODEL_STRATEGY,
        help=(
            "Strategy name to treat as the current operational model for "
            "early-signal verdict comparisons."
        ),
    )
    run.add_argument("--target-tokens", type=positive_int, default=200)
    run.add_argument("--overlap-messages", type=non_negative_int, default=0)
    run.add_argument(
        "--allow-local-models",
        action="store_true",
        default=False,
        help=(
            "Allow benchmark-local model strategies to call a loopback "
            "OpenAI-compatible endpoint. Non-local URLs are refused."
        ),
    )
    run.add_argument(
        "--local-model-base-url",
        default=LOCAL_MODEL_DEFAULT_BASE_URL,
        help=(
            "Loopback OpenAI-compatible base URL for local-model strategies. "
            f"Default: {LOCAL_MODEL_DEFAULT_BASE_URL}."
        ),
    )
    run.add_argument(
        "--local-model-timeout-seconds",
        type=positive_int,
        default=LOCAL_MODEL_DEFAULT_TIMEOUT_SECONDS,
    )
    run.add_argument(
        "--local-model-max-tokens",
        type=positive_int,
        default=LOCAL_MODEL_DEFAULT_MAX_TOKENS,
    )
    run.add_argument(
        "--compute-model-sha256",
        action="store_true",
        default=False,
        help="Compute local model file SHA256 values during local-model runs.",
    )

    llama_bench = subparsers.add_parser("llama-bench")
    model_source = llama_bench.add_mutually_exclusive_group(required=True)
    model_source.add_argument("--strategy")
    model_source.add_argument("--model")
    llama_bench.add_argument("--llama-bench-bin", default="llama-bench")
    llama_bench.add_argument("--output-dir", required=True)
    llama_bench.add_argument("--prompt-tokens", type=positive_int, default=512)
    llama_bench.add_argument("--generation-tokens", type=positive_int, default=128)
    llama_bench.add_argument("--repetitions", type=positive_int, default=3)
    llama_bench.add_argument("--gpu-layers", type=int, default=99)
    llama_bench.add_argument("--threads", type=positive_int, default=8)
    llama_bench.add_argument("--batch-size", type=positive_int, default=2048)
    llama_bench.add_argument("--ubatch-size", type=positive_int, default=512)
    llama_bench.add_argument("--ctx-size", type=positive_int, default=49152)
    llama_bench.add_argument("--flash-attn", choices=("on", "off"), default="on")
    llama_bench.add_argument("--cache-type-k", default="q8_0")
    llama_bench.add_argument("--cache-type-v", default="q8_0")
    llama_bench.add_argument(
        "--min-generation-tps",
        type=positive_float,
        help=(
            "Fail the smoke artifact if llama-bench generation throughput is "
            "below this tokens/second value."
        ),
    )
    llama_bench.add_argument(
        "--extra-arg",
        action="append",
        default=[],
        help="Additional raw argument to append to llama-bench; repeat as needed.",
    )

    score = subparsers.add_parser("score")
    score.add_argument("--results", required=True)

    report = subparsers.add_parser("report")
    report.add_argument("--results", required=True)
    report.add_argument(
        "--format",
        choices=("markdown", "html", "both"),
        default="markdown",
        help="Report format to write. Default: markdown.",
    )
    report.add_argument("--output-dir")
    report.add_argument("--max-parents", type=positive_int, default=50)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "validate-dataset":
            dataset = load_public_dataset(
                args.manifest,
                split=args.split,
                limit=args.limit,
            )
            print(
                f"valid dataset: {dataset.manifest.dataset_name} "
                f"parents={len(dataset.parents)} path={dataset.manifest.local_path}"
            )
            return 0
        if args.command == "validate-fixtures":
            bundle = load_fixtures(args.fixtures, args.expected_claims)
            claim_count = sum(len(claims) for claims in bundle.expected_claims_by_fixture.values())
            print(
                f"valid fixtures: parents={len(bundle.parents)} "
                f"fixture_version={bundle.fixture_version} expected_claims={claim_count}"
            )
            return 0
        if args.command == "sample-plan":
            if args.benchmark_tier == "decision":
                raise NotImplementedError(
                    "decision benchmark tier sample plans are pending implementation"
                )
            dataset = load_public_dataset(args.dataset_manifest, split=args.split)
            plan = create_sample_plan(
                dataset,
                benchmark_tier=args.benchmark_tier,
                split=args.split,
                sample_seed=args.sample_seed,
                target_sample_size=args.target_size,
            )
            path = write_sample_plan(plan, args.output)
            print(path)
            return 0
        if args.command == "list-strategies":
            for name, strategy in sorted(DEFAULT_STRATEGIES.items()):
                print(f"{name}\t{strategy.kind}")
            return 0
        if args.command == "run":
            return run_command(args)
        if args.command == "llama-bench":
            return llama_bench_command(args)
        if args.command == "score":
            score = score_run_file(args.results)
            print(json.dumps(score, indent=2, sort_keys=True))
            return 0
        if args.command == "report":
            paths = write_report_files(
                run_json_path=args.results,
                output_dir=args.output_dir,
                report_format=args.format,
                max_parents=args.max_parents,
            )
            for path in paths:
                print(path)
            return 0
    except BenchmarkValidationError as exc:
        for error in exc.errors:
            print(error, file=sys.stderr)
        return 2
    except (StrategyUnavailable, LlamaBenchError, NotImplementedError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    parser.error(f"unknown command {args.command}")
    return 2


def run_command(args: argparse.Namespace) -> int:
    if args.benchmark_tier == "decision":
        raise NotImplementedError("decision benchmark tier execution is pending implementation")
    selection_caveat = args.selection_caveat or selection_caveat_for_tier(args.benchmark_tier)
    if args.early_signal_thresholds and args.benchmark_tier != "early_signal":
        raise ValueError("--early-signal-thresholds is only valid with --benchmark-tier early_signal")
    threshold_set = (
        load_threshold_set(args.early_signal_thresholds)
        if args.early_signal_thresholds
        else None
    )
    sample_plan = load_sample_plan(args.sample_plan) if args.sample_plan else None
    if args.benchmark_tier == "early_signal" and sample_plan is None:
        raise ValueError("--benchmark-tier early_signal requires --sample-plan")
    if sample_plan and args.limit is not None:
        raise ValueError("--sample-plan cannot be combined with --limit")
    if sample_plan and sample_plan.benchmark_tier != args.benchmark_tier:
        raise ValueError(
            f"sample plan tier {sample_plan.benchmark_tier!r} does not match "
            f"--benchmark-tier {args.benchmark_tier!r}"
        )

    dataset = load_public_dataset(
        args.dataset_manifest,
        split=(sample_plan.split if sample_plan else args.split),
        limit=None if sample_plan else args.limit,
    )
    if sample_plan:
        validate_sample_plan_for_manifest(sample_plan, dataset.manifest, split=args.split)
        dataset = PublicDataset(
            manifest=dataset.manifest,
            parents=select_parents_from_plan(dataset, sample_plan),
        )
    fixture_bundle = None
    if args.fixtures:
        fixture_bundle = load_fixtures(args.fixtures, args.expected_claims)
        synthetic_parents = tuple(
            replace(
                parent,
                expected_boundaries=expected_boundaries_from_fixture(
                    parent,
                    fixture_bundle.expected_segments_by_fixture.get(
                        str(parent.fixture_id), ()
                    ),
                ),
            )
            for parent in fixture_bundle.parents
        )
        dataset = PublicDataset(
            manifest=dataset.manifest,
            parents=tuple(dataset.parents) + synthetic_parents,
        )

    strategy_names = args.strategy
    unknown = [name for name in strategy_names if name not in DEFAULT_STRATEGIES]
    if unknown:
        raise ValueError(f"unknown strategies: {', '.join(unknown)}")

    strategy_outputs: dict[str, dict[str, StrategyOutput]] = {}
    durations: dict[str, dict[str, float]] = {}
    for strategy_name in strategy_names:
        strategy = DEFAULT_STRATEGIES[strategy_name]
        strategy_outputs[strategy_name] = {}
        durations[strategy_name] = {}
        for parent in dataset.parents:
            config = RunConfig(
                run_id="pending",
                allow_local_models=args.allow_local_models,
                fixture_version=fixture_bundle.fixture_version if fixture_bundle else None,
                strategy_config={
                    "target_tokens": args.target_tokens,
                    "overlap_messages": args.overlap_messages,
                    "local_model_base_url": args.local_model_base_url,
                    "local_model_timeout_seconds": args.local_model_timeout_seconds,
                    "local_model_max_tokens": args.local_model_max_tokens,
                    "compute_model_sha256": args.compute_model_sha256,
                },
            )
            started = time.perf_counter()
            output = strategy.segment(parent, config)
            durations[strategy_name][parent.parent_id] = time.perf_counter() - started
            strategy_outputs[strategy_name][parent.parent_id] = output

    run_path = write_run_results(
        output_dir=Path(args.output_dir),
        dataset=dataset,
        strategy_outputs=strategy_outputs,
        durations=durations,
        fixture_bundle=fixture_bundle,
        benchmark_tier=args.benchmark_tier,
        selection_caveat=selection_caveat,
        sample_plan=sample_plan,
        threshold_set=threshold_set,
        operational_model_strategy=args.operational_model_strategy,
    )
    print(run_path)
    return 0


def llama_bench_command(args: argparse.Namespace) -> int:
    model_path = args.model or model_path_for_strategy(args.strategy)
    config = LlamaBenchConfig(
        llama_bench_bin=args.llama_bench_bin,
        model_path=model_path,
        output_dir=Path(args.output_dir),
        strategy_name=args.strategy,
        prompt_tokens=args.prompt_tokens,
        generation_tokens=args.generation_tokens,
        repetitions=args.repetitions,
        gpu_layers=args.gpu_layers,
        threads=args.threads,
        batch_size=args.batch_size,
        ubatch_size=args.ubatch_size,
        ctx_size=args.ctx_size,
        flash_attn=args.flash_attn,
        cache_type_k=args.cache_type_k,
        cache_type_v=args.cache_type_v,
        min_generation_tps=args.min_generation_tps,
        extra_args=tuple(args.extra_arg or ()),
    )
    output_path = run_llama_bench(config)
    print(output_path)
    return 0


def positive_int(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be positive")
    return parsed


def non_negative_int(value: str) -> int:
    parsed = int(value)
    if parsed < 0:
        raise argparse.ArgumentTypeError("must be non-negative")
    return parsed


def positive_float(value: str) -> float:
    parsed = float(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be positive")
    return parsed


def expected_boundaries_from_fixture(parent, expected_segments) -> tuple[int, ...]:
    sequence_by_id = {message.id: message.sequence_index for message in parent.messages}
    boundaries: list[int] = []
    for segment in expected_segments[1:]:
        sequences = [
            sequence_by_id[message_id]
            for message_id in segment.message_ids
            if message_id in sequence_by_id
        ]
        if sequences:
            boundaries.append(min(sequences))
    return tuple(sorted(set(boundaries)))


if __name__ == "__main__":
    raise SystemExit(main())
