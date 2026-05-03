"""Synthetic fixture loading and validation for segmentation benchmarks."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from benchmarks.segmentation.strategies import BenchmarkMessage, BenchmarkParent


FIXTURE_SCHEMA_VERSION = "segmentation-fixtures.v1"
EXPECTED_CLAIMS_SCHEMA_VERSION = "segmentation-expected-claims.v1"


class BenchmarkValidationError(ValueError):
    """Validation error that preserves every discovered issue."""

    def __init__(self, errors: list[str]) -> None:
        self.errors = errors
        super().__init__("\n".join(errors))


@dataclass(frozen=True)
class ExpectedSegment:
    segment_id: str
    message_ids: tuple[str, ...]
    embeddable_message_ids: tuple[str, ...]
    topic_label: str | None
    summary: str | None
    expected_claim_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class ExpectedClaim:
    claim_id: str
    claim_text: str
    evidence_message_ids: tuple[str, ...]
    expected_segment_ids: tuple[str, ...]
    privacy_tier: int
    stability_class: str | None = None
    valid_from: str | None = None
    valid_to: str | None = None
    match_aliases: tuple[str, ...] = ()


@dataclass(frozen=True)
class FixtureBundle:
    fixture_version: str
    fixture_schema_version: str
    parents: tuple[BenchmarkParent, ...]
    expected_segments_by_fixture: dict[str, tuple[ExpectedSegment, ...]]
    expected_claims_by_fixture: dict[str, tuple[ExpectedClaim, ...]] = field(
        default_factory=dict
    )
    expected_claims_schema_version: str | None = None


def load_fixtures(
    fixtures_path: str | Path,
    expected_claims_path: str | Path | None = None,
) -> FixtureBundle:
    fixture_records, fixture_errors = load_jsonl_records(fixtures_path)
    errors = list(fixture_errors)
    if not fixture_records:
        raise BenchmarkValidationError(errors or [f"{fixtures_path}: file is empty"])

    header = fixture_records[0][1]
    if not isinstance(header, dict) or header.get("record_type") != "header":
        errors.append(f"{fixtures_path}: first JSONL record must be a header")
        header = {}
    fixture_version = string_field(header, "fixture_version", errors, str(fixtures_path))
    schema_version = string_field(header, "schema_version", errors, str(fixtures_path))
    if schema_version and schema_version != FIXTURE_SCHEMA_VERSION:
        errors.append(
            f"{fixtures_path}: unsupported schema_version {schema_version!r}; "
            f"expected {FIXTURE_SCHEMA_VERSION}"
        )

    parents: list[BenchmarkParent] = []
    expected_by_fixture: dict[str, tuple[ExpectedSegment, ...]] = {}
    known_fixture_ids: set[str] = set()
    message_ids_by_fixture: dict[str, set[str]] = {}

    for line_number, record in fixture_records[1:]:
        if not isinstance(record, dict):
            errors.append(f"{fixtures_path}:{line_number}: record must be a JSON object")
            continue
        if record.get("record_type") != "fixture":
            errors.append(f"{fixtures_path}:{line_number}: record_type must be 'fixture'")
            continue
        parsed = parse_fixture_record(record, line_number, str(fixtures_path), errors)
        if parsed is None:
            continue
        parent, expected_segments = parsed
        if parent.fixture_id in known_fixture_ids:
            errors.append(f"{fixtures_path}:{line_number}: duplicate fixture_id {parent.fixture_id}")
        known_fixture_ids.add(str(parent.fixture_id))
        parents.append(parent)
        expected_by_fixture[str(parent.fixture_id)] = tuple(expected_segments)
        message_ids_by_fixture[str(parent.fixture_id)] = {message.id for message in parent.messages}

    expected_claims_by_fixture: dict[str, tuple[ExpectedClaim, ...]] = {}
    expected_claims_schema_version: str | None = None
    if expected_claims_path:
        claims_records, claim_errors = load_jsonl_records(expected_claims_path)
        errors.extend(claim_errors)
        if not claims_records:
            errors.append(f"{expected_claims_path}: file is empty")
        else:
            (
                expected_claims_by_fixture,
                expected_claims_schema_version,
            ) = parse_expected_claims(
                claims_records,
                str(expected_claims_path),
                fixture_version,
                known_fixture_ids,
                message_ids_by_fixture,
                expected_by_fixture,
                errors,
            )

    validate_expected_segment_claim_refs(
        expected_by_fixture,
        expected_claims_by_fixture,
        errors,
    )

    if errors:
        raise BenchmarkValidationError(errors)

    return FixtureBundle(
        fixture_version=str(fixture_version),
        fixture_schema_version=str(schema_version),
        parents=tuple(parents),
        expected_segments_by_fixture=expected_by_fixture,
        expected_claims_by_fixture=expected_claims_by_fixture,
        expected_claims_schema_version=expected_claims_schema_version,
    )


def load_jsonl_records(path: str | Path) -> tuple[list[tuple[int, Any]], list[str]]:
    path = Path(path)
    errors: list[str] = []
    records: list[tuple[int, Any]] = []
    if not path.exists():
        return records, [f"{path}: file does not exist"]
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                records.append((line_number, json.loads(stripped)))
            except json.JSONDecodeError as exc:
                errors.append(f"{path}:{line_number}: invalid JSON: {exc}")
    return records, errors


def parse_fixture_record(
    record: dict[str, Any],
    line_number: int,
    path_label: str,
    errors: list[str],
) -> tuple[BenchmarkParent, list[ExpectedSegment]] | None:
    fixture_id = string_field(record, "fixture_id", errors, f"{path_label}:{line_number}")
    source_kind = string_field(record, "source_kind", errors, f"{path_label}:{line_number}")
    parent_id = string_field(record, "parent_id", errors, f"{path_label}:{line_number}")
    if parent_id:
        validate_uuid(parent_id, errors, f"{path_label}:{line_number}:parent_id")
    privacy_tier = int_field(record, "privacy_tier", errors, f"{path_label}:{line_number}", 1)
    messages_raw = record.get("messages")
    if not isinstance(messages_raw, list) or not messages_raw:
        errors.append(f"{path_label}:{line_number}: messages must be a non-empty list")
        return None

    messages: list[BenchmarkMessage] = []
    seen_message_ids: set[str] = set()
    for index, message_raw in enumerate(messages_raw):
        label = f"{path_label}:{line_number}:messages[{index}]"
        if not isinstance(message_raw, dict):
            errors.append(f"{label}: message must be an object")
            continue
        message_id = string_field(message_raw, "id", errors, label)
        if message_id:
            validate_uuid(message_id, errors, f"{label}.id")
            if message_id in seen_message_ids:
                errors.append(f"{label}.id: duplicate message id {message_id}")
            seen_message_ids.add(message_id)
        sequence_index = int_field(message_raw, "sequence_index", errors, label, index)
        role = message_raw.get("role")
        if role is not None and not isinstance(role, str):
            errors.append(f"{label}.role: must be a string or null")
            role = None
        content_text = message_raw.get("content_text")
        if content_text is not None and not isinstance(content_text, str):
            errors.append(f"{label}.content_text: must be a string or null")
            content_text = None
        placeholders = tuple(string_list_field(message_raw, "placeholders", errors, label))
        messages.append(
            BenchmarkMessage(
                id=str(message_id),
                sequence_index=sequence_index,
                role=role,
                content_text=content_text,
                privacy_tier=int_field(message_raw, "privacy_tier", errors, label, privacy_tier),
                placeholders=placeholders,
            )
        )

    sequence_indexes = [message.sequence_index for message in messages]
    if len(sequence_indexes) != len(set(sequence_indexes)):
        errors.append(f"{path_label}:{line_number}: duplicate message sequence_index")
    if sequence_indexes != sorted(sequence_indexes):
        errors.append(f"{path_label}:{line_number}: messages must be ordered by sequence_index")

    message_ids = {message.id for message in messages}
    sequence_by_id = {message.id: message.sequence_index for message in messages}
    expected_segments = parse_expected_segments(
        record.get("expected_segments"),
        message_ids,
        sequence_by_id,
        f"{path_label}:{line_number}",
        errors,
    )

    if not fixture_id or not source_kind or not parent_id:
        return None

    parent = BenchmarkParent(
        fixture_id=str(fixture_id),
        source_kind=str(source_kind),
        parent_id=str(parent_id),
        title=record.get("title") if isinstance(record.get("title"), str) else None,
        privacy_tier=privacy_tier,
        messages=tuple(messages),
        dataset_kind="synthetic",
        dataset_name="synthetic_fixtures",
        metadata={"fixture_notes": record.get("fixture_notes", [])},
    )
    return parent, expected_segments


def parse_expected_segments(
    raw_segments: Any,
    message_ids: set[str],
    sequence_by_id: dict[str, int],
    label: str,
    errors: list[str],
) -> list[ExpectedSegment]:
    if not isinstance(raw_segments, list) or not raw_segments:
        errors.append(f"{label}: expected_segments must be a non-empty list")
        return []
    segments: list[ExpectedSegment] = []
    seen_segment_ids: set[str] = set()
    for index, raw_segment in enumerate(raw_segments):
        segment_label = f"{label}:expected_segments[{index}]"
        if not isinstance(raw_segment, dict):
            errors.append(f"{segment_label}: segment must be an object")
            continue
        segment_id = string_field(raw_segment, "segment_id", errors, segment_label)
        if segment_id in seen_segment_ids:
            errors.append(f"{segment_label}.segment_id: duplicate segment id {segment_id}")
        seen_segment_ids.add(str(segment_id))
        segment_message_ids = tuple(
            string_list_field(raw_segment, "message_ids", errors, segment_label)
        )
        embeddable_message_ids = tuple(
            string_list_field(raw_segment, "embeddable_message_ids", errors, segment_label)
        )
        if not segment_message_ids:
            errors.append(f"{segment_label}.message_ids: must not be empty")
        validate_parent_local_ids(
            segment_message_ids,
            message_ids,
            sequence_by_id,
            f"{segment_label}.message_ids",
            errors,
            require_ordered=True,
        )
        validate_parent_local_ids(
            embeddable_message_ids,
            message_ids,
            sequence_by_id,
            f"{segment_label}.embeddable_message_ids",
            errors,
            require_ordered=True,
        )
        for message_id in embeddable_message_ids:
            if message_id not in segment_message_ids:
                errors.append(
                    f"{segment_label}.embeddable_message_ids: {message_id} is not in message_ids"
                )
        segments.append(
            ExpectedSegment(
                segment_id=str(segment_id),
                message_ids=segment_message_ids,
                embeddable_message_ids=embeddable_message_ids,
                topic_label=raw_segment.get("topic_label")
                if isinstance(raw_segment.get("topic_label"), str)
                else None,
                summary=raw_segment.get("summary")
                if isinstance(raw_segment.get("summary"), str)
                else None,
                expected_claim_ids=tuple(
                    string_list_field(raw_segment, "expected_claim_ids", errors, segment_label)
                ),
            )
        )
    return segments


def parse_expected_claims(
    records: list[tuple[int, Any]],
    path_label: str,
    fixture_version: str | None,
    known_fixture_ids: set[str],
    message_ids_by_fixture: dict[str, set[str]],
    expected_by_fixture: dict[str, tuple[ExpectedSegment, ...]],
    errors: list[str],
) -> tuple[dict[str, tuple[ExpectedClaim, ...]], str | None]:
    header = records[0][1]
    if not isinstance(header, dict) or header.get("record_type") != "header":
        errors.append(f"{path_label}: first JSONL record must be a header")
        header = {}
    claims_fixture_version = string_field(header, "fixture_version", errors, path_label)
    schema_version = string_field(header, "schema_version", errors, path_label)
    if schema_version and schema_version != EXPECTED_CLAIMS_SCHEMA_VERSION:
        errors.append(
            f"{path_label}: unsupported schema_version {schema_version!r}; "
            f"expected {EXPECTED_CLAIMS_SCHEMA_VERSION}"
        )
    if fixture_version and claims_fixture_version and claims_fixture_version != fixture_version:
        errors.append(
            f"{path_label}: fixture_version {claims_fixture_version!r} does not match "
            f"{fixture_version!r}"
        )

    claims_by_fixture: dict[str, tuple[ExpectedClaim, ...]] = {}
    for line_number, record in records[1:]:
        label = f"{path_label}:{line_number}"
        if not isinstance(record, dict):
            errors.append(f"{label}: record must be an object")
            continue
        if record.get("record_type") != "expected_claim_set":
            errors.append(f"{label}: record_type must be 'expected_claim_set'")
            continue
        fixture_id = string_field(record, "fixture_id", errors, label)
        if fixture_id not in known_fixture_ids:
            errors.append(f"{label}.fixture_id: unknown fixture id {fixture_id}")
            continue
        raw_claims = record.get("claims")
        if not isinstance(raw_claims, list):
            errors.append(f"{label}.claims: must be a list")
            continue
        claims: list[ExpectedClaim] = []
        seen_claim_ids: set[str] = set()
        expected_segment_ids = {
            segment.segment_id for segment in expected_by_fixture.get(str(fixture_id), ())
        }
        for index, raw_claim in enumerate(raw_claims):
            claim_label = f"{label}:claims[{index}]"
            if not isinstance(raw_claim, dict):
                errors.append(f"{claim_label}: claim must be an object")
                continue
            claim_id = string_field(raw_claim, "claim_id", errors, claim_label)
            if claim_id in seen_claim_ids:
                errors.append(f"{claim_label}.claim_id: duplicate claim id {claim_id}")
            seen_claim_ids.add(str(claim_id))
            claim_text = string_field(raw_claim, "claim_text", errors, claim_label)
            evidence_ids = tuple(
                string_list_field(raw_claim, "evidence_message_ids", errors, claim_label)
            )
            validate_id_membership(
                evidence_ids,
                message_ids_by_fixture.get(str(fixture_id), set()),
                f"{claim_label}.evidence_message_ids",
                errors,
            )
            expected_segment_refs = tuple(
                string_list_field(raw_claim, "expected_segment_ids", errors, claim_label)
            )
            validate_id_membership(
                expected_segment_refs,
                expected_segment_ids,
                f"{claim_label}.expected_segment_ids",
                errors,
            )
            claims.append(
                ExpectedClaim(
                    claim_id=str(claim_id),
                    claim_text=str(claim_text),
                    evidence_message_ids=evidence_ids,
                    expected_segment_ids=expected_segment_refs,
                    privacy_tier=int_field(raw_claim, "privacy_tier", errors, claim_label, 1),
                    stability_class=raw_claim.get("stability_class")
                    if isinstance(raw_claim.get("stability_class"), str)
                    else None,
                    valid_from=raw_claim.get("valid_from")
                    if isinstance(raw_claim.get("valid_from"), str)
                    else None,
                    valid_to=raw_claim.get("valid_to")
                    if isinstance(raw_claim.get("valid_to"), str)
                    else None,
                    match_aliases=tuple(
                        string_list_field(raw_claim, "match_aliases", errors, claim_label)
                    ),
                )
            )
        claims_by_fixture[str(fixture_id)] = tuple(claims)
    return claims_by_fixture, str(schema_version) if schema_version else None


def validate_expected_segment_claim_refs(
    expected_by_fixture: dict[str, tuple[ExpectedSegment, ...]],
    expected_claims_by_fixture: dict[str, tuple[ExpectedClaim, ...]],
    errors: list[str],
) -> None:
    for fixture_id, segments in expected_by_fixture.items():
        claim_ids = {
            claim.claim_id for claim in expected_claims_by_fixture.get(fixture_id, ())
        }
        if not claim_ids:
            continue
        for segment in segments:
            for claim_id in segment.expected_claim_ids:
                if claim_id not in claim_ids:
                    errors.append(
                        f"fixture {fixture_id} segment {segment.segment_id}: "
                        f"unknown expected_claim_id {claim_id}"
                    )


def validate_uuid(value: str, errors: list[str], label: str) -> None:
    try:
        uuid.UUID(value)
    except (TypeError, ValueError):
        errors.append(f"{label}: invalid UUID {value!r}")


def validate_parent_local_ids(
    values: tuple[str, ...],
    message_ids: set[str],
    sequence_by_id: dict[str, int],
    label: str,
    errors: list[str],
    *,
    require_ordered: bool,
) -> None:
    validate_id_membership(values, message_ids, label, errors)
    if require_ordered:
        known_sequences = [
            sequence_by_id[value] for value in values if value in sequence_by_id
        ]
        if known_sequences != sorted(known_sequences):
            errors.append(f"{label}: ids must be ordered by parent message sequence")


def validate_id_membership(
    values: tuple[str, ...],
    known_ids: set[str],
    label: str,
    errors: list[str],
) -> None:
    for value in values:
        if value not in known_ids:
            errors.append(f"{label}: unknown id {value}")


def string_field(
    record: dict[str, Any],
    key: str,
    errors: list[str],
    label: str,
) -> str | None:
    value = record.get(key)
    if not isinstance(value, str) or not value:
        errors.append(f"{label}.{key}: must be a non-empty string")
        return None
    return value


def int_field(
    record: dict[str, Any],
    key: str,
    errors: list[str],
    label: str,
    default: int,
) -> int:
    value = record.get(key, default)
    if isinstance(value, bool) or not isinstance(value, int):
        errors.append(f"{label}.{key}: must be an integer")
        return default
    return value


def string_list_field(
    record: dict[str, Any],
    key: str,
    errors: list[str],
    label: str,
) -> list[str]:
    value = record.get(key, [])
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        errors.append(f"{label}.{key}: must be a list of strings")
        return []
    return list(value)
