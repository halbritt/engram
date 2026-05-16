"""Build-artifact importer (RFC 0050 Layer 2).

Walks a local artifact directory and ingests JUnit XML, coverage JSON/XML,
benchmark JSON, lint output (ruff JSON, eslint JSON, pyright JSON), and
plain log files. No outbound network. No remote artifact retrieval.

Identity: ``(artifact_root_id, relative_path, content_hash)`` where
``artifact_root_id`` is the sha256 of the resolved root path. This keeps the
importer idempotent against the same on-disk artifact set while still
recording multiple revisions of the same artifact path when the content
changes.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import datetime, timezone  # noqa: I001 — used by record_source_audit timestamp
from pathlib import Path
from typing import Any

import psycopg
from psycopg.types.json import Jsonb

from engram.source_audit import compute_input_signature, record_source_audit

SOURCE_KIND = "build_artifact"
ADAPTER_VERSION = "build_artifact_import.v1"
DEFAULT_TENANT_ID = "personal"
DEFAULT_CORPUS_ID = "personal"

# Module-top tunables (RFC 0012 § Tunables).
ENGRAM_BUILD_ARTIFACT_MAX_BYTES = int(
    os.environ.get("ENGRAM_BUILD_ARTIFACT_MAX_BYTES", str(64 * 1024 * 1024))  # 64 MiB
)
ENGRAM_BUILD_ARTIFACT_LOG_TAIL_BYTES = int(
    os.environ.get("ENGRAM_BUILD_ARTIFACT_LOG_TAIL_BYTES", "8192")
)
ENGRAM_BUILD_ARTIFACT_INCLUDE_LOG_BODY = (
    os.environ.get("ENGRAM_BUILD_ARTIFACT_INCLUDE_LOG_BODY", "0") == "1"
)
ENGRAM_BUILD_ARTIFACT_REDACTION_PATTERN = os.environ.get(
    "ENGRAM_BUILD_ARTIFACT_REDACTION_PATTERN",
    # Conservative default: matches common secret-token shapes (xoxb, AKIA, ghp_, etc.).
    # Extend via env var when adapter use cases need more coverage.
    r"\b(?:xox[abprs]-[A-Za-z0-9-]+|AKIA[0-9A-Z]{16}|ghp_[A-Za-z0-9]{20,}|"
    r"glpat-[A-Za-z0-9-]+|password\s*=\s*\S+|token\s*=\s*\S+)\b",
)

_REDACTION_RE = re.compile(ENGRAM_BUILD_ARTIFACT_REDACTION_PATTERN, re.IGNORECASE)

# Closed file-extension routing table. New families land here, not in the
# importer body.
_KIND_BY_NAME: tuple[tuple[str, str], ...] = (
    ("junit", "junit_xml"),
    ("test-results", "junit_xml"),
    ("coverage", "coverage_report"),
    ("cov", "coverage_report"),
    ("benchmark", "benchmark_json"),
    ("bench", "benchmark_json"),
    ("ruff", "lint_report"),
    ("eslint", "lint_report"),
    ("pyright", "lint_report"),
    ("lint", "lint_report"),
)

_KIND_BY_EXT: dict[str, str] = {
    ".log": "log_file",
    ".txt": "log_file",
    ".out": "log_file",
}


class BuildArtifactImportError(RuntimeError):
    """Root of the build-artifact import exception family."""


class BuildArtifactParseError(BuildArtifactImportError):
    """Raised when an artifact file cannot be parsed for its declared kind."""


class BuildArtifactConflict(BuildArtifactImportError):
    """Raised when an existing artifact row's content hash differs from input."""


@dataclass(frozen=True)
class BuildArtifactFinding:
    """One parsed finding from a build artifact."""

    finding_index: int
    finding_kind: str
    status: str | None = None
    name: str | None = None
    file_path: str | None = None
    line_number: int | None = None
    column_number: int | None = None
    duration_ms: float | None = None
    severity: str | None = None
    message: str | None = None
    raw_payload: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class BuildArtifactRecord:
    """A single artifact ready to land in ``build_artifacts``."""

    relative_path: str
    artifact_kind: str
    content_hash: str
    size_bytes: int
    mtime: datetime | None
    findings: tuple[BuildArtifactFinding, ...]
    raw_payload: dict[str, Any]
    redacted: bool


@dataclass(frozen=True)
class BuildArtifactImportResult:
    """Summary of one ``import_build_artifacts`` invocation."""

    source_id: str
    artifact_root_id: str
    artifacts_inserted: int
    artifacts_seen: int
    artifacts_skipped: int
    findings_inserted: int
    coverage_gap_count: int
    redacted_artifacts: int


def import_build_artifacts(
    conn: psycopg.Connection,
    root: Path,
    *,
    tenant_id: str = DEFAULT_TENANT_ID,
    corpus_id: str = DEFAULT_CORPUS_ID,
    run_id: str | None = None,
    commit_sha: str | None = None,
    repo_label: str | None = None,
    dry_run: bool = False,
) -> BuildArtifactImportResult:
    """Walk ``root`` and ingest build artifacts into Engram."""
    if tenant_id.strip() == "" or corpus_id.strip() == "":
        raise ValueError("tenant_id and corpus_id must be non-empty")

    root_path = Path(root).expanduser().resolve()
    if not root_path.is_dir():
        raise BuildArtifactImportError(f"artifact root is not a directory: {root_path}")

    artifact_root_id = _artifact_root_id(root_path)
    records = list(_walk_artifacts(root_path))

    if dry_run:
        return BuildArtifactImportResult(
            source_id="",
            artifact_root_id=artifact_root_id,
            artifacts_inserted=0,
            artifacts_seen=len(records),
            artifacts_skipped=0,
            findings_inserted=0,
            coverage_gap_count=0,
            redacted_artifacts=sum(1 for r in records if r.redacted),
        )

    inserted = 0
    skipped = 0
    findings_inserted = 0
    coverage_gap_count = 0
    redacted = 0

    with conn.transaction():
        source_id = _get_or_create_source(
            conn,
            artifact_root_id=artifact_root_id,
            tenant_id=tenant_id,
            corpus_id=corpus_id,
            root_path=root_path,
            repo_label=repo_label,
        )
        for record in records:
            if record.redacted:
                redacted += 1
            artifact_id, was_inserted = _insert_artifact(
                conn,
                source_id=source_id,
                tenant_id=tenant_id,
                corpus_id=corpus_id,
                artifact_root_id=artifact_root_id,
                record=record,
                run_id=run_id,
                commit_sha=commit_sha,
            )
            if was_inserted:
                inserted += 1
            else:
                skipped += 1
                continue
            for finding in record.findings:
                if _insert_finding(
                    conn,
                    artifact_id=artifact_id,
                    tenant_id=tenant_id,
                    corpus_id=corpus_id,
                    finding=finding,
                ):
                    findings_inserted += 1
            if record.artifact_kind == "other":
                _emit_coverage_gap(
                    conn,
                    source_id=source_id,
                    tenant_id=tenant_id,
                    corpus_id=corpus_id,
                    artifact_root_id=artifact_root_id,
                    relative_path=record.relative_path,
                    reason="unrecognized_artifact_kind",
                )
                coverage_gap_count += 1

        record_source_audit(
            conn,
            tenant_id=tenant_id,
            corpus_id=corpus_id,
            source_kind=SOURCE_KIND,
            source_id=source_id,
            adapter_version=ADAPTER_VERSION,
            input_signature=compute_input_signature(
                [artifact_root_id, *sorted(r.content_hash for r in records)]
            ),
            outcome="ok",
            rows_inserted=inserted,
            rows_skipped=skipped,
            coverage_gap_count=coverage_gap_count,
            completed_at=datetime.now(tz=timezone.utc),
            raw_payload={
                "artifact_root_path": str(root_path),
                "artifacts_seen": len(records),
                "findings_inserted": findings_inserted,
                "redacted_artifacts": redacted,
                "run_id": run_id,
                "commit_sha": commit_sha,
            },
        )

    return BuildArtifactImportResult(
        source_id=source_id,
        artifact_root_id=artifact_root_id,
        artifacts_inserted=inserted,
        artifacts_seen=len(records),
        artifacts_skipped=skipped,
        findings_inserted=findings_inserted,
        coverage_gap_count=coverage_gap_count,
        redacted_artifacts=redacted,
    )


# --- artifact discovery ------------------------------------------------------


def _artifact_root_id(root: Path) -> str:
    return hashlib.sha256(str(root).encode("utf-8")).hexdigest()


def _walk_artifacts(root: Path):
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        try:
            stat = path.stat()
        except OSError:
            continue
        if stat.st_size > ENGRAM_BUILD_ARTIFACT_MAX_BYTES:
            continue
        rel = path.relative_to(root).as_posix()
        if rel.startswith(".git/") or rel == ".git":
            continue
        record = _read_record(path, rel)
        if record is None:
            continue
        yield record


def _read_record(path: Path, rel: str) -> BuildArtifactRecord | None:
    raw = path.read_bytes()
    content_hash = hashlib.sha256(raw).hexdigest()
    mtime = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
    kind = _classify(path)
    text = _safe_decode(raw)
    redacted = bool(text and _REDACTION_RE.search(text))
    findings: tuple[BuildArtifactFinding, ...] = ()
    raw_payload: dict[str, Any] = {
        "adapter_version": ADAPTER_VERSION,
        "redacted": redacted,
    }
    try:
        if kind == "junit_xml":
            findings = tuple(_parse_junit(text or ""))
        elif kind == "coverage_report":
            findings = tuple(_parse_coverage(text or ""))
        elif kind == "benchmark_json":
            findings = tuple(_parse_benchmark(text or ""))
        elif kind == "lint_report":
            findings = tuple(_parse_lint(text or ""))
        elif kind == "log_file":
            findings = tuple(_parse_log(text or "", redacted=redacted))
    except BuildArtifactParseError as exc:
        # Demote a parse failure to "other" + a redaction-marker finding so the
        # importer remains forward-progressing instead of aborting.
        kind = "other"
        findings = (
            BuildArtifactFinding(
                finding_index=0,
                finding_kind="log_summary",
                severity="warn",
                message=f"parse_failed: {exc}",
            ),
        )
    return BuildArtifactRecord(
        relative_path=rel,
        artifact_kind=kind,
        content_hash=content_hash,
        size_bytes=len(raw),
        mtime=mtime,
        findings=findings,
        raw_payload=raw_payload,
        redacted=redacted,
    )


def _classify(path: Path) -> str:
    name = path.name.lower()
    suffix = path.suffix.lower()
    if suffix in (".xml",):
        for token, kind in _KIND_BY_NAME:
            if token in name:
                return kind
        return "junit_xml" if "test" in name else "other"
    if suffix in (".json",):
        for token, kind in _KIND_BY_NAME:
            if token in name:
                return kind
        return "other"
    if suffix in _KIND_BY_EXT:
        return _KIND_BY_EXT[suffix]
    return "other"


def _safe_decode(raw: bytes) -> str | None:
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        try:
            return raw.decode("utf-8", errors="replace")
        except Exception:  # noqa: BLE001 — last-resort guard
            return None


# --- parsers -----------------------------------------------------------------


def _parse_junit(text: str):
    try:
        root = ET.fromstring(text)
    except ET.ParseError as exc:
        raise BuildArtifactParseError(f"invalid JUnit XML: {exc}") from exc
    cases = root.findall(".//testcase")
    for index, case in enumerate(cases):
        status = "passed"
        message: str | None = None
        for marker in ("failure", "error", "skipped"):
            element = case.find(marker)
            if element is not None:
                status = marker
                message = element.text
                break
        duration_text = case.attrib.get("time")
        duration_ms: float | None
        try:
            duration_ms = float(duration_text) * 1000.0 if duration_text else None
        except ValueError:
            duration_ms = None
        yield BuildArtifactFinding(
            finding_index=index,
            finding_kind="test_case",
            status=status,
            name=case.attrib.get("name"),
            file_path=case.attrib.get("file"),
            line_number=_safe_int(case.attrib.get("line")),
            duration_ms=duration_ms,
            severity=("error" if status in {"failure", "error"} else None),
            message=message,
            raw_payload={"classname": case.attrib.get("classname")},
        )


def _parse_coverage(text: str):
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise BuildArtifactParseError(f"invalid coverage JSON: {exc}") from exc
    if not isinstance(data, dict):
        return
    totals = data.get("totals")
    if isinstance(totals, dict):
        yield BuildArtifactFinding(
            finding_index=0,
            finding_kind="coverage_summary",
            name="totals",
            duration_ms=None,
            message=None,
            raw_payload=_json_safe(totals),
        )
    files = data.get("files")
    if isinstance(files, dict):
        for index, (file_path, payload) in enumerate(sorted(files.items()), start=1):
            summary = payload.get("summary") if isinstance(payload, dict) else None
            yield BuildArtifactFinding(
                finding_index=index,
                finding_kind="coverage_file",
                file_path=file_path,
                raw_payload=_json_safe(summary or {}),
            )


def _parse_benchmark(text: str):
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise BuildArtifactParseError(f"invalid benchmark JSON: {exc}") from exc
    items = data.get("benchmarks") if isinstance(data, dict) else None
    if not isinstance(items, list):
        items = data if isinstance(data, list) else []
    for index, entry in enumerate(items):
        if not isinstance(entry, dict):
            continue
        yield BuildArtifactFinding(
            finding_index=index,
            finding_kind="benchmark",
            name=str(entry.get("name") or entry.get("benchmark_name") or f"benchmark_{index}"),
            duration_ms=_safe_float(entry.get("mean") or entry.get("real_time")),
            raw_payload=_json_safe(entry),
        )


def _parse_lint(text: str):
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise BuildArtifactParseError(f"invalid lint JSON: {exc}") from exc
    items = data if isinstance(data, list) else data.get("results") if isinstance(data, dict) else []
    if not isinstance(items, list):
        return
    for index, entry in enumerate(items):
        if not isinstance(entry, dict):
            continue
        yield BuildArtifactFinding(
            finding_index=index,
            finding_kind="lint_finding",
            file_path=entry.get("filename") or entry.get("file"),
            line_number=_safe_int(entry.get("line") or entry.get("location", {}).get("row")),
            column_number=_safe_int(entry.get("column") or entry.get("location", {}).get("column")),
            severity=entry.get("severity") or entry.get("level") or entry.get("code"),
            message=entry.get("message"),
            raw_payload=_json_safe(entry),
        )


def _parse_log(text: str, *, redacted: bool):
    body = text
    if redacted:
        body = _REDACTION_RE.sub("[REDACTED]", body)
    tail_bytes = ENGRAM_BUILD_ARTIFACT_LOG_TAIL_BYTES
    head = body[:tail_bytes]
    tail = body[-tail_bytes:] if len(body) > tail_bytes else ""
    summary = {
        "total_bytes": len(body),
        "head_bytes": len(head),
        "tail_bytes": len(tail),
        "redacted": redacted,
    }
    yield BuildArtifactFinding(
        finding_index=0,
        finding_kind="log_summary",
        severity="warn" if redacted else None,
        message="redacted log body detected" if redacted else None,
        raw_payload=summary,
    )
    if ENGRAM_BUILD_ARTIFACT_INCLUDE_LOG_BODY:
        if head:
            yield BuildArtifactFinding(
                finding_index=1,
                finding_kind="log_chunk",
                severity="info",
                message=head,
                raw_payload={"position": "head"},
            )
        if tail:
            yield BuildArtifactFinding(
                finding_index=2,
                finding_kind="log_chunk",
                severity="info",
                message=tail,
                raw_payload={"position": "tail"},
            )
    if redacted:
        yield BuildArtifactFinding(
            finding_index=3,
            finding_kind="redaction_marker",
            severity="warn",
            message="secret-shaped content redacted before storage",
            raw_payload={"pattern_source": "ENGRAM_BUILD_ARTIFACT_REDACTION_PATTERN"},
        )


# --- helpers -----------------------------------------------------------------


def _safe_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _safe_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _json_safe(value: Any) -> dict[str, Any]:
    """Coerce ``value`` to a JSON-serializable dict; flatten lists to a wrapper."""
    if isinstance(value, dict):
        return {str(k): _coerce_scalar(v) for k, v in value.items()}
    return {"value": _coerce_scalar(value)}


def _coerce_scalar(value: Any) -> Any:
    if isinstance(value, (int, float, str, bool)) or value is None:
        return value
    if isinstance(value, (list, tuple)):
        return [_coerce_scalar(item) for item in value]
    if isinstance(value, dict):
        return {str(k): _coerce_scalar(v) for k, v in value.items()}
    return str(value)


# --- database helpers --------------------------------------------------------


def _get_or_create_source(
    conn: psycopg.Connection,
    *,
    artifact_root_id: str,
    tenant_id: str,
    corpus_id: str,
    root_path: Path,
    repo_label: str | None,
) -> str:
    raw_payload: dict[str, Any] = {
        "artifact_root_id": artifact_root_id,
        "artifact_root_path": str(root_path),
        "adapter_version": ADAPTER_VERSION,
    }
    if repo_label:
        raw_payload["repo_label"] = repo_label
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id FROM sources WHERE source_kind = %s AND external_id = %s
            """,
            (SOURCE_KIND, artifact_root_id),
        )
        row = cur.fetchone()
        if row is not None:
            return str(row[0])
        cur.execute(
            """
            INSERT INTO sources (
                source_kind, external_id, filesystem_path, content_hash,
                raw_payload, tenant_id, corpus_id
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (
                SOURCE_KIND,
                artifact_root_id,
                str(root_path),
                None,
                Jsonb(raw_payload),
                tenant_id,
                corpus_id,
            ),
        )
        new_row = cur.fetchone()
        assert new_row is not None
        return str(new_row[0])


def _insert_artifact(
    conn: psycopg.Connection,
    *,
    source_id: str,
    tenant_id: str,
    corpus_id: str,
    artifact_root_id: str,
    record: BuildArtifactRecord,
    run_id: str | None,
    commit_sha: str | None,
) -> tuple[str, bool]:
    sensitivity = "routine_project"
    # Promote sensitivity when secret-shaped content was detected.
    if record.redacted:
        sensitivity = "credential_or_secret_reference"
    raw_payload = dict(record.raw_payload)
    raw_payload.setdefault("redacted", record.redacted)
    raw_payload.setdefault("findings_count", len(record.findings))
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, content_hash FROM build_artifacts
            WHERE tenant_id = %s
              AND corpus_id = %s
              AND artifact_root_id = %s
              AND relative_path = %s
              AND content_hash = %s
            """,
            (tenant_id, corpus_id, artifact_root_id, record.relative_path, record.content_hash),
        )
        existing = cur.fetchone()
        if existing is not None:
            return str(existing[0]), False
        cur.execute(
            """
            INSERT INTO build_artifacts (
                source_id, tenant_id, corpus_id, artifact_root_id, relative_path,
                artifact_kind, content_hash, size_bytes, artifact_mtime,
                run_id, commit_sha, adapter_version, privacy_tier,
                sensitivity_class, raw_payload
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (
                source_id,
                tenant_id,
                corpus_id,
                artifact_root_id,
                record.relative_path,
                record.artifact_kind,
                record.content_hash,
                record.size_bytes,
                record.mtime,
                run_id,
                commit_sha,
                ADAPTER_VERSION,
                1,
                sensitivity,
                Jsonb(raw_payload),
            ),
        )
        new_row = cur.fetchone()
        assert new_row is not None
        return str(new_row[0]), True


def _insert_finding(
    conn: psycopg.Connection,
    *,
    artifact_id: str,
    tenant_id: str,
    corpus_id: str,
    finding: BuildArtifactFinding,
) -> bool:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO build_artifact_findings (
                artifact_id, tenant_id, corpus_id, finding_index, finding_kind,
                status, name, file_path, line_number, column_number,
                duration_ms, severity, message, raw_payload
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (artifact_id, finding_index) DO NOTHING
            RETURNING id
            """,
            (
                artifact_id,
                tenant_id,
                corpus_id,
                finding.finding_index,
                finding.finding_kind,
                finding.status,
                finding.name,
                finding.file_path,
                finding.line_number,
                finding.column_number,
                finding.duration_ms,
                finding.severity,
                finding.message,
                Jsonb(finding.raw_payload),
            ),
        )
        return cur.fetchone() is not None


def _emit_coverage_gap(
    conn: psycopg.Connection,
    *,
    source_id: str,
    tenant_id: str,
    corpus_id: str,
    artifact_root_id: str,
    relative_path: str,
    reason: str,
) -> None:
    external_id = f"coverage_gap:{artifact_root_id}:{relative_path}:{reason}"
    payload = {
        "kind": "coverage_gap",
        "reason": reason,
        "artifact_root_id": artifact_root_id,
        "relative_path": relative_path,
        "adapter_version": ADAPTER_VERSION,
    }
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO captures (
                source_id, source_kind, external_id, raw_payload, privacy_tier,
                capture_type, content_text, observed_at, tenant_id, corpus_id
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, NULL, %s, %s)
            ON CONFLICT (source_id, external_id) DO NOTHING
            """,
            (
                source_id,
                SOURCE_KIND,
                external_id,
                Jsonb(payload),
                1,
                "reference",
                f"coverage_gap: {reason}",
                tenant_id,
                corpus_id,
            ),
        )
