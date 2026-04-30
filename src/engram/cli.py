from __future__ import annotations

import argparse
import sys
from pathlib import Path

from engram.chatgpt_export import IngestConflict as ChatGPTIngestConflict
from engram.chatgpt_export import ingest_chatgpt_export
from engram.claude_export import IngestConflict as ClaudeIngestConflict
from engram.claude_export import ingest_claude_export
from engram.db import connect
from engram.gemini_export import IngestConflict as GeminiIngestConflict
from engram.gemini_export import ingest_gemini_export
from engram.migrations import migrate


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


if __name__ == "__main__":
    raise SystemExit(main())
