"""CLI skeleton for the segmentation benchmark.

The live runner is intentionally not implemented yet. This module exists so
the reviewed CLI shape has a concrete home.
"""

from __future__ import annotations

import argparse


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m benchmarks.segmentation.run_benchmark",
        description="Spec-only segmentation benchmark CLI skeleton.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate = subparsers.add_parser("validate-fixtures")
    validate.add_argument("--fixtures", required=True)
    validate.add_argument("--expected-claims")

    subparsers.add_parser("list-strategies")

    run = subparsers.add_parser("run")
    run.add_argument("--fixtures", required=True)
    run.add_argument("--expected-claims")
    run.add_argument("--strategy", action="append", required=True)
    run.add_argument("--output-dir", required=True)
    run.add_argument("--offline", action="store_true", default=True)

    score = subparsers.add_parser("score")
    score.add_argument("--results", required=True)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    parser.parse_args(argv)
    parser.exit(2, "segmentation benchmark runner is not implemented yet\n")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
