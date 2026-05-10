"""CLI drivers for the RFC 0029 bench triage workbench."""

from __future__ import annotations

import sys
from argparse import Namespace
from pathlib import Path

from engram.bench_review.artifacts import (
    BenchReviewArtifactError,
    build_segment_comparisons,
    fetch_prior_summaries,
    load_candidate_run,
    load_segment_records,
    load_slice_segment_ids,
    resolve_segment_records_path,
)
from engram.bench_review.export import export_markdown, render_status
from engram.bench_review.storage import ReviewSessionConfig, initialize_review_db

SERVE_LOOPBACK_HOSTS: frozenset[str] = frozenset({"127.0.0.1", "localhost", "::1"})


def run_phase3_bench_review_serve(args: Namespace) -> int:
    """Build scratch review DB and run the local FastAPI workbench."""
    host = str(args.host)
    if host not in SERVE_LOOPBACK_HOSTS:
        print(
            "phase3 bench-review serve: refusing non-loopback host "
            f"(--host={host}); v1 is loopback-only",
            file=sys.stderr,
        )
        sys.exit(8)
    try:
        review_db = prepare_review_db(args)
    except (BenchReviewArtifactError, OSError) as exc:
        print(f"phase3 bench-review serve: {exc}", file=sys.stderr)
        return 1
    try:
        import uvicorn

        from engram.bench_review.web import create_app
    except ImportError as exc:
        print(
            "phase3 bench-review serve: missing dependency "
            f"({exc}). Install with: pip install engram[serve]",
            file=sys.stderr,
        )
        return 2
    port = int(args.port)
    print(
        f"phase3 bench-review serve: listening on http://{host}:{port} "
        f"review_db={review_db}"
    )
    uvicorn.run(create_app(review_db_path=review_db, host=host, port=port), host=host, port=port)
    return 0


def run_phase3_bench_review_status(args: Namespace) -> int:
    """Print aggregate review status."""
    try:
        print(render_status(Path(args.review_db)), end="")
    except Exception as exc:
        print(f"phase3 bench-review status: {exc}", file=sys.stderr)
        return 1
    return 0


def run_phase3_bench_review_export(args: Namespace) -> int:
    """Write a redacted Markdown export."""
    try:
        output = export_markdown(
            db_path=Path(args.review_db),
            output_path=Path(args.output),
            repo_root=Path.cwd(),
            allow_outside_reviews=bool(args.allow_outside_reviews),
        )
    except Exception as exc:
        print(f"phase3 bench-review export: {exc}", file=sys.stderr)
        return 1
    print(f"phase3 bench-review export: wrote {output}")
    return 0


def prepare_review_db(args: Namespace) -> Path:
    """Build or update the scratch review DB for a candidate run."""
    slice_path = Path(args.slice)
    run_path = Path(args.run)
    candidate_run = load_candidate_run(run_path)
    segments_path = resolve_segment_records_path(
        run_path=run_path,
        candidate_run=candidate_run,
        explicit_path=Path(args.segments) if args.segments else None,
    )
    segment_ids = load_slice_segment_ids(slice_path)
    candidate_records = load_segment_records(segments_path)
    prior_summaries = {}
    try:
        from engram.db import connect

        with connect() as conn:
            prior_summaries = fetch_prior_summaries(
                conn,
                segment_ids=segment_ids,
                prompt_version=str(args.prior_prompt_version),
                model_version=str(args.prior_model_version),
                request_profile_version=str(args.prior_request_profile_version),
            )
    except Exception as exc:  # Deliberate fallback to prior_missing metadata mode.
        print(
            "phase3 bench-review: prior lookup unavailable; "
            f"marking rows prior_missing ({exc})",
            file=sys.stderr,
        )
    rows = build_segment_comparisons(
        segment_ids=segment_ids,
        candidate_records=candidate_records,
        prior_summaries=prior_summaries,
    )
    review_db = (
        Path(args.review_db)
        if getattr(args, "review_db", None)
        else Path(".scratch")
        / "benchmarks"
        / "extraction-review"
        / candidate_run.run_id
        / "review.sqlite3"
    )
    initialize_review_db(
        review_db,
        config=ReviewSessionConfig(
            run_id=candidate_run.run_id,
            slice_path=slice_path,
            run_path=run_path,
            segments_path=segments_path,
            candidate_prompt_version=candidate_run.prompt_version,
            candidate_model_version=candidate_run.model_version,
            candidate_request_profile_version=candidate_run.request_profile_version,
            prior_prompt_version=str(args.prior_prompt_version),
            prior_model_version=str(args.prior_model_version),
            prior_request_profile_version=str(args.prior_request_profile_version),
        ),
        rows=rows,
    )
    return review_db
