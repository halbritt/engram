"""Local-only Phase 3 extraction backend benchmark harness.

The harness exercises the production extractor prompt and parser against a
fixed active-segment slice, but it writes only scratch artifacts. It never
inserts into ``claim_extractions`` or ``claims``.
"""

from __future__ import annotations

import argparse
import json
import random
import shlex
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import psycopg

from benchmarks.segmentation.results import git_commit, utc_now
from benchmarks.segmentation.strategies import expanded_model_path, model_file_sha256
from engram.db import connect
from engram.extractor import (
    DEFAULT_EXTRACTION_MAX_TOKENS,
    EXTRACTION_PROMPT_VERSION,
    EXTRACTION_RETRIES,
    EXTRACTION_SYSTEM_PROMPT,
    ClaimDraft,
    ExtractionError,
    ExtractorModelOutput,
    SegmentPayload,
    attach_attempt_diagnostics,
    attach_chunk_diagnostics,
    build_extraction_prompt,
    build_validation_repair_feedback,
    chunk_dropped_claims,
    coerce_client_output,
    default_extractor_model_id,
    dropped_error_counts,
    extraction_json_schema,
    extraction_prompt_chunks,
    fetch_segment_payload,
    is_schema_construction_error,
    parse_extraction_response,
    redact_dropped_claims,
    salvage_claims,
    split_extraction_chunk,
    validate_chunk_output,
)
from engram.segmenter import assert_context_budget, ensure_local_base_url

SLICE_SCHEMA_VERSION = "phase3-extraction-backend-slice.v1"
RUN_SCHEMA_VERSION = "phase3-extraction-backend-run.v1"
COMPARISON_SCHEMA_VERSION = "phase3-extraction-backend-comparison.v1"
BENCHMARK_REQUEST_PROFILE_VERSION = "openai-json-schema.d034.extraction-benchmark.v1"
DEFAULT_OUTPUT_DIR = ".scratch/benchmarks/extraction-backend"
DEFAULT_BASE_URL = "http://127.0.0.1:8081"
DEFAULT_TIMEOUT_SECONDS = 600
DEFAULT_CONTEXT_WINDOW = 49152
DEFAULT_SERVER_READY_TIMEOUT_SECONDS = 180
MAX_RECORDED_METRICS_CHARS = 200_000


class ExtractionBenchmarkError(RuntimeError):
    """Raised when an extraction benchmark cannot complete."""


class LocalEndpointError(ExtractionBenchmarkError):
    """Raised when a local OpenAI-compatible endpoint cannot be used."""

    def __init__(
        self,
        message: str,
        *,
        kind: str = "backend_error",
        response: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.kind = kind
        self.response = response


@dataclass(frozen=True)
class SliceSegment:
    segment_id: str
    generation_id: str
    conversation_id: str
    source_kind: str
    sequence_index: int
    message_count: int
    content_chars: int
    size_bucket: str

    @property
    def bucket(self) -> str:
        return f"{self.source_kind}:{self.size_bucket}"


@dataclass(frozen=True)
class BenchmarkRunConfig:
    backend_name: str
    base_url: str
    model_id: str
    request_profile_version: str
    output_dir: Path
    max_tokens: int
    timeout_seconds: int
    retries: int
    concurrency: int
    context_window: int | None
    include_chat_template_kwargs: bool
    include_claim_text: bool
    compute_model_sha256: bool
    metrics_url: str | None = None
    model_path: str | None = None
    server_command: str | None = None
    server_ready_timeout_seconds: int = DEFAULT_SERVER_READY_TIMEOUT_SECONDS


@dataclass(frozen=True)
class SegmentBenchmarkResult:
    index: int
    segment_id: str
    status: str
    duration_seconds: float
    claim_count: int
    dropped_count: int
    schema_valid: bool
    provenance_valid: bool
    claims: list[dict[str, Any]]
    dropped_claims: list[dict[str, Any]]
    parse_metadata: dict[str, Any]
    failure: dict[str, Any] | None = None


@dataclass(frozen=True)
class ManagedServer:
    process: subprocess.Popen[str]
    command: list[str]
    log_path: Path


class BenchmarkExtractorClient:
    """Benchmark-local OpenAI-compatible extraction client."""

    def __init__(
        self,
        base_url: str,
        *,
        timeout_seconds: int,
        context_window: int | None,
        include_chat_template_kwargs: bool,
    ) -> None:
        ensure_local_base_url(base_url)
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.context_window = context_window
        self.include_chat_template_kwargs = include_chat_template_kwargs

    def extract(
        self,
        prompt: str,
        *,
        model_id: str,
        max_tokens: int,
        allowed_message_ids: list[str] | None = None,
        relaxed_schema: bool = False,
    ) -> ExtractorModelOutput:
        payload = build_chat_completion_payload(
            model_id=model_id,
            prompt=prompt,
            max_tokens=max_tokens,
            allowed_message_ids=allowed_message_ids,
            relaxed_schema=relaxed_schema,
            include_chat_template_kwargs=self.include_chat_template_kwargs,
        )
        if self.context_window is not None:
            assert_context_budget(
                prompt,
                max_tokens=max_tokens,
                context_window=self.context_window,
            )
        response = request_json(
            "POST",
            f"{self.base_url}/v1/chat/completions",
            payload=payload,
            timeout_seconds=self.timeout_seconds,
        )
        return parse_extraction_response(response, relaxed_schema=relaxed_schema)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m benchmarks.extraction.run_benchmark",
        description="RFC 0019 local-only Phase 3 extraction backend benchmark.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    sample_slice = subparsers.add_parser("sample-slice")
    sample_slice.add_argument("--output", required=True)
    sample_slice.add_argument("--target-size", type=positive_int, default=1000)
    sample_slice.add_argument("--seed", type=int, default=19)
    sample_slice.add_argument("--source-kind", action="append")

    smoke = subparsers.add_parser("smoke")
    add_endpoint_args(smoke)

    run = subparsers.add_parser("run")
    run.add_argument("--slice", required=True)
    run.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    run.add_argument("--backend-name", required=True)
    run.add_argument("--concurrency", type=positive_int, default=1)
    run.add_argument("--include-claim-text", action="store_true", default=False)
    run.add_argument("--server-command")
    run.add_argument("--server-ready-timeout-seconds", type=positive_int, default=180)
    run.add_argument("--metrics-url")
    add_endpoint_args(run)

    compare = subparsers.add_parser("compare")
    compare.add_argument("--control-run", required=True)
    compare.add_argument("--candidate-run", required=True)
    compare.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    compare.add_argument(
        "--review-output",
        help=(
            "Optional tracked markdown summary path, for example "
            "docs/reviews/phase3/PHASE_3_EXTRACTION_BACKEND_BENCHMARK_2026_05_07.md"
        ),
    )

    return parser


def add_endpoint_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--allow-local-models",
        action="store_true",
        default=False,
        help="Required before any local model HTTP request is made.",
    )
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--model-id")
    parser.add_argument("--model-path")
    parser.add_argument("--request-profile-version", default=BENCHMARK_REQUEST_PROFILE_VERSION)
    parser.add_argument("--max-tokens", type=positive_int, default=DEFAULT_EXTRACTION_MAX_TOKENS)
    parser.add_argument("--timeout-seconds", type=positive_int, default=DEFAULT_TIMEOUT_SECONDS)
    parser.add_argument("--retries", type=non_negative_int, default=EXTRACTION_RETRIES)
    parser.add_argument("--context-window", type=positive_int, default=DEFAULT_CONTEXT_WINDOW)
    parser.add_argument(
        "--no-context-guard",
        action="store_true",
        default=False,
        help="Skip the benchmark-local prompt/context budget guard.",
    )
    parser.add_argument(
        "--chat-template-kwargs",
        choices=("disable-thinking", "none"),
        default="disable-thinking",
    )
    parser.add_argument("--compute-model-sha256", action="store_true", default=False)


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "sample-slice":
            with connect() as conn:
                selected = create_segment_slice(
                    conn,
                    target_size=args.target_size,
                    seed=args.seed,
                    source_kinds=tuple(args.source_kind or ()),
                )
            path = write_slice_manifest(
                selected,
                output_path=Path(args.output),
                target_size=args.target_size,
                seed=args.seed,
                source_kinds=tuple(args.source_kind or ()),
            )
            print(path)
            return 0
        if args.command == "smoke":
            require_local_model_opt_in(args.allow_local_models)
            config = config_from_args(
                args,
                backend_name="smoke",
                output_dir=Path(DEFAULT_OUTPUT_DIR),
            )
            client = client_from_config(config)
            run_extractor_health_smoke_threadsafe(
                client,
                model_id=config.model_id,
                max_tokens=min(128, config.max_tokens),
                retries=0,
            )
            print("smoke ok")
            return 0
        if args.command == "run":
            require_local_model_opt_in(args.allow_local_models)
            config = config_from_args(
                args,
                backend_name=args.backend_name,
                output_dir=Path(args.output_dir),
            )
            run_path = run_backend_benchmark(config, slice_path=Path(args.slice))
            print(run_path)
            return 0
        if args.command == "compare":
            comparison_path = compare_backend_runs(
                control_run_path=Path(args.control_run),
                candidate_run_path=Path(args.candidate_run),
                output_dir=Path(args.output_dir),
                review_output=Path(args.review_output) if args.review_output else None,
            )
            print(comparison_path)
            return 0
    except (ExtractionBenchmarkError, ValueError, OSError, psycopg.Error) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    parser.error(f"unknown command: {args.command}")
    return 2


def config_from_args(
    args: argparse.Namespace,
    *,
    backend_name: str,
    output_dir: Path,
) -> BenchmarkRunConfig:
    base_url = normalized_local_base_url(args.base_url)
    model_id = args.model_id or args.model_path or default_extractor_model_id()
    model_id = expanded_model_path(model_id) if looks_like_path(model_id) else model_id
    context_window = None if args.no_context_guard else args.context_window
    include_chat_template_kwargs = args.chat_template_kwargs == "disable-thinking"
    return BenchmarkRunConfig(
        backend_name=backend_name,
        base_url=base_url,
        model_id=model_id,
        request_profile_version=args.request_profile_version,
        output_dir=output_dir,
        max_tokens=args.max_tokens,
        timeout_seconds=args.timeout_seconds,
        retries=args.retries,
        concurrency=getattr(args, "concurrency", 1),
        context_window=context_window,
        include_chat_template_kwargs=include_chat_template_kwargs,
        include_claim_text=getattr(args, "include_claim_text", False),
        compute_model_sha256=args.compute_model_sha256,
        metrics_url=getattr(args, "metrics_url", None),
        model_path=args.model_path,
        server_command=getattr(args, "server_command", None),
        server_ready_timeout_seconds=getattr(
            args,
            "server_ready_timeout_seconds",
            DEFAULT_SERVER_READY_TIMEOUT_SECONDS,
        ),
    )


def create_segment_slice(
    conn: psycopg.Connection,
    *,
    target_size: int,
    seed: int,
    source_kinds: tuple[str, ...] = (),
) -> list[SliceSegment]:
    rows = conn.execute(
        """
        SELECT
            s.id::text,
            s.generation_id::text,
            s.conversation_id::text,
            s.source_kind::text,
            s.sequence_index,
            cardinality(s.message_ids),
            length(COALESCE(s.content_text, ''))
        FROM segments s
        JOIN segment_generations sg ON sg.id = s.generation_id
        WHERE s.is_active = true
          AND sg.status = 'active'
          AND s.conversation_id IS NOT NULL
          AND s.source_kind IN ('chatgpt', 'claude', 'gemini')
          AND (cardinality(%s::text[]) = 0 OR s.source_kind = ANY(%s::text[]))
        ORDER BY s.source_kind, s.conversation_id, s.sequence_index, s.id
        """,
        (list(source_kinds), list(source_kinds)),
    ).fetchall()
    candidates = [
        SliceSegment(
            segment_id=row[0],
            generation_id=row[1],
            conversation_id=row[2],
            source_kind=row[3],
            sequence_index=int(row[4]),
            message_count=int(row[5] or 0),
            content_chars=int(row[6] or 0),
            size_bucket=size_bucket(int(row[5] or 0), int(row[6] or 0)),
        )
        for row in rows
    ]
    return select_balanced_slice(candidates, target_size=target_size, seed=seed)


def select_balanced_slice(
    candidates: list[SliceSegment],
    *,
    target_size: int,
    seed: int,
) -> list[SliceSegment]:
    if not candidates:
        raise ExtractionBenchmarkError("no active AI-conversation segments are available")
    by_bucket: dict[str, list[SliceSegment]] = defaultdict(list)
    for candidate in candidates:
        by_bucket[candidate.bucket].append(candidate)
    rng = random.Random(seed)
    for rows in by_bucket.values():
        rng.shuffle(rows)

    selected: list[SliceSegment] = []
    bucket_names = sorted(by_bucket)
    while len(selected) < target_size and bucket_names:
        next_bucket_names: list[str] = []
        for bucket_name in bucket_names:
            rows = by_bucket[bucket_name]
            if not rows:
                continue
            selected.append(rows.pop())
            if len(selected) >= target_size:
                break
            if rows:
                next_bucket_names.append(bucket_name)
        bucket_names = next_bucket_names
    return selected


def size_bucket(message_count: int, content_chars: int) -> str:
    if message_count <= 2 and content_chars < 2_000:
        return "short"
    if message_count <= 8 and content_chars < 8_000:
        return "medium"
    return "long"


def write_slice_manifest(
    selected: list[SliceSegment],
    *,
    output_path: Path,
    target_size: int,
    seed: int,
    source_kinds: tuple[str, ...],
) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": SLICE_SCHEMA_VERSION,
        "created_at": utc_now(),
        "git_commit": git_commit(),
        "target_size": target_size,
        "actual_size": len(selected),
        "seed": seed,
        "source_kinds": list(source_kinds) if source_kinds else "all",
        "stratification": {
            "kind": "source_kind_x_size_bucket",
            "bucket_counts": dict(Counter(segment.bucket for segment in selected)),
        },
        "segments": [slice_segment_to_dict(segment) for segment in selected],
    }
    output_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return output_path


def run_backend_benchmark(config: BenchmarkRunConfig, *, slice_path: Path) -> Path:
    slice_payload = load_slice_manifest(slice_path)
    run_id = make_run_id(config.backend_name)
    run_dir = config.output_dir / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    server = None
    try:
        if config.server_command:
            server = start_managed_server(config, run_dir=run_dir)
        server_before = probe_server(config)
        metrics_before = fetch_metrics_snapshot(config.metrics_url)
        with connect() as conn:
            segments = [
                fetch_segment_payload(conn, item["segment_id"])
                for item in slice_payload["segments"]
            ]

        started = time.perf_counter()
        results = run_segments_concurrently(segments, config)
        wall_clock_seconds = time.perf_counter() - started
        metrics_after = fetch_metrics_snapshot(config.metrics_url)

        records_path = run_dir / "segments.jsonl"
        write_segment_records(records_path, results)
        run_payload = build_run_payload(
            config,
            run_id=run_id,
            slice_payload=slice_payload,
            segment_records_path=records_path.name,
            results=results,
            wall_clock_seconds=wall_clock_seconds,
            server_before=server_before,
            metrics_before=metrics_before,
            metrics_after=metrics_after,
            server=server,
        )
        run_path = run_dir / "run.json"
        run_path.write_text(
            json.dumps(run_payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return run_path
    finally:
        if server is not None:
            stop_managed_server(server)


def run_segments_concurrently(
    segments: list[SegmentPayload],
    config: BenchmarkRunConfig,
) -> list[SegmentBenchmarkResult]:
    results: list[SegmentBenchmarkResult] = []
    workers = max(1, config.concurrency)
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(extract_segment_for_benchmark, index, segment, config): index
            for index, segment in enumerate(segments, start=1)
        }
        for future in as_completed(futures):
            results.append(future.result())
            print(
                f"extract-benchmark: {len(results)}/{len(segments)} segments complete",
                file=sys.stderr,
                flush=True,
            )
    return sorted(results, key=lambda result: result.index)


def extract_segment_for_benchmark(
    index: int,
    segment: SegmentPayload,
    config: BenchmarkRunConfig,
) -> SegmentBenchmarkResult:
    client = client_from_config(config)
    started = time.perf_counter()
    try:
        output = extract_segment_chunks_threadsafe(
            client,
            extraction_prompt_chunks(segment),
            model_id=config.model_id,
            max_tokens=config.max_tokens,
            retries=config.retries,
        )
        valid, dropped = salvage_claims(output.claims, segment)
        dropped = chunk_dropped_claims(output) + dropped
        if not valid and dropped:
            output, valid, dropped = retry_after_trigger_violation_threadsafe(
                client,
                segment,
                prior_output=output,
                prior_dropped=dropped,
                model_id=config.model_id,
                max_tokens=config.max_tokens,
            )
    except Exception as exc:
        duration_seconds = time.perf_counter() - started
        return SegmentBenchmarkResult(
            index=index,
            segment_id=segment.id,
            status="failed",
            duration_seconds=duration_seconds,
            claim_count=0,
            dropped_count=0,
            schema_valid=False,
            provenance_valid=False,
            claims=[],
            dropped_claims=[],
            parse_metadata={},
            failure={
                "kind": classify_exception(exc),
                "error": str(exc),
            },
        )

    duration_seconds = time.perf_counter() - started
    return SegmentBenchmarkResult(
        index=index,
        segment_id=segment.id,
        status="ok",
        duration_seconds=duration_seconds,
        claim_count=len(valid),
        dropped_count=len(dropped),
        schema_valid=True,
        provenance_valid=not provenance_drop_count(dropped),
        claims=[claim_to_record(claim, include_text=config.include_claim_text) for claim in valid],
        dropped_claims=redact_dropped_claims(dropped),
        parse_metadata=summarize_parse_metadata(output.parse_metadata),
    )


def extract_segment_chunks_threadsafe(
    client: BenchmarkExtractorClient,
    chunks: list[SegmentPayload],
    *,
    model_id: str,
    max_tokens: int,
    retries: int,
    validation_feedback: str | None = None,
) -> ExtractorModelOutput:
    outputs: list[ExtractorModelOutput] = []
    chunk_metadata: list[dict[str, Any]] = []
    for index, chunk in enumerate(chunks, start=1):
        extract_chunk_adaptively_threadsafe(
            client,
            chunk,
            model_id=model_id,
            max_tokens=max_tokens,
            retries=retries,
            validation_feedback=validation_feedback,
            root_chunk_index=index,
            root_chunk_count=len(chunks),
            split_path=[index],
            split_depth=0,
            outputs=outputs,
            chunk_metadata=chunk_metadata,
        )
    if len(outputs) == 1:
        output = outputs[0]
        return ExtractorModelOutput(
            claims=output.claims,
            model_response=output.model_response,
            parse_metadata={
                **output.parse_metadata,
                "chunked": False,
                "chunk_count": 1,
                "chunks": chunk_metadata,
            },
            relaxed_schema=output.relaxed_schema,
        )
    claims = [claim for output in outputs for claim in output.claims]
    dropped = [drop for output in outputs for drop in chunk_dropped_claims(output)]
    return ExtractorModelOutput(
        claims=claims,
        model_response=json.dumps(
            {"chunks": [output.model_response for output in outputs]},
            sort_keys=True,
        ),
        parse_metadata={
            "chunked": True,
            "chunk_count": len(outputs),
            "chunks": chunk_metadata,
            "chunk_dropped_claims": dropped,
        },
        relaxed_schema=any(output.relaxed_schema for output in outputs),
    )


def extract_chunk_adaptively_threadsafe(
    client: BenchmarkExtractorClient,
    chunk: SegmentPayload,
    *,
    model_id: str,
    max_tokens: int,
    retries: int,
    validation_feedback: str | None,
    root_chunk_index: int,
    root_chunk_count: int,
    split_path: list[int],
    split_depth: int,
    outputs: list[ExtractorModelOutput],
    chunk_metadata: list[dict[str, Any]],
) -> None:
    try:
        output = call_extractor_with_retries_threadsafe(
            client,
            build_extraction_prompt(chunk, validation_feedback=validation_feedback),
            model_id=model_id,
            max_tokens=max_tokens,
            allowed_message_ids=chunk.message_ids,
            retries=retries,
        )
    except Exception as exc:
        subchunks = split_extraction_chunk(chunk)
        if split_depth < 4 and len(subchunks) > 1:
            child_retries = max(0, retries - 1)
            for subindex, subchunk in enumerate(subchunks, start=1):
                extract_chunk_adaptively_threadsafe(
                    client,
                    subchunk,
                    model_id=model_id,
                    max_tokens=max_tokens,
                    retries=child_retries,
                    validation_feedback=validation_feedback,
                    root_chunk_index=root_chunk_index,
                    root_chunk_count=root_chunk_count,
                    split_path=[*split_path, subindex],
                    split_depth=split_depth + 1,
                    outputs=outputs,
                    chunk_metadata=chunk_metadata,
                )
            return
        attach_chunk_diagnostics(
            exc,
            chunk_index=root_chunk_index,
            chunk_count=root_chunk_count,
            split_depth=split_depth,
            split_path=split_path,
            message_count=len(chunk.message_ids),
        )
        raise
    output = validate_chunk_output(output, chunk, split_path=split_path)
    outputs.append(output)
    chunk_metadata.append(
        {
            "root_chunk_index": root_chunk_index,
            "root_chunk_count": root_chunk_count,
            "split_path": split_path,
            "split_depth": split_depth,
            "message_count": len(chunk.message_ids),
            "claim_count": len(output.claims),
            "parse_metadata": summarize_parse_metadata(output.parse_metadata),
        }
    )


def call_extractor_with_retries_threadsafe(
    client: BenchmarkExtractorClient,
    prompt: str,
    *,
    model_id: str,
    max_tokens: int,
    allowed_message_ids: list[str] | None,
    retries: int,
) -> ExtractorModelOutput:
    errors: list[str] = []
    relaxed_schema_only = False
    for attempt in range(retries + 1):
        try:
            return coerce_client_output(
                client.extract(
                    prompt,
                    model_id=model_id,
                    max_tokens=max_tokens,
                    allowed_message_ids=allowed_message_ids,
                    relaxed_schema=relaxed_schema_only,
                )
            )
        except Exception as exc:
            errors.append(str(exc))
            if is_schema_construction_error(exc) and not relaxed_schema_only:
                relaxed_schema_only = True
                try:
                    return coerce_client_output(
                        client.extract(
                            prompt,
                            model_id=model_id,
                            max_tokens=max_tokens,
                            allowed_message_ids=allowed_message_ids,
                            relaxed_schema=True,
                        )
                    )
                except Exception as relaxed_exc:
                    errors.append(str(relaxed_exc))
                    if attempt >= retries:
                        attach_attempt_diagnostics(
                            relaxed_exc,
                            errors,
                            max_tokens=max_tokens,
                        )
                        raise
                    continue
            if attempt >= retries:
                attach_attempt_diagnostics(exc, errors, max_tokens=max_tokens)
                raise
    raise ExtractionError("extractor retry loop exhausted unexpectedly")


def retry_after_trigger_violation_threadsafe(
    client: BenchmarkExtractorClient,
    segment: SegmentPayload,
    *,
    prior_output: ExtractorModelOutput,
    prior_dropped: list[dict[str, Any]],
    model_id: str,
    max_tokens: int,
) -> tuple[ExtractorModelOutput, list[ClaimDraft], list[dict[str, Any]]]:
    feedback = build_validation_repair_feedback(prior_dropped)
    try:
        repaired = extract_segment_chunks_threadsafe(
            client,
            extraction_prompt_chunks(segment),
            model_id=model_id,
            max_tokens=max_tokens,
            retries=0,
            validation_feedback=feedback,
        )
    except Exception as exc:
        return (
            replace(
                prior_output,
                parse_metadata={
                    **prior_output.parse_metadata,
                    "validation_repair": {
                        "attempted": True,
                        "result": "failed",
                        "prior_dropped_count": len(prior_dropped),
                        "prior_error_counts": dropped_error_counts(prior_dropped),
                        "prior_dropped_claims": redact_dropped_claims(prior_dropped),
                        "final_dropped_count": 0,
                        "final_error_counts": {},
                        "final_dropped_claims": [],
                        "last_error": str(exc),
                    },
                },
            ),
            [],
            prior_dropped,
        )

    valid, dropped = salvage_claims(repaired.claims, segment)
    dropped = chunk_dropped_claims(repaired) + dropped
    return (
        replace(
            repaired,
            parse_metadata={
                **repaired.parse_metadata,
                "validation_repair": {
                    "attempted": True,
                    "result": "accepted" if (valid or not dropped) else "still_invalid",
                    "prior_dropped_count": len(prior_dropped),
                    "prior_error_counts": dropped_error_counts(prior_dropped),
                    "prior_dropped_claims": redact_dropped_claims(prior_dropped),
                    "final_dropped_count": len(dropped),
                    "final_error_counts": dropped_error_counts(dropped),
                    "final_dropped_claims": redact_dropped_claims(dropped),
                },
            },
        ),
        valid,
        dropped,
    )


def run_extractor_health_smoke_threadsafe(
    client: BenchmarkExtractorClient,
    *,
    model_id: str,
    max_tokens: int,
    retries: int,
) -> None:
    call_extractor_with_retries_threadsafe(
        client,
        'Health check only. Return exactly one schema-valid JSON object: {"claims":[]}.',
        model_id=model_id,
        max_tokens=max_tokens,
        allowed_message_ids=None,
        retries=retries,
    )


def build_chat_completion_payload(
    *,
    model_id: str,
    prompt: str,
    max_tokens: int,
    allowed_message_ids: list[str] | None,
    relaxed_schema: bool,
    include_chat_template_kwargs: bool,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "model": model_id,
        "messages": [
            {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        "stream": False,
        "temperature": 0,
        "top_p": 1,
        "max_tokens": max_tokens,
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": "ClaimExtractionResult",
                "strict": True,
                "schema": extraction_json_schema(
                    allowed_message_ids,
                    relaxed_schema=relaxed_schema,
                ),
            },
        },
    }
    if include_chat_template_kwargs:
        payload["chat_template_kwargs"] = {"enable_thinking": False}
    return payload


def build_run_payload(
    config: BenchmarkRunConfig,
    *,
    run_id: str,
    slice_payload: dict[str, Any],
    segment_records_path: str,
    results: list[SegmentBenchmarkResult],
    wall_clock_seconds: float,
    server_before: dict[str, Any],
    metrics_before: dict[str, Any] | None,
    metrics_after: dict[str, Any] | None,
    server: ManagedServer | None,
) -> dict[str, Any]:
    model_path = config.model_path
    if model_path is None and looks_like_path(config.model_id):
        model_path = config.model_id
    return {
        "schema_version": RUN_SCHEMA_VERSION,
        "run_id": run_id,
        "created_at": utc_now(),
        "git_commit": git_commit(),
        "rfc": "0019",
        "backend_name": config.backend_name,
        "prompt_version": EXTRACTION_PROMPT_VERSION,
        "request_profile_version": config.request_profile_version,
        "model": model_metadata(
            model_id=config.model_id,
            model_path=model_path,
            compute_sha256=config.compute_model_sha256,
        ),
        "request": {
            "base_url": config.base_url,
            "endpoint": f"{config.base_url}/v1/chat/completions",
            "max_tokens": config.max_tokens,
            "timeout_seconds": config.timeout_seconds,
            "retries": config.retries,
            "concurrency": config.concurrency,
            "context_window": config.context_window,
            "chat_template_kwargs": (
                {"enable_thinking": False} if config.include_chat_template_kwargs else "omitted"
            ),
            "response_format_type": "json_schema",
        },
        "server": {
            "managed": server is not None,
            "command": server.command if server else None,
            "log_path": str(server.log_path) if server else None,
            "probe_before": server_before,
            "metrics_before": metrics_before,
            "metrics_after": metrics_after,
        },
        "slice": {
            "schema_version": slice_payload.get("schema_version"),
            "created_at": slice_payload.get("created_at"),
            "seed": slice_payload.get("seed"),
            "target_size": slice_payload.get("target_size"),
            "actual_size": len(slice_payload.get("segments", [])),
            "stratification": slice_payload.get("stratification"),
        },
        "segment_records_path": segment_records_path,
        "metrics": aggregate_metrics(results, wall_clock_seconds=wall_clock_seconds),
        "artifact_privacy": {
            "segments_jsonl_contains_claim_text": config.include_claim_text,
            "default_claim_record_policy": (
                "claim text and rationale are omitted unless --include-claim-text is set"
            ),
        },
    }


def aggregate_metrics(
    results: list[SegmentBenchmarkResult],
    *,
    wall_clock_seconds: float,
) -> dict[str, Any]:
    total = len(results)
    ok = sum(1 for result in results if result.status == "ok")
    failed = total - ok
    claims = [claim for result in results for claim in result.claims]
    dropped_count = sum(result.dropped_count for result in results)
    claim_count = len(claims)
    denominator = claim_count + dropped_count
    predicate_counts = Counter(str(claim.get("predicate")) for claim in claims)
    stability_counts = Counter(str(claim.get("stability_class")) for claim in claims)
    usage = aggregate_usage(results)
    return {
        "segments_total": total,
        "segments_ok": ok,
        "segments_failed": failed,
        "schema_valid_rate": ratio(ok, total),
        "provenance_clean_segments": sum(1 for result in results if result.provenance_valid),
        "provenance_clean_segment_rate": ratio(
            sum(1 for result in results if result.provenance_valid),
            total,
        ),
        "claim_count": claim_count,
        "dropped_claim_count": dropped_count,
        "dropped_claim_rate": ratio(dropped_count, denominator),
        "predicate_counts": dict(sorted(predicate_counts.items())),
        "stability_class_counts": dict(sorted(stability_counts.items())),
        "field_presence": field_presence_metrics(claims),
        "wall_clock_seconds": wall_clock_seconds,
        "sum_segment_seconds": sum(result.duration_seconds for result in results),
        "throughput_segments_per_second": ratio(total, wall_clock_seconds),
        "throughput_claims_per_second": ratio(claim_count, wall_clock_seconds),
        "usage": usage,
        "failure_counts": dict(
            sorted(
                Counter(
                    str(result.failure.get("kind"))
                    for result in results
                    if result.failure is not None
                ).items()
            )
        ),
    }


def field_presence_metrics(claims: list[dict[str, Any]]) -> dict[str, float | None]:
    fields = [
        "subject_text",
        "predicate",
        "object",
        "stability_class",
        "confidence",
        "evidence_message_ids",
    ]
    if not claims:
        return {field: None for field in fields}
    return {
        field: ratio(
            sum(1 for claim in claims if claim.get("field_presence", {}).get(field) is True),
            len(claims),
        )
        for field in fields
    }


def aggregate_usage(results: list[SegmentBenchmarkResult]) -> dict[str, int]:
    totals = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
    for result in results:
        usage = result.parse_metadata.get("usage")
        if isinstance(usage, dict):
            add_usage(totals, usage)
            continue
        for chunk in result.parse_metadata.get("chunks", []):
            if not isinstance(chunk, dict):
                continue
            parse_metadata = chunk.get("parse_metadata")
            if isinstance(parse_metadata, dict):
                add_usage(totals, parse_metadata.get("usage"))
    return totals


def add_usage(totals: dict[str, int], usage: Any) -> None:
    if not isinstance(usage, dict):
        return
    for key in totals:
        value = usage.get(key)
        if isinstance(value, int):
            totals[key] += value


def claim_to_record(claim: ClaimDraft, *, include_text: bool) -> dict[str, Any]:
    object_json_keys = sorted(claim.object_json) if isinstance(claim.object_json, dict) else []
    record: dict[str, Any] = {
        "subject_text_present": bool(claim.subject_text.strip()),
        "predicate": claim.predicate,
        "object_kind": "json" if claim.object_json is not None else "text",
        "object_present": claim.object_json is not None or bool((claim.object_text or "").strip()),
        "object_json_keys": object_json_keys,
        "stability_class": claim.stability_class,
        "confidence": claim.confidence,
        "evidence_message_ids": list(claim.evidence_message_ids),
        "evidence_message_count": len(claim.evidence_message_ids),
        "rationale_present": bool(claim.rationale),
        "field_presence": {
            "subject_text": bool(claim.subject_text.strip()),
            "predicate": bool(claim.predicate),
            "object": claim.object_json is not None or bool((claim.object_text or "").strip()),
            "stability_class": bool(claim.stability_class),
            "confidence": 0 <= claim.confidence <= 1,
            "evidence_message_ids": bool(claim.evidence_message_ids),
        },
    }
    if include_text:
        record["subject_text"] = claim.subject_text
        record["object_text"] = claim.object_text
        record["object_json"] = claim.object_json
        record["rationale"] = claim.rationale
    return record


def summarize_parse_metadata(parse_metadata: dict[str, Any]) -> dict[str, Any]:
    summarized = dict(parse_metadata)
    if "chunk_dropped_claims" in summarized:
        value = summarized["chunk_dropped_claims"]
        dropped = value if isinstance(value, list) else []
        summarized["chunk_dropped_claims"] = redact_dropped_claims(dropped)
    return summarized


def write_segment_records(path: Path, results: list[SegmentBenchmarkResult]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for result in results:
            handle.write(json.dumps(segment_result_to_dict(result), sort_keys=True) + "\n")


def compare_backend_runs(
    *,
    control_run_path: Path,
    candidate_run_path: Path,
    output_dir: Path,
    review_output: Path | None,
) -> Path:
    control_run, control_records = load_run_artifacts(control_run_path)
    candidate_run, candidate_records = load_run_artifacts(candidate_run_path)
    comparison = build_comparison_payload(
        control_run,
        control_records,
        candidate_run,
        candidate_records,
    )
    comparison_dir = output_dir / make_run_id("comparison")
    comparison_dir.mkdir(parents=True, exist_ok=False)
    comparison_path = comparison_dir / "comparison.json"
    comparison_path.write_text(
        json.dumps(comparison, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    markdown = render_comparison_markdown(comparison)
    (comparison_dir / "report.md").write_text(markdown, encoding="utf-8")
    if review_output is not None:
        review_output.parent.mkdir(parents=True, exist_ok=True)
        review_output.write_text(markdown, encoding="utf-8")
    return comparison_path


def build_comparison_payload(
    control_run: dict[str, Any],
    control_records: list[dict[str, Any]],
    candidate_run: dict[str, Any],
    candidate_records: list[dict[str, Any]],
) -> dict[str, Any]:
    control_metrics = control_run["metrics"]
    candidate_metrics = candidate_run["metrics"]
    control_wall = float(control_metrics.get("wall_clock_seconds") or 0)
    candidate_wall = float(candidate_metrics.get("wall_clock_seconds") or 0)
    speedup = None if candidate_wall <= 0 else control_wall / candidate_wall
    control_claims = [claim for record in control_records for claim in record.get("claims", [])]
    candidate_claims = [claim for record in candidate_records for claim in record.get("claims", [])]
    return {
        "schema_version": COMPARISON_SCHEMA_VERSION,
        "created_at": utc_now(),
        "git_commit": git_commit(),
        "rfc": "0019",
        "control": run_summary(control_run),
        "candidate": run_summary(candidate_run),
        "shared_segment_count": len(
            set(record["segment_id"] for record in control_records)
            & set(record["segment_id"] for record in candidate_records)
        ),
        "metrics": {
            "speedup": speedup,
            "schema_valid_rate_delta": (
                none_safe_delta(
                    candidate_metrics.get("schema_valid_rate"),
                    control_metrics.get("schema_valid_rate"),
                )
            ),
            "provenance_clean_segment_rate_delta": (
                none_safe_delta(
                    candidate_metrics.get("provenance_clean_segment_rate"),
                    control_metrics.get("provenance_clean_segment_rate"),
                )
            ),
            "dropped_claim_rate_delta": (
                none_safe_delta(
                    candidate_metrics.get("dropped_claim_rate"),
                    control_metrics.get("dropped_claim_rate"),
                )
            ),
            "claim_count_delta": (
                int(candidate_metrics.get("claim_count") or 0)
                - int(control_metrics.get("claim_count") or 0)
            ),
            "predicate_distribution_l1": distribution_l1(
                Counter(str(claim.get("predicate")) for claim in control_claims),
                Counter(str(claim.get("predicate")) for claim in candidate_claims),
            ),
            "stability_distribution_l1": distribution_l1(
                Counter(str(claim.get("stability_class")) for claim in control_claims),
                Counter(str(claim.get("stability_class")) for claim in candidate_claims),
            ),
        },
        "promotion_readiness": promotion_readiness(control_metrics, candidate_metrics, speedup),
    }


def promotion_readiness(
    control_metrics: dict[str, Any],
    candidate_metrics: dict[str, Any],
    speedup: float | None,
) -> dict[str, Any]:
    checks = {
        "schema_valid_rate_at_least_control": (
            candidate_metrics.get("schema_valid_rate", 0)
            >= control_metrics.get("schema_valid_rate", 0)
        ),
        "provenance_clean_segment_rate_at_least_control": (
            candidate_metrics.get("provenance_clean_segment_rate", 0)
            >= control_metrics.get("provenance_clean_segment_rate", 0)
        ),
        "speedup_at_least_floor_2x": speedup is not None and speedup >= 2.0,
        "speedup_at_least_target_5x": speedup is not None and speedup >= 5.0,
        "no_candidate_failures": int(candidate_metrics.get("segments_failed") or 0) == 0,
    }
    return {
        "checks": checks,
        "candidate_for_production_switch": (
            checks["schema_valid_rate_at_least_control"]
            and checks["provenance_clean_segment_rate_at_least_control"]
            and checks["speedup_at_least_floor_2x"]
            and checks["no_candidate_failures"]
        ),
        "note": (
            "This comparison is evidence only. Production promotion still requires "
            "DECISION_LOG.md, request_profile_version/extraction_model_version changes, "
            "and RFC 0017 re-extraction handling."
        ),
    }


def render_comparison_markdown(comparison: dict[str, Any]) -> str:
    metrics = comparison["metrics"]
    readiness = comparison["promotion_readiness"]["checks"]
    lines = [
        "# Phase 3 Extraction Backend Benchmark",
        "",
        "| Field | Value |",
        "|---|---|",
        f"| Created | `{comparison['created_at']}` |",
        f"| RFC | `{comparison['rfc']}` |",
        f"| Control | `{comparison['control']['backend_name']}` |",
        f"| Candidate | `{comparison['candidate']['backend_name']}` |",
        f"| Shared segments | `{comparison['shared_segment_count']}` |",
        "",
        "## Metrics",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Speedup | `{format_optional_float(metrics['speedup'])}` |",
        f"| Schema valid delta | `{format_optional_float(metrics['schema_valid_rate_delta'])}` |",
        "| Provenance clean segment delta | "
        f"`{format_optional_float(metrics['provenance_clean_segment_rate_delta'])}` |",
        "| Dropped claim rate delta | "
        f"`{format_optional_float(metrics['dropped_claim_rate_delta'])}` |",
        f"| Claim count delta | `{metrics['claim_count_delta']}` |",
        "| Predicate distribution L1 | "
        f"`{format_optional_float(metrics['predicate_distribution_l1'])}` |",
        "| Stability distribution L1 | "
        f"`{format_optional_float(metrics['stability_distribution_l1'])}` |",
        "",
        "## Promotion Checks",
        "",
        "| Check | Passed |",
        "|---|---:|",
    ]
    for key, value in readiness.items():
        lines.append(f"| `{key}` | `{value}` |")
    lines.extend(
        [
            "",
            "This report is aggregate-only. Raw segment prompts, completions, claim text, "
            "and private corpus content are intentionally absent from the tracked summary.",
            "",
            comparison["promotion_readiness"]["note"],
            "",
        ]
    )
    return "\n".join(lines)


def load_run_artifacts(run_path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    run = json.loads(run_path.read_text(encoding="utf-8"))
    records_path = run_path.parent / run["segment_records_path"]
    records = [
        json.loads(line)
        for line in records_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    return run, records


def start_managed_server(config: BenchmarkRunConfig, *, run_dir: Path) -> ManagedServer:
    command = shlex.split(config.server_command or "")
    if not command:
        raise ExtractionBenchmarkError("--server-command did not contain a command")
    log_path = run_dir / "server.log"
    log_handle = log_path.open("w", encoding="utf-8")
    process = subprocess.Popen(
        command,
        text=True,
        stdout=log_handle,
        stderr=subprocess.STDOUT,
    )
    log_handle.close()
    deadline = time.monotonic() + config.server_ready_timeout_seconds
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise ExtractionBenchmarkError(
                f"managed server exited before readiness; log: {log_path}"
            )
        try:
            request_json(
                "GET",
                f"{config.base_url}/v1/models",
                timeout_seconds=5,
            )
            return ManagedServer(process=process, command=command, log_path=log_path)
        except LocalEndpointError:
            time.sleep(1)
    stop_managed_server(ManagedServer(process=process, command=command, log_path=log_path))
    raise ExtractionBenchmarkError(f"managed server did not become ready; log: {log_path}")


def stop_managed_server(server: ManagedServer) -> None:
    if server.process.poll() is not None:
        return
    server.process.terminate()
    try:
        server.process.wait(timeout=30)
    except subprocess.TimeoutExpired:
        server.process.kill()
        server.process.wait(timeout=30)


def probe_server(config: BenchmarkRunConfig) -> dict[str, Any]:
    probe: dict[str, Any] = {}
    try:
        probe["models_response"] = request_json(
            "GET",
            f"{config.base_url}/v1/models",
            timeout_seconds=min(30, config.timeout_seconds),
        )
    except LocalEndpointError as exc:
        probe["models_error"] = {"kind": exc.kind, "error": str(exc)}
    return probe


def fetch_metrics_snapshot(metrics_url: str | None) -> dict[str, Any] | None:
    if not metrics_url:
        return None
    ensure_local_base_url(metrics_url)
    try:
        text = request_text("GET", metrics_url, timeout_seconds=15)
    except LocalEndpointError as exc:
        return {"error": {"kind": exc.kind, "message": str(exc)}}
    truncated = len(text) > MAX_RECORDED_METRICS_CHARS
    return {
        "url": metrics_url,
        "truncated": truncated,
        "text": text[:MAX_RECORDED_METRICS_CHARS],
    }


def request_json(
    method: str,
    url: str,
    *,
    payload: dict[str, Any] | None = None,
    timeout_seconds: int,
) -> dict[str, Any]:
    text = request_text(method, url, payload=payload, timeout_seconds=timeout_seconds)
    try:
        decoded = json.loads(text)
    except json.JSONDecodeError as exc:
        raise LocalEndpointError(
            f"local endpoint returned invalid JSON: {exc}",
            kind="schema_invalid",
        ) from exc
    if not isinstance(decoded, dict):
        raise LocalEndpointError(
            "local endpoint returned non-object JSON",
            kind="schema_invalid",
        )
    return decoded


def request_text(
    method: str,
    url: str,
    *,
    payload: dict[str, Any] | None = None,
    timeout_seconds: int,
) -> str:
    ensure_local_base_url(url)
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    headers = {"Accept": "application/json"}
    if payload is not None:
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            return response.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", "replace")
        raise LocalEndpointError(
            f"HTTP {exc.code} from local endpoint: {raw[:500]}",
            kind=classify_backend_error(raw, status=exc.code),
        ) from exc
    except TimeoutError as exc:
        raise LocalEndpointError("local endpoint request timed out", kind="read_timeout") from exc
    except urllib.error.URLError as exc:
        message = str(exc.reason or exc)
        raise LocalEndpointError(
            f"local endpoint unavailable: {message}",
            kind=classify_backend_error(message),
        ) from exc


def model_metadata(
    *,
    model_id: str,
    model_path: str | None,
    compute_sha256: bool,
) -> dict[str, Any]:
    metadata: dict[str, Any] = {
        "model_id": model_id,
        "model_path": model_path,
        "path_exists": None,
        "size_bytes": None,
        "sha256": "not_applicable",
    }
    if model_path is None:
        return metadata
    path = Path(expanded_model_path(model_path))
    metadata["model_path"] = str(path)
    metadata["path_exists"] = path.exists()
    try:
        metadata["size_bytes"] = path.stat().st_size
    except OSError:
        metadata["size_bytes"] = None
    if compute_sha256:
        try:
            metadata["sha256"] = model_file_sha256(str(path))
        except OSError as exc:
            metadata["sha256"] = "not_computed"
            metadata["sha256_error"] = str(exc)
    else:
        metadata["sha256"] = "not_computed"
    return metadata


def load_slice_manifest(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema_version") != SLICE_SCHEMA_VERSION:
        raise ExtractionBenchmarkError(
            f"unsupported slice schema_version: {payload.get('schema_version')!r}"
        )
    segments = payload.get("segments")
    if not isinstance(segments, list) or not segments:
        raise ExtractionBenchmarkError("slice manifest contains no segments")
    return payload


def segment_result_to_dict(result: SegmentBenchmarkResult) -> dict[str, Any]:
    return {
        "index": result.index,
        "segment_id": result.segment_id,
        "status": result.status,
        "duration_seconds": result.duration_seconds,
        "claim_count": result.claim_count,
        "dropped_count": result.dropped_count,
        "schema_valid": result.schema_valid,
        "provenance_valid": result.provenance_valid,
        "claims": result.claims,
        "dropped_claims": result.dropped_claims,
        "parse_metadata": result.parse_metadata,
        "failure": result.failure,
    }


def slice_segment_to_dict(segment: SliceSegment) -> dict[str, Any]:
    return {
        "segment_id": segment.segment_id,
        "generation_id": segment.generation_id,
        "conversation_id": segment.conversation_id,
        "source_kind": segment.source_kind,
        "sequence_index": segment.sequence_index,
        "message_count": segment.message_count,
        "content_chars": segment.content_chars,
        "size_bucket": segment.size_bucket,
        "bucket": segment.bucket,
    }


def run_summary(run: dict[str, Any]) -> dict[str, Any]:
    return {
        "backend_name": run.get("backend_name"),
        "run_id": run.get("run_id"),
        "created_at": run.get("created_at"),
        "model_id": run.get("model", {}).get("model_id"),
        "request_profile_version": run.get("request_profile_version"),
        "metrics": run.get("metrics"),
    }


def distribution_l1(control: Counter[str], candidate: Counter[str]) -> float | None:
    control_total = sum(control.values())
    candidate_total = sum(candidate.values())
    if control_total == 0 and candidate_total == 0:
        return 0.0
    if control_total == 0 or candidate_total == 0:
        return None
    keys = set(control) | set(candidate)
    return sum(
        abs((control[key] / control_total) - (candidate[key] / candidate_total)) for key in keys
    )


def none_safe_delta(candidate: Any, control: Any) -> float | None:
    if not isinstance(candidate, int | float) or not isinstance(control, int | float):
        return None
    return float(candidate) - float(control)


def provenance_drop_count(dropped: list[dict[str, Any]]) -> int:
    return sum(
        1
        for drop in dropped
        if isinstance(drop.get("error"), str)
        and "evidence_message_ids must be a subset" in drop["error"]
    )


def classify_exception(exc: BaseException) -> str:
    if isinstance(exc, LocalEndpointError):
        return exc.kind
    text = str(exc).casefold()
    return classify_backend_error(text)


def classify_backend_error(message: str, *, status: int | None = None) -> str:
    lowered = message.casefold()
    if "connection refused" in lowered or "errno 111" in lowered:
        return "connect_refused"
    if "timed out" in lowered or "timeout" in lowered:
        return "read_timeout"
    if "empty grammar stack" in lowered:
        return "grammar_stack_empty"
    if "cuda" in lowered and ("out of memory" in lowered or "oom" in lowered):
        return "cuda_oom"
    if "json" in lowered or "schema" in lowered:
        return "schema_invalid"
    if status is not None and status >= 500:
        return "http_5xx"
    return "unknown"


def require_local_model_opt_in(allow_local_models: bool) -> None:
    if not allow_local_models:
        raise ExtractionBenchmarkError(
            "local model execution requires --allow-local-models; no request was made"
        )


def client_from_config(config: BenchmarkRunConfig) -> BenchmarkExtractorClient:
    return BenchmarkExtractorClient(
        config.base_url,
        timeout_seconds=config.timeout_seconds,
        context_window=config.context_window,
        include_chat_template_kwargs=config.include_chat_template_kwargs,
    )


def normalized_local_base_url(base_url: str) -> str:
    ensure_local_base_url(base_url)
    parsed = urllib.parse.urlparse(base_url)
    if parsed.username or parsed.password:
        raise ExtractionBenchmarkError("local base URL must not include credentials")
    if parsed.params or parsed.query or parsed.fragment:
        raise ExtractionBenchmarkError("local base URL must not include params/query/fragment")
    path = parsed.path.rstrip("/")
    if path:
        raise ExtractionBenchmarkError("local base URL must not include a path")
    return urllib.parse.urlunparse((parsed.scheme, parsed.netloc, "", "", "", ""))


def looks_like_path(value: str) -> bool:
    return value.startswith(("~", "/", "."))


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


def ratio(numerator: int | float, denominator: int | float) -> float | None:
    if denominator == 0:
        return None
    return float(numerator) / float(denominator)


def format_optional_float(value: Any) -> str:
    if not isinstance(value, int | float):
        return "n/a"
    return f"{float(value):.4f}"


def make_run_id(label: str) -> str:
    safe_label = "".join(char if char.isalnum() or char in "-_" else "-" for char in label)
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    suffix = uuid.uuid4().hex[:8]
    return f"{timestamp}.{safe_label}.{suffix}"


if __name__ == "__main__":
    raise SystemExit(main())
