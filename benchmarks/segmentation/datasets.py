"""Public dataset manifest validation and local snapshot adapters."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from benchmarks.segmentation.fixtures import BenchmarkValidationError
from benchmarks.segmentation.strategies import BenchmarkMessage, BenchmarkParent


PUBLIC_DATASET_MANIFEST_SCHEMA_VERSION = "segmentation-public-dataset-manifest.v1"
PUBLIC_PREPROCESSING_VERSION = "segmentation-public-preprocess.v1"
SUPPORTED_DATASETS = {"superdialseg", "lmsys_chat_1m"}


@dataclass(frozen=True)
class PublicDatasetManifest:
    schema_version: str
    dataset_name: str
    dataset_source: str
    dataset_version: str
    local_path: Path
    local_path_raw: str
    license_name: str
    license_accepted_at: str | None
    preprocessing_version: str
    created_at: str | None
    manifest_path: Path
    local_path_sha256: str | None = None
    requires_license_acceptance: bool = False

    @property
    def snapshot(self) -> str:
        return f"{self.dataset_source}:{self.dataset_version}"


@dataclass(frozen=True)
class PublicDataset:
    manifest: PublicDatasetManifest
    parents: tuple[BenchmarkParent, ...]


def load_public_dataset_manifest(path: str | Path) -> PublicDatasetManifest:
    path = Path(path)
    errors: list[str] = []
    if not path.exists():
        raise BenchmarkValidationError([f"{path}: manifest does not exist"])
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise BenchmarkValidationError([f"{path}: invalid JSON: {exc}"]) from exc
    if not isinstance(payload, dict):
        raise BenchmarkValidationError([f"{path}: manifest must be a JSON object"])

    schema_version = required_string(payload, "schema_version", errors, str(path))
    dataset_name = required_string(payload, "dataset_name", errors, str(path))
    dataset_source = required_string(payload, "dataset_source", errors, str(path))
    dataset_version = required_string(payload, "dataset_version", errors, str(path))
    local_path_raw = required_string(payload, "local_path", errors, str(path))
    license_name = required_string(payload, "license_name", errors, str(path))
    preprocessing_version = required_string(
        payload, "preprocessing_version", errors, str(path)
    )

    if schema_version and schema_version != PUBLIC_DATASET_MANIFEST_SCHEMA_VERSION:
        errors.append(
            f"{path}: unsupported schema_version {schema_version!r}; expected "
            f"{PUBLIC_DATASET_MANIFEST_SCHEMA_VERSION}"
        )
    if dataset_name and dataset_name not in SUPPORTED_DATASETS:
        errors.append(
            f"{path}: unsupported dataset_name {dataset_name!r}; expected one of "
            f"{sorted(SUPPORTED_DATASETS)}"
        )
    if preprocessing_version and preprocessing_version != PUBLIC_PREPROCESSING_VERSION:
        errors.append(
            f"{path}: unsupported preprocessing_version {preprocessing_version!r}; "
            f"expected {PUBLIC_PREPROCESSING_VERSION}"
        )

    requires_license_acceptance = bool(payload.get("requires_license_acceptance", False))
    if dataset_name == "lmsys_chat_1m":
        requires_license_acceptance = True
    license_accepted_at = payload.get("license_accepted_at")
    if license_accepted_at is not None and not isinstance(license_accepted_at, str):
        errors.append(f"{path}.license_accepted_at: must be a string or null")
        license_accepted_at = None
    if requires_license_acceptance and not license_accepted_at:
        errors.append(
            f"{path}: dataset {dataset_name!r} requires local license acceptance; "
            "set license_accepted_at after accepting the dataset terms"
        )

    if dataset_name and dataset_source:
        validate_dataset_source(dataset_name, dataset_source, str(path), errors)

    local_path = Path(local_path_raw) if local_path_raw else Path()
    if local_path_raw and not local_path.is_absolute():
        local_path = (path.parent / local_path).resolve()
    if local_path_raw and not local_path.exists():
        errors.append(f"{path}: local_path does not exist: {local_path}")

    if errors:
        raise BenchmarkValidationError(errors)

    return PublicDatasetManifest(
        schema_version=str(schema_version),
        dataset_name=str(dataset_name),
        dataset_source=str(dataset_source),
        dataset_version=str(dataset_version),
        local_path=local_path,
        local_path_raw=str(local_path_raw),
        local_path_sha256=payload.get("local_path_sha256")
        if isinstance(payload.get("local_path_sha256"), str)
        else None,
        license_name=str(license_name),
        license_accepted_at=license_accepted_at,
        preprocessing_version=str(preprocessing_version),
        created_at=payload.get("created_at")
        if isinstance(payload.get("created_at"), str)
        else None,
        manifest_path=path,
        requires_license_acceptance=requires_license_acceptance,
    )


def load_public_dataset(
    manifest_or_path: PublicDatasetManifest | str | Path,
    *,
    split: str | None = None,
    limit: int | None = None,
) -> PublicDataset:
    manifest = (
        manifest_or_path
        if isinstance(manifest_or_path, PublicDatasetManifest)
        else load_public_dataset_manifest(manifest_or_path)
    )
    if manifest.dataset_name == "superdialseg":
        parents = load_superdialseg(manifest, split=split, limit=limit)
    elif manifest.dataset_name == "lmsys_chat_1m":
        parents = load_lmsys_chat_1m(manifest, split=split, limit=limit)
    else:
        raise BenchmarkValidationError([f"unsupported dataset {manifest.dataset_name!r}"])
    return PublicDataset(manifest=manifest, parents=parents)


def load_superdialseg(
    manifest: PublicDatasetManifest,
    *,
    split: str | None = None,
    limit: int | None = None,
) -> tuple[BenchmarkParent, ...]:
    rows = read_json_rows(manifest.local_path)
    grouped: dict[str, list[dict[str, Any]]] = {}
    errors: list[str] = []
    for line_number, row in rows:
        if row.get("record_type") == "header":
            continue
        row_split = row.get("split") or row.get("dataset_split")
        if split and row_split and row_split != split:
            continue
        dial_id = row.get("dial_id") or row.get("dialogue_id") or row.get("conversation_id")
        if not isinstance(dial_id, str) or not dial_id:
            errors.append(f"{manifest.local_path}:{line_number}: missing dial_id")
            continue
        grouped.setdefault(dial_id, []).append(row)

    parents: list[BenchmarkParent] = []
    for dial_id in sorted(grouped):
        raw_turns = sorted(
            grouped[dial_id],
            key=lambda row: int(row.get("turn_id", row.get("sequence_index", 0))),
        )
        messages: list[BenchmarkMessage] = []
        boundaries: set[int] = set()
        previous_topic: str | None = None
        has_segmentation_labels = any(
            usable_boundary_label(row.get("segmentation_label")) for row in raw_turns
        )
        for sequence_index, row in enumerate(raw_turns):
            utterance = row.get("utterance")
            if utterance is None:
                utterance = row.get("text") or row.get("content")
            if not isinstance(utterance, str):
                errors.append(
                    f"{manifest.local_path}: dial_id={dial_id!r} turn={sequence_index}: "
                    "missing utterance"
                )
                utterance = ""
            role = row.get("role")
            if not isinstance(role, str) or not role:
                role = "speaker"
            turn_id = row.get("turn_id", sequence_index)
            messages.append(
                BenchmarkMessage(
                    id=stable_public_message_uuid(
                        manifest.dataset_name,
                        manifest.dataset_version,
                        dial_id,
                        str(turn_id),
                    ),
                    sequence_index=sequence_index,
                    role=role,
                    content_text=utterance,
                    privacy_tier=1,
                )
            )
            if has_segmentation_labels:
                if (
                    truthy_boundary_label(row.get("segmentation_label"))
                    and sequence_index < len(raw_turns) - 1
                ):
                    boundaries.add(sequence_index + 1)
                continue
            topic = row.get("topic_id")
            topic_str = str(topic) if topic is not None else None
            if sequence_index > 0 and previous_topic is not None and topic_str != previous_topic:
                boundaries.add(sequence_index)
            if topic_str is not None:
                previous_topic = topic_str
        if messages:
            parents.append(
                BenchmarkParent(
                    fixture_id=None,
                    source_kind="public",
                    parent_id=f"public:superdialseg:{dial_id}",
                    title=f"SuperDialseg {dial_id}",
                    privacy_tier=1,
                    messages=tuple(messages),
                    dataset_kind="public",
                    dataset_name="superdialseg",
                    dataset_split=split or first_string(raw_turns, "split", "dataset_split"),
                    expected_boundaries=tuple(sorted(boundaries)),
                    metadata={"dial_id": dial_id},
                )
            )
            if limit is not None and len(parents) >= limit:
                break

    if errors:
        raise BenchmarkValidationError(errors)
    return tuple(parents)


def load_lmsys_chat_1m(
    manifest: PublicDatasetManifest,
    *,
    split: str | None = None,
    limit: int | None = None,
) -> tuple[BenchmarkParent, ...]:
    rows = read_json_rows(manifest.local_path)
    grouped: dict[str, list[dict[str, Any]]] = {}
    errors: list[str] = []

    for line_number, row in rows:
        if row.get("record_type") == "header":
            continue
        row_split = row.get("split") or row.get("dataset_split")
        if split and row_split and row_split != split:
            continue
        conversation_id = row.get("conversation_id") or row.get("id")
        if not isinstance(conversation_id, str) or not conversation_id:
            errors.append(f"{manifest.local_path}:{line_number}: missing conversation_id")
            continue
        if isinstance(row.get("messages"), list):
            for index, message in enumerate(row["messages"]):
                if isinstance(message, dict):
                    normalized = dict(message)
                    normalized.setdefault("turn_id", index)
                    normalized.setdefault("conversation_id", conversation_id)
                    grouped.setdefault(conversation_id, []).append(normalized)
                else:
                    errors.append(
                        f"{manifest.local_path}:{line_number}: messages[{index}] must be an object"
                    )
        else:
            grouped.setdefault(conversation_id, []).append(row)

    parents: list[BenchmarkParent] = []
    for conversation_id in sorted(grouped):
        raw_turns = sorted(
            grouped[conversation_id],
            key=lambda row: int(row.get("turn_id", row.get("sequence_index", 0))),
        )
        messages: list[BenchmarkMessage] = []
        for sequence_index, row in enumerate(raw_turns):
            content = row.get("content") or row.get("text") or row.get("utterance")
            if not isinstance(content, str):
                errors.append(
                    f"{manifest.local_path}: conversation_id={conversation_id!r} "
                    f"turn={sequence_index}: missing content"
                )
                content = ""
            role = row.get("role")
            if not isinstance(role, str) or not role:
                role = "unknown"
            turn_id = row.get("turn_id", sequence_index)
            messages.append(
                BenchmarkMessage(
                    id=stable_public_message_uuid(
                        manifest.dataset_name,
                        manifest.dataset_version,
                        conversation_id,
                        str(turn_id),
                    ),
                    sequence_index=sequence_index,
                    role=role,
                    content_text=content,
                    privacy_tier=1,
                )
            )
        if messages:
            parents.append(
                BenchmarkParent(
                    fixture_id=None,
                    source_kind="public",
                    parent_id=f"public:lmsys_chat_1m:{conversation_id}",
                    title=f"LMSYS-Chat-1M {conversation_id}",
                    privacy_tier=1,
                    messages=tuple(messages),
                    dataset_kind="public",
                    dataset_name="lmsys_chat_1m",
                    dataset_split=split or first_string(raw_turns, "split", "dataset_split"),
                    expected_boundaries=None,
                    metadata={"conversation_id": conversation_id},
                )
            )
            if limit is not None and len(parents) >= limit:
                break

    if errors:
        raise BenchmarkValidationError(errors)
    return tuple(parents)


def read_json_rows(path: Path) -> list[tuple[int, dict[str, Any]]]:
    errors: list[str] = []
    rows: list[tuple[int, dict[str, Any]]] = []
    paths = sorted(path.glob("*.jsonl")) if path.is_dir() else [path]
    for row_path in paths:
        with row_path.open("r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                stripped = line.strip()
                if not stripped:
                    continue
                try:
                    payload = json.loads(stripped)
                except json.JSONDecodeError as exc:
                    errors.append(f"{row_path}:{line_number}: invalid JSON: {exc}")
                    continue
                if not isinstance(payload, dict):
                    errors.append(f"{row_path}:{line_number}: row must be a JSON object")
                    continue
                rows.append((line_number, payload))
    if errors:
        raise BenchmarkValidationError(errors)
    return rows


def validate_dataset_source(
    dataset_name: str,
    dataset_source: str,
    label: str,
    errors: list[str],
) -> None:
    if dataset_name == "superdialseg":
        allowed = (
            "huggingface:Coldog2333/super_dialseg",
            "github:Coldog2333/SuperDialseg",
            "local:superdialseg",
            "Coldog2333/super_dialseg",
            "Coldog2333/SuperDialseg",
        )
    else:
        allowed = (
            "huggingface:lmsys/lmsys-chat-1m",
            "local:lmsys_chat_1m",
            "lmsys/lmsys-chat-1m",
        )
    if dataset_source not in allowed:
        errors.append(
            f"{label}: dataset_source {dataset_source!r} does not match known "
            f"{dataset_name} sources {allowed}"
        )


def required_string(
    payload: dict[str, Any],
    key: str,
    errors: list[str],
    label: str,
) -> str | None:
    value = payload.get(key)
    if not isinstance(value, str) or not value:
        errors.append(f"{label}.{key}: must be a non-empty string")
        return None
    return value


def stable_public_message_uuid(
    dataset_name: str,
    dataset_version: str,
    parent_id: str,
    turn_id: str,
) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"engram:{dataset_name}:{dataset_version}:{parent_id}:{turn_id}"))


def truthy_boundary_label(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        return value.strip().casefold() in {"1", "true", "yes", "boundary", "b"}
    return False


def usable_boundary_label(value: Any) -> bool:
    if isinstance(value, bool):
        return True
    if isinstance(value, (int, float)):
        return value in {0, 1}
    if isinstance(value, str):
        return value.strip().casefold() in {
            "0",
            "1",
            "false",
            "true",
            "no",
            "yes",
            "boundary",
            "b",
        }
    return False


def first_string(rows: Iterable[dict[str, Any]], *keys: str) -> str | None:
    for row in rows:
        for key in keys:
            value = row.get(key)
            if isinstance(value, str) and value:
                return value
    return None
