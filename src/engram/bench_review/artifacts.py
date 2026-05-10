"""Artifact normalization for the RFC 0029 bench triage workbench."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from engram.bench_review.classify import classify_tags, queue_sort_key, resolve_data_state

JsonValue = Any  # JSON artifacts are untyped at the IO boundary.


class BenchReviewArtifactError(RuntimeError):
    """Raised when a required bench review artifact is unusable."""


@dataclass(frozen=True)
class CandidateSegmentResult:
    segment_id: str
    candidate_claim_count: int | None
    candidate_dropped_count: int | None
    candidate_predicates: tuple[str, ...]
    candidate_provenance_count: int | None
    data_state_hint: str | None
    source: str


@dataclass(frozen=True)
class CandidateRun:
    run_id: str
    artifact_path: Path
    generated_at: str | None
    prompt_version: str | None
    model_version: str | None
    request_profile_version: str | None
    segment_count: int | None
    result_rows: tuple[CandidateSegmentResult, ...]
    segment_records_path: str | None


@dataclass(frozen=True)
class PriorSegmentResult:
    segment_id: str
    prior_claim_count: int
    prior_dropped_count: int
    prior_predicates: tuple[str, ...]
    prior_provenance_count: int


@dataclass(frozen=True)
class SegmentComparison:
    segment_id: str
    data_state: str
    tags: tuple[str, ...]
    prior_claim_count: int | None
    candidate_claim_count: int | None
    prior_dropped_count: int | None
    candidate_dropped_count: int | None
    prior_predicates: tuple[str, ...]
    candidate_predicates: tuple[str, ...]
    prior_provenance_count: int | None
    candidate_provenance_count: int | None
    instruction: str


@dataclass(frozen=True)
class SegmentRecordLoad:
    records: dict[str, CandidateSegmentResult]
    malformed_segment_ids: frozenset[str]
    global_malformed: bool


def load_slice_segment_ids(path: Path) -> tuple[str, ...]:
    """Load ordered segment IDs from a benchmark slice manifest."""
    payload = _load_json(path)
    if not isinstance(payload, dict):
        raise BenchReviewArtifactError("slice manifest must be a JSON object")
    rows = payload.get("segments")
    if not isinstance(rows, list) or not rows:
        raise BenchReviewArtifactError("slice manifest contains no segments")
    ids: list[str] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        segment_id = _first_str(row, ("segment_id", "source_segment_id", "id"))
        if segment_id:
            ids.append(segment_id)
    if not ids:
        raise BenchReviewArtifactError("slice manifest contains no segment IDs")
    return tuple(ids)


def load_candidate_run(path: Path) -> CandidateRun:
    """Load candidate run metadata and inline segment rows when present."""
    payload = _load_json(path)
    if not isinstance(payload, dict):
        raise BenchReviewArtifactError("run artifact must be a JSON object")
    inline_rows = _extract_rows(payload)
    rows = tuple(
        record
        for record in (
            _parse_candidate_segment(row, source=str(path))
            for row in inline_rows
            if isinstance(row, dict)
        )
        if record is not None
    )
    model_value = _first_str(
        payload,
        ("model_version", "extraction_model_version", "candidate_model_version"),
    )
    model_payload = payload.get("model")
    if model_value is None and isinstance(model_payload, dict):
        model_value = _first_str(model_payload, ("model_id", "id", "name", "path"))
    return CandidateRun(
        run_id=_first_str(payload, ("run_id", "id", "name")) or path.stem,
        artifact_path=path,
        generated_at=_first_str(payload, ("generated_at", "created_at", "completed_at")),
        prompt_version=_first_str(
            payload,
            ("prompt_version", "extraction_prompt_version", "candidate_prompt_version"),
        ),
        model_version=model_value,
        request_profile_version=_first_str(
            payload,
            (
                "request_profile_version",
                "extraction_request_profile_version",
                "candidate_request_profile_version",
            ),
        ),
        segment_count=_first_int(payload, ("segment_count", "segments_count")) or len(rows) or None,
        result_rows=rows,
        segment_records_path=_first_str(payload, ("segment_records_path", "segments_path")),
    )


def resolve_segment_records_path(
    *, run_path: Path, candidate_run: CandidateRun, explicit_path: Path | None
) -> Path | None:
    """Resolve a segment-record path from explicit CLI arg, run metadata, or siblings."""
    if explicit_path is not None:
        return explicit_path
    if candidate_run.segment_records_path:
        candidate_path = Path(candidate_run.segment_records_path)
        return candidate_path if candidate_path.is_absolute() else run_path.parent / candidate_path
    sibling = run_path.parent / "segments.jsonl"
    if sibling.exists():
        return sibling
    return None


def load_segment_records(path: Path | None) -> SegmentRecordLoad:
    """Load candidate segment rows from JSON/JSONL; malformed files become state."""
    if path is None:
        return SegmentRecordLoad({}, frozenset(), False)
    try:
        rows = _load_rows(path)
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return SegmentRecordLoad({}, frozenset(), True)
    records: dict[str, CandidateSegmentResult] = {}
    malformed: set[str] = set()
    for row in rows:
        if not isinstance(row, dict):
            continue
        segment_id = _first_str(row, ("segment_id", "source_segment_id", "id"))
        record = _parse_candidate_segment(row, source=str(path))
        if not segment_id or record is None:
            if segment_id:
                malformed.add(segment_id)
            continue
        if segment_id in records:
            records.pop(segment_id, None)
            malformed.add(segment_id)
            continue
        records[segment_id] = record
    return SegmentRecordLoad(records, frozenset(malformed), False)


def build_segment_comparisons(
    *,
    segment_ids: tuple[str, ...],
    candidate_records: SegmentRecordLoad,
    prior_summaries: dict[str, PriorSegmentResult],
) -> tuple[SegmentComparison, ...]:
    """Build ordered comparison rows for review state initialization."""
    rows: list[SegmentComparison] = []
    for segment_id in segment_ids:
        candidate_malformed = (
            candidate_records.global_malformed
            or segment_id in candidate_records.malformed_segment_ids
        )
        candidate = candidate_records.records.get(segment_id)
        prior = prior_summaries.get(segment_id)
        state = resolve_data_state(
            candidate_malformed=candidate_malformed,
            candidate_missing=not candidate_malformed and candidate is None,
            prior_missing=not candidate_malformed and candidate is not None and prior is None,
            candidate_redacted=(
                candidate is not None and candidate.data_state_hint == "candidate_redacted"
            ),
            candidate_claim_count=(
                candidate.candidate_claim_count if candidate is not None else None
            ),
        )
        prior_claim_count = prior.prior_claim_count if prior is not None else None
        prior_dropped_count = prior.prior_dropped_count if prior is not None else None
        prior_predicates = prior.prior_predicates if prior is not None else ()
        prior_provenance_count = prior.prior_provenance_count if prior is not None else None
        candidate_claim_count = candidate.candidate_claim_count if candidate is not None else None
        candidate_dropped_count = (
            candidate.candidate_dropped_count if candidate is not None else None
        )
        candidate_predicates = candidate.candidate_predicates if candidate is not None else ()
        candidate_provenance_count = (
            candidate.candidate_provenance_count if candidate is not None else None
        )
        tags = classify_tags(
            data_state=state,
            prior_claim_count=prior_claim_count,
            candidate_claim_count=candidate_claim_count,
            prior_dropped_count=prior_dropped_count,
            candidate_dropped_count=candidate_dropped_count,
            prior_predicates=prior_predicates,
            candidate_predicates=candidate_predicates,
            prior_provenance_count=prior_provenance_count,
            candidate_provenance_count=candidate_provenance_count,
        )
        rows.append(
            SegmentComparison(
                segment_id=segment_id,
                data_state=state,
                tags=tags,
                prior_claim_count=prior_claim_count,
                candidate_claim_count=candidate_claim_count,
                prior_dropped_count=prior_dropped_count,
                candidate_dropped_count=candidate_dropped_count,
                prior_predicates=prior_predicates,
                candidate_predicates=candidate_predicates,
                prior_provenance_count=prior_provenance_count,
                candidate_provenance_count=candidate_provenance_count,
                instruction=_state_instruction(state),
            )
        )
    return tuple(
        sorted(rows, key=lambda row: queue_sort_key(row.data_state, row.tags, row.segment_id))
    )


def fetch_prior_summaries(
    conn: Any,
    *,
    segment_ids: tuple[str, ...],
    prompt_version: str,
    model_version: str,
    request_profile_version: str,
) -> dict[str, PriorSegmentResult]:
    """Fetch read-only prior claim summaries from production claims."""
    if not segment_ids:
        return {}
    rows = conn.execute(
        """
        SELECT segment_id::text, predicate, cardinality(evidence_message_ids)
        FROM claims
        WHERE segment_id::text = ANY(%s)
          AND extraction_prompt_version = %s
          AND extraction_model_version = %s
          AND request_profile_version = %s
        """,
        (list(segment_ids), prompt_version, model_version, request_profile_version),
    ).fetchall()
    predicates: dict[str, set[str]] = {}
    evidence_counts: dict[str, int] = {}
    claim_counts: dict[str, int] = {}
    for segment_id, predicate, evidence_count in rows:
        key = str(segment_id)
        claim_counts[key] = claim_counts.get(key, 0) + 1
        predicates.setdefault(key, set()).add(str(predicate))
        evidence_counts[key] = evidence_counts.get(key, 0) + int(evidence_count or 0)
    return {
        segment_id: PriorSegmentResult(
            segment_id=segment_id,
            prior_claim_count=claim_counts[segment_id],
            prior_dropped_count=0,
            prior_predicates=tuple(sorted(predicates.get(segment_id, set()))),
            prior_provenance_count=evidence_counts.get(segment_id, 0),
        )
        for segment_id in claim_counts
    }


def _state_instruction(data_state: str) -> str:
    from engram.bench_review.classify import state_instruction

    return state_instruction(data_state)


def _load_json(path: Path) -> JsonValue:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise BenchReviewArtifactError(str(exc)) from exc
    except json.JSONDecodeError as exc:
        raise BenchReviewArtifactError(f"invalid JSON: {path}") from exc


def _load_rows(path: Path) -> list[JsonValue]:
    text = path.read_text(encoding="utf-8")
    if path.suffix == ".jsonl":
        return [json.loads(line) for line in text.splitlines() if line.strip()]
    payload = json.loads(text)
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        return _extract_rows(payload)
    return []


def _extract_rows(payload: dict[str, JsonValue]) -> list[JsonValue]:
    for key in ("segments", "segment_results", "results", "rows", "items"):
        value = payload.get(key)
        if isinstance(value, list):
            return value
    return []


def _parse_candidate_segment(
    row: dict[str, JsonValue], *, source: str
) -> CandidateSegmentResult | None:
    segment_id = _first_str(row, ("segment_id", "source_segment_id", "id"))
    if not segment_id:
        return None
    if _has_invalid_int(
        row,
        (
            "candidate_claim_count",
            "claim_count",
            "claims_count",
            "total_claims",
            "valid_claim_count",
            "candidate_dropped_count",
            "dropped_count",
            "dropped_claim_count",
            "invalid_claim_count",
            "candidate_provenance_count",
            "provenance_count",
            "evidence_count",
        ),
    ):
        return None
    claim_count = _first_int(
        row,
        (
            "candidate_claim_count",
            "claim_count",
            "claims_count",
            "total_claims",
            "valid_claim_count",
        ),
    )
    claims = row.get("claims")
    if claim_count is None and isinstance(claims, list):
        claim_count = len(claims)
    if claim_count is None:
        claim_count = 0
    dropped_count = _first_int(
        row,
        ("candidate_dropped_count", "dropped_count", "dropped_claim_count", "invalid_claim_count"),
    )
    predicates = _predicates_from_row(row)
    provenance_count = _first_int(
        row,
        ("candidate_provenance_count", "provenance_count", "evidence_count"),
    )
    if provenance_count is None and isinstance(claims, list):
        provenance_count = 0
        for claim in claims:
            if isinstance(claim, dict):
                evidence_ids = claim.get("evidence_ids") or claim.get("evidence_message_ids")
                if isinstance(evidence_ids, list):
                    provenance_count += len(evidence_ids)
    state_hint = _first_str(row, ("data_state", "data_state_hint", "availability"))
    if state_hint != "candidate_redacted":
        state_hint = None
    return CandidateSegmentResult(
        segment_id=segment_id,
        candidate_claim_count=claim_count,
        candidate_dropped_count=dropped_count,
        candidate_predicates=predicates,
        candidate_provenance_count=provenance_count,
        data_state_hint=state_hint,
        source=source,
    )


def _predicates_from_row(row: dict[str, JsonValue]) -> tuple[str, ...]:
    for key in ("candidate_predicates", "predicates", "predicate_names"):
        value = row.get(key)
        if isinstance(value, list):
            return tuple(sorted({str(item) for item in value if str(item)}))
    claims = row.get("claims")
    if isinstance(claims, list):
        values: set[str] = set()
        for claim in claims:
            if isinstance(claim, dict) and isinstance(claim.get("predicate"), str):
                values.add(str(claim["predicate"]))
        return tuple(sorted(values))
    return ()


def _first_str(row: dict[str, JsonValue], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = row.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _first_int(row: dict[str, JsonValue], keys: tuple[str, ...]) -> int | None:
    for key in keys:
        value = row.get(key)
        coerced = _coerce_int(value)
        if coerced is not None:
            return coerced
    return None


def _coerce_int(value: JsonValue) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int) and value >= 0:
        return value
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return None


def _has_invalid_int(row: dict[str, JsonValue], keys: tuple[str, ...]) -> bool:
    return any(key in row and _coerce_int(row.get(key)) is None for key in keys)
