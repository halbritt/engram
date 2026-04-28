from __future__ import annotations

import argparse
import sys
from pathlib import Path

from engram.chatgpt_export import IngestConflict, ingest_chatgpt_export
from engram.db import connect
from engram.migrations import migrate


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="engram")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("migrate", help="Apply SQL migrations")

    ingest_parser = subparsers.add_parser(
        "ingest-chatgpt",
        help="Ingest a local ChatGPT export directory",
    )
    ingest_parser.add_argument("path", type=Path)

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
            print(f"source_id={result.source_id}")
            print(
                "conversations: "
                f"{result.conversations_inserted} inserted / {result.conversations_seen} seen"
            )
            print(
                "messages: "
                f"{result.messages_inserted} inserted / {result.messages_seen} seen"
            )
            return 0
    except IngestConflict as exc:
        print(f"ingest conflict: {exc}", file=sys.stderr)
        return 1

    parser.error(f"unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
