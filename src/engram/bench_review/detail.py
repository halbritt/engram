"""On-demand private detail hydration for bench review pages."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

import psycopg

from engram import db
from engram.bench_review import storage

SEGMENT_EXCERPT_MAX_CHARS: int = int(
    os.environ.get("ENGRAM_BENCH_REVIEW_SEGMENT_EXCERPT_MAX_CHARS", "12000")
)
DETAIL_CLAIM_LIMIT: int = int(os.environ.get("ENGRAM_BENCH_REVIEW_DETAIL_CLAIM_LIMIT", "80"))
MAX_CANDIDATE_RECORD_BYTES: int = int(
    os.environ.get("ENGRAM_BENCH_REVIEW_MAX_CANDIDATE_RECORD_BYTES", "104857600")
)


@dataclass(frozen=True)
class PriorClaimDetail:
    claim_id: str
    subject_text: str | None
    predicate: str
    object_display: str | None
    stability_class: str
    confidence: float
    evidence_count: int
    evidence_message_ids: tuple[str, ...]
    privacy_tier: int


@dataclass(frozen=True)
class CandidateClaimDetail:
    predicate: str | None
    stability_class: str | None
    confidence: float | None
    evidence_count: int | None
    evidence_message_ids: tuple[str, ...]
    object_kind: str | None
    object_present: bool | None
    subject_text_present: bool | None
    rationale_present: bool | None


@dataclass(frozen=True)
class SegmentDetail:
    segment_id: str
    summary_text: str | None
    segment_excerpt: str | None
    excerpt_truncated: bool
    privacy_tier: int | None
    prior_claims: tuple[PriorClaimDetail, ...]
    candidate_claims: tuple[CandidateClaimDetail, ...]
    candidate_detail_note: str | None
    error: str | None


def fetch_segment_detail(review_db_path: Path, segment_id: str) -> SegmentDetail:
    """Fetch operator-visible detail from local Postgres and candidate artifacts."""
    session = storage.get_session(review_db_path)
    candidate_claims, candidate_note = _load_candidate_claims(
        Path(session["segments_path"]) if session["segments_path"] else None,
        segment_id=segment_id,
    )
    try:
        with db.connect() as conn:
            segment_summary, excerpt, truncated, privacy_tier = _fetch_segment_excerpt(
                conn, segment_id
            )
            prior_claims = _fetch_prior_claims(
                conn,
                segment_id=segment_id,
                prompt_version=session["prior_prompt_version"],
                model_version=session["prior_model_version"],
                request_profile_version=session["prior_request_profile_version"],
            )
    except (psycopg.Error, OSError) as exc:
        return SegmentDetail(
            segment_id=segment_id,
            summary_text=None,
            segment_excerpt=None,
            excerpt_truncated=False,
            privacy_tier=None,
            prior_claims=(),
            candidate_claims=candidate_claims,
            candidate_detail_note=candidate_note,
            error=f"{type(exc).__name__}: {exc}",
        )
    return SegmentDetail(
        segment_id=segment_id,
        summary_text=segment_summary,
        segment_excerpt=excerpt,
        excerpt_truncated=truncated,
        privacy_tier=privacy_tier,
        prior_claims=prior_claims,
        candidate_claims=candidate_claims,
        candidate_detail_note=candidate_note,
        error=None,
    )


def _fetch_segment_excerpt(
    conn: psycopg.Connection, segment_id: str
) -> tuple[str | None, str | None, bool, int | None]:
    row = conn.execute(
        """
        SELECT summary_text, content_text, privacy_tier
        FROM segments
        WHERE id = %s
        """,
        (segment_id,),
    ).fetchone()
    if row is None:
        return None, None, False, None
    summary_text, content_text, privacy_tier = row
    tier = int(privacy_tier)
    if tier > 1:
        return str(summary_text) if summary_text else None, None, False, tier
    excerpt = str(content_text or "")
    truncated = len(excerpt) > SEGMENT_EXCERPT_MAX_CHARS
    if truncated:
        excerpt = excerpt[:SEGMENT_EXCERPT_MAX_CHARS].rstrip()
    return str(summary_text) if summary_text else None, excerpt, truncated, tier


def _fetch_prior_claims(
    conn: psycopg.Connection,
    *,
    segment_id: str,
    prompt_version: str,
    model_version: str,
    request_profile_version: str,
) -> tuple[PriorClaimDetail, ...]:
    rows = conn.execute(
        """
        SELECT
            id::text,
            subject_text,
            predicate,
            object_text,
            object_json::text,
            stability_class,
            confidence,
            evidence_message_ids::text[],
            privacy_tier
        FROM claims
        WHERE segment_id::text = %s
          AND extraction_prompt_version = %s
          AND extraction_model_version = %s
          AND request_profile_version = %s
        ORDER BY predicate, subject_text, id
        LIMIT %s
        """,
        (segment_id, prompt_version, model_version, request_profile_version, DETAIL_CLAIM_LIMIT),
    ).fetchall()
    claims: list[PriorClaimDetail] = []
    for row in rows:
        (
            claim_id,
            subject_text,
            predicate,
            object_text,
            object_json,
            stability_class,
            confidence,
            evidence_ids,
            privacy_tier,
        ) = row
        tier = int(privacy_tier)
        claims.append(
            PriorClaimDetail(
                claim_id=str(claim_id),
                subject_text=str(subject_text) if tier <= 1 else None,
                predicate=str(predicate),
                object_display=_object_display(object_text, object_json) if tier <= 1 else None,
                stability_class=str(stability_class),
                confidence=float(confidence),
                evidence_count=len(evidence_ids or []),
                evidence_message_ids=tuple(str(value) for value in evidence_ids or ()),
                privacy_tier=tier,
            )
        )
    return tuple(claims)


def _load_candidate_claims(
    segments_path: Path | None, *, segment_id: str
) -> tuple[tuple[CandidateClaimDetail, ...], str | None]:
    if segments_path is None:
        return (), "No candidate segment artifact path is recorded for this review session."
    try:
        if segments_path.stat().st_size > MAX_CANDIDATE_RECORD_BYTES:
            return (), "Candidate artifact is too large for on-demand detail loading."
        row = _find_candidate_row(segments_path, segment_id)
    except (OSError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        return (), f"Candidate artifact could not be read: {type(exc).__name__}: {exc}"
    if row is None:
        return (), "No candidate artifact row was found for this segment."
    claims_value = row.get("claims")
    if not isinstance(claims_value, list):
        return (), "Candidate artifact row has no claim details."
    claims: list[CandidateClaimDetail] = []
    for claim in claims_value:
        if isinstance(claim, dict):
            claims.append(_candidate_claim_from_artifact(claim))
    if not claims:
        return (), "Candidate artifact has zero claims for this segment."
    return (
        tuple(claims),
        "Candidate artifact contains metadata only; subject/object text is not stored.",
    )


def _find_candidate_row(path: Path, segment_id: str) -> dict[str, object] | None:
    if path.suffix == ".jsonl":
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            if isinstance(row, dict) and _row_segment_id(row) == segment_id:
                return row
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows: object = payload
    if isinstance(payload, dict):
        rows = next(
            (
                payload[key]
                for key in ("segments", "segment_results", "results", "rows", "items")
                if isinstance(payload.get(key), list)
            ),
            [],
        )
    if not isinstance(rows, list):
        return None
    for row in rows:
        if isinstance(row, dict) and _row_segment_id(row) == segment_id:
            return row
    return None


def _candidate_claim_from_artifact(claim: dict[str, object]) -> CandidateClaimDetail:
    evidence_ids = claim.get("evidence_message_ids") or claim.get("evidence_ids")
    if not isinstance(evidence_ids, list):
        evidence_ids = []
    evidence_count = _coerce_int(claim.get("evidence_message_count")) or len(evidence_ids)
    return CandidateClaimDetail(
        predicate=_optional_str(claim.get("predicate")),
        stability_class=_optional_str(claim.get("stability_class")),
        confidence=_optional_float(claim.get("confidence")),
        evidence_count=evidence_count,
        evidence_message_ids=tuple(str(value) for value in evidence_ids if str(value)),
        object_kind=_optional_str(claim.get("object_kind")),
        object_present=_optional_bool(claim.get("object_present")),
        subject_text_present=_optional_bool(claim.get("subject_text_present")),
        rationale_present=_optional_bool(claim.get("rationale_present")),
    )


def _row_segment_id(row: dict[str, object]) -> str | None:
    for key in ("segment_id", "source_segment_id", "id"):
        value = row.get(key)
        if isinstance(value, str) and value:
            return value
    return None


def _object_display(object_text: object, object_json: object) -> str | None:
    if isinstance(object_text, str) and object_text:
        return object_text
    if isinstance(object_json, str) and object_json:
        return object_json
    return None


def _optional_str(value: object) -> str | None:
    return value if isinstance(value, str) and value else None


def _optional_float(value: object) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (float, int)):
        return float(value)
    return None


def _optional_bool(value: object) -> bool | None:
    return value if isinstance(value, bool) else None


def _coerce_int(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int) and value >= 0:
        return value
    return None
