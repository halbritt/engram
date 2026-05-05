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
from engram.consolidator import (
    CONSOLIDATOR_PROMPT_VERSION,
    active_beliefs_with_other_consolidator_version,
    apply_phase3_reclassification_invalidations,
    consolidate_beliefs,
)
from engram.db import connect
from engram.embedder import DEFAULT_EMBEDDING_MODEL_VERSION, embed_pending_segments
from engram.extractor import (
    EXTRACTION_PROMPT_VERSION,
    IkLlamaExtractorClient,
    PREDICATE_VOCABULARY,
    default_extractor_model_id,
    extract_claims_from_segment,
    extract_pending_claims,
    requeue_extraction_conversation,
    run_extractor_health_smoke,
)
from engram.gemini_export import IngestConflict as GeminiIngestConflict
from engram.gemini_export import ingest_gemini_export
from engram.migrations import migrate, migration_integrity_errors
from engram.progress import upsert_progress
from engram.segmenter import DEFAULT_RETRIES, apply_reclassification_invalidations, segment_pending


class Phase3SchemaPreflightError(RuntimeError):
    """Raised when Phase 3 pipeline prerequisites are not present in the DB."""


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

    extract_parser = subparsers.add_parser(
        "extract",
        help="Extract atomic claims from active segments",
    )
    extract_parser.add_argument("--batch-size", type=int, default=50)
    extract_parser.add_argument("--limit", type=int)
    extract_parser.add_argument("--segment-id")
    extract_parser.add_argument("--conversation-id")
    extract_parser.add_argument("--requeue", action="store_true")
    extract_parser.add_argument("--prompt-version", default=EXTRACTION_PROMPT_VERSION)

    consolidate_parser = subparsers.add_parser(
        "consolidate",
        help="Consolidate claims into bitemporal beliefs",
    )
    consolidate_parser.add_argument("--batch-size", type=int, default=100)
    consolidate_parser.add_argument("--limit", type=int)
    consolidate_parser.add_argument("--conversation-id")
    consolidate_parser.add_argument("--rebuild", action="store_true")
    consolidate_parser.add_argument("--prompt-version", default=CONSOLIDATOR_PROMPT_VERSION)

    pipeline_parser = subparsers.add_parser(
        "pipeline",
        help="Run Phase 1/2 memory pipeline: segment -> embed",
    )
    pipeline_parser.add_argument("--source-id")
    pipeline_parser.add_argument("--segment-batch-size", type=int, default=10)
    pipeline_parser.add_argument("--embed-batch-size", type=int, default=100)
    pipeline_parser.add_argument("--limit", type=int)
    pipeline_parser.add_argument("--model-version", default=DEFAULT_EMBEDDING_MODEL_VERSION)
    pipeline_parser.add_argument("--segment-retries", type=int, default=DEFAULT_RETRIES)

    pipeline3_parser = subparsers.add_parser(
        "pipeline-3",
        help="Run explicit Phase 3 pipeline: extract -> consolidate",
    )
    pipeline3_parser.add_argument("--extract-batch-size", type=int, default=10)
    pipeline3_parser.add_argument("--consolidate-batch-size", type=int, default=10)
    pipeline3_parser.add_argument("--limit", type=int)

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

        if args.command == "extract":
            with connect() as conn:
                apply_phase3_reclassification_invalidations(conn)
                if args.requeue:
                    if not args.conversation_id:
                        parser.error("extract --requeue requires --conversation-id UUID")
                    requeued = requeue_extraction_conversation(conn, args.conversation_id)
                    conn.commit()
                    print(f"extract requeue: {requeued} in-flight extraction(s) marked failed")
                if args.segment_id:
                    model_id = default_extractor_model_id()
                    extractor_client = IkLlamaExtractorClient()
                    run_extractor_health_smoke(extractor_client, model_id=model_id)
                    result_one = extract_claims_from_segment(
                        conn,
                        args.segment_id,
                        model_version=model_id,
                        prompt_version=args.prompt_version,
                        client=extractor_client,
                    )
                    run_extractor_health_smoke(extractor_client, model_id=model_id)
                    conn.commit()
                    result = SimpleNamespace(
                        processed=1,
                        created=result_one.claim_count,
                        skipped=1 if result_one.noop else 0,
                        failed=1 if result_one.status == "failed" else 0,
                    )
                else:
                    result = run_extract_batches(
                        conn,
                        batch_size=args.batch_size,
                        prompt_version=args.prompt_version,
                        limit=args.limit,
                        conversation_id=args.conversation_id,
                    )
            print(
                "extract: "
                f"{result.created} claims created / {result.processed} segments processed "
                f"({result.skipped} skipped, {result.failed} failed)"
            )
            return 0 if result.failed == 0 else 1

        if args.command == "consolidate":
            with connect() as conn:
                apply_phase3_reclassification_invalidations(conn)
                result = run_consolidate_batches(
                    conn,
                    batch_size=args.batch_size,
                    prompt_version=args.prompt_version,
                    limit=args.limit,
                    conversation_id=args.conversation_id,
                    rebuild=args.rebuild,
                )
            print(
                "consolidate: "
                f"{result.processed} groups processed / "
                f"{result.created} beliefs created / "
                f"{result.superseded} superseded / "
                f"{result.contradictions} contradictions"
            )
            return 0

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
            return 0 if (
                segment_result.failed == 0 and
                embed_result.failed == 0
            ) else 1

        if args.command == "pipeline-3":
            with connect() as conn:
                phase3_schema_preflight(conn)
                apply_phase3_reclassification_invalidations(conn)
                other_versions = active_beliefs_with_other_consolidator_version(conn)
                if other_versions:
                    print(
                        "warning: active beliefs exist for a different consolidator prompt_version",
                        file=sys.stderr,
                    )
                conversations = fetch_phase3_conversation_batch(conn, args.limit)
                model_id = None
                extractor_client = None
                if conversations:
                    model_id = default_extractor_model_id()
                    extractor_client = IkLlamaExtractorClient()
                    run_extractor_health_smoke(extractor_client, model_id=model_id)
                totals = {
                    "extract_processed": 0,
                    "extract_created": 0,
                    "extract_failed": 0,
                    "consolidate_processed": 0,
                    "consolidate_skipped": 0,
                    "beliefs_created": 0,
                    "beliefs_superseded": 0,
                    "contradictions": 0,
                }
                for conversation_id in conversations:
                    extract_result = run_extract_batches(
                        conn,
                        batch_size=args.extract_batch_size,
                        limit=None,
                        conversation_id=conversation_id,
                        model_version=model_id,
                        client=extractor_client,
                        health_smoke=False,
                    )
                    totals["extract_processed"] += extract_result.processed
                    totals["extract_created"] += extract_result.created
                    totals["extract_failed"] += extract_result.failed
                    if extract_result.failed:
                        totals["consolidate_skipped"] += 1
                        skip_reason = (
                            f"skipped after {extract_result.failed} extraction failure(s)"
                        )
                        upsert_progress(
                            conn,
                            stage="consolidator",
                            scope=f"conversation:{conversation_id}",
                            status="failed",
                            position={
                                "conversation_id": conversation_id,
                                "skipped_after_extraction_failures": extract_result.failed,
                            },
                            last_error=skip_reason,
                            increment_error=True,
                        )
                        print(
                            "consolidate skipped "
                            f"conversation={conversation_id} "
                            f"after {extract_result.failed} extraction failure(s)",
                            file=sys.stderr,
                            flush=True,
                        )
                        continue
                    consolidate_result = run_consolidate_batches(
                        conn,
                        batch_size=args.consolidate_batch_size,
                        limit=1,
                        conversation_id=conversation_id,
                    )
                    totals["consolidate_processed"] += consolidate_result.processed
                    totals["beliefs_created"] += consolidate_result.created
                    totals["beliefs_superseded"] += consolidate_result.superseded
                    totals["contradictions"] += consolidate_result.contradictions
                if conversations:
                    run_extractor_health_smoke(extractor_client, model_id=model_id)
                conn.commit()
            print(
                "extract: "
                f"{totals['extract_created']} claims created / "
                f"{totals['extract_processed']} segments processed "
                f"({totals['extract_failed']} failed)"
            )
            print(
                "consolidate: "
                f"{totals['consolidate_processed']} conversations processed / "
                f"{totals['consolidate_skipped']} skipped / "
                f"{totals['beliefs_created']} beliefs created / "
                f"{totals['beliefs_superseded']} superseded / "
                f"{totals['contradictions']} contradictions"
            )
            return 0 if totals["extract_failed"] == 0 else 1
    except (ChatGPTIngestConflict, ClaudeIngestConflict, GeminiIngestConflict) as exc:
        print(f"ingest conflict: {exc}", file=sys.stderr)
        return 1
    except Phase3SchemaPreflightError as exc:
        print(f"phase3 preflight failed: {exc}", file=sys.stderr)
        return 1

    parser.error(f"unknown command: {args.command}")
    return 2


def phase3_schema_preflight(conn) -> None:
    errors = migration_integrity_errors(conn)
    schema_migrations_exists = (
        conn.execute("SELECT to_regclass('public.schema_migrations')").fetchone()[0]
        is not None
    )
    if schema_migrations_exists:
        phase3_migration = conn.execute(
            """
            SELECT checksum IS NOT NULL
            FROM schema_migrations
            WHERE filename = '006_claims_beliefs.sql'
            """
        ).fetchone()
        if phase3_migration is None:
            errors.append("006_claims_beliefs.sql is not recorded in schema_migrations")
        elif phase3_migration[0] is not True:
            errors.append("006_claims_beliefs.sql checksum is missing")

    required_tables = [
        "predicate_vocabulary",
        "claim_extractions",
        "claims",
        "beliefs",
        "belief_audit",
        "contradictions",
    ]
    existing_tables: set[str] = set()
    for table in required_tables:
        exists = conn.execute("SELECT to_regclass(%s)", (f"public.{table}",)).fetchone()[0]
        if exists is None:
            errors.append(f"{table} table is missing")
        else:
            existing_tables.add(table)
    required_columns = {
        "predicate_vocabulary": [
            "predicate",
            "stability_class",
            "cardinality_class",
            "object_kind",
            "group_object_keys",
            "required_object_keys",
        ],
        "claims": [
            "extraction_id",
            "subject_normalized",
            "predicate",
            "object_text",
            "object_json",
            "evidence_message_ids",
        ],
        "beliefs": [
            "subject_normalized",
            "cardinality_class",
            "group_object_key",
            "closed_at",
            "claim_ids",
        ],
        "belief_audit": ["evidence_message_ids", "request_uuid"],
        "contradictions": ["detection_kind", "resolution_status"],
    }
    for table, columns in required_columns.items():
        existing_columns = {
            row[0]
            for row in conn.execute(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = %s
                """,
                (table,),
            ).fetchall()
        }
        for column in columns:
            if column not in existing_columns:
                errors.append(f"{table}.{column} is missing")
    _check_phase3_predicate_vocabulary(conn, existing_tables, errors)
    _check_phase3_indexes(conn, errors)
    _check_phase3_functions(conn, errors)
    _check_phase3_triggers(conn, errors)
    if errors:
        raise Phase3SchemaPreflightError("; ".join(errors))


def _check_phase3_predicate_vocabulary(
    conn,
    existing_tables: set[str],
    errors: list[str],
) -> None:
    if "predicate_vocabulary" not in existing_tables:
        return

    actual = {
        row[0]: {
            "predicate": row[0],
            "stability_class": row[1],
            "cardinality_class": row[2],
            "object_kind": row[3],
            "group_object_keys": list(row[4]),
            "required_object_keys": list(row[5]),
        }
        for row in conn.execute(
            """
            SELECT predicate, stability_class, cardinality_class, object_kind,
                   group_object_keys, required_object_keys
            FROM predicate_vocabulary
            """
        ).fetchall()
    }
    expected = {row["predicate"]: row for row in PREDICATE_VOCABULARY}

    for predicate in sorted(expected.keys() - actual.keys()):
        errors.append(f"predicate_vocabulary missing predicate: {predicate}")
    for predicate in sorted(actual.keys() - expected.keys()):
        errors.append(f"predicate_vocabulary has unexpected predicate: {predicate}")
    for predicate in sorted(expected.keys() & actual.keys()):
        expected_row = expected[predicate]
        actual_row = actual[predicate]
        for key in [
            "stability_class",
            "cardinality_class",
            "object_kind",
            "group_object_keys",
            "required_object_keys",
        ]:
            if actual_row[key] != expected_row[key]:
                errors.append(
                    "predicate_vocabulary mismatch for "
                    f"{predicate}.{key}: {actual_row[key]!r} != {expected_row[key]!r}"
                )


def _check_phase3_indexes(conn, errors: list[str]) -> None:
    required_indexes = {
        "claim_extractions_active_unique_idx": {
            "table": "claim_extractions",
            "fragments": [
                "CREATE UNIQUE INDEX",
                "ON public.claim_extractions",
                "(segment_id, extraction_prompt_version, extraction_model_version)",
                "extracting",
                "extracted",
            ],
        },
        "beliefs_active_group_unique_idx": {
            "table": "beliefs",
            "fragments": [
                "CREATE UNIQUE INDEX",
                "ON public.beliefs",
                "(subject_normalized, predicate, group_object_key)",
                "valid_to IS NULL",
                "candidate",
                "provisional",
                "accepted",
            ],
        },
    }
    for index_name, spec in required_indexes.items():
        row = conn.execute(
            """
            SELECT t.relname, i.indisunique, i.indisvalid, pg_get_indexdef(i.indexrelid)
            FROM pg_index i
            JOIN pg_class index_class ON index_class.oid = i.indexrelid
            JOIN pg_class t ON t.oid = i.indrelid
            WHERE index_class.oid = to_regclass(%s)
            """,
            (f"public.{index_name}",),
        ).fetchone()
        if row is None:
            errors.append(f"{index_name} index is missing")
            continue
        table_name, is_unique, is_valid, definition = row
        if table_name != spec["table"]:
            errors.append(f"{index_name} index is on {table_name}, expected {spec['table']}")
        if is_unique is not True:
            errors.append(f"{index_name} index is not unique")
        if is_valid is not True:
            errors.append(f"{index_name} index is not valid")
        for fragment in spec["fragments"]:
            if fragment not in definition:
                errors.append(f"{index_name} index definition missing {fragment!r}")


def _check_phase3_functions(conn, errors: list[str]) -> None:
    required_functions = [
        "engram_normalize_subject(text)",
        "engram_normalize_group_object_value(text)",
        "fn_claim_extractions_mutation_guard()",
        "fn_claims_insert_prepare_validate()",
        "fn_claims_insert_only()",
        "fn_beliefs_prepare_validate()",
        "fn_belief_audit_append_only()",
        "fn_contradictions_mutation_guard()",
    ]
    for function_signature in required_functions:
        exists = conn.execute(
            "SELECT to_regprocedure(%s)",
            (f"public.{function_signature}",),
        ).fetchone()[0]
        if exists is None:
            errors.append(f"{function_signature} function is missing")


def _check_phase3_triggers(conn, errors: list[str]) -> None:
    required_triggers = {
        "claim_extractions_mutation_guard": {
            "table": "claim_extractions",
            "function": "fn_claim_extractions_mutation_guard",
            "fragments": ["BEFORE DELETE OR UPDATE", "ON public.claim_extractions"],
        },
        "claims_insert_prepare_validate": {
            "table": "claims",
            "function": "fn_claims_insert_prepare_validate",
            "fragments": ["BEFORE INSERT", "ON public.claims"],
        },
        "claims_insert_only": {
            "table": "claims",
            "function": "fn_claims_insert_only",
            "fragments": ["BEFORE DELETE OR UPDATE", "ON public.claims"],
        },
        "beliefs_prepare_validate": {
            "table": "beliefs",
            "function": "fn_beliefs_prepare_validate",
            "fragments": ["BEFORE INSERT OR DELETE OR UPDATE", "ON public.beliefs"],
        },
        "belief_audit_append_only": {
            "table": "belief_audit",
            "function": "fn_belief_audit_append_only",
            "fragments": ["BEFORE DELETE OR UPDATE", "ON public.belief_audit"],
        },
        "contradictions_mutation_guard": {
            "table": "contradictions",
            "function": "fn_contradictions_mutation_guard",
            "fragments": ["BEFORE DELETE OR UPDATE", "ON public.contradictions"],
        },
    }
    for trigger_name, spec in required_triggers.items():
        row = conn.execute(
            """
            SELECT c.relname, p.proname, t.tgenabled, pg_get_triggerdef(t.oid)
            FROM pg_trigger t
            JOIN pg_class c ON c.oid = t.tgrelid
            JOIN pg_proc p ON p.oid = t.tgfoid
            WHERE NOT t.tgisinternal
              AND t.tgname = %s
            """,
            (trigger_name,),
        ).fetchone()
        if row is None:
            errors.append(f"{trigger_name} trigger is missing")
            continue
        table_name, function_name, enabled_state, definition = row
        if table_name != spec["table"]:
            errors.append(
                f"{trigger_name} trigger is on {table_name}, expected {spec['table']}"
            )
        if function_name != spec["function"]:
            errors.append(
                f"{trigger_name} trigger calls {function_name}, expected {spec['function']}"
            )
        if enabled_state == "D":
            errors.append(f"{trigger_name} trigger is disabled")
        for fragment in spec["fragments"]:
            if fragment not in definition:
                errors.append(f"{trigger_name} trigger definition missing {fragment!r}")


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
        conn.commit()
        totals["processed"] += result.processed
        totals["created"] += result.created
        totals["skipped"] += result.skipped
        totals["failed"] += result.failed
        if result.failed:
            break
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
        conn.commit()
        totals["processed"] += result.processed
        totals["created"] += result.created
        totals["cache_hits"] += result.cache_hits
        totals["activated"] += result.activated
        totals["failed"] += result.failed
        if result.processed == 0 or result.processed < batch_limit:
            break
    return SimpleNamespace(**totals)


def run_extract_batches(
    conn,
    *,
    batch_size: int,
    prompt_version: str = EXTRACTION_PROMPT_VERSION,
    limit: int | None,
    conversation_id: str | None = None,
    model_version: str | None = None,
    client=None,
    health_smoke: bool = True,
):
    totals = {"processed": 0, "created": 0, "skipped": 0, "failed": 0}
    model_id = model_version
    extractor_client = client
    if health_smoke:
        model_id = model_id or default_extractor_model_id()
        extractor_client = extractor_client or IkLlamaExtractorClient()
        run_extractor_health_smoke(extractor_client, model_id=model_id)
    while limit is None or totals["processed"] < limit:
        remaining = None if limit is None else limit - totals["processed"]
        batch_limit = batch_size if remaining is None else min(batch_size, remaining)
        result = extract_pending_claims(
            conn,
            batch_size=batch_size,
            model_version=model_id,
            prompt_version=prompt_version,
            limit=batch_limit,
            conversation_id=conversation_id,
            client=extractor_client,
            progress_callback=print_extract_progress,
        )
        conn.commit()
        totals["processed"] += result.processed
        totals["created"] += result.created
        totals["skipped"] += result.skipped
        totals["failed"] += result.failed
        if result.failed:
            break
        if result.processed == 0 or result.processed < batch_limit:
            break
    if health_smoke:
        run_extractor_health_smoke(extractor_client, model_id=model_id)
    return SimpleNamespace(**totals)


def run_consolidate_batches(
    conn,
    *,
    batch_size: int,
    prompt_version: str = CONSOLIDATOR_PROMPT_VERSION,
    limit: int | None,
    conversation_id: str | None = None,
    rebuild: bool = False,
):
    totals = {"processed": 0, "created": 0, "superseded": 0, "contradictions": 0}
    while limit is None or totals["processed"] < limit:
        remaining = None if limit is None else limit - totals["processed"]
        batch_limit = batch_size if remaining is None else min(batch_size, remaining)
        result = consolidate_beliefs(
            conn,
            batch_size=batch_size,
            prompt_version=prompt_version,
            limit=batch_limit,
            conversation_id=conversation_id,
            rebuild=rebuild and totals["processed"] == 0,
            progress_callback=print_consolidate_progress,
        )
        conn.commit()
        totals["processed"] += result.processed
        totals["created"] += result.created
        totals["superseded"] += result.superseded
        totals["contradictions"] += result.contradictions
        if result.processed == 0 or result.processed < batch_limit:
            break
    return SimpleNamespace(**totals)


def fetch_phase3_conversation_batch(conn, limit: int | None) -> list[str]:
    rows = conn.execute(
        """
        SELECT DISTINCT s.conversation_id::text
        FROM segments s
        JOIN segment_generations sg ON sg.id = s.generation_id
        WHERE s.is_active = true
          AND sg.status = 'active'
          AND s.source_kind IN ('chatgpt', 'claude', 'gemini')
          AND s.conversation_id IS NOT NULL
        ORDER BY s.conversation_id::text
        LIMIT %s
        """,
        (limit,),
    ).fetchall()
    return [row[0] for row in rows]


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
        return
    if event == "segment_service_unavailable":
        print(
            "segment "
            f"{payload['index']}/{payload['batch_size']} service_unavailable "
            f"conversation={payload['conversation_id']} "
            f"elapsed={elapsed:.1f}s",
            flush=True,
        )
        return
    if event == "segment_probe_failed":
        print(
            "segment probe failed "
            f"elapsed={elapsed:.1f}s "
            f"error={payload['error']}",
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


def print_extract_progress(event: str, payload: dict[str, Any]) -> None:
    if event == "extract_start":
        print(
            f"extract segment={payload['segment_id']}",
            flush=True,
        )
        return
    if event == "extract_done":
        print(
            f"extract segment={payload['segment_id']} done "
            f"claims={payload['claim_count']} "
            f"elapsed={payload['elapsed']:.1f}s",
            flush=True,
        )
        return
    if event == "extract_failed":
        print(
            f"extract segment={payload['segment_id']} failed "
            f"elapsed={payload['elapsed']:.1f}s",
            flush=True,
        )


def print_consolidate_progress(event: str, payload: dict[str, Any]) -> None:
    if event == "consolidate_start":
        print(
            f"consolidate conversation={payload['conversation_id']}",
            flush=True,
        )
        return
    if event == "consolidate_done":
        print(
            f"consolidate conversation={payload['conversation_id']} done "
            f"created={payload['beliefs_created']} "
            f"superseded={payload['beliefs_superseded']} "
            f"contradictions={payload['contradictions_detected']} "
            f"elapsed={payload['elapsed']:.1f}s",
            flush=True,
        )
        return
    if event == "consolidate_failed":
        print(
            f"consolidate failed: {payload['error']}",
            flush=True,
        )


if __name__ == "__main__":
    raise SystemExit(main())
