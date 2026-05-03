"""CLI for the local-only segmentation benchmark harness."""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import replace
from pathlib import Path

from benchmarks.segmentation.datasets import PublicDataset, load_public_dataset
from benchmarks.segmentation.fixtures import BenchmarkValidationError, load_fixtures
from benchmarks.segmentation.reporting import write_report_files
from benchmarks.segmentation.results import score_run_file, write_run_results
from benchmarks.segmentation.strategies import (
    DEFAULT_STRATEGIES,
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

    subparsers.add_parser("list-strategies")

    run = subparsers.add_parser("run")
    run.add_argument("--dataset-manifest", required=True)
    run.add_argument("--fixtures")
    run.add_argument("--expected-claims")
    run.add_argument("--strategy", action="append", required=True)
    run.add_argument("--output-dir", required=True)
    run.add_argument("--split")
    run.add_argument("--limit", type=positive_int)
    run.add_argument("--target-tokens", type=positive_int, default=200)
    run.add_argument("--overlap-messages", type=non_negative_int, default=0)
    run.add_argument(
        "--allow-local-models",
        action="store_true",
        default=False,
        help=(
            "Allow future local-model strategies to be selected. In this "
            "implementation they still raise NotImplementedError before any "
            "model or network call."
        ),
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
        if args.command == "list-strategies":
            for name, strategy in sorted(DEFAULT_STRATEGIES.items()):
                print(f"{name}\t{strategy.kind}")
            return 0
        if args.command == "run":
            return run_command(args)
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
    except (StrategyUnavailable, NotImplementedError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    parser.error(f"unknown command {args.command}")
    return 2


def run_command(args: argparse.Namespace) -> int:
    dataset = load_public_dataset(
        args.dataset_manifest,
        split=args.split,
        limit=args.limit,
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
    )
    print(run_path)
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
