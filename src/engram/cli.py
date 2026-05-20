from __future__ import annotations

import argparse
import dataclasses
import inspect
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from uuid import UUID

from engram.build_artifact_import import import_build_artifacts
from engram.chatgpt_export import IngestConflict as ChatGPTIngestConflict
from engram.chatgpt_export import ingest_chatgpt_export
from engram.claim_grounding import ClaimGroundingError, ground_claim_entity_locally
from engram.claim_grounding_runtime import (
    record_claim_grounding_approved_grant,
    record_claim_grounding_denied_grant,
    record_claim_grounding_draft_grant,
    record_claim_grounding_request,
    record_claim_grounding_revoked_grant,
)
from engram.claude_export import IngestConflict as ClaudeIngestConflict
from engram.claude_export import ingest_claude_export
from engram.consolidator import (
    CONSOLIDATOR_PROMPT_VERSION,
    active_beliefs_with_other_consolidator_version,
    apply_phase3_reclassification_invalidations,
    consolidate_beliefs,
)
from engram.context import ContextForRequest, context_for
from engram.context_eval import (
    CONTEXT_EVAL_DATASET_ENV_VAR,
    ContextCompileRequest,
    ContextEvalError,
    resolve_context_eval_gold_set_path,
    run_context_eval_file,
    write_json_report,
    write_markdown_summary,
)
from engram.db import connect
from engram.embedder import DEFAULT_EMBEDDING_MODEL_VERSION, embed_pending_segments
from engram.evidence import refresh_evidence_reference_index
from engram.extractor import (
    DEFAULT_EXTRACTION_CONCURRENCY,
    EXTRACTION_PROMPT_VERSION,
    PREDICATE_VOCABULARY,
    IkLlamaExtractorClient,
    ReExtractError,
    ReExtractResult,
    default_extractor_model_id,
    extract_claims_from_segment,
    extract_pending_claims,
    extract_pending_claims_concurrently,
    re_extract,
    requeue_extraction_conversation,
    run_extractor_health_smoke,
)
from engram.gemini_export import IngestConflict as GeminiIngestConflict
from engram.gemini_export import ingest_gemini_export
from engram.git_import import import_git_repo
from engram.interview import (
    SAMPLER_ID as INTERVIEW_SAMPLER_ID,
)
from engram.interview import (
    SAMPLER_VERSION as INTERVIEW_SAMPLER_VERSION,
)
from engram.interview import (
    GoldLabelSampler,
    GoldLabelStorageError,
    GoldLabelVerdictError,
    InterviewAgent,
    SessionTarget,
    get_active_learning_signal_version,
    insert_active_learning_event,
    insert_session,
    insert_session_targets,
    list_sessions,
    mark_session_completed,
    session_target_to_sampled,
    unanswered_session_targets,
)
from engram.interview.render import (
    VERDICT_ALIAS,
    VERDICT_PROMPT,
    VERDICT_VALID,
    fetch_target_display,
    format_evidence_dates,
    format_evidence_excerpts,
    format_header,
    format_summary_line,
    pick_question,
    rationale_prompt_for,
)
from engram.markdown_import import import_markdown_tree
from engram.memory import MemoryService
from engram.migrations import migrate, migration_integrity_errors
from engram.no_egress import NoEgressError, probe_enforcement, run_under_no_egress
from engram.phase4 import (
    Phase4SchemaPreflightError,
    accept_belief,
    build_deterministic_entities,
    correct_belief,
    promote_to_pinned,
    refresh_current_beliefs,
    reject_review_belief,
    run_phase4_smoke,
)
from engram.policy import decide_local_release
from engram.progress import upsert_progress
from engram.segmenter import DEFAULT_RETRIES, apply_reclassification_invalidations, segment_pending
from engram.striatum_ingest import (
    IngestConflict as StriatumIngestConflict,
)
from engram.striatum_ingest import (
    StriatumBundleError,
    ingest_striatum_bundle,
)


class Phase3SchemaPreflightError(RuntimeError):
    """Raised when Phase 3 pipeline prerequisites are not present in the DB."""


class EntityGroundingCliError(RuntimeError):
    """Raised when the RFC 0054/0055 CLI integration cannot dispatch."""


AMBIGUOUS_PIPELINE_COMMAND = """ambiguous command: pipeline
Use one of:
  engram phase2 run
  engram phase3 run
  engram phase4 smoke"""


_SECRET_OUTPUT_KEY_FRAGMENTS: tuple[str, ...] = (
    "api_key",
    "apikey",
    "authorization",
    "bearer",
    "credential",
    "password",
    "secret",
    "token",
)
ENTITY_GROUNDING_BROKER_DATABASE_URL_ENV = "ENGRAM_ENTITY_GROUNDING_BROKER_DATABASE_URL"


def warn_legacy_command(invoked_command: str, replacement: str | None) -> None:
    if replacement is None:
        return
    print(
        f"warning: `engram {invoked_command}` is deprecated; use `engram {replacement}`",
        file=sys.stderr,
    )


_INTERVIEW_STRATA_KEYS: frozenset[str] = frozenset(
    {"stability_class", "conf_band", "recency_band", "belief_status"}
)


def parse_interview_strata_expr(value: str | None) -> dict[str, str]:
    """Parse ``key=value,key=value`` strata filters for interview sampling."""
    if value is None or value.strip() == "":
        return {}
    filters: dict[str, str] = {}
    for part in value.split(","):
        item = part.strip()
        if not item:
            continue
        key, sep, raw = item.partition("=")
        key = key.strip()
        parsed = raw.strip()
        if sep != "=" or not key or not parsed:
            raise argparse.ArgumentTypeError(
                "strata must use key=value pairs, e.g. stability_class=identity"
            )
        if key not in _INTERVIEW_STRATA_KEYS:
            allowed = ", ".join(sorted(_INTERVIEW_STRATA_KEYS))
            raise argparse.ArgumentTypeError(f"unknown strata key {key!r}; allowed keys: {allowed}")
        filters[key] = parsed
    return filters


def _parse_cli_datetime(value: str) -> datetime:
    """Parse an RFC3339-ish timestamp for CLI filters."""
    normalized = value.strip()
    if normalized.endswith("Z"):
        normalized = f"{normalized[:-1]}+00:00"
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise ValueError("expected RFC3339 timestamp, e.g. 2026-05-13T12:00:00Z") from exc
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed


def read_context_query(
    query: str | None,
    query_file: Path | None,
    parser: argparse.ArgumentParser,
) -> str:
    """Resolve a context query from --query or --query-file."""
    if query is not None and query_file is not None:
        parser.error("context-for accepts either --query or --query-file, not both")
    if query_file is not None:
        query_text = query_file.read_text(encoding="utf-8")
    elif query is not None:
        query_text = query
    else:
        parser.error("context-for requires --query or --query-file")
    query_text = query_text.strip()
    if query_text == "":
        parser.error("context query must not be empty")
    return query_text


def read_claim_grounding_request_file(
    path: Path,
    parser: argparse.ArgumentParser,
) -> dict[str, object]:
    """Read a JSON object for RFC 0053 claim-grounding commands."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        parser.error("--request-json must contain a JSON object")
    if not all(isinstance(key, str) for key in payload):
        parser.error("--request-json object keys must be strings")
    return payload


def list_claim_grounding_grants(
    conn: Any,
    *,
    tenant_id: str,
    corpus_id: str,
    status: str,
    limit: int,
) -> list[dict[str, Any]]:
    """Return operator-visible RFC 0053 grant lifecycle rows."""
    bounded_limit = max(1, min(limit, 100))
    rows = conn.execute(
        """
        SELECT
            g.id::text,
            r.id::text,
            r.request_payload->>'request_id',
            g.grant_payload->>'grant_id',
            g.grant_status,
            g.tenant_id,
            g.corpus_id,
            g.surface_form,
            g.search_query,
            g.query_text_class,
            g.query_privacy_tier,
            g.allowed_network_targets,
            g.granted_by,
            g.granted_at,
            g.expires_at,
            g.revoked_at,
            r.extraction_run_id,
            r.source_refs,
            g.created_at
        FROM claim_grounding_grants g
        LEFT JOIN claim_grounding_requests r ON r.id = g.request_id
        WHERE g.tenant_id = %s
          AND g.corpus_id = %s
          AND (%s = 'all' OR g.grant_status = %s)
        ORDER BY g.created_at DESC, g.id DESC
        LIMIT %s
        """,
        (tenant_id, corpus_id, status, status, bounded_limit),
    ).fetchall()
    return [
        {
            "grant_record_id": row[0],
            "request_record_id": row[1],
            "request_id": row[2],
            "grant_id": row[3],
            "status": row[4],
            "tenant_id": row[5],
            "corpus_id": row[6],
            "surface_form": row[7],
            "search_query": row[8],
            "query_text_class": row[9],
            "query_privacy_tier": row[10],
            "allowed_network_targets": list(row[11] or []),
            "granted_by": row[12],
            "granted_at": _json_datetime(row[13]),
            "expires_at": _json_datetime(row[14]),
            "revoked_at": _json_datetime(row[15]),
            "extraction_run_id": row[16],
            "source_refs": row[17] or [],
            "created_at": _json_datetime(row[18]),
        }
        for row in rows
    ]


def load_claim_grounding_request_for_grant(
    conn: Any,
    *,
    request_id: str,
    grant_id: str,
    tenant_id: str,
    corpus_id: str,
    parser: argparse.ArgumentParser,
) -> dict[str, object]:
    """Load the latest persisted request payload for a grant lifecycle action."""
    row = conn.execute(
        """
        SELECT request_payload
        FROM claim_grounding_requests
        WHERE request_payload->>'request_id' = %s
          AND tenant_id = %s
          AND corpus_id = %s
        ORDER BY created_at DESC, id DESC
        LIMIT 1
        """,
        (request_id, tenant_id, corpus_id),
    ).fetchone()
    if row is None:
        parser.error(f'no persisted claim-grounding request found for request_id "{request_id}"')
    payload = row[0]
    if not isinstance(payload, dict):
        parser.error(f'persisted claim-grounding request "{request_id}" is not a JSON object')
    network_grant = payload.get("network_grant")
    if not isinstance(network_grant, dict):
        parser.error(f'claim-grounding request "{request_id}" has no network_grant')
    if network_grant.get("grant_id") != grant_id:
        parser.error(
            f'claim-grounding request "{request_id}" has grant_id '
            f'"{network_grant.get("grant_id")}", not "{grant_id}"'
        )
    return payload


def approved_claim_grounding_request_payload(
    payload: dict[str, object],
    *,
    granted_by: str,
) -> dict[str, object]:
    """Stamp an operator approval actor/time onto a request payload copy."""
    copied = dict(payload)
    network_grant = copied.get("network_grant")
    if not isinstance(network_grant, dict):
        return copied
    copied["network_grant"] = {
        **network_grant,
        "granted_by": granted_by,
        "granted_at": _rfc3339_now(),
    }
    return copied


def claim_grounding_lifecycle_output(
    *,
    action: str,
    record: Any,
    request_payload: dict[str, object],
) -> dict[str, object]:
    """Return a compact audit payload after appending a grant lifecycle row."""
    network_grant = request_payload.get("network_grant")
    grant_payload = network_grant if isinstance(network_grant, dict) else {}
    return {
        "action": action,
        "status": record.status,
        "request_id": record.request_id,
        "grant_id": record.grant_id,
        "grant_record_id": str(record.id),
        "display": {
            "tenant_id": request_payload.get("tenant_id"),
            "corpus_id": request_payload.get("corpus_id"),
            "surface_form": request_payload.get("surface_form"),
            "search_query": grant_payload.get("search_query"),
            "query_text_class": grant_payload.get("query_text_class"),
            "query_privacy_tier": grant_payload.get("query_privacy_tier"),
            "allowed_network_targets": grant_payload.get("allowed_network_targets"),
            "extraction_run_id": request_payload.get("extraction_run_id"),
            "source_refs": request_payload.get("source_refs"),
        },
    }


def run_entity_grounding_draft(
    conn: Any,
    *,
    tenant_id: str,
    corpus_id: str,
    limit: int,
    entity_id: str | None,
) -> Any:
    """Dispatch RFC 0054 draft workflow through the implementation module."""
    try:
        from engram import entity_grounding_workflow
    except ModuleNotFoundError as exc:
        if exc.name == "engram.entity_grounding_workflow":
            raise EntityGroundingCliError(
                "entity-grounding draft implementation is unavailable"
            ) from exc
        raise
    worker = _first_callable(
        entity_grounding_workflow,
        (
            "draft_entity_grounding",
            "draft_entity_grounding_batch",
            "run_entity_grounding_draft",
            "run_entity_grounding_batch",
        ),
        "entity-grounding draft",
    )
    return _call_worker_with_supported_kwargs(
        worker,
        conn,
        {
            "tenant_id": tenant_id,
            "corpus_id": corpus_id,
            "limit": limit,
            "entity_id": entity_id,
        },
    )


def run_entity_grounding_process_approved(
    conn: Any,
    *,
    tenant_id: str,
    corpus_id: str,
    limit: int,
    request_id: str | None,
    grant_id: str | None,
    target_adapter: str | None,
) -> Any:
    """Dispatch RFC 0055 approved-grant materialization through its module."""
    try:
        from engram import entity_grounding_materialization
    except ModuleNotFoundError as exc:
        if exc.name == "engram.entity_grounding_materialization":
            raise EntityGroundingCliError(
                "entity-grounding process-approved implementation is unavailable"
            ) from exc
        raise
    worker = _first_callable(
        entity_grounding_materialization,
        (
            "process_approved_entity_grounding",
            "process_approved_entity_grounding_grants",
            "process_approved_grounding_grants",
            "run_entity_grounding_process_approved",
        ),
        "entity-grounding process-approved",
    )
    return _call_worker_with_supported_kwargs(
        worker,
        conn,
        {
            "tenant_id": tenant_id,
            "corpus_id": corpus_id,
            "limit": limit,
            "request_id": request_id,
            "grant_id": grant_id,
            "target_adapter": target_adapter,
        },
    )


def run_entity_grounding_broker_daemon(
    *,
    broker_database_url: str,
    tenant_id: str,
    corpus_id: str,
    limit: int | None,
    interval_seconds: float | None,
    target_adapter: str | None,
    max_iterations: int | None,
) -> Any:
    """Dispatch the local RFC 0055 broker daemon workflow."""
    try:
        from engram import entity_grounding_daemon
    except ModuleNotFoundError as exc:
        if exc.name == "engram.entity_grounding_daemon":
            raise EntityGroundingCliError(
                "entity-grounding broker-daemon implementation is unavailable"
            ) from exc
        raise
    worker = _first_callable(
        entity_grounding_daemon,
        (
            "run_entity_grounding_broker_daemon",
            "run_entity_grounding_daemon",
            "run_broker_daemon",
        ),
        "entity-grounding broker-daemon",
    )

    def connect_factory() -> Any:
        return connect(url=broker_database_url)

    try:
        return worker(
            connect_factory,
            tenant_id=tenant_id,
            corpus_id=corpus_id,
            limit=(
                limit
                if limit is not None
                else entity_grounding_daemon.DEFAULT_ENTITY_GROUNDING_BROKER_DAEMON_BATCH_SIZE
            ),
            interval_seconds=(
                interval_seconds
                if interval_seconds is not None
                else entity_grounding_daemon.DEFAULT_ENTITY_GROUNDING_BROKER_DAEMON_INTERVAL_SECONDS
            ),
            target_adapter=target_adapter,
            max_iterations=max_iterations,
        )
    except entity_grounding_daemon.EntityGroundingBrokerDaemonError as exc:
        raise EntityGroundingCliError(str(exc)) from exc


def entity_grounding_broker_database_url() -> str | None:
    """Return the optional restricted DSN for network-capable materialization."""
    configured = os.environ.get(ENTITY_GROUNDING_BROKER_DATABASE_URL_ENV)
    if configured is None or configured.strip() == "":
        return None
    return configured


def _first_callable(module: Any, names: tuple[str, ...], command_name: str) -> Any:
    """Return the first supported implementation entrypoint on a module."""
    for name in names:
        candidate = getattr(module, name, None)
        if callable(candidate):
            return candidate
    raise EntityGroundingCliError(
        f"{command_name} implementation has no supported entrypoint: {', '.join(names)}"
    )


def _call_worker_with_supported_kwargs(
    worker: Any,
    conn: Any,
    kwargs: dict[str, Any],
) -> Any:
    """Call a worker while tolerating narrower implementation signatures."""
    parameters = inspect.signature(worker).parameters
    accepts_var_kwargs = any(
        parameter.kind == inspect.Parameter.VAR_KEYWORD
        for parameter in parameters.values()
    )
    supported_kwargs = kwargs if accepts_var_kwargs else {
        key: value for key, value in kwargs.items() if key in parameters
    }
    return worker(conn, **supported_kwargs)


def entity_grounding_output(result: Any) -> dict[str, Any]:
    """Convert an RFC 0054/0055 result object into sanitized CLI JSON."""
    if hasattr(result, "to_json") and callable(result.to_json):
        payload = result.to_json()
    elif isinstance(result, dict):
        payload = result
    elif dataclasses.is_dataclass(result) and not isinstance(result, type):
        payload = dataclasses.asdict(result)
    else:
        payload = {
            key: value
            for key, value in vars(result).items()
            if not key.startswith("_")
        }
    if not isinstance(payload, dict):
        raise EntityGroundingCliError("entity-grounding result must serialize to a JSON object")
    return _sanitize_cli_json(payload)


def _sanitize_cli_json(value: Any) -> Any:
    """Redact secret-shaped fields from operator-facing JSON output."""
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return _sanitize_cli_json(dataclasses.asdict(value))
    if isinstance(value, dict):
        redacted: dict[str, Any] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                continue
            lowered = key.lower()
            if any(fragment in lowered for fragment in _SECRET_OUTPUT_KEY_FRAGMENTS):
                redacted[key] = "[redacted]"
            else:
                redacted[key] = _sanitize_cli_json(item)
        return redacted
    if isinstance(value, list):
        return [_sanitize_cli_json(item) for item in value]
    if isinstance(value, tuple):
        return [_sanitize_cli_json(item) for item in value]
    if isinstance(value, datetime):
        return _json_datetime(value)
    if isinstance(value, UUID):
        return str(value)
    return value


def _json_datetime(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat().replace("+00:00", "Z")
    return str(value)


def _rfc3339_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def build_cli_context_eval_compiler(
    conn: Any,
    *,
    tenant_id: str,
    corpus_id: str,
    word_budget: int,
    privacy_tier_max: int,
) -> Any:
    """Build the eval runner seam around the installed context_for service."""

    def compile_request(request: ContextCompileRequest) -> dict[str, Any]:
        context_request = ContextForRequest(
            query_text=request.query_text,
            tenant_id=tenant_id,
            corpus_id=corpus_id,
            word_budget=word_budget,
            privacy_tier_ceiling=min(request.privacy_ceiling, privacy_tier_max),
        )
        return context_for(conn, context_request).to_json()

    return compile_request


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="engram")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("migrate", help="Apply SQL migrations")

    chatgpt_parser = subparsers.add_parser(
        "ingest-chatgpt",
        help="Deprecated; use `engram phase1 ingest-chatgpt`",
    )
    chatgpt_parser.add_argument("path", type=Path)
    chatgpt_parser.set_defaults(
        invoked_command="ingest-chatgpt",
        legacy_replacement="phase1 ingest-chatgpt",
    )

    claude_parser = subparsers.add_parser(
        "ingest-claude",
        help="Deprecated; use `engram phase1 ingest-claude`",
    )
    claude_parser.add_argument("path", type=Path)
    claude_parser.set_defaults(
        invoked_command="ingest-claude",
        legacy_replacement="phase1 ingest-claude",
    )

    gemini_parser = subparsers.add_parser(
        "ingest-gemini",
        help="Deprecated; use `engram phase1 ingest-gemini`",
    )
    gemini_parser.add_argument("path", nargs="?", type=Path)
    gemini_parser.add_argument("--path", dest="path_option", type=Path)
    gemini_parser.set_defaults(
        invoked_command="ingest-gemini",
        legacy_replacement="phase1 ingest-gemini",
    )

    striatum_parser = subparsers.add_parser(
        "ingest-striatum",
        help="Ingest a local Striatum corpus export bundle",
    )
    striatum_parser.add_argument("--bundle", type=Path, required=True)
    striatum_parser.add_argument("--repo", default="striatum")
    striatum_parser.set_defaults(invoked_command="ingest-striatum")

    # RFC 0050 Layer 1: `engram import git <repo-path>`.
    import_parser = subparsers.add_parser(
        "import",
        help="RFC 0050 source-contract importers",
    )
    import_subparsers = import_parser.add_subparsers(dest="import_command", required=True)
    import_git_parser = import_subparsers.add_parser(
        "git",
        help="Import commit metadata + diff stats from a local git repository",
    )
    import_git_parser.add_argument("path", type=Path)
    import_git_parser.add_argument("--tenant-id", default="personal")
    import_git_parser.add_argument("--corpus-id", default="personal")
    import_git_parser.add_argument("--repo-label", default=None)
    import_git_parser.add_argument("--allow-dirty", action="store_true")
    import_git_parser.add_argument("--dry-run", action="store_true")
    import_git_parser.add_argument(
        "--full-patch",
        default="false",
        choices=("false",),
        help=(
            "Reserved for a future opt-in slice (RFC 0050 OQ-SI-001); Layer 1 only accepts 'false'."
        ),
    )
    import_git_parser.set_defaults(command="import-git", invoked_command="import git")
    import_build_parser = import_subparsers.add_parser(
        "build-artifacts",
        help="Import a local build/test/lint/coverage/benchmark artifact directory",
    )
    import_build_parser.add_argument("path", type=Path)
    import_build_parser.add_argument("--tenant-id", default="personal")
    import_build_parser.add_argument("--corpus-id", default="personal")
    import_build_parser.add_argument("--run-id", default=None)
    import_build_parser.add_argument("--commit-sha", default=None)
    import_build_parser.add_argument("--repo-label", default=None)
    import_build_parser.add_argument("--dry-run", action="store_true")
    import_build_parser.set_defaults(
        command="import-build-artifacts", invoked_command="import build-artifacts"
    )
    import_md_parser = import_subparsers.add_parser(
        "markdown",
        help="Import a local Markdown / project-doc tree",
    )
    import_md_parser.add_argument("path", type=Path)
    import_md_parser.add_argument("--tenant-id", default="personal")
    import_md_parser.add_argument("--corpus-id", default="personal")
    import_md_parser.add_argument("--repo-label", default=None)
    import_md_parser.add_argument("--dry-run", action="store_true")
    import_md_parser.set_defaults(command="import-markdown", invoked_command="import markdown")

    describe_corpus_parser = subparsers.add_parser(
        "describe-corpus",
        help="Describe an authorized local Engram corpus",
    )
    describe_corpus_parser.add_argument("corpus")
    describe_corpus_parser.add_argument("--tenant", default=None)
    describe_corpus_parser.set_defaults(invoked_command="describe-corpus")

    phase_projection_parser = subparsers.add_parser(
        "phase-projection",
        help="Striatum projection commands",
    )
    phase_projection_subparsers = phase_projection_parser.add_subparsers(
        dest="phase_projection_command", required=True
    )
    phase_projection_run_parser = phase_projection_subparsers.add_parser(
        "run",
        help="Fast-forward Striatum reference projections",
    )
    phase_projection_run_parser.add_argument("--tenant", default="striatum")
    phase_projection_run_parser.add_argument("--corpus", default="striatum")
    phase_projection_run_parser.set_defaults(
        command="phase-projection-run",
        invoked_command="phase-projection run",
    )

    evidence_parser = subparsers.add_parser(
        "evidence",
        help="Generic evidence/reference projection commands",
    )
    evidence_subparsers = evidence_parser.add_subparsers(
        dest="evidence_command",
        required=True,
    )
    evidence_refresh_parser = evidence_subparsers.add_parser(
        "refresh-index",
        help="Rebuild the generic evidence/reference index for one tenant/corpus",
    )
    evidence_refresh_parser.add_argument("--tenant", default="personal")
    evidence_refresh_parser.add_argument("--corpus", default="personal")
    evidence_refresh_parser.set_defaults(command="evidence-refresh-index")

    context_for_parser = subparsers.add_parser(
        "context-for",
        help="Compile a local personal context package for a query",
    )
    context_for_parser.add_argument("--query")
    context_for_parser.add_argument("--query-file", type=Path)
    context_for_parser.add_argument("--tenant", default="personal")
    context_for_parser.add_argument("--corpus", default="personal")
    context_for_parser.add_argument("--format", choices=["json", "markdown"], default="markdown")
    context_for_parser.add_argument("--word-budget", type=int, default=500)
    context_for_parser.add_argument("--privacy-tier-max", type=int, default=1)
    context_for_parser.set_defaults(command="context-for")

    claim_grounding_parser = subparsers.add_parser(
        "claim-grounding",
        help="RFC 0053 local claim-grounding broker commands",
    )
    claim_grounding_subparsers = claim_grounding_parser.add_subparsers(
        dest="claim_grounding_command",
        required=True,
    )
    claim_grounding_entity_parser = claim_grounding_subparsers.add_parser(
        "entity",
        help="Resolve a claim_grounding.request.v1 against local grounding evidence",
    )
    claim_grounding_entity_parser.add_argument("--request-json", type=Path, required=True)
    claim_grounding_entity_parser.add_argument("--limit", type=int, default=5)
    claim_grounding_entity_parser.set_defaults(command="claim-grounding-entity")
    claim_grounding_grants_parser = claim_grounding_subparsers.add_parser(
        "grants",
        help="Inspect and append claim-grounding network grant lifecycle rows",
    )
    claim_grounding_grants_subparsers = claim_grounding_grants_parser.add_subparsers(
        dest="claim_grounding_grants_command",
        required=True,
    )
    claim_grounding_grants_list_parser = claim_grounding_grants_subparsers.add_parser(
        "list",
        help="List exact operator-visible grant rows",
    )
    claim_grounding_grants_list_parser.add_argument(
        "--status",
        choices=["all", "draft", "approved", "denied", "revoked", "expired"],
        default="draft",
    )
    claim_grounding_grants_list_parser.add_argument("--tenant", default="personal")
    claim_grounding_grants_list_parser.add_argument("--corpus", default="personal")
    claim_grounding_grants_list_parser.add_argument("--limit", type=int, default=20)
    claim_grounding_grants_list_parser.set_defaults(command="claim-grounding-grants-list")
    claim_grounding_grants_draft_parser = claim_grounding_grants_subparsers.add_parser(
        "draft",
        help="Persist a draft grant from a claim_grounding.request.v1 JSON file",
    )
    claim_grounding_grants_draft_parser.add_argument("--request-json", type=Path, required=True)
    claim_grounding_grants_draft_parser.set_defaults(command="claim-grounding-grants-draft")
    claim_grounding_grants_approve_parser = claim_grounding_grants_subparsers.add_parser(
        "approve",
        help="Append an approved grant row for a persisted request",
    )
    claim_grounding_grants_approve_parser.add_argument("--request-id", required=True)
    claim_grounding_grants_approve_parser.add_argument("--grant-id", required=True)
    claim_grounding_grants_approve_parser.add_argument("--granted-by", required=True)
    claim_grounding_grants_approve_parser.add_argument("--tenant", default="personal")
    claim_grounding_grants_approve_parser.add_argument("--corpus", default="personal")
    claim_grounding_grants_approve_parser.set_defaults(command="claim-grounding-grants-approve")
    claim_grounding_grants_deny_parser = claim_grounding_grants_subparsers.add_parser(
        "deny",
        help="Append a denied grant row for a persisted request",
    )
    claim_grounding_grants_deny_parser.add_argument("--request-id", required=True)
    claim_grounding_grants_deny_parser.add_argument("--grant-id", required=True)
    claim_grounding_grants_deny_parser.add_argument("--denied-by", required=True)
    claim_grounding_grants_deny_parser.add_argument("--reason", required=True)
    claim_grounding_grants_deny_parser.add_argument("--tenant", default="personal")
    claim_grounding_grants_deny_parser.add_argument("--corpus", default="personal")
    claim_grounding_grants_deny_parser.set_defaults(command="claim-grounding-grants-deny")
    claim_grounding_grants_revoke_parser = claim_grounding_grants_subparsers.add_parser(
        "revoke",
        help="Append a revoked grant row for a persisted request",
    )
    claim_grounding_grants_revoke_parser.add_argument("--request-id", required=True)
    claim_grounding_grants_revoke_parser.add_argument("--grant-id", required=True)
    claim_grounding_grants_revoke_parser.add_argument("--revoked-by", required=True)
    claim_grounding_grants_revoke_parser.add_argument("--reason", required=True)
    claim_grounding_grants_revoke_parser.add_argument("--tenant", default="personal")
    claim_grounding_grants_revoke_parser.add_argument("--corpus", default="personal")
    claim_grounding_grants_revoke_parser.set_defaults(command="claim-grounding-grants-revoke")

    entity_grounding_parser = subparsers.add_parser(
        "entity-grounding",
        help="RFC 0054/0055 entity-wide grounding workflow commands",
    )
    entity_grounding_subparsers = entity_grounding_parser.add_subparsers(
        dest="entity_grounding_command",
        required=True,
    )
    entity_grounding_draft_parser = entity_grounding_subparsers.add_parser(
        "draft",
        help="Draft local-first RFC 0053 grounding requests for unresolved entities",
    )
    entity_grounding_draft_parser.add_argument("--tenant", default="personal")
    entity_grounding_draft_parser.add_argument("--corpus", default="personal")
    entity_grounding_draft_parser.add_argument("--limit", type=int, default=50)
    entity_grounding_draft_parser.add_argument("--entity-id")
    entity_grounding_draft_parser.set_defaults(command="entity-grounding-draft")
    entity_grounding_process_parser = entity_grounding_subparsers.add_parser(
        "process-approved",
        help="Materialize approved entity-grounding grants into local evidence",
    )
    entity_grounding_process_parser.add_argument("--tenant", default="personal")
    entity_grounding_process_parser.add_argument("--corpus", default="personal")
    entity_grounding_process_parser.add_argument("--limit", type=int, default=20)
    entity_grounding_process_parser.add_argument("--request-id")
    entity_grounding_process_parser.add_argument("--grant-id")
    entity_grounding_process_parser.add_argument("--target-adapter", default=None)
    entity_grounding_process_parser.epilog = (
        f"Requires {ENTITY_GROUNDING_BROKER_DATABASE_URL_ENV}; the network-capable "
        "materializer always runs through the restricted broker database role."
    )
    entity_grounding_process_parser.set_defaults(command="entity-grounding-process-approved")
    entity_grounding_daemon_parser = entity_grounding_subparsers.add_parser(
        "broker-daemon",
        help="Poll approved entity-grounding grants with the restricted broker role",
    )
    entity_grounding_daemon_parser.add_argument("--tenant", default="personal")
    entity_grounding_daemon_parser.add_argument("--corpus", default="personal")
    entity_grounding_daemon_parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help=(
            "Approved grants to process per iteration; default comes from "
            "ENGRAM_ENTITY_GROUNDING_BROKER_DAEMON_BATCH_SIZE or 20"
        ),
    )
    entity_grounding_daemon_parser.add_argument(
        "--interval",
        "--interval-seconds",
        dest="interval_seconds",
        type=float,
        default=None,
        help=(
            "Seconds to sleep between iterations; default comes from "
            "ENGRAM_ENTITY_GROUNDING_BROKER_DAEMON_INTERVAL_SECONDS or 10"
        ),
    )
    entity_grounding_daemon_parser.add_argument("--target-adapter", default=None)
    entity_grounding_daemon_parser.add_argument(
        "--max-iterations",
        type=int,
        default=None,
        help="Stop after N iterations; omit for a long-running daemon",
    )
    entity_grounding_daemon_parser.epilog = (
        f"Requires {ENTITY_GROUNDING_BROKER_DATABASE_URL_ENV}; this command is the "
        "local long-running network-capable broker workflow."
    )
    entity_grounding_daemon_parser.set_defaults(command="entity-grounding-broker-daemon")

    eval_parser = subparsers.add_parser(
        "eval",
        help="Local deterministic evaluation commands",
    )
    eval_subparsers = eval_parser.add_subparsers(dest="eval_command", required=True)
    eval_context_parser = eval_subparsers.add_parser(
        "context",
        help="Run a context_for evaluation over an external local dataset",
    )
    eval_context_dataset_group = eval_context_parser.add_mutually_exclusive_group()
    eval_context_dataset_group.add_argument(
        "--dataset-path",
        type=Path,
        help=(
            "External private eval dataset directory or JSONL file. "
            f"Overrides {CONTEXT_EVAL_DATASET_ENV_VAR}."
        ),
    )
    eval_context_dataset_group.add_argument(
        "--gold-set",
        type=Path,
        help="Deprecated alias for a direct context eval JSONL file",
    )
    eval_context_parser.add_argument("--output", type=Path, required=True)
    eval_context_parser.add_argument("--markdown-output", type=Path)
    eval_context_parser.add_argument("--tenant", default="personal")
    eval_context_parser.add_argument("--corpus", default="personal")
    eval_context_parser.add_argument("--word-budget", type=int, default=500)
    eval_context_parser.add_argument("--privacy-tier-max", type=int, default=1)
    eval_context_parser.set_defaults(command="eval-context")

    no_egress_parser = subparsers.add_parser(
        "no-egress",
        help="Probe or run commands inside an OS-level no-egress boundary",
    )
    no_egress_subparsers = no_egress_parser.add_subparsers(
        dest="no_egress_command",
        required=True,
    )
    no_egress_probe_parser = no_egress_subparsers.add_parser(
        "probe",
        help="Probe local OS support for enforced no-egress execution",
    )
    no_egress_probe_parser.set_defaults(command="no-egress-probe")
    no_egress_run_parser = no_egress_subparsers.add_parser(
        "run",
        help="Run a command inside the best available no-egress boundary",
    )
    no_egress_run_parser.add_argument("command_argv", nargs=argparse.REMAINDER)
    no_egress_run_parser.set_defaults(command="no-egress-run")

    segment_parser = subparsers.add_parser(
        "segment",
        help="Deprecated; use `engram phase2 segment`",
    )
    segment_parser.add_argument("--source-id")
    segment_parser.add_argument("--batch-size", type=int, default=10)
    segment_parser.add_argument("--limit", type=int)
    segment_parser.add_argument("--retries", type=int, default=DEFAULT_RETRIES)
    segment_parser.set_defaults(
        invoked_command="segment",
        legacy_replacement="phase2 segment",
    )

    embed_parser = subparsers.add_parser(
        "embed",
        help="Deprecated; use `engram phase2 embed`",
    )
    embed_parser.add_argument("--model-version", default=DEFAULT_EMBEDDING_MODEL_VERSION)
    embed_parser.add_argument("--batch-size", type=int, default=100)
    embed_parser.add_argument("--limit", type=int)
    embed_parser.set_defaults(
        invoked_command="embed",
        legacy_replacement="phase2 embed",
    )

    extract_parser = subparsers.add_parser(
        "extract",
        help="Deprecated; use `engram phase3 extract`",
    )
    extract_parser.add_argument("--batch-size", type=int, default=50)
    extract_parser.add_argument("--limit", type=int)
    extract_parser.add_argument("--segment-id")
    extract_parser.add_argument("--conversation-id")
    extract_parser.add_argument("--requeue", action="store_true")
    extract_parser.add_argument("--prompt-version", default=EXTRACTION_PROMPT_VERSION)
    extract_parser.add_argument("--concurrency", type=int, default=DEFAULT_EXTRACTION_CONCURRENCY)
    extract_parser.set_defaults(
        invoked_command="extract",
        legacy_replacement="phase3 extract",
    )

    re_extract_parser = subparsers.add_parser(
        "re-extract",
        help="Deprecated; use `engram phase3 re-extract`",
    )
    re_extract_parser.add_argument(
        "--version",
        required=True,
        help=(
            "Target prompt version, e.g. extractor.v9.d065.descriptor. "
            "Must differ from the live EXTRACTION_PROMPT_VERSION."
        ),
    )
    re_extract_parser.add_argument("--batch-size", type=int, default=50)
    re_extract_parser.add_argument("--limit", type=int)
    re_extract_parser.add_argument("--source-id")
    re_extract_parser.add_argument("--diff-sample", type=int, default=5)
    re_extract_parser.add_argument("--dry-run", action="store_true")
    re_extract_parser.set_defaults(
        invoked_command="re-extract",
        legacy_replacement="phase3 re-extract",
    )

    consolidate_parser = subparsers.add_parser(
        "consolidate",
        help="Deprecated; use `engram phase3 consolidate`",
    )
    consolidate_parser.add_argument("--batch-size", type=int, default=100)
    consolidate_parser.add_argument("--limit", type=int)
    consolidate_parser.add_argument("--conversation-id")
    consolidate_parser.add_argument("--rebuild", action="store_true")
    consolidate_parser.add_argument("--prompt-version", default=CONSOLIDATOR_PROMPT_VERSION)
    consolidate_parser.set_defaults(
        invoked_command="consolidate",
        legacy_replacement="phase3 consolidate",
    )

    pipeline_parser = subparsers.add_parser(
        "pipeline",
        description=AMBIGUOUS_PIPELINE_COMMAND,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        help="Ambiguous legacy command; use a phase-scoped command",
    )
    pipeline_parser.add_argument("--source-id", help=argparse.SUPPRESS)
    pipeline_parser.add_argument(
        "--segment-batch-size",
        type=int,
        default=10,
        help=argparse.SUPPRESS,
    )
    pipeline_parser.add_argument(
        "--embed-batch-size",
        type=int,
        default=100,
        help=argparse.SUPPRESS,
    )
    pipeline_parser.add_argument("--limit", type=int, help=argparse.SUPPRESS)
    pipeline_parser.add_argument(
        "--model-version",
        default=DEFAULT_EMBEDDING_MODEL_VERSION,
        help=argparse.SUPPRESS,
    )
    pipeline_parser.add_argument(
        "--segment-retries",
        type=int,
        default=DEFAULT_RETRIES,
        help=argparse.SUPPRESS,
    )
    pipeline_parser.set_defaults(invoked_command="pipeline")

    pipeline3_parser = subparsers.add_parser(
        "pipeline-3",
        help="Deprecated; use `engram phase3 run`",
    )
    pipeline3_parser.add_argument("--extract-batch-size", type=int, default=10)
    pipeline3_parser.add_argument("--consolidate-batch-size", type=int, default=10)
    pipeline3_parser.add_argument("--limit", type=int)
    pipeline3_parser.add_argument(
        "--extract-concurrency",
        type=int,
        default=DEFAULT_EXTRACTION_CONCURRENCY,
    )
    pipeline3_parser.set_defaults(
        invoked_command="pipeline-3",
        legacy_replacement="phase3 run",
    )

    phase4_refresh_parser = subparsers.add_parser(
        "phase4-refresh",
        help="Deprecated; use `engram phase4 refresh-current-beliefs`",
    )
    phase4_refresh_parser.set_defaults(
        invoked_command="phase4-refresh",
        legacy_replacement="phase4 refresh-current-beliefs",
    )

    phase4_entities_parser = subparsers.add_parser(
        "phase4-build-entities",
        help="Deprecated; use `engram phase4 build-entities`",
    )
    phase4_entities_parser.add_argument("--limit", type=int)
    phase4_entities_parser.set_defaults(
        invoked_command="phase4-build-entities",
        legacy_replacement="phase4 build-entities",
    )

    phase4_smoke_parser = subparsers.add_parser(
        "phase4-smoke",
        help="Deprecated; use `engram phase4 smoke`",
    )
    phase4_smoke_parser.add_argument("--limit", type=int, default=25)
    phase4_smoke_parser.set_defaults(
        invoked_command="phase4-smoke",
        legacy_replacement="phase4 smoke",
    )

    review_parser = subparsers.add_parser(
        "review-belief",
        help="Deprecated; use `engram phase4 review-belief`",
    )
    review_parser.add_argument("belief_id")
    review_parser.add_argument(
        "action",
        choices=["accept", "reject", "correct", "promote-to-pinned"],
    )
    review_parser.add_argument("--note")
    review_parser.add_argument("--actor", default="local")
    review_parser.set_defaults(
        invoked_command="review-belief",
        legacy_replacement="phase4 review-belief",
    )

    phase1_parser = subparsers.add_parser("phase1", help="Phase 1 ingestion commands")
    phase1_subparsers = phase1_parser.add_subparsers(dest="phase1_command", required=True)
    phase1_chatgpt_parser = phase1_subparsers.add_parser(
        "ingest-chatgpt",
        help="Ingest a local ChatGPT export directory",
    )
    phase1_chatgpt_parser.add_argument("path", type=Path)
    phase1_chatgpt_parser.set_defaults(command="ingest-chatgpt")
    phase1_claude_parser = phase1_subparsers.add_parser(
        "ingest-claude",
        help="Ingest a local Claude.ai export (directory or .zip)",
    )
    phase1_claude_parser.add_argument("path", type=Path)
    phase1_claude_parser.set_defaults(command="ingest-claude")
    phase1_gemini_parser = phase1_subparsers.add_parser(
        "ingest-gemini",
        help="Ingest a local Gemini Google Takeout directory",
    )
    phase1_gemini_parser.add_argument("path", nargs="?", type=Path)
    phase1_gemini_parser.add_argument("--path", dest="path_option", type=Path)
    phase1_gemini_parser.set_defaults(command="ingest-gemini")
    phase1_striatum_parser = phase1_subparsers.add_parser(
        "ingest-striatum",
        help="Ingest a local Striatum corpus export bundle",
    )
    phase1_striatum_parser.add_argument("--bundle", type=Path, required=True)
    phase1_striatum_parser.add_argument("--repo", default="striatum")
    phase1_striatum_parser.set_defaults(command="ingest-striatum")

    phase2_parser = subparsers.add_parser(
        "phase2",
        help="Phase 2 segmentation and embedding commands",
    )
    phase2_subparsers = phase2_parser.add_subparsers(dest="phase2_command", required=True)
    phase2_segment_parser = phase2_subparsers.add_parser(
        "segment",
        help="Segment pending conversations into inactive segment generations",
    )
    phase2_segment_parser.add_argument("--source-id")
    phase2_segment_parser.add_argument("--batch-size", type=int, default=10)
    phase2_segment_parser.add_argument("--limit", type=int)
    phase2_segment_parser.add_argument("--retries", type=int, default=DEFAULT_RETRIES)
    phase2_segment_parser.set_defaults(command="segment")
    phase2_embed_parser = phase2_subparsers.add_parser(
        "embed",
        help="Embed pending segments and activate completed generations",
    )
    phase2_embed_parser.add_argument("--model-version", default=DEFAULT_EMBEDDING_MODEL_VERSION)
    phase2_embed_parser.add_argument("--batch-size", type=int, default=100)
    phase2_embed_parser.add_argument("--limit", type=int)
    phase2_embed_parser.set_defaults(command="embed")
    phase2_run_parser = phase2_subparsers.add_parser(
        "run",
        help="Run Phase 2 pipeline: segment -> embed",
    )
    phase2_run_parser.add_argument("--source-id")
    phase2_run_parser.add_argument("--segment-batch-size", type=int, default=10)
    phase2_run_parser.add_argument("--embed-batch-size", type=int, default=100)
    phase2_run_parser.add_argument("--limit", type=int)
    phase2_run_parser.add_argument("--model-version", default=DEFAULT_EMBEDDING_MODEL_VERSION)
    phase2_run_parser.add_argument("--segment-retries", type=int, default=DEFAULT_RETRIES)
    phase2_run_parser.set_defaults(command="pipeline", invoked_command="phase2 run")

    phase3_parser = subparsers.add_parser(
        "phase3",
        help="Phase 3 claim extraction and belief consolidation commands",
    )
    phase3_subparsers = phase3_parser.add_subparsers(dest="phase3_command", required=True)
    phase3_extract_parser = phase3_subparsers.add_parser(
        "extract",
        help="Extract atomic claims from active segments",
    )
    phase3_extract_parser.add_argument("--batch-size", type=int, default=50)
    phase3_extract_parser.add_argument("--limit", type=int)
    phase3_extract_parser.add_argument("--segment-id")
    phase3_extract_parser.add_argument("--conversation-id")
    phase3_extract_parser.add_argument("--requeue", action="store_true")
    phase3_extract_parser.add_argument("--prompt-version", default=EXTRACTION_PROMPT_VERSION)
    phase3_extract_parser.add_argument(
        "--concurrency",
        type=int,
        default=DEFAULT_EXTRACTION_CONCURRENCY,
    )
    phase3_extract_parser.set_defaults(command="extract")
    phase3_consolidate_parser = phase3_subparsers.add_parser(
        "consolidate",
        help="Consolidate claims into bitemporal beliefs",
    )
    phase3_consolidate_parser.add_argument("--batch-size", type=int, default=100)
    phase3_consolidate_parser.add_argument("--limit", type=int)
    phase3_consolidate_parser.add_argument("--conversation-id")
    phase3_consolidate_parser.add_argument("--rebuild", action="store_true")
    phase3_consolidate_parser.add_argument(
        "--prompt-version",
        default=CONSOLIDATOR_PROMPT_VERSION,
    )
    phase3_consolidate_parser.set_defaults(command="consolidate")
    phase3_run_parser = phase3_subparsers.add_parser(
        "run",
        help="Run Phase 3 pipeline: extract -> consolidate",
    )
    phase3_run_parser.add_argument("--extract-batch-size", type=int, default=10)
    phase3_run_parser.add_argument("--consolidate-batch-size", type=int, default=10)
    phase3_run_parser.add_argument("--limit", type=int)
    phase3_run_parser.add_argument(
        "--extract-concurrency",
        type=int,
        default=DEFAULT_EXTRACTION_CONCURRENCY,
    )
    phase3_run_parser.set_defaults(command="pipeline-3")

    phase3_re_extract_parser = phase3_subparsers.add_parser(
        "re-extract",
        help=(
            "Re-extract claims under a new prompt version (RFC 0017 Part 2). "
            "Old rows are preserved for audit; consolidation is not auto-triggered."
        ),
    )
    phase3_re_extract_parser.add_argument(
        "--version",
        required=True,
        help=(
            "Target prompt version, e.g. extractor.v9.d065.descriptor. "
            "Must differ from the live EXTRACTION_PROMPT_VERSION."
        ),
    )
    phase3_re_extract_parser.add_argument("--batch-size", type=int, default=50)
    phase3_re_extract_parser.add_argument("--limit", type=int)
    phase3_re_extract_parser.add_argument("--source-id")
    phase3_re_extract_parser.add_argument("--diff-sample", type=int, default=5)
    phase3_re_extract_parser.add_argument("--dry-run", action="store_true")
    phase3_re_extract_parser.set_defaults(command="re-extract")

    phase3_interview_parser = phase3_subparsers.add_parser(
        "interview",
        help="Gold-set interview loop (RFC 0021)",
    )
    interview_subparsers = phase3_interview_parser.add_subparsers(
        dest="phase3_interview_command", required=True
    )

    phase3_interview_start_parser = interview_subparsers.add_parser(
        "start",
        help="Start a new gold-set interview session",
    )
    phase3_interview_start_parser.add_argument("--n", type=int, default=10)
    phase3_interview_start_parser.add_argument(
        "--strata",
        type=parse_interview_strata_expr,
        default={},
        help=("comma-separated sampling filters, e.g. stability_class=identity,conf_band=0.6-0.8"),
    )
    phase3_interview_start_parser.add_argument("--seed", type=int, default=None)
    phase3_interview_start_parser.add_argument("--include-superseded", action="store_true")
    phase3_interview_start_parser.add_argument("--ignore-cooldown", action="store_true")
    phase3_interview_start_parser.add_argument("--ignore-reask-cap", action="store_true")
    phase3_interview_start_parser.add_argument(
        "--non-interactive",
        action="store_true",
        help="Open a session and sample targets without prompting; for scripts and tests.",
    )
    phase3_interview_start_parser.set_defaults(command="phase3-interview-start")

    phase3_interview_resume_parser = interview_subparsers.add_parser(
        "resume",
        help="Resume an existing gold-set interview session",
    )
    phase3_interview_resume_parser.add_argument("--session-id", type=str, default=None)
    phase3_interview_resume_parser.set_defaults(command="phase3-interview-resume")

    phase3_interview_history_parser = interview_subparsers.add_parser(
        "history",
        help="Show gold-label history for a target",
    )
    phase3_interview_history_parser.add_argument("--target", type=str, default=None)
    phase3_interview_history_parser.add_argument("--since", type=str, default=None)
    phase3_interview_history_parser.set_defaults(command="phase3-interview-history")

    phase3_interview_export_parser = interview_subparsers.add_parser(
        "export",
        help="Export gold-label rows (default --privacy-tier-max 1)",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    phase3_interview_export_parser.add_argument(
        "--privacy-tier-max",
        type=int,
        default=1,
        help="fail-closed Tier ceiling (default: 1; higher tiers require opt-in)",
    )
    phase3_interview_export_parser.add_argument("--format", choices=["jsonl"], default="jsonl")
    phase3_interview_export_parser.add_argument("--output", type=Path, default=None)
    phase3_interview_export_parser.set_defaults(command="phase3-interview-export")

    phase3_interview_list_sessions_parser = interview_subparsers.add_parser(
        "list-sessions",
        help="List gold-label sessions",
    )
    phase3_interview_list_sessions_parser.add_argument(
        "--state",
        choices=["open", "completed", "all"],
        default="all",
    )
    phase3_interview_list_sessions_parser.set_defaults(command="phase3-interview-list-sessions")

    phase3_interview_coverage_parser = interview_subparsers.add_parser(
        "coverage",
        help="Show stratum coverage for the gold-label corpus",
    )
    phase3_interview_coverage_parser.add_argument("--strata", type=str, required=True)
    phase3_interview_coverage_parser.set_defaults(command="phase3-interview-coverage")

    phase3_interview_active_learning_parser = interview_subparsers.add_parser(
        "enable-active-learning",
        help="Enable opt-in active-learning bias for the next session",
    )
    phase3_interview_active_learning_parser.add_argument(
        "--signal-version", type=str, required=True
    )
    phase3_interview_active_learning_parser.set_defaults(
        command="phase3-interview-enable-active-learning"
    )

    phase3_interview_serve_parser = interview_subparsers.add_parser(
        "serve",
        help="Run the local web UI for the gold-set interview (RFC 0027)",
    )
    phase3_interview_serve_parser.add_argument("--host", type=str, default="127.0.0.1")
    phase3_interview_serve_parser.add_argument("--port", type=int, default=8765)
    phase3_interview_serve_parser.set_defaults(command="phase3-interview-serve")

    phase3_bench_review_parser = phase3_subparsers.add_parser(
        "bench-review",
        help="Review extraction benchmark deltas in a local workbench (RFC 0029)",
    )
    bench_review_subparsers = phase3_bench_review_parser.add_subparsers(
        dest="phase3_bench_review_command", required=True
    )
    phase3_bench_review_serve_parser = bench_review_subparsers.add_parser(
        "serve",
        help="Run the local bench review web UI",
    )
    phase3_bench_review_serve_parser.add_argument("--slice", required=True)
    phase3_bench_review_serve_parser.add_argument("--run", required=True)
    phase3_bench_review_serve_parser.add_argument("--segments")
    phase3_bench_review_serve_parser.add_argument("--review-db")
    phase3_bench_review_serve_parser.add_argument("--prior-prompt-version", required=True)
    phase3_bench_review_serve_parser.add_argument("--prior-model-version", required=True)
    phase3_bench_review_serve_parser.add_argument("--prior-request-profile-version", required=True)
    phase3_bench_review_serve_parser.add_argument("--host", type=str, default="127.0.0.1")
    phase3_bench_review_serve_parser.add_argument("--port", type=int, default=8770)
    phase3_bench_review_serve_parser.set_defaults(command="phase3-bench-review-serve")

    phase3_bench_review_status_parser = bench_review_subparsers.add_parser(
        "status",
        help="Print bench review progress",
    )
    phase3_bench_review_status_parser.add_argument("--review-db", required=True)
    phase3_bench_review_status_parser.set_defaults(command="phase3-bench-review-status")

    phase3_bench_review_export_parser = bench_review_subparsers.add_parser(
        "export",
        help="Export a redacted bench review summary",
    )
    phase3_bench_review_export_parser.add_argument("--review-db", required=True)
    phase3_bench_review_export_parser.add_argument("--output", required=True)
    phase3_bench_review_export_parser.add_argument(
        "--allow-outside-reviews", action="store_true", default=False
    )
    phase3_bench_review_export_parser.set_defaults(command="phase3-bench-review-export")

    phase4_parser = subparsers.add_parser(
        "phase4",
        help="Phase 4 current-belief, entity, smoke, and review commands",
    )
    phase4_subparsers = phase4_parser.add_subparsers(dest="phase4_command", required=True)
    phase4_refresh_current_parser = phase4_subparsers.add_parser(
        "refresh-current-beliefs",
        help="Refresh Phase 4 current belief projections",
    )
    phase4_refresh_current_parser.set_defaults(command="phase4-refresh")
    phase4_build_entities_parser = phase4_subparsers.add_parser(
        "build-entities",
        help="Build deterministic Phase 4 entity scaffolding from current beliefs",
    )
    phase4_build_entities_parser.add_argument("--limit", type=int)
    phase4_build_entities_parser.set_defaults(command="phase4-build-entities")
    phase4_run_smoke_parser = phase4_subparsers.add_parser(
        "smoke",
        help="Run a bounded local-only Phase 4 Tier 0 smoke build",
    )
    phase4_run_smoke_parser.add_argument("--limit", type=int, default=25)
    phase4_run_smoke_parser.set_defaults(command="phase4-smoke")
    phase4_review_parser = phase4_subparsers.add_parser(
        "review-belief",
        help="Apply a Phase 4 belief review action",
    )
    phase4_review_parser.add_argument("belief_id")
    phase4_review_parser.add_argument(
        "action",
        choices=["accept", "reject", "correct", "promote-to-pinned"],
    )
    phase4_review_parser.add_argument("--note")
    phase4_review_parser.add_argument("--actor", default="local")
    phase4_review_parser.set_defaults(command="review-belief")

    args = parser.parse_args(argv)
    invoked_command = getattr(args, "invoked_command", args.command)
    if args.command == "pipeline" and invoked_command == "pipeline":
        print(AMBIGUOUS_PIPELINE_COMMAND, file=sys.stderr)
        return 2
    warn_legacy_command(
        invoked_command,
        getattr(args, "legacy_replacement", None),
    )

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

        if args.command == "ingest-striatum":
            with connect() as conn:
                result = ingest_striatum_bundle(conn, args.bundle, repo=args.repo)
            print_striatum_ingest_result(result)
            return 0

        if args.command == "import-markdown":
            with connect() as conn:
                result = import_markdown_tree(
                    conn,
                    args.path,
                    tenant_id=args.tenant_id,
                    corpus_id=args.corpus_id,
                    repo_label=args.repo_label,
                    dry_run=bool(args.dry_run),
                )
            print(
                json.dumps(
                    {
                        "source_id": result.source_id,
                        "markdown_root_id": result.markdown_root_id,
                        "files_inserted": result.files_inserted,
                        "files_seen": result.files_seen,
                        "files_skipped": result.files_skipped,
                        "files_tombstoned": result.files_tombstoned,
                        "chunks_inserted": result.chunks_inserted,
                        "links_inserted": result.links_inserted,
                        "coverage_gap_count": result.coverage_gap_count,
                    },
                    indent=2,
                    sort_keys=True,
                )
            )
            return 0

        if args.command == "import-build-artifacts":
            with connect() as conn:
                result = import_build_artifacts(
                    conn,
                    args.path,
                    tenant_id=args.tenant_id,
                    corpus_id=args.corpus_id,
                    run_id=args.run_id,
                    commit_sha=args.commit_sha,
                    repo_label=args.repo_label,
                    dry_run=bool(args.dry_run),
                )
            print(
                json.dumps(
                    {
                        "source_id": result.source_id,
                        "artifact_root_id": result.artifact_root_id,
                        "artifacts_inserted": result.artifacts_inserted,
                        "artifacts_seen": result.artifacts_seen,
                        "artifacts_skipped": result.artifacts_skipped,
                        "findings_inserted": result.findings_inserted,
                        "coverage_gap_count": result.coverage_gap_count,
                        "redacted_artifacts": result.redacted_artifacts,
                    },
                    indent=2,
                    sort_keys=True,
                )
            )
            return 0

        if args.command == "import-git":
            with connect() as conn:
                result = import_git_repo(
                    conn,
                    args.path,
                    tenant_id=args.tenant_id,
                    corpus_id=args.corpus_id,
                    repo_label=args.repo_label,
                    allow_dirty=bool(args.allow_dirty),
                    dry_run=bool(args.dry_run),
                )
            print(
                json.dumps(
                    {
                        "source_id": result.source_id,
                        "repository_id": result.repository_id,
                        "commits_inserted": result.commits_inserted,
                        "commits_seen": result.commits_seen,
                        "commits_skipped": result.commits_skipped,
                        "paths_inserted": result.paths_inserted,
                        "coverage_gap_count": result.coverage_gap_count,
                        "dirty_worktree": result.dirty_worktree,
                    },
                    indent=2,
                    sort_keys=True,
                )
            )
            return 0

        if args.command == "describe-corpus":
            # EG-000 baseline: the positional-only shorthand collapses
            # tenant_id == corpus_id only for the sanctioned `striatum` value.
            # Every other corpus requires an explicit --tenant.
            if args.tenant:
                tenant_id = args.tenant
            elif args.corpus == "striatum":
                tenant_id = "striatum"
            else:
                print(
                    "engram describe-corpus: specify --tenant for non-striatum corpora",
                    file=sys.stderr,
                )
                return 2
            with connect() as conn:
                description = MemoryService(conn).describe_corpus(
                    tenant_id=tenant_id,
                    corpus_id=args.corpus,
                )
            print(json.dumps(description, indent=2, sort_keys=True))
            return 0

        if args.command == "phase-projection-run":
            with connect() as conn:
                result = run_phase_projection(
                    conn,
                    tenant_id=args.tenant,
                    corpus_id=args.corpus,
                )
                conn.commit()
            print_phase_projection_result(result, tenant_id=args.tenant, corpus_id=args.corpus)
            return 0

        if args.command == "evidence-refresh-index":
            with connect() as conn:
                result = refresh_evidence_reference_index(
                    conn,
                    tenant_id=args.tenant,
                    corpus_id=args.corpus,
                )
                conn.commit()
            print(
                "evidence index: "
                f"tenant={result.tenant_id} "
                f"corpus={result.corpus_id} "
                f"evidence_items={result.evidence_items} "
                f"evidence_refs={result.evidence_refs}"
            )
            return 0

        if args.command == "context-for":
            query_text = read_context_query(args.query, args.query_file, parser)
            request = ContextForRequest(
                query_text=query_text,
                tenant_id=args.tenant,
                corpus_id=args.corpus,
                word_budget=args.word_budget,
                privacy_tier_ceiling=args.privacy_tier_max,
            )
            with connect() as conn:
                result = context_for(conn, request)
            if args.format == "json":
                print(json.dumps(result.to_json(), indent=2, sort_keys=True))
            else:
                print(result.rendered_context)
            return 0

        if args.command == "claim-grounding-entity":
            request_payload = read_claim_grounding_request_file(args.request_json, parser)
            with connect() as conn:
                response = ground_claim_entity_locally(
                    conn,
                    request_payload,
                    limit=args.limit,
                )
            print(json.dumps(response.to_json(), indent=2, sort_keys=True))
            return 0

        if args.command == "claim-grounding-grants-list":
            with connect() as conn:
                rows = list_claim_grounding_grants(
                    conn,
                    tenant_id=args.tenant,
                    corpus_id=args.corpus,
                    status=args.status,
                    limit=args.limit,
                )
            print(json.dumps({"grants": rows}, indent=2, sort_keys=True))
            return 0

        if args.command == "claim-grounding-grants-draft":
            request_payload = read_claim_grounding_request_file(args.request_json, parser)
            with connect() as conn:
                record_claim_grounding_request(conn, request_payload)
                record = record_claim_grounding_draft_grant(conn, request_payload)
                conn.commit()
            print(
                json.dumps(
                    claim_grounding_lifecycle_output(
                        action="draft",
                        record=record,
                        request_payload=request_payload,
                    ),
                    indent=2,
                    sort_keys=True,
                )
            )
            return 0

        if args.command == "claim-grounding-grants-approve":
            with connect() as conn:
                request_payload = load_claim_grounding_request_for_grant(
                    conn,
                    request_id=args.request_id,
                    grant_id=args.grant_id,
                    tenant_id=args.tenant,
                    corpus_id=args.corpus,
                    parser=parser,
                )
                approved_payload = approved_claim_grounding_request_payload(
                    request_payload,
                    granted_by=args.granted_by,
                )
                record = record_claim_grounding_approved_grant(conn, approved_payload)
                conn.commit()
            print(
                json.dumps(
                    claim_grounding_lifecycle_output(
                        action="approve",
                        record=record,
                        request_payload=approved_payload,
                    ),
                    indent=2,
                    sort_keys=True,
                )
            )
            return 0

        if args.command == "claim-grounding-grants-deny":
            with connect() as conn:
                request_payload = load_claim_grounding_request_for_grant(
                    conn,
                    request_id=args.request_id,
                    grant_id=args.grant_id,
                    tenant_id=args.tenant,
                    corpus_id=args.corpus,
                    parser=parser,
                )
                record = record_claim_grounding_denied_grant(
                    conn,
                    request_payload,
                    denied_by=args.denied_by,
                    reason=args.reason,
                )
                conn.commit()
            print(
                json.dumps(
                    claim_grounding_lifecycle_output(
                        action="deny",
                        record=record,
                        request_payload=request_payload,
                    ),
                    indent=2,
                    sort_keys=True,
                )
            )
            return 0

        if args.command == "claim-grounding-grants-revoke":
            with connect() as conn:
                request_payload = load_claim_grounding_request_for_grant(
                    conn,
                    request_id=args.request_id,
                    grant_id=args.grant_id,
                    tenant_id=args.tenant,
                    corpus_id=args.corpus,
                    parser=parser,
                )
                record = record_claim_grounding_revoked_grant(
                    conn,
                    request_payload,
                    revoked_by=args.revoked_by,
                    reason=args.reason,
                )
                conn.commit()
            print(
                json.dumps(
                    claim_grounding_lifecycle_output(
                        action="revoke",
                        record=record,
                        request_payload=request_payload,
                    ),
                    indent=2,
                    sort_keys=True,
                )
            )
            return 0

        if args.command == "entity-grounding-draft":
            with connect() as conn:
                result = run_entity_grounding_draft(
                    conn,
                    tenant_id=args.tenant,
                    corpus_id=args.corpus,
                    limit=args.limit,
                    entity_id=args.entity_id,
                )
                conn.commit()
            print(json.dumps(entity_grounding_output(result), indent=2, sort_keys=True))
            return 0

        if args.command == "entity-grounding-process-approved":
            broker_database_url = entity_grounding_broker_database_url()
            if broker_database_url is None:
                raise EntityGroundingCliError(
                    "process-approved requires "
                    f"{ENTITY_GROUNDING_BROKER_DATABASE_URL_ENV} to be set"
                )
            with connect(url=broker_database_url) as conn:
                result = run_entity_grounding_process_approved(
                    conn,
                    tenant_id=args.tenant,
                    corpus_id=args.corpus,
                    limit=args.limit,
                    request_id=args.request_id,
                    grant_id=args.grant_id,
                    target_adapter=args.target_adapter,
                )
                conn.commit()
            print(json.dumps(entity_grounding_output(result), indent=2, sort_keys=True))
            return 0

        if args.command == "entity-grounding-broker-daemon":
            broker_database_url = entity_grounding_broker_database_url()
            if broker_database_url is None:
                raise EntityGroundingCliError(
                    "broker-daemon requires "
                    f"{ENTITY_GROUNDING_BROKER_DATABASE_URL_ENV} to be set"
                )
            result = run_entity_grounding_broker_daemon(
                broker_database_url=broker_database_url,
                tenant_id=args.tenant,
                corpus_id=args.corpus,
                limit=args.limit,
                interval_seconds=args.interval_seconds,
                target_adapter=args.target_adapter,
                max_iterations=args.max_iterations,
            )
            print(json.dumps(entity_grounding_output(result), indent=2, sort_keys=True))
            return 0

        if args.command == "eval-context":
            try:
                gold_set_path = resolve_context_eval_gold_set_path(
                    dataset_path=args.dataset_path,
                    gold_set_path=args.gold_set,
                    environ=os.environ,
                )
            except ContextEvalError as exc:
                parser.error(str(exc))
            with connect() as conn:
                report = run_context_eval_file(
                    gold_set_path,
                    compiler=build_cli_context_eval_compiler(
                        conn,
                        tenant_id=args.tenant,
                        corpus_id=args.corpus,
                        word_budget=args.word_budget,
                        privacy_tier_max=args.privacy_tier_max,
                    ),
                )
            write_json_report(report, args.output)
            if args.markdown_output is not None:
                write_markdown_summary(report, args.markdown_output)
            print(
                "context eval: "
                f"items={report.item_count} "
                f"required_fact_recall={report.summary['required_fact_recall']:.3f} "
                f"citation_coverage={report.summary['citation_coverage']:.3f}"
            )
            return 0

        if args.command == "no-egress-probe":
            result = probe_enforcement()
            print(json.dumps(result.to_dict(), indent=2, sort_keys=True))
            return 0 if result.status == "egress_enforced" else 1

        if args.command == "no-egress-run":
            command_argv = list(args.command_argv)
            if command_argv and command_argv[0] == "--":
                command_argv = command_argv[1:]
            if not command_argv:
                parser.error("no-egress run requires -- <command>")
            result = run_under_no_egress(command_argv)
            if result.status != "egress_enforced":
                print(json.dumps(result.to_dict(), indent=2, sort_keys=True), file=sys.stderr)
            return result.returncode

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
                        concurrency=args.concurrency,
                        connection_factory=connect,
                    )
            print(
                "extract: "
                f"{result.created} claims created / {result.processed} segments processed "
                f"({result.skipped} skipped, {result.failed} failed)"
            )
            return 0 if result.failed == 0 else 1

        if args.command == "re-extract":
            try:
                with connect() as conn:
                    apply_phase3_reclassification_invalidations(conn)
                    result = run_re_extract(
                        conn,
                        target_version=args.version,
                        batch_size=args.batch_size,
                        limit=args.limit,
                        source_id=args.source_id,
                        diff_sample=args.diff_sample,
                        dry_run=args.dry_run,
                    )
            except ReExtractError as exc:
                print(f"re-extract: {exc}", file=sys.stderr)
                return 1
            print_re_extract_result(result)
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
            return 0 if (segment_result.failed == 0 and embed_result.failed == 0) else 1

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
                        client=extractor_client if args.extract_concurrency <= 1 else None,
                        client_factory=(
                            IkLlamaExtractorClient if args.extract_concurrency > 1 else None
                        ),
                        health_smoke=False,
                        concurrency=args.extract_concurrency,
                        connection_factory=connect,
                    )
                    totals["extract_processed"] += extract_result.processed
                    totals["extract_created"] += extract_result.created
                    totals["extract_failed"] += extract_result.failed
                    if extract_result.failed:
                        totals["consolidate_skipped"] += 1
                        skip_reason = f"skipped after {extract_result.failed} extraction failure(s)"
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

        if args.command == "phase4-refresh":
            with connect() as conn:
                refresh_current_beliefs(conn)
                conn.commit()
            print("phase4 refresh: current_beliefs refreshed")
            return 0

        if args.command == "phase4-build-entities":
            with connect() as conn:
                refresh_current_beliefs(conn)
                result = build_deterministic_entities(conn, limit=args.limit)
                conn.commit()
            print_phase4_entity_result(result)
            return 0

        if args.command == "phase4-smoke":
            with connect() as conn:
                result = run_phase4_smoke(conn, limit=args.limit)
                conn.commit()
            print_phase4_smoke_result(result)
            return 0

        if args.command == "review-belief":
            with connect() as conn:
                if args.action == "accept":
                    action_result = accept_belief(
                        conn,
                        args.belief_id,
                        actor=args.actor,
                        note=args.note,
                    )
                elif args.action == "reject":
                    action_result = reject_review_belief(
                        conn,
                        args.belief_id,
                        actor=args.actor,
                        note=args.note,
                    )
                elif args.action == "correct":
                    if args.note is None:
                        parser.error("review-belief correct requires --note")
                    action_result = correct_belief(
                        conn,
                        args.belief_id,
                        args.note,
                        actor=args.actor,
                    )
                else:
                    action_result = promote_to_pinned(
                        conn,
                        args.belief_id,
                        actor=args.actor,
                        note=args.note,
                    )
                conn.commit()
            print(
                "review-belief: "
                f"{action_result.action_kind} {action_result.action_status} "
                f"belief={action_result.belief_id} "
                f"request_uuid={action_result.request_uuid}"
            )
            if action_result.capture_id:
                print(f"  correction_capture_id={action_result.capture_id}")
            return 0

        if args.command == "phase3-interview-start":
            return run_phase3_interview_start(args)
        if args.command == "phase3-interview-resume":
            return run_phase3_interview_resume(args)
        if args.command == "phase3-interview-history":
            return run_phase3_interview_history(args)
        if args.command == "phase3-interview-export":
            return run_phase3_interview_export(args)
        if args.command == "phase3-interview-list-sessions":
            return run_phase3_interview_list_sessions(args)
        if args.command == "phase3-interview-coverage":
            return run_phase3_interview_coverage(args)
        if args.command == "phase3-interview-enable-active-learning":
            return run_phase3_interview_enable_active_learning(args)
        if args.command == "phase3-interview-serve":
            return run_phase3_interview_serve(args)
        if args.command == "phase3-bench-review-serve":
            from engram.bench_review.cli import (
                run_phase3_bench_review_serve,
            )

            return run_phase3_bench_review_serve(args)
        if args.command == "phase3-bench-review-status":
            from engram.bench_review.cli import (
                run_phase3_bench_review_status,
            )

            return run_phase3_bench_review_status(args)
        if args.command == "phase3-bench-review-export":
            from engram.bench_review.cli import (
                run_phase3_bench_review_export,
            )

            return run_phase3_bench_review_export(args)
    except (
        ChatGPTIngestConflict,
        ClaudeIngestConflict,
        GeminiIngestConflict,
        StriatumIngestConflict,
    ) as exc:
        print(f"ingest conflict: {exc}", file=sys.stderr)
        return 1
    except (StriatumBundleError, FileNotFoundError) as exc:
        print(f"ingest-striatum: {exc}", file=sys.stderr)
        return 1
    except Phase3SchemaPreflightError as exc:
        print(f"phase3 preflight failed: {exc}", file=sys.stderr)
        return 1
    except Phase4SchemaPreflightError as exc:
        print(f"phase4 preflight failed: {exc}", file=sys.stderr)
        return 1
    except (GoldLabelStorageError, GoldLabelVerdictError) as exc:
        print(f"phase3 interview: {exc}", file=sys.stderr)
        return 1
    except ClaimGroundingError as exc:
        print(f"claim-grounding: {exc}", file=sys.stderr)
        return 2
    except EntityGroundingCliError as exc:
        print(f"entity-grounding: {exc}", file=sys.stderr)
        return 2
    except NoEgressError as exc:
        print(f"no-egress: {exc}", file=sys.stderr)
        return 2

    parser.error(f"unknown command: {args.command}")
    return 2


def phase3_schema_preflight(conn) -> None:
    errors = migration_integrity_errors(conn)
    schema_migrations_exists = (
        conn.execute("SELECT to_regclass('public.schema_migrations')").fetchone()[0] is not None
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
            "description",
            "subject_kind_hint",
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
    table_columns: dict[str, set[str]] = {}
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
        table_columns[table] = existing_columns
        for column in columns:
            if column not in existing_columns:
                errors.append(f"{table}.{column} is missing")
    _check_phase3_predicate_vocabulary(conn, existing_tables, table_columns, errors)
    _check_phase3_indexes(conn, errors)
    _check_phase3_functions(conn, errors)
    _check_phase3_triggers(conn, errors)
    if errors:
        raise Phase3SchemaPreflightError("; ".join(errors))


def _check_phase3_predicate_vocabulary(
    conn,
    existing_tables: set[str],
    table_columns: dict[str, set[str]],
    errors: list[str],
) -> None:
    if "predicate_vocabulary" not in existing_tables:
        return
    if {
        "predicate",
        "stability_class",
        "cardinality_class",
        "object_kind",
        "group_object_keys",
        "required_object_keys",
        "description",
        "subject_kind_hint",
    } - table_columns.get("predicate_vocabulary", set()):
        return

    actual = {
        row[0]: {
            "predicate": row[0],
            "stability_class": row[1],
            "cardinality_class": row[2],
            "object_kind": row[3],
            "group_object_keys": list(row[4]),
            "required_object_keys": list(row[5]),
            "description": row[6],
            "subject_kind_hint": row[7],
        }
        for row in conn.execute(
            """
            SELECT predicate, stability_class, cardinality_class, object_kind,
                   group_object_keys, required_object_keys, description,
                   subject_kind_hint
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
            "description",
            "subject_kind_hint",
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
                (
                    "(segment_id, extraction_prompt_version, extraction_model_version, "
                    "request_profile_version)"
                ),
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
            errors.append(f"{trigger_name} trigger is on {table_name}, expected {spec['table']}")
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
    print(f"messages: {result.messages_inserted} inserted / {result.messages_seen} seen")


def print_striatum_ingest_result(result) -> None:
    print(f"source_id={result.source_id}")
    print(f"bundle_id={result.bundle_id}")
    print(f"repo={result.repo}")
    print(
        "striatum records: "
        f"{result.records_inserted} inserted / {result.records_seen} seen "
        f"({result.records_skipped} skipped)"
    )
    if result.row_counts:
        counts = ", ".join(f"{kind}={count}" for kind, count in sorted(result.row_counts.items()))
        print(f"  sub_kind: {counts}")


def print_phase_projection_result(result: Any, *, tenant_id: str, corpus_id: str) -> None:
    """Print a compact summary for Striatum projection runs."""
    fields = {
        "generation_id": _projection_result_value(result, "generation_id"),
        "captures_seen": _projection_result_value(result, "captures_seen"),
        "captures_processed": _projection_result_value(result, "captures_processed"),
        "references_seen": _projection_result_value(result, "references_seen"),
        "references_inserted": _projection_result_value(result, "references_inserted"),
        "references_created": _projection_result_value(result, "references_created"),
        "references_activated": _projection_result_value(result, "references_activated"),
        "references_active": _projection_result_value(result, "references_active"),
        "reused_active_generation": _projection_result_value(result, "reused_active_generation"),
        "activated": _projection_result_value(result, "activated"),
    }
    suffix = " ".join(f"{key}={value}" for key, value in fields.items() if value is not None)
    line = f"phase-projection: tenant={tenant_id} corpus={corpus_id}"
    if suffix:
        line = f"{line} {suffix}"
    print(line)


def _projection_result_value(result: Any, key: str) -> Any:
    """Read a projection result field from either a dataclass-like object or dict."""
    if isinstance(result, dict):
        return result.get(key)
    return getattr(result, key, None)


def print_embed_result(result) -> None:
    print(
        "embed: "
        f"{result.created} segment embeddings created / {result.processed} segments processed "
        f"({result.cache_hits} cache hits, {result.activated} generations activated, "
        f"{result.failed} failed)"
    )


def print_phase4_entity_result(result) -> None:
    print(
        "phase4 entities: "
        f"{result.beliefs_processed} beliefs processed / "
        f"{result.entities_created} entities created / "
        f"{result.entities_reused} entities reused / "
        f"{result.edges_created} edges created / "
        f"{result.edges_reused} edges reused"
    )


def print_phase4_smoke_result(result) -> None:
    print(
        "phase4 smoke: "
        f"current_beliefs={result.current_beliefs} "
        f"review_queue_items={result.review_queue_items} "
        f"beliefs_processed={result.beliefs_processed} "
        f"entities_created={result.entities_created} "
        f"entities_reused={result.entities_reused} "
        f"edges_created={result.edges_created} "
        f"edges_reused={result.edges_reused} "
        f"neighborhood_rows={result.neighborhood_rows}"
    )


def run_phase_projection(conn: Any, *, tenant_id: str, corpus_id: str) -> Any:
    """Run the Striatum projection worker."""
    from engram.striatum_projection import project_striatum_references

    return project_striatum_references(conn, tenant_id=tenant_id, corpus_id=corpus_id)


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
    client_factory=None,
    concurrency: int = DEFAULT_EXTRACTION_CONCURRENCY,
    connection_factory=None,
    health_smoke: bool = True,
):
    totals = {"processed": 0, "created": 0, "skipped": 0, "failed": 0}
    model_id = model_version
    extractor_client = client
    if health_smoke:
        model_id = model_id or default_extractor_model_id()
        extractor_client = extractor_client or IkLlamaExtractorClient()
        run_extractor_health_smoke(extractor_client, model_id=model_id)
    workers = max(1, concurrency)
    while limit is None or totals["processed"] < limit:
        remaining = None if limit is None else limit - totals["processed"]
        batch_limit = batch_size if remaining is None else min(batch_size, remaining)
        if workers > 1:
            resolved_client_factory: Any = client_factory
            if resolved_client_factory is None and client is not None:

                def shared_client_factory() -> Any:
                    return client

                resolved_client_factory = shared_client_factory

            result = extract_pending_claims_concurrently(
                conn,
                batch_size=batch_size,
                connection_factory=connection_factory or connect,
                model_version=model_id,
                prompt_version=prompt_version,
                limit=batch_limit,
                conversation_id=conversation_id,
                client_factory=resolved_client_factory,
                max_workers=workers,
                progress_callback=print_extract_progress,
            )
        else:
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
            f"segment probe failed elapsed={elapsed:.1f}s error={payload['error']}",
            flush=True,
        )


def print_embed_progress(event: str, payload: dict[str, Any]) -> None:
    if event == "embed_start":
        if payload["index"] == 1 or payload["index"] % 25 == 0:
            print(
                f"embed {payload['index']}/{payload['batch_size']} segment={payload['segment_id']}",
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
            f"extract segment={payload['segment_id']} failed elapsed={payload['elapsed']:.1f}s",
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


def run_re_extract(
    conn,
    *,
    target_version: str,
    batch_size: int,
    limit: int | None,
    source_id: str | None,
    diff_sample: int,
    dry_run: bool,
) -> ReExtractResult:
    """Drive the RFC 0017 Part 2 re-extraction orchestrator.

    Health-smokes the extractor backend before and after the run when not in
    dry-run mode, mirroring the ``extract`` subcommand's safety check.
    """

    model_id: str | None = None
    extractor_client = None
    if not dry_run:
        model_id = default_extractor_model_id()
        extractor_client = IkLlamaExtractorClient()
        run_extractor_health_smoke(extractor_client, model_id=model_id)
    result = re_extract(
        conn,
        target_version,
        batch_size=batch_size,
        limit=limit,
        source_id=source_id,
        diff_sample=diff_sample,
        dry_run=dry_run,
        model_version=model_id,
        client=extractor_client,
        progress_callback=print_re_extract_progress,
    )
    if not dry_run and result.processed and extractor_client is not None:
        run_extractor_health_smoke(extractor_client, model_id=model_id)
    conn.commit()
    return result


def print_re_extract_progress(event: str, payload: dict[str, Any]) -> None:
    if event == "re_extract_start":
        print(
            f"re-extract segment={payload['segment_id']}",
            flush=True,
        )
        return
    if event == "re_extract_done":
        print(
            f"re-extract segment={payload['segment_id']} done "
            f"claims={payload['claim_count']} "
            f"elapsed={payload['elapsed']:.1f}s",
            flush=True,
        )
        return
    if event == "re_extract_failed":
        print(
            f"re-extract segment={payload['segment_id']} failed elapsed={payload['elapsed']:.1f}s",
            flush=True,
        )


def print_re_extract_result(result: ReExtractResult) -> None:
    plan = result.plan
    if result.dry_run:
        print(
            "re-extract DRY-RUN target="
            f"{result.target_version} "
            f"current={plan.current_version} "
            f"segments={plan.segment_count}"
        )
    else:
        print(
            "re-extract target="
            f"{result.target_version} "
            f"current={plan.current_version} "
            f"segments={plan.segment_count} "
            f"processed={result.processed} "
            f"created={result.created} "
            f"skipped={result.skipped} "
            f"failed={result.failed}"
        )
    if plan.source_kind_counts:
        breakdown = ", ".join(
            f"{kind}={count}" for kind, count in sorted(plan.source_kind_counts.items())
        )
        print(f"  source_kind: {breakdown}")
    if plan.prior_version_counts:
        prior = ", ".join(
            f"{version}={count}" for version, count in sorted(plan.prior_version_counts.items())
        )
        print(f"  prior_versions: {prior}")
    if not result.dry_run:
        if result.coverage_gaps:
            print(f"coverage gaps ({len(result.coverage_gaps)}):")
            print("  segment_id                            prior_claims  prior_versions")
            for gap in result.coverage_gaps:
                versions = ",".join(gap["prior_versions"]) or "-"
                print(f"  {gap['segment_id']:<38} {gap['prior_claim_count']:<13} {versions}")
        else:
            print("coverage gaps: none")
        if result.diff_samples:
            print(f"diff sample ({len(result.diff_samples)}):")
            for sample in result.diff_samples:
                prior_predicates = (
                    ",".join(f"{p}={c}" for p, c in sorted(sample["prior_predicates"].items()))
                    or "-"
                )
                new_predicates = (
                    ",".join(f"{p}={c}" for p, c in sorted(sample["new_predicates"].items())) or "-"
                )
                print(
                    "  segment="
                    f"{sample['segment_id']} "
                    f"prior_count={sample['prior_claim_count']} "
                    f"new_count={sample['new_claim_count']}"
                )
                print(f"    prior_predicates: {prior_predicates}")
                print(f"    new_predicates:   {new_predicates}")
        else:
            print("diff sample: no segments with claims under both versions")
        print(
            "hint: run `engram consolidate --rebuild` to reconsolidate beliefs "
            "from the new claim version (RFC 0017 Part 2 step 3)."
        )


def _prompt_verdict(stdin_isatty: bool) -> str | None:
    """Prompt until a valid verdict is entered. Returns None on EOF/q.

    The prompt copy and verdict vocabulary live in
    :mod:`engram.interview.render` so the CLI and the web UI share one
    source of truth.
    """
    while True:
        try:
            raw = input(VERDICT_PROMPT).strip().lower()
        except EOFError:
            return None
        if raw in {"q", "quit", "save-and-quit"}:
            return None
        canonical = VERDICT_ALIAS.get(raw, raw)
        if canonical in VERDICT_VALID:
            return canonical
        print(
            f"  invalid verdict: {raw!r}; choose from {sorted(VERDICT_VALID)} "
            "or 'q' to save and quit"
        )


def _prompt_rationale(verdict: str) -> str | None:
    """Verdict-specific rationale prompt; ``true``/``skip`` skip the prompt.

    Wraps :func:`engram.interview.render.rationale_prompt_for` with the
    blocking ``input()`` call that only the CLI needs.
    """
    prompt = rationale_prompt_for(verdict)
    if prompt is None:
        return None
    try:
        raw = input(prompt).strip()
    except EOFError:
        return None
    return raw or None


def _run_phase3_interview_prompt_loop(
    conn,
    *,
    session_id: str,
    targets: list[SessionTarget],
    total: int,
) -> tuple[int, dict[str, int], bool]:
    """Prompt through materialized session targets.

    Returns ``(answered_count, verdict_counts, completed)``. ``completed`` is
    false when the operator saves/quits or interrupts before exhausting the
    provided target list.
    """
    print("verdicts: t/f/stale/unsupported/unsure/skip   q to save and quit\n")
    agent = InterviewAgent(
        conn,
        sampler_id=INTERVIEW_SAMPLER_ID,
        sampler_version=INTERVIEW_SAMPLER_VERSION,
    )
    counts: dict[str, int] = {}
    answered = 0
    try:
        for target_row in targets:
            idx = target_row.idx + 1
            target = session_target_to_sampled(target_row)
            display = fetch_target_display(conn, target)
            print(format_header(target, idx, total))
            print(f"  {format_summary_line(display)}")
            ev_dates_line = format_evidence_dates(display)
            if ev_dates_line is not None:
                print(f"  {ev_dates_line}")
            excerpts = display.get("excerpts") or []
            if excerpts:
                for line in format_evidence_excerpts(excerpts, display.get("evidence_count", 0)):
                    print(line)
            question = pick_question(target, display)
            print(f"  {question}")
            verdict = _prompt_verdict(sys.stdin.isatty())
            if verdict is None:
                print(
                    f"\nsaved-and-quit at [{idx}/{total}]; session "
                    f"{session_id} stays open. Resume with: "
                    f"engram phase3 interview resume --session-id {session_id}"
                )
                return answered, counts, False
            rationale = _prompt_rationale(verdict)
            try:
                agent.record_verdict(session_id, target, verdict, rationale=rationale)
                conn.commit()
            except (GoldLabelStorageError, GoldLabelVerdictError) as exc:
                conn.rollback()
                print(f"  record failed: {exc}", file=sys.stderr)
                print("  (continuing; the target was not labeled.)", file=sys.stderr)
                continue
            counts[verdict] = counts.get(verdict, 0) + 1
            answered += 1
            print()
    except KeyboardInterrupt:
        next_idx = targets[min(answered, len(targets) - 1)].idx + 1 if targets else 1
        print(
            f"\n\ninterrupted at [{next_idx}/{total}]; session "
            f"{session_id} stays open. Resume with: "
            f"engram phase3 interview resume --session-id {session_id}"
        )
        return answered, counts, False
    return answered, counts, True


def run_phase3_interview_start(args) -> int:  # type: ignore[no-untyped-def]
    """RFC 0021 v1 interview loop: open a session, sample n targets, prompt the
    operator one verdict at a time, commit each row as it's answered.

    Pass ``--non-interactive`` to skip the prompt loop (used by tests and
    scripts that wire their own UX on top of :class:`InterviewAgent`).
    """

    seed = args.seed if args.seed is not None else int.from_bytes(os.urandom(4), "big")
    n = max(0, int(args.n))
    interactive = not bool(getattr(args, "non_interactive", False)) and sys.stdin.isatty()
    strata_filters = dict(getattr(args, "strata", {}) or {})
    with connect() as conn:
        active_learning_signal = get_active_learning_signal_version(conn)
        session_id = insert_session(
            conn,
            seed=seed,
            sampler_id=INTERVIEW_SAMPLER_ID,
            sampler_version=INTERVIEW_SAMPLER_VERSION,
            strata_weights=strata_filters,
        )
        conn.commit()
        sampler = GoldLabelSampler(
            conn,
            seed=seed,
            strata_weights=strata_filters,
            include_superseded=bool(args.include_superseded),
            ignore_cooldown=bool(args.ignore_cooldown),
            active_learning_signal_version=active_learning_signal,
            ignore_reask_cap=bool(getattr(args, "ignore_reask_cap", False)),
        )
        sampled = sampler.sample(n)

        if sampled:
            # Materialize the sampled order before prompting so CLI and web
            # resume share the same stable target list.
            insert_session_targets(conn, session_id=session_id, sampled=sampled)
            conn.commit()

        if not interactive:
            print(
                "phase3 interview start: "
                f"session={session_id} seed={seed} "
                f"sampler={INTERVIEW_SAMPLER_ID}@{INTERVIEW_SAMPLER_VERSION} "
                f"sampled={len(sampled)} "
                f"active_learning={active_learning_signal or 'off'} "
                f"strata={strata_filters or {}} "
                "(non-interactive)"
            )
            return 0

        if not sampled:
            mark_session_completed(conn, session_id)
            conn.commit()
            print(
                "phase3 interview start: no targets matched "
                "(empty corpus, all on cooldown, or current_beliefs not refreshed). "
                f"session={session_id} marked complete."
            )
            return 0

        print(
            f"session: {session_id}  seed: {seed}  "
            f"sampler: {INTERVIEW_SAMPLER_ID}@{INTERVIEW_SAMPLER_VERSION}  "
            f"sampled: {len(sampled)}  "
            f"active_learning: {active_learning_signal or 'off'}"
        )
        targets = unanswered_session_targets(conn, session_id=session_id)
        answered, counts, completed = _run_phase3_interview_prompt_loop(
            conn,
            session_id=session_id,
            targets=targets,
            total=len(sampled),
        )
        if not completed:
            return 0

        mark_session_completed(conn, session_id)
        conn.commit()
        summary = ", ".join(f"{k}={v}" for k, v in sorted(counts.items())) or "no verdicts"
        print(f"session {session_id} complete: {answered}/{len(sampled)} answered ({summary})")
        return 0


def run_phase3_interview_resume(args) -> int:  # type: ignore[no-untyped-def]
    """Resume an open CLI interview session from materialized targets."""
    if args.session_id is None:
        print(
            "phase3 interview resume: provide --session-id; "
            "use `engram phase3 interview list-sessions --state open` to discover.",
            file=sys.stderr,
        )
        return 2
    with connect() as conn:
        sessions = list_sessions(conn, state="all")
    matched = [s for s in sessions if s.session_id == args.session_id]
    if not matched:
        print(
            f"phase3 interview resume: session {args.session_id} not found",
            file=sys.stderr,
        )
        return 1
    session = matched[0]
    state = "open" if session.completed_at is None else "completed"
    with connect() as conn:
        targets = unanswered_session_targets(conn, session_id=args.session_id)
        label_count_row = conn.execute(
            "SELECT count(*) FROM gold_labels WHERE session_id = %s",
            (args.session_id,),
        ).fetchone()
        label_count = int(label_count_row[0]) if label_count_row is not None else 0
        total = (
            len(targets)
            + label_count
        )
        if state == "completed":
            print(
                "phase3 interview resume: "
                f"session={session.session_id} state=completed "
                f"started_at={session.started_at.isoformat()}"
            )
            return 0
        if not targets:
            mark_session_completed(conn, args.session_id)
            conn.commit()
            print(
                "phase3 interview resume: "
                f"session={session.session_id} had no unanswered targets; marked completed"
            )
            return 0
        if not sys.stdin.isatty():
            next_idx = targets[0].idx + 1
            print(
                "phase3 interview resume: "
                f"session={session.session_id} state=open "
                f"unanswered={len(targets)} next=q/{next_idx} "
                "(run from a TTY to continue the prompt loop)"
            )
            return 0
        print(
            "phase3 interview resume: "
            f"session={session.session_id} state=open "
            f"unanswered={len(targets)} started_at={session.started_at.isoformat()}"
        )
        answered, counts, completed = _run_phase3_interview_prompt_loop(
            conn,
            session_id=args.session_id,
            targets=targets,
            total=total,
        )
        if not completed:
            return 0
        mark_session_completed(conn, args.session_id)
        conn.commit()
    summary = ", ".join(f"{k}={v}" for k, v in sorted(counts.items())) or "no verdicts"
    print(f"session {args.session_id} complete: {answered}/{len(targets)} answered ({summary})")
    return 0


def run_phase3_interview_history(args) -> int:  # type: ignore[no-untyped-def]
    """Print gold-label verdict history for ``--target``."""
    if args.target is None:
        print(
            "phase3 interview history: provide --target <uuid>",
            file=sys.stderr,
        )
        return 2
    since: datetime | None = None
    if args.since is not None:
        try:
            since = _parse_cli_datetime(args.since)
        except ValueError as exc:
            print(f"phase3 interview history: invalid --since: {exc}", file=sys.stderr)
            return 2
    where = "WHERE target_id = %s"
    params: list[Any] = [args.target]
    if since is not None:
        where += " AND answered_at >= %s"
        params.append(since)
    with connect() as conn:
        rows = conn.execute(
            f"""
            SELECT id::text, target_kind, verdict, answered_at
            FROM gold_labels
            {where}
            ORDER BY answered_at DESC
            """,
            tuple(params),
        ).fetchall()
    if not rows:
        print(f"phase3 interview history: no rows for target {args.target}")
        return 0
    print(f"phase3 interview history: {len(rows)} row(s) for target {args.target}")
    for row in rows:
        print(f"  {row[1]} verdict={row[2]} answered_at={row[3].isoformat()}")
    return 0


def run_phase3_interview_export(args) -> int:  # type: ignore[no-untyped-def]
    """RFC 0021 v1: JSONL export with the fail-closed Tier 1 default ceiling."""
    tier_max = int(args.privacy_tier_max)
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT
                id::text,
                session_id::text,
                target_kind,
                target_id::text,
                verdict,
                rationale,
                stability_class,
                conf_band,
                recency_band,
                belief_status,
                privacy_tier,
                evidence_excerpt,
                answered_at
            FROM gold_labels
            ORDER BY answered_at
            """,
        ).fetchall()
    output_lines: list[str] = []
    for row in rows:
        decision = decide_local_release(
            privacy_tier=int(row[10]),
            privacy_tier_ceiling=tier_max,
            target_surface="external_export",
            purpose="phase3_interview_export",
            source_kind="gold_label",
        )
        if decision.action != "allow":
            continue
        output_lines.append(
            json.dumps(
                {
                    "id": row[0],
                    "session_id": row[1],
                    "target_kind": row[2],
                    "target_id": row[3],
                    "verdict": row[4],
                    "rationale": row[5],
                    "stability_class": row[6],
                    "conf_band": row[7],
                    "recency_band": row[8],
                    "belief_status": row[9],
                    "privacy_tier": row[10],
                    "evidence_excerpt": row[11],
                    "answered_at": row[12].isoformat() if row[12] else None,
                }
            )
        )
    payload = "\n".join(output_lines)
    if args.output is not None:
        Path(args.output).write_text(payload + ("\n" if payload else ""), encoding="utf-8")
        print(
            "phase3 interview export: "
            f"{len(output_lines)} row(s) written to {args.output} "
            f"(privacy_tier_max={tier_max})"
        )
    else:
        if payload:
            print(payload)
        print(
            f"phase3 interview export: {len(output_lines)} row(s) (privacy_tier_max={tier_max})",
            file=sys.stderr,
        )
    return 0


def run_phase3_interview_list_sessions(args) -> int:  # type: ignore[no-untyped-def]
    state = args.state if args.state in ("open", "completed") else None
    with connect() as conn:
        sessions = list_sessions(conn, state=state)
    print(f"phase3 interview list-sessions: {len(sessions)} row(s) state={args.state}")
    for session in sessions:
        completed = "open" if session.completed_at is None else session.completed_at.isoformat()
        print(
            f"  {session.session_id} seed={session.seed} "
            f"sampler={session.sampler_id}@{session.sampler_version} "
            f"started_at={session.started_at.isoformat()} completed={completed}"
        )
    return 0


def run_phase3_interview_coverage(args) -> int:  # type: ignore[no-untyped-def]
    """RFC 0021 v1 stub: counts rows by stratum slice ``stability_class``."""
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT stability_class, count(*)
            FROM gold_labels
            GROUP BY stability_class
            ORDER BY stability_class
            """,
        ).fetchall()
    print(
        f"phase3 interview coverage strata={args.strata!r}: {sum(r[1] for r in rows)} row(s) total"
    )
    for stability_class, count in rows:
        print(f"  {stability_class}: {count}")
    return 0


def run_phase3_interview_enable_active_learning(args) -> int:  # type: ignore[no-untyped-def]
    """Persist the active-learning signal version stamped onto new sessions."""
    signal_version = str(args.signal_version).strip()
    if not signal_version:
        print(
            "phase3 interview enable-active-learning: --signal-version must not be blank",
            file=sys.stderr,
        )
        return 2
    with connect() as conn:
        event_id = insert_active_learning_event(conn, signal_version=signal_version)
        conn.commit()
    print(
        "phase3 interview enable-active-learning: "
        f"signal_version={signal_version} event_id={event_id} "
        "(will be stamped onto subsequent session targets)"
    )
    return 0


# RFC 0027 / Spec 0027: loopback hosts the serve driver accepts. The
# `--allow-non-loopback` escape clause is intentionally absent (F005); a
# follow-on RFC will land non-loopback bind if/when the design lands.
_SERVE_LOOPBACK_HOSTS: frozenset[str] = frozenset({"127.0.0.1", "localhost", "::1"})


def run_phase3_interview_serve(args) -> int:  # type: ignore[no-untyped-def]
    """RFC 0027 v1: run the local FastAPI/htmx web UI for the gold-set interview.

    The driver enforces the loopback-only invariant before importing FastAPI
    so that the CLI can refuse a non-loopback bind even on installs that
    don't have the optional ``engram[serve]`` extras. The
    ``engram.interview.web`` import is deferred until after the host check
    so that non-serve subcommands (and headless installs) never load
    FastAPI/Uvicorn/Jinja2.
    """

    host = str(args.host)
    if host not in _SERVE_LOOPBACK_HOSTS:
        print(
            "phase3 interview serve: refusing non-loopback host "
            f"(--host={host}); v1 is loopback-only",
            file=sys.stderr,
        )
        sys.exit(8)

    try:
        import uvicorn

        from engram.interview.web import app
    except ImportError as exc:
        print(
            "phase3 interview serve: missing dependency "
            f"({exc}). Install with: pip install engram[serve]",
            file=sys.stderr,
        )
        sys.exit(2)

    port = int(args.port)
    print(
        f"phase3 interview serve: listening on http://{host}:{port} "
        "(ctrl-c to stop; non-loopback hosts refused)"
    )
    uvicorn.run(app, host=host, port=port, workers=1, log_level="warning")
    return 0


# Bind agent type so unused-import linters don't strip it; the agent is
# re-exported for operators driving the loop programmatically.
_ = InterviewAgent
_ = mark_session_completed


if __name__ == "__main__":
    raise SystemExit(main())
