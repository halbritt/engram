from __future__ import annotations

import argparse
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from engram.chatgpt_export import IngestConflict as ChatGPTIngestConflict
from engram.chatgpt_export import ingest_chatgpt_export
from engram.claude_export import IngestConflict as ClaudeIngestConflict
from engram.claude_export import ingest_claude_export
from engram.db import connect
from engram.embedder import DEFAULT_EMBEDDING_MODEL_VERSION, embed_pending_segments
from engram.gemini_export import IngestConflict as GeminiIngestConflict
from engram.gemini_export import ingest_gemini_export
from engram.migrations import migrate
from engram.segmenter import DEFAULT_RETRIES, apply_reclassification_invalidations, segment_pending


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="engram")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("migrate", help="Apply SQL migrations")

    chatgpt_parser = subparsers.add_parser(
        "ingest-chatgpt",
        help="Ingest a local ChatGPT export directory",
    )
    chatgpt_parser.add_argument("path", type=Path)

    claude_parser = subparsers.add_parser(
        "ingest-claude",
        help="Ingest a local Claude.ai export (directory or .zip)",
    )
    claude_parser.add_argument("path", type=Path)

    gemini_parser = subparsers.add_parser(
        "ingest-gemini",
        help="Ingest a local Gemini Google Takeout directory",
    )
    gemini_parser.add_argument("path", nargs="?", type=Path)
    gemini_parser.add_argument("--path", dest="path_option", type=Path)

    segment_parser = subparsers.add_parser(
        "segment",
        help="Segment pending conversations into inactive segment generations",
    )
    segment_parser.add_argument("--source-id")
    segment_parser.add_argument("--batch-size", type=int, default=10)
    segment_parser.add_argument("--limit", type=int)
    segment_parser.add_argument("--retries", type=int, default=DEFAULT_RETRIES)

    embed_parser = subparsers.add_parser(
        "embed",
        help="Embed pending segments and activate completed generations",
    )
    embed_parser.add_argument("--model-version", default=DEFAULT_EMBEDDING_MODEL_VERSION)
    embed_parser.add_argument("--batch-size", type=int, default=100)
    embed_parser.add_argument("--limit", type=int)

    pipeline_parser = subparsers.add_parser(
        "pipeline",
        help="Run segmentation then embedding with defaults",
    )
    pipeline_parser.add_argument("--source-id")
    pipeline_parser.add_argument("--segment-batch-size", type=int, default=10)
    pipeline_parser.add_argument("--embed-batch-size", type=int, default=100)
    pipeline_parser.add_argument("--limit", type=int)
    pipeline_parser.add_argument("--model-version", default=DEFAULT_EMBEDDING_MODEL_VERSION)
    pipeline_parser.add_argument("--segment-retries", type=int, default=DEFAULT_RETRIES)

    args = parser.parse_args(argv)

    try:
        if args.command == "migrate":
            with connect() as conn:
                applied = migrate(conn)
            if applied:
                print("Applied migrations:")
                for filename in applied:
                    print(f"  {filename}")
            else:
                print("No migrations to apply.")
            return 0

        if args.command == "ingest-chatgpt":
            with connect() as conn:
                result = ingest_chatgpt_export(conn, args.path)
            print_ingest_result(result)
            return 0

        if args.command == "ingest-claude":
            with connect() as conn:
                result = ingest_claude_export(conn, args.path)
            print_ingest_result(result)
            return 0

        if args.command == "ingest-gemini":
            ingest_path = args.path_option or args.path
            if ingest_path is None:
                parser.error("ingest-gemini requires PATH or --path PATH")
            with connect() as conn:
                result = ingest_gemini_export(conn, ingest_path)
            print_ingest_result(result)
            return 0

        if args.command == "segment":
            with connect() as conn:
                invalidated = apply_reclassification_invalidations(conn)
                result = run_segment_batches(
                    conn,
                    batch_size=args.batch_size,
                    source_id=args.source_id,
                    limit=args.limit,
                    retries=args.retries,
                )
            print(
                "segment: "
                f"{result.created} segments created / {result.processed} parents processed "
                f"({result.skipped} skipped, {result.failed} failed)"
            )
            if invalidated:
                print(f"privacy invalidation: {invalidated} active segment(s) deactivated")
            if result.created:
                print(
                    "warning: standalone segment runs create inactive generations; "
                    "run `engram embed` before retrieval visibility",
                    file=sys.stderr,
                )
            return 0 if result.failed == 0 else 1

        if args.command == "embed":
            with connect() as conn:
                result = run_embed_batches(
                    conn,
                    batch_size=args.batch_size,
                    model_version=args.model_version,
                    limit=args.limit,
                    show_progress=True,
                )
            print_embed_result(result)
            return 0 if result.failed == 0 else 1

        if args.command == "pipeline":
            with connect() as conn:
                invalidated = apply_reclassification_invalidations(conn)
                segment_result = run_segment_batches(
                    conn,
                    batch_size=args.segment_batch_size,
                    source_id=args.source_id,
                    limit=args.limit,
                    retries=args.segment_retries,
                )
                embed_result = run_embed_batches(
                    conn,
                    batch_size=args.embed_batch_size,
                    model_version=args.model_version,
                    limit=args.limit,
                    show_progress=True,
                )
            print(
                "segment: "
                f"{segment_result.created} segments created / "
                f"{segment_result.processed} parents processed "
                f"({segment_result.skipped} skipped, {segment_result.failed} failed)"
            )
            if invalidated:
                print(f"privacy invalidation: {invalidated} active segment(s) deactivated")
            print_embed_result(embed_result)
            return 0 if segment_result.failed == 0 and embed_result.failed == 0 else 1
    except (ChatGPTIngestConflict, ClaudeIngestConflict, GeminiIngestConflict) as exc:
        print(f"ingest conflict: {exc}", file=sys.stderr)
        return 1

    parser.error(f"unknown command: {args.command}")
    return 2


def print_ingest_result(result) -> None:
    print(f"source_id={result.source_id}")
    print(
        "conversations: "
        f"{result.conversations_inserted} inserted / {result.conversations_seen} seen"
    )
    print(
        "messages: "
        f"{result.messages_inserted} inserted / {result.messages_seen} seen"
    )


def print_embed_result(result) -> None:
    print(
        "embed: "
        f"{result.created} segment embeddings created / {result.processed} segments processed "
        f"({result.cache_hits} cache hits, {result.activated} generations activated, "
        f"{result.failed} failed)"
    )


def run_segment_batches(
    conn,
    *,
    batch_size: int,
    source_id: str | None,
    limit: int | None,
    retries: int,
):
    totals = {"processed": 0, "created": 0, "skipped": 0, "failed": 0}
    while limit is None or totals["processed"] < limit:
        remaining = None if limit is None else limit - totals["processed"]
        batch_limit = batch_size if remaining is None else min(batch_size, remaining)
        result = segment_pending(
            conn,
            batch_size=batch_size,
            source_id=source_id,
            limit=batch_limit,
            retries=retries,
            progress_callback=print_segment_progress,
        )
        totals["processed"] += result.processed
        totals["created"] += result.created
        totals["skipped"] += result.skipped
        totals["failed"] += result.failed
        if result.processed == 0 or result.processed < batch_limit:
            break
    return SimpleNamespace(**totals)


def run_embed_batches(
    conn,
    *,
    batch_size: int,
    model_version: str,
    limit: int | None,
    show_progress: bool = False,
):
    totals = {"processed": 0, "created": 0, "cache_hits": 0, "activated": 0, "failed": 0}
    while limit is None or totals["processed"] < limit:
        remaining = None if limit is None else limit - totals["processed"]
        batch_limit = batch_size if remaining is None else min(batch_size, remaining)
        result = embed_pending_segments(
            conn,
            batch_size=batch_size,
            model_version=model_version,
            limit=batch_limit,
            progress_callback=print_embed_progress if show_progress else None,
        )
        totals["processed"] += result.processed
        totals["created"] += result.created
        totals["cache_hits"] += result.cache_hits
        totals["activated"] += result.activated
        totals["failed"] += result.failed
        if result.processed == 0 or result.processed < batch_limit:
            break
    return SimpleNamespace(**totals)


def print_segment_progress(event: str, payload: dict[str, Any]) -> None:
    if event == "segment_start":
        print(
            "segment "
            f"{payload['index']}/{payload['batch_size']} "
            f"conversation={payload['conversation_id']}",
            flush=True,
        )
        return
    elapsed = payload.get("elapsed_seconds", 0.0)
    if event == "segment_done":
        state = "noop" if payload.get("noop") else "done"
        print(
            "segment "
            f"{payload['index']}/{payload['batch_size']} {state} "
            f"conversation={payload['conversation_id']} "
            f"segments={payload['segments_inserted']} "
            f"windows={payload['windows_processed']} "
            f"skipped={payload['skipped_windows']} "
            f"elapsed={elapsed:.1f}s",
            flush=True,
        )
        return
    if event == "segment_failed":
        print(
            "segment "
            f"{payload['index']}/{payload['batch_size']} failed "
            f"conversation={payload['conversation_id']} "
            f"elapsed={elapsed:.1f}s",
            flush=True,
        )


def print_embed_progress(event: str, payload: dict[str, Any]) -> None:
    if event == "embed_start":
        if payload["index"] == 1 or payload["index"] % 25 == 0:
            print(
                "embed "
                f"{payload['index']}/{payload['batch_size']} "
                f"segment={payload['segment_id']}",
                flush=True,
            )
        return
    if event == "embed_done":
        if payload["index"] == payload["batch_size"] or payload["index"] % 25 == 0:
            print(
                "embed "
                f"{payload['index']}/{payload['batch_size']} done "
                f"cache_hit={payload['cache_hit']} "
                f"elapsed={payload['elapsed_seconds']:.1f}s",
                flush=True,
            )
        return
    if event == "embed_failed":
        print(
            "embed "
            f"{payload['index']}/{payload['batch_size']} failed "
            f"segment={payload['segment_id']} "
            f"elapsed={payload['elapsed_seconds']:.1f}s",
            flush=True,
        )


if __name__ == "__main__":
    raise SystemExit(main())
