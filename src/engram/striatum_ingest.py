from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import psycopg
from psycopg.types.json import Jsonb

SCHEMA_VERSION = "striatum.corpus_export.v1"
SOURCE_KIND = "striatum"
TENANT_ID = "striatum"
CORPUS_ID = "striatum"
DEFAULT_REPO = "striatum"

JSONL_FILES: dict[str, str] = {
    "rfc": "rfcs.jsonl",
    "decision_log_row": "decision_log_rows.jsonl",
    "operator_report": "operator_reports.jsonl",
    "run_summary": "run_summaries.jsonl",
    "audit_chain_entry": "audit_chain.jsonl",
    "changelog_entry": "changelog.jsonl",
    "ubiquitous_language_term": "ubiquitous_language.jsonl",
    "harness_friction_pattern": "harness_friction_patterns.jsonl",
    "commit": "commits.jsonl",
}
SUB_KINDS: tuple[str, ...] = tuple(JSONL_FILES)


class StriatumBundleError(RuntimeError):
    """Raised when a Striatum bundle cannot be ingested."""


class ManifestValidationError(StriatumBundleError):
    """Raised when manifest or JSONL verification fails."""


class IngestConflict(StriatumBundleError):
    """Raised when immutable Striatum raw evidence would need to change."""


@dataclass(frozen=True)
class StriatumCorpusRow:
    """One validated row from a Striatum corpus bundle."""

    external_id: str
    sub_kind: str
    content: str
    observed_at: datetime | None
    raw_payload: dict[str, Any]  # JSON bundle rows are intentionally schemaless at the edge.
    content_sha256: str


@dataclass(frozen=True)
class StriatumBundle:
    """A verified Striatum corpus bundle read from disk."""

    root: Path
    manifest: dict[str, Any]  # Manifest JSON is preserved exactly for provenance.
    bundle_id: str
    rows: list[StriatumCorpusRow]
    row_counts: dict[str, int]


@dataclass(frozen=True)
class StriatumIngestResult:
    """Summary of one Striatum bundle ingest."""

    source_id: str
    bundle_id: str
    repo: str
    records_inserted: int
    records_seen: int
    records_skipped: int
    row_counts: dict[str, int]


def ingest_striatum_bundle(
    conn: psycopg.Connection,
    bundle_dir: Path,
    *,
    repo: str = DEFAULT_REPO,
) -> StriatumIngestResult:
    """Validate and ingest a Striatum JSONL bundle from local disk."""
    if repo.strip() == "":
        raise ValueError("repo label cannot be empty")

    bundle = load_striatum_bundle(bundle_dir)
    with conn.transaction():
        source_id = get_or_create_source(conn, bundle, repo=repo)
        inserted, skipped = insert_captures(conn, source_id, bundle, repo=repo)

    return StriatumIngestResult(
        source_id=source_id,
        bundle_id=bundle.bundle_id,
        repo=repo,
        records_inserted=inserted,
        records_seen=len(bundle.rows),
        records_skipped=skipped,
        row_counts=bundle.row_counts,
    )


def load_striatum_bundle(bundle_dir: Path) -> StriatumBundle:
    """Read and verify a Striatum corpus export directory."""
    root = bundle_dir.expanduser().resolve()
    if not root.is_dir():
        raise FileNotFoundError(f"Striatum bundle path is not a directory: {root}")

    manifest_path = root / "manifest.json"
    if not manifest_path.is_file():
        raise ManifestValidationError(f"Striatum bundle manifest is missing: {manifest_path}")
    # JSON payloads are untyped until each field is validated below.
    manifest: dict[str, Any] = json.loads(manifest_path.read_text(encoding="utf-8"))
    validate_manifest_header(manifest)
    bundle_id = canonical_manifest_sha256(manifest)
    expected_bundle_id = manifest.get("bundle_sha256")
    if expected_bundle_id is not None and expected_bundle_id != bundle_id:
        raise ManifestValidationError("manifest bundle_sha256 does not match canonical manifest")

    rows: list[StriatumCorpusRow] = []
    row_counts = {sub_kind: 0 for sub_kind in SUB_KINDS}
    seen: set[tuple[str, str]] = set()
    files = manifest.get("files")
    if not isinstance(files, dict):
        raise ManifestValidationError("manifest files must be an object")

    for sub_kind, filename in JSONL_FILES.items():
        file_meta = files.get(filename)
        if not isinstance(file_meta, dict):
            raise ManifestValidationError(f"manifest missing file metadata: {filename}")
        file_rows = load_jsonl_file(
            root / filename,
            filename=filename,
            expected_sub_kind=sub_kind,
            expected=file_meta,
            seen=seen,
        )
        rows.extend(file_rows)
        row_counts[sub_kind] = len(file_rows)

    validate_manifest_counts(manifest, row_counts)
    return StriatumBundle(
        root=root,
        manifest=manifest,
        bundle_id=bundle_id,
        rows=rows,
        row_counts=row_counts,
    )


def validate_manifest_header(manifest: dict[str, Any]) -> None:
    """Validate manifest fields that do not require reading JSONL files."""
    if manifest.get("schema_version") != SCHEMA_VERSION:
        raise ManifestValidationError("invalid Striatum corpus manifest schema_version")
    source_kinds = manifest.get("source_kinds")
    if source_kinds is not None and source_kinds != [SOURCE_KIND]:
        raise ManifestValidationError("manifest source_kinds must be ['striatum']")
    schema = manifest.get("schema")
    if isinstance(schema, dict):
        sub_kinds = schema.get("sub_kinds")
        if sub_kinds is not None and list(sub_kinds) != list(SUB_KINDS):
            raise ManifestValidationError("manifest sub_kinds do not match RFC 0044 V1")


def load_jsonl_file(
    path: Path,
    *,
    filename: str,
    expected_sub_kind: str,
    expected: dict[str, Any],
    seen: set[tuple[str, str]],
) -> list[StriatumCorpusRow]:
    """Verify one JSONL file and return validated rows."""
    if not path.is_file():
        raise ManifestValidationError(f"corpus file is missing: {filename}")
    data = path.read_bytes()
    expected_sha = expected.get("sha256")
    if not isinstance(expected_sha, str):
        raise ManifestValidationError(f"manifest sha256 missing for {filename}")
    actual_sha = hashlib.sha256(data).hexdigest()
    if actual_sha != expected_sha:
        raise ManifestValidationError(f"corpus file hash mismatch: {filename}")

    expected_bytes = expected.get("bytes")
    if expected_bytes is not None and int(expected_bytes) != len(data):
        raise ManifestValidationError(f"corpus byte count mismatch: {filename}")

    rows: list[StriatumCorpusRow] = []
    for line_number, line in enumerate(data.decode("utf-8").splitlines(), start=1):
        if line == "":
            continue
        payload = parse_json_line(line, filename=filename, line_number=line_number)
        row = validate_row_payload(
            payload,
            filename=filename,
            expected_sub_kind=expected_sub_kind,
        )
        key = (row.sub_kind, row.external_id)
        if key in seen:
            raise ManifestValidationError(
                f"duplicate Striatum corpus row: {row.sub_kind} {row.external_id}"
            )
        seen.add(key)
        rows.append(row)

    expected_rows = expected.get("rows")
    if expected_rows is None or int(expected_rows) != len(rows):
        raise ManifestValidationError(f"corpus row count mismatch: {filename}")
    return rows


def parse_json_line(line: str, *, filename: str, line_number: int) -> dict[str, Any]:
    """Parse one JSONL line with file context for diagnostics."""
    try:
        payload = json.loads(line)
    except json.JSONDecodeError as exc:
        raise ManifestValidationError(
            f"invalid JSON in {filename}:{line_number}: {exc.msg}"
        ) from exc
    if not isinstance(payload, dict):
        raise ManifestValidationError(f"corpus row must be an object: {filename}:{line_number}")
    return payload


def validate_row_payload(
    payload: dict[str, Any],
    *,
    filename: str,
    expected_sub_kind: str,
) -> StriatumCorpusRow:
    """Validate one Striatum corpus row."""
    if payload.get("source_kind") != SOURCE_KIND:
        raise ManifestValidationError(f"invalid corpus row source_kind in {filename}")
    sub_kind = payload.get("sub_kind")
    if sub_kind != expected_sub_kind:
        raise ManifestValidationError(f"corpus row in wrong file: {filename}")
    external_id = payload.get("external_id")
    if not isinstance(external_id, str) or external_id.strip() == "":
        raise ManifestValidationError(f"invalid corpus row external_id in {filename}")
    content = payload.get("content")
    if not isinstance(content, str):
        raise ManifestValidationError(f"invalid corpus row content in {filename}")
    provenance = payload.get("provenance")
    if not isinstance(provenance, dict):
        raise ManifestValidationError(f"invalid corpus row provenance in {filename}")
    observed_at = parse_timestamp(payload.get("observed_at"))
    return StriatumCorpusRow(
        external_id=external_id,
        sub_kind=str(sub_kind),
        content=content,
        observed_at=observed_at,
        raw_payload=payload,
        content_sha256=canonical_json_sha256(payload),
    )


def validate_manifest_counts(manifest: dict[str, Any], row_counts: dict[str, int]) -> None:
    """Verify manifest row_counts after JSONL parsing."""
    counts = manifest.get("row_counts")
    if not isinstance(counts, dict):
        raise ManifestValidationError("manifest row_counts must be an object")
    for sub_kind in SUB_KINDS:
        if int(counts.get(sub_kind, -1)) != row_counts[sub_kind]:
            raise ManifestValidationError(f"manifest row count mismatch: {sub_kind}")


def get_or_create_source(
    conn: psycopg.Connection,
    bundle: StriatumBundle,
    *,
    repo: str,
) -> str:
    """Insert or fetch the immutable bundle source row."""
    external_id = source_external_id(bundle, repo=repo)
    source_payload = {
        "schema_version": SCHEMA_VERSION,
        "repo": repo,
        "bundle_id": bundle.bundle_id,
        "manifest": bundle.manifest,
    }
    row = conn.execute(
        """
        INSERT INTO sources (
            source_kind,
            external_id,
            filesystem_path,
            content_hash,
            raw_payload,
            tenant_id,
            corpus_id,
            bundle_id
        )
        VALUES ('striatum', %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (source_kind, external_id) DO NOTHING
        RETURNING id
        """,
        (
            external_id,
            str(bundle.root),
            bundle.bundle_id,
            Jsonb(source_payload),
            TENANT_ID,
            CORPUS_ID,
            bundle.bundle_id,
        ),
    ).fetchone()
    if row:
        return str(row[0])

    existing = conn.execute(
        """
        SELECT id, content_hash, tenant_id, corpus_id, bundle_id
        FROM sources
        WHERE source_kind::text = 'striatum'
          AND external_id = %s
        """,
        (external_id,),
    ).fetchone()
    if existing is None:
        raise IngestConflict(f"Striatum source insert conflicted but no row exists: {external_id}")
    source_id, content_hash, tenant_id, corpus_id, bundle_id = existing
    if tenant_id != TENANT_ID or corpus_id != CORPUS_ID:
        raise IngestConflict(f"Striatum source boundary differs for {external_id}")
    if content_hash != bundle.bundle_id or bundle_id != bundle.bundle_id:
        raise IngestConflict(f"Striatum source content hash differs for {external_id}")
    return str(source_id)


def insert_captures(
    conn: psycopg.Connection,
    source_id: str,
    bundle: StriatumBundle,
    *,
    repo: str,
) -> tuple[int, int]:
    """Insert Striatum rows as immutable raw captures."""
    inserted = 0
    skipped = 0
    for row in bundle.rows:
        external_id = capture_external_id(row, repo=repo)
        existing = conn.execute(
            """
            SELECT id, raw_payload ->> 'content_sha256'
            FROM captures
            WHERE tenant_id = %s
              AND corpus_id = %s
              AND source_kind::text = 'striatum'
              AND external_id = %s
            """,
            (TENANT_ID, CORPUS_ID, external_id),
        ).fetchone()
        if existing is not None:
            existing_hash = existing[1]
            if existing_hash != row.content_sha256:
                raise IngestConflict(
                    "Striatum corpus row content differs from immutable capture row "
                    f"for {external_id}"
                )
            skipped += 1
            continue

        payload = dict(row.raw_payload)
        payload.update(
            {
                "repo": repo,
                "bundle_id": bundle.bundle_id,
                "content_sha256": row.content_sha256,
                "manifest": {
                    "schema_version": bundle.manifest.get("schema_version"),
                    "git_head": bundle.manifest.get("git_head"),
                    "since_ref": bundle.manifest.get("since_ref"),
                    "since_commit": bundle.manifest.get("since_commit"),
                },
            }
        )
        conn.execute(
            """
            INSERT INTO captures (
                source_id,
                source_kind,
                external_id,
                raw_payload,
                privacy_tier,
                capture_type,
                content_text,
                observed_at,
                tenant_id,
                corpus_id,
                bundle_id
            )
            VALUES (%s, 'striatum', %s, %s, 1, 'reference', %s, %s, %s, %s, %s)
            """,
            (
                source_id,
                external_id,
                Jsonb(payload),
                row.content,
                row.observed_at,
                TENANT_ID,
                CORPUS_ID,
                bundle.bundle_id,
            ),
        )
        inserted += 1
    return inserted, skipped


def source_external_id(bundle: StriatumBundle, *, repo: str) -> str:
    """Return the immutable bundle source key."""
    since_ref = str(bundle.manifest.get("since_ref") or "unknown")
    return f"striatum:{repo}:bundle:{since_ref}:{bundle.bundle_id}"


def capture_external_id(row: StriatumCorpusRow, *, repo: str) -> str:
    """Return the stable per-row key inside the local Striatum tenant."""
    return f"{repo}:{row.sub_kind}:{row.external_id}"


def canonical_json_sha256(payload: dict[str, Any]) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def canonical_manifest_sha256(manifest: dict[str, Any]) -> str:
    payload = dict(manifest)
    payload.pop("bundle_sha256", None)
    return canonical_json_sha256(payload)


def parse_timestamp(value: Any) -> datetime | None:
    """Parse an RFC3339 timestamp from a Striatum corpus row."""
    if value is None:
        return None
    if not isinstance(value, str):
        raise ManifestValidationError("observed_at must be an RFC3339 string when present")
    normalized = value.removesuffix("Z") + "+00:00" if value.endswith("Z") else value
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed
