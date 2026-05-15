from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import psycopg
from psycopg.types.json import Jsonb

PROJECTION_SCHEMA_VERSION = "striatum.references.v1"
PROJECTION_CODE_VERSION = "striatum_projection.py:1"
CONTRACT_VERSION = "striatum.corpus_export.v1"
SOURCE_KIND = "striatum"
DEFAULT_TENANT_ID = "striatum"
DEFAULT_CORPUS_ID = "striatum"
PARENT_KIND = "corpus"

RFC_ID_PATTERN = re.compile(r"(?:^|[^0-9])(?:rfc[:\-_ ]?)?0*([0-9]{1,5})(?:[^0-9]|$)", re.I)
DECISION_ID_PATTERN = re.compile(r"(D[0-9]{3,})", re.I)


class StriatumProjectionError(RuntimeError):
    """Raised when Striatum projection cannot be completed."""


@dataclass(frozen=True)
class ProjectionReference:
    """One deterministic reference derived from a raw Striatum capture."""

    capture_id: str
    tenant_id: str
    corpus_id: str
    privacy_tier: int
    ref_kind: str
    ref_value: str
    ref_value_normalized: str
    content_hash: str
    observed_at: datetime | None
    raw_payload: dict[str, Any]  # JSON projection payload stays schema-flexible by design.


@dataclass(frozen=True)
class StriatumProjectionResult:
    """Summary of one projection run."""

    generation_id: str
    captures_seen: int
    references_seen: int
    references_inserted: int
    reused_active_generation: bool
    activated: bool
    superseded_generation_ids: tuple[str, ...]


def project_striatum_references(
    conn: psycopg.Connection,
    *,
    tenant_id: str = DEFAULT_TENANT_ID,
    corpus_id: str = DEFAULT_CORPUS_ID,
    activate: bool = True,
    force_rebuild: bool = False,
) -> StriatumProjectionResult:
    """Project raw Striatum captures into active exact-reference rows."""
    captures = load_striatum_captures(conn, tenant_id=tenant_id, corpus_id=corpus_id)
    references = derive_references(captures)
    manifest = build_generation_manifest(
        captures=captures,
        references=references,
        tenant_id=tenant_id,
        corpus_id=corpus_id,
    )

    with conn.transaction():
        active = find_active_generation(conn, tenant_id=tenant_id, corpus_id=corpus_id)
        if (
            active is not None
            and not force_rebuild
            and dict(active[1] or {}).get("input_hash") == manifest["input_hash"]
        ):
            return StriatumProjectionResult(
                generation_id=str(active[0]),
                captures_seen=len(captures),
                references_seen=len(references),
                references_inserted=0,
                reused_active_generation=True,
                activated=str(active[2]) == "activated",
                superseded_generation_ids=(),
            )

        generation_id = create_generation(
            conn,
            tenant_id=tenant_id,
            corpus_id=corpus_id,
            manifest=manifest,
        )
        inserted = insert_references(conn, generation_id=generation_id, references=references)
        superseded: tuple[str, ...] = ()
        if activate:
            superseded = activate_generation(
                conn,
                generation_id=generation_id,
                tenant_id=tenant_id,
                corpus_id=corpus_id,
            )

    return StriatumProjectionResult(
        generation_id=generation_id,
        captures_seen=len(captures),
        references_seen=len(references),
        references_inserted=inserted,
        reused_active_generation=False,
        activated=activate,
        superseded_generation_ids=superseded,
    )


def load_striatum_captures(
    conn: psycopg.Connection,
    *,
    tenant_id: str,
    corpus_id: str,
) -> list[dict[str, Any]]:
    """Load source Striatum captures in deterministic projection order."""
    rows = conn.execute(
        """
        SELECT
            id::text,
            tenant_id,
            corpus_id,
            external_id,
            privacy_tier,
            COALESCE(content_text, ''),
            raw_payload,
            COALESCE(observed_at, imported_at),
            bundle_id
        FROM captures
        WHERE tenant_id = %s
          AND corpus_id = %s
          AND source_kind::text = 'striatum'
        ORDER BY observed_at NULLS LAST, external_id, id::text
        """,
        (tenant_id, corpus_id),
    ).fetchall()
    captures: list[dict[str, Any]] = []
    for row in rows:
        raw_payload = dict(row[6] or {})
        captures.append(
            {
                "id": str(row[0]),
                "tenant_id": str(row[1]),
                "corpus_id": str(row[2]),
                "external_id": str(row[3]),
                "privacy_tier": int(row[4]),
                "content_text": str(row[5] or ""),
                "raw_payload": raw_payload,
                "observed_at": row[7],
                "bundle_id": str(row[8] or "unknown"),
                "content_hash": capture_content_hash(raw_payload, str(row[5] or "")),
            }
        )
    return captures


def derive_references(captures: list[dict[str, Any]]) -> list[ProjectionReference]:
    """Derive the closed reference vocabulary from Striatum capture payloads."""
    references: list[ProjectionReference] = []
    for capture in captures:
        seen: set[tuple[str, str]] = set()
        raw_payload = dict(capture["raw_payload"])
        provenance = dict(raw_payload.get("provenance") or {})
        sub_kind = str(raw_payload.get("sub_kind") or "unknown")
        external_id = str(raw_payload.get("external_id") or capture["external_id"])

        candidates: list[tuple[str, str, str]] = []
        add_candidate(candidates, "path", first_text(raw_payload, provenance, "path"), "path")
        add_candidate(
            candidates,
            "commit_sha",
            first_text(raw_payload, provenance, "commit"),
            "commit",
        )
        add_candidate(candidates, "item_id", external_id, "external_id")

        if sub_kind == "rfc":
            add_candidate(
                candidates,
                "rfc_id",
                first_text(raw_payload, provenance, "rfc_id") or parse_rfc_id(external_id),
                "sub_kind",
            )
        elif sub_kind == "decision_log_row":
            add_candidate(
                candidates,
                "decision_id",
                first_text(raw_payload, provenance, "decision_id")
                or parse_decision_id(external_id),
                "sub_kind",
            )
        elif sub_kind == "commit":
            add_candidate(
                candidates,
                "commit_sha",
                first_text(raw_payload, provenance, "commit") or external_id,
                "sub_kind",
            )

        for ref_kind, ref_value, source_field in candidates:
            normalized = normalize_ref_value(ref_kind, ref_value)
            key = (ref_kind, normalized)
            if key in seen:
                continue
            seen.add(key)
            references.append(
                ProjectionReference(
                    capture_id=str(capture["id"]),
                    tenant_id=str(capture["tenant_id"]),
                    corpus_id=str(capture["corpus_id"]),
                    privacy_tier=int(capture["privacy_tier"]),
                    ref_kind=ref_kind,
                    ref_value=ref_value,
                    ref_value_normalized=normalized,
                    content_hash=str(capture["content_hash"]),
                    observed_at=capture["observed_at"],
                    raw_payload={
                        "projection_schema_version": PROJECTION_SCHEMA_VERSION,
                        "source_sub_kind": sub_kind,
                        "source_external_id": external_id,
                        "source_field": source_field,
                    },
                )
            )
    references.sort(
        key=lambda item: (
            item.capture_id,
            item.ref_kind,
            item.ref_value_normalized,
        )
    )
    return references


def add_candidate(
    candidates: list[tuple[str, str, str]],
    ref_kind: str,
    ref_value: str | None,
    source_field: str,
) -> None:
    """Append a non-empty reference candidate."""
    if ref_value is None:
        return
    stripped = ref_value.strip()
    if stripped == "":
        return
    candidates.append((ref_kind, stripped, source_field))


def first_text(
    raw_payload: dict[str, Any],
    provenance: dict[str, Any],
    key: str,
) -> str | None:
    """Return the first string value for a structured field."""
    raw_value = raw_payload.get(key)
    if isinstance(raw_value, str) and raw_value.strip() != "":
        return raw_value
    provenance_value = provenance.get(key)
    if isinstance(provenance_value, str) and provenance_value.strip() != "":
        return provenance_value
    return None


def parse_rfc_id(value: str) -> str | None:
    """Parse a stable RFC id from a Striatum external id or path."""
    match = RFC_ID_PATTERN.search(value)
    if match is None:
        return None
    return f"RFC {int(match.group(1)):04d}"


def parse_decision_id(value: str) -> str | None:
    """Parse a decision id from a Striatum external id."""
    match = DECISION_ID_PATTERN.search(value)
    if match is None:
        return None
    return match.group(1).upper()


def normalize_ref_value(ref_kind: str, ref_value: str) -> str:
    """Normalize a reference value for exact lookup."""
    value = " ".join(ref_value.strip().split())
    if ref_kind == "path":
        return value.replace("\\", "/").lower()
    if ref_kind == "commit_sha":
        return value.lower()
    if ref_kind == "rfc_id":
        parsed = parse_rfc_id(value)
        return parsed.lower() if parsed is not None else value.lower()
    if ref_kind == "decision_id":
        return value.upper()
    return value.lower()


def capture_content_hash(raw_payload: dict[str, Any], content_text: str) -> str:
    """Return the capture content hash used in projection manifests."""
    raw_hash = raw_payload.get("content_sha256")
    if isinstance(raw_hash, str) and raw_hash.strip() != "":
        return raw_hash
    return hashlib.sha256(content_text.encode("utf-8")).hexdigest()


def build_generation_manifest(
    *,
    captures: list[dict[str, Any]],
    references: list[ProjectionReference],
    tenant_id: str,
    corpus_id: str,
) -> dict[str, Any]:
    """Build a deterministic manifest for idempotency and audit."""
    input_items = [
        {
            "capture_id": str(capture["id"]),
            "external_id": str(capture["external_id"]),
            "content_hash": str(capture["content_hash"]),
            "observed_at": format_datetime(capture["observed_at"]),
        }
        for capture in captures
    ]
    reference_items = [
        {
            "capture_id": reference.capture_id,
            "ref_kind": reference.ref_kind,
            "ref_value_normalized": reference.ref_value_normalized,
            "content_hash": reference.content_hash,
        }
        for reference in references
    ]
    input_hash = canonical_json_sha256(
        {
            "projection_schema_version": PROJECTION_SCHEMA_VERSION,
            "inputs": input_items,
            "references": reference_items,
        }
    )
    return {
        "projection_schema_version": PROJECTION_SCHEMA_VERSION,
        "projection_code_version": PROJECTION_CODE_VERSION,
        "contract_version": CONTRACT_VERSION,
        "tenant_id": tenant_id,
        "corpus_id": corpus_id,
        "parent_kind": PARENT_KIND,
        "parent_id": parent_id(tenant_id=tenant_id, corpus_id=corpus_id),
        "bundle_id": bundle_id(captures),
        "capture_count": len(captures),
        "reference_count": len(references),
        "input_hash": input_hash,
    }


def find_active_generation(
    conn: psycopg.Connection,
    *,
    tenant_id: str,
    corpus_id: str,
) -> tuple[Any, ...] | None:
    """Return the current active generation row, if any."""
    return conn.execute(
        """
        SELECT id::text, raw_payload, status
        FROM striatum_projection_generations
        WHERE tenant_id = %s
          AND corpus_id = %s
          AND parent_kind = %s
          AND parent_id = %s
          AND status = 'activated'
          AND superseded_at IS NULL
        ORDER BY activated_at DESC NULLS LAST, started_at DESC
        LIMIT 1
        """,
        (tenant_id, corpus_id, PARENT_KIND, parent_id(tenant_id=tenant_id, corpus_id=corpus_id)),
    ).fetchone()


def create_generation(
    conn: psycopg.Connection,
    *,
    tenant_id: str,
    corpus_id: str,
    manifest: dict[str, Any],
) -> str:
    """Insert one inactive projection generation."""
    row = conn.execute(
        """
        INSERT INTO striatum_projection_generations (
            tenant_id,
            corpus_id,
            parent_kind,
            parent_id,
            bundle_id,
            contract_version,
            projection_schema_version,
            projection_code_version,
            input_manifest_sha256,
            input_item_count,
            status,
            raw_payload
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'ready', %s)
        ON CONFLICT (
            tenant_id,
            corpus_id,
            bundle_id,
            projection_schema_version,
            projection_code_version,
            input_manifest_sha256
        )
        DO UPDATE SET raw_payload = EXCLUDED.raw_payload
        RETURNING id::text
        """,
        (
            tenant_id,
            corpus_id,
            PARENT_KIND,
            parent_id(tenant_id=tenant_id, corpus_id=corpus_id),
            str(manifest["bundle_id"]),
            CONTRACT_VERSION,
            PROJECTION_SCHEMA_VERSION,
            PROJECTION_CODE_VERSION,
            str(manifest["input_hash"]),
            int(manifest["capture_count"]),
            Jsonb(manifest),
        ),
    ).fetchone()
    if row is None:
        raise StriatumProjectionError("projection generation insert returned no id")
    return str(row[0])


def insert_references(
    conn: psycopg.Connection,
    *,
    generation_id: str,
    references: list[ProjectionReference],
) -> int:
    """Insert reference projection rows for one generation."""
    inserted = 0
    for reference in references:
        row = conn.execute(
            """
            INSERT INTO striatum_references (
                capture_id,
                tenant_id,
                corpus_id,
                privacy_tier,
                ref_kind,
                ref_value,
                ref_value_normalized,
                content_hash,
                generation_id,
                is_active,
                observed_at,
                source_sub_kind,
                ref_scope,
                raw_payload
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, FALSE, %s, %s, %s, %s)
            ON CONFLICT (generation_id, capture_id, ref_kind, ref_value_normalized)
            DO NOTHING
            RETURNING id
            """,
            (
                reference.capture_id,
                reference.tenant_id,
                reference.corpus_id,
                reference.privacy_tier,
                reference.ref_kind,
                reference.ref_value,
                reference.ref_value_normalized,
                reference.content_hash,
                generation_id,
                reference.observed_at,
                str(reference.raw_payload.get("source_sub_kind") or ""),
                str(reference.raw_payload.get("source_field") or ""),
                Jsonb(reference.raw_payload),
            ),
        ).fetchone()
        if row is not None:
            inserted += 1
    return inserted


def activate_generation(
    conn: psycopg.Connection,
    *,
    generation_id: str,
    tenant_id: str,
    corpus_id: str,
) -> tuple[str, ...]:
    """Atomically activate one generation and supersede prior rows."""
    prior_rows = conn.execute(
        """
        SELECT id::text
        FROM striatum_projection_generations
        WHERE tenant_id = %s
          AND corpus_id = %s
          AND parent_kind = %s
          AND parent_id = %s
          AND status = 'activated'
          AND superseded_at IS NULL
          AND id <> %s
        ORDER BY activated_at DESC NULLS LAST, started_at DESC
        """,
        (
            tenant_id,
            corpus_id,
            PARENT_KIND,
            parent_id(tenant_id=tenant_id, corpus_id=corpus_id),
            generation_id,
        ),
    ).fetchall()
    superseded = tuple(str(row[0]) for row in prior_rows)
    conn.execute(
        """
        UPDATE striatum_references
        SET is_active = FALSE
        WHERE tenant_id = %s
          AND corpus_id = %s
          AND is_active = TRUE
          AND generation_id <> %s
        """,
        (tenant_id, corpus_id, generation_id),
    )
    conn.execute(
        """
        UPDATE striatum_projection_generations
        SET status = 'superseded',
            superseded_at = NOW()
        WHERE tenant_id = %s
          AND corpus_id = %s
          AND parent_kind = %s
          AND parent_id = %s
          AND status = 'activated'
          AND superseded_at IS NULL
          AND id <> %s
        """,
        (
            tenant_id,
            corpus_id,
            PARENT_KIND,
            parent_id(tenant_id=tenant_id, corpus_id=corpus_id),
            generation_id,
        ),
    )
    conn.execute(
        """
        UPDATE striatum_projection_generations
        SET status = 'activated',
            completed_at = COALESCE(completed_at, NOW()),
            activated_at = NOW(),
            superseded_at = NULL
        WHERE id = %s
        """,
        (generation_id,),
    )
    conn.execute(
        """
        UPDATE striatum_references
        SET is_active = TRUE
        WHERE generation_id = %s
        """,
        (generation_id,),
    )
    return superseded


def parent_id(*, tenant_id: str, corpus_id: str) -> str:
    """Return the generation parent id for a tenant/corpus capture set."""
    return f"{tenant_id}/{corpus_id}"


def bundle_id(captures: list[dict[str, Any]]) -> str:
    """Return a stable bundle id label for the projected capture set."""
    bundle_ids = sorted(
        {
            str(capture.get("bundle_id") or "unknown")
            for capture in captures
            if str(capture.get("bundle_id") or "").strip() != ""
        }
    )
    if len(bundle_ids) == 1:
        return bundle_ids[0]
    if not bundle_ids:
        return "unknown"
    return canonical_json_sha256({"bundle_ids": bundle_ids})


def canonical_json_sha256(payload: dict[str, Any]) -> str:
    """Return a deterministic SHA-256 over a JSON-compatible payload."""
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def format_datetime(value: Any) -> str | None:
    """Return a stable timestamp string for manifest hashing."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)
