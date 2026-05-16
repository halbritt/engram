"""Source contract validator (RFC 0050 Layer 1).

Loads a YAML source contract from disk and verifies it against the closed
field and vocabulary set declared in RFC 0050 § Source Contract.

The validator is documentation + tests at Layer 1; no importer invokes it
at runtime. A pytest module exercises every contract under
``docs/source-contracts/`` so contract drift fails the suite.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-not-found]  # PyYAML ships with the project test deps.

# --- Closed vocabularies (RFC 0050 § Source Contract) -------------------------

PROJECTION_FAMILIES: frozenset[str] = frozenset({
    "conversation_thread",
    "document_record",
    "project_event",
    "execution_artifact",
    "code_reference",
    "artifact_reference",
    "observation",
    "place_event",
    "asset_record",
})

OPERATIONAL_FAMILIES: frozenset[str] = frozenset({
    "coverage_gap",
    "source_audit",
})

SOURCE_FAMILIES: frozenset[str] = frozenset({
    "project_execution",
    "documents",
    "conversation",
    "observation",
    "asset",
})

SENSITIVITY_CLASSES: frozenset[str] = frozenset({
    "routine_project",
    "personal_private",
    "third_party_communication",
    "calendar_contact",
    "behavioral_activity",
    "raw_media",
    "exact_location",
    "health",
    "biometric",
    "finance",
    "credential_or_secret_reference",
})

NETWORK_POLICIES: frozenset[str] = frozenset({"no outbound calls"})

CONFLICT_POLICIES: frozenset[str] = frozenset({
    "raise_on_changed_raw_artifact_hash",
    "raise_on_changed_manifest",
    "tombstone_and_replace",
})

EXTRACTION_DEFAULTS: frozenset[str] = frozenset({
    "metadata_only",
    "disabled",
    "opt_in",
})

# Closed test names that a contract may declare. New names land in this set as
# new families introduce new gates.
KNOWN_TEST_NAMES: frozenset[str] = frozenset({
    "contract_validator",
    "idempotent_reimport",
    "conflict_on_changed_raw_hash",
    "raw_evidence_immutable",
    "projection_rebuild_from_raw",
    "no_network_access",
    "privacy_inheritance",
    "third_party_extraction_off_by_default",
    "exact_reference_citation",
    "redaction_pattern_promotion",
    "log_body_opt_in",
})


class ContractErrorCode(str, Enum):
    """Closed error vocabulary for contract validation."""

    CONTRACT_FILE_NOT_FOUND = "CONTRACT_FILE_NOT_FOUND"
    CONTRACT_NOT_YAML = "CONTRACT_NOT_YAML"
    CONTRACT_NOT_OBJECT = "CONTRACT_NOT_OBJECT"
    MISSING_FIELD = "MISSING_FIELD"
    EMPTY_FIELD = "EMPTY_FIELD"
    UNKNOWN_SOURCE_FAMILY = "UNKNOWN_SOURCE_FAMILY"
    UNKNOWN_PROJECTION_FAMILY = "UNKNOWN_PROJECTION_FAMILY"
    UNKNOWN_OPERATIONAL_FAMILY = "UNKNOWN_OPERATIONAL_FAMILY"
    UNKNOWN_SENSITIVITY_CLASS = "UNKNOWN_SENSITIVITY_CLASS"
    UNKNOWN_NETWORK_POLICY = "UNKNOWN_NETWORK_POLICY"
    UNKNOWN_CONFLICT_POLICY = "UNKNOWN_CONFLICT_POLICY"
    UNKNOWN_TEST_NAME = "UNKNOWN_TEST_NAME"
    INVALID_PRIVACY_TIER = "INVALID_PRIVACY_TIER"
    INVALID_EXTRACTION_DEFAULT = "INVALID_EXTRACTION_DEFAULT"
    INVALID_PARTICIPANT_THIRD_PARTY = "INVALID_PARTICIPANT_THIRD_PARTY"
    INVALID_RAW_RETENTION = "INVALID_RAW_RETENTION"
    INVALID_PROVENANCE = "INVALID_PROVENANCE"


class SourceContractError(RuntimeError):
    """Root of the source-contract exception family."""


@dataclass(frozen=True)
class ContractValidationError:
    code: ContractErrorCode
    field_path: str
    message: str


@dataclass(frozen=True)
class ContractValidationWarning:
    field_path: str
    message: str


@dataclass(frozen=True)
class ContractValidationResult:
    contract_path: Path
    source_kind: str
    is_valid: bool
    errors: tuple[ContractValidationError, ...] = field(default_factory=tuple)
    warnings: tuple[ContractValidationWarning, ...] = field(default_factory=tuple)


# Mandatory top-level fields. Each entry maps a key to a predicate that
# checks the value's shape; the predicate may emit additional errors.
_REQUIRED_TOP_LEVEL_FIELDS: tuple[str, ...] = (
    "source_kind",
    "source_family",
    "sub_kinds",
    "raw_artifact_boundary",
    "identity",
    "temporal_fields",
    "deduplication",
    "privacy",
    "projection_families",
    "operational_families",
    "extraction_eligibility",
    "raw_retention",
    "provenance",
    "rebuild",
    "tests",
)


def validate_contract(path: Path) -> ContractValidationResult:
    """Validate a source contract YAML file.

    Returns a ``ContractValidationResult`` whose ``errors`` tuple is empty
    iff the contract passes. Loading failures are reported as a single
    error and short-circuit the structural checks.
    """
    contract_path = Path(path)
    errors: list[ContractValidationError] = []
    warnings: list[ContractValidationWarning] = []

    if not contract_path.is_file():
        errors.append(
            ContractValidationError(
                ContractErrorCode.CONTRACT_FILE_NOT_FOUND,
                "$",
                f"contract file not found: {contract_path}",
            )
        )
        return ContractValidationResult(contract_path, "", False, tuple(errors))

    try:
        text = contract_path.read_text(encoding="utf-8")
        parsed: Any = yaml.safe_load(text)
    except (yaml.YAMLError, UnicodeDecodeError) as exc:
        errors.append(
            ContractValidationError(
                ContractErrorCode.CONTRACT_NOT_YAML,
                "$",
                f"unable to parse YAML: {exc}",
            )
        )
        return ContractValidationResult(contract_path, "", False, tuple(errors))

    if not isinstance(parsed, dict):
        errors.append(
            ContractValidationError(
                ContractErrorCode.CONTRACT_NOT_OBJECT,
                "$",
                "YAML root must be a mapping",
            )
        )
        return ContractValidationResult(contract_path, "", False, tuple(errors))

    source_kind = str(parsed.get("source_kind", "") or "")

    for required in _REQUIRED_TOP_LEVEL_FIELDS:
        if required not in parsed:
            errors.append(
                ContractValidationError(
                    ContractErrorCode.MISSING_FIELD,
                    required,
                    f"required field missing: {required}",
                )
            )

    if errors:
        return ContractValidationResult(
            contract_path, source_kind, False, tuple(errors), tuple(warnings)
        )

    # Each helper appends to errors/warnings in encounter order.
    _check_source_family(parsed, errors)
    _check_sub_kinds(parsed, errors)
    _check_raw_artifact_boundary(parsed, errors)
    _check_identity(parsed, errors)
    _check_temporal_fields(parsed, errors)
    _check_deduplication(parsed, errors)
    _check_privacy(parsed, errors)
    _check_projection_families(parsed, errors)
    _check_operational_families(parsed, errors)
    _check_extraction_eligibility(parsed, errors, warnings)
    _check_raw_retention(parsed, errors)
    _check_provenance(parsed, errors)
    _check_rebuild(parsed, errors)
    _check_tests(parsed, errors)

    return ContractValidationResult(
        contract_path=contract_path,
        source_kind=source_kind,
        is_valid=not errors,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


def _empty_or_missing(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str) and value.strip() == "":
        return True
    if isinstance(value, (list, tuple, dict)) and len(value) == 0:
        return True
    return False


def _check_source_family(data: dict[str, Any], errors: list[ContractValidationError]) -> None:
    value = data.get("source_family")
    if _empty_or_missing(value):
        errors.append(
            ContractValidationError(
                ContractErrorCode.EMPTY_FIELD, "source_family", "source_family is empty"
            )
        )
        return
    if value not in SOURCE_FAMILIES:
        errors.append(
            ContractValidationError(
                ContractErrorCode.UNKNOWN_SOURCE_FAMILY,
                "source_family",
                f"unknown source_family: {value}",
            )
        )


def _check_sub_kinds(data: dict[str, Any], errors: list[ContractValidationError]) -> None:
    value = data.get("sub_kinds")
    if not isinstance(value, list) or len(value) == 0:
        errors.append(
            ContractValidationError(
                ContractErrorCode.EMPTY_FIELD, "sub_kinds", "sub_kinds must be a non-empty list"
            )
        )
        return
    for entry in value:
        if not isinstance(entry, str) or entry.strip() == "":
            errors.append(
                ContractValidationError(
                    ContractErrorCode.EMPTY_FIELD,
                    "sub_kinds",
                    f"sub_kinds entry must be a non-empty string: {entry!r}",
                )
            )


def _check_raw_artifact_boundary(
    data: dict[str, Any], errors: list[ContractValidationError]
) -> None:
    value = data.get("raw_artifact_boundary")
    if not isinstance(value, dict):
        errors.append(
            ContractValidationError(
                ContractErrorCode.EMPTY_FIELD,
                "raw_artifact_boundary",
                "raw_artifact_boundary must be an object",
            )
        )
        return
    if _empty_or_missing(value.get("description")):
        errors.append(
            ContractValidationError(
                ContractErrorCode.MISSING_FIELD,
                "raw_artifact_boundary.description",
                "description is required",
            )
        )
    acquisition = value.get("acquisition")
    if not isinstance(acquisition, list) or len(acquisition) == 0:
        errors.append(
            ContractValidationError(
                ContractErrorCode.MISSING_FIELD,
                "raw_artifact_boundary.acquisition",
                "acquisition must be a non-empty list",
            )
        )
    network_policy = value.get("network_policy")
    if network_policy not in NETWORK_POLICIES:
        errors.append(
            ContractValidationError(
                ContractErrorCode.UNKNOWN_NETWORK_POLICY,
                "raw_artifact_boundary.network_policy",
                f"network_policy must be one of {sorted(NETWORK_POLICIES)}",
            )
        )


def _check_identity(data: dict[str, Any], errors: list[ContractValidationError]) -> None:
    value = data.get("identity")
    if not isinstance(value, dict):
        errors.append(
            ContractValidationError(
                ContractErrorCode.EMPTY_FIELD, "identity", "identity must be an object"
            )
        )
        return
    for key in ("source_instance_id", "item_identity_keys"):
        if _empty_or_missing(value.get(key)):
            errors.append(
                ContractValidationError(
                    ContractErrorCode.MISSING_FIELD,
                    f"identity.{key}",
                    f"identity.{key} is required",
                )
            )


def _check_temporal_fields(data: dict[str, Any], errors: list[ContractValidationError]) -> None:
    value = data.get("temporal_fields")
    if not isinstance(value, dict):
        errors.append(
            ContractValidationError(
                ContractErrorCode.EMPTY_FIELD,
                "temporal_fields",
                "temporal_fields must be an object",
            )
        )
        return
    for key in ("observed_at", "recorded_at"):
        if _empty_or_missing(value.get(key)):
            errors.append(
                ContractValidationError(
                    ContractErrorCode.MISSING_FIELD,
                    f"temporal_fields.{key}",
                    f"temporal_fields.{key} is required",
                )
            )


def _check_deduplication(data: dict[str, Any], errors: list[ContractValidationError]) -> None:
    value = data.get("deduplication")
    if not isinstance(value, dict):
        errors.append(
            ContractValidationError(
                ContractErrorCode.EMPTY_FIELD,
                "deduplication",
                "deduplication must be an object",
            )
        )
        return
    if _empty_or_missing(value.get("idempotency_key")):
        errors.append(
            ContractValidationError(
                ContractErrorCode.MISSING_FIELD,
                "deduplication.idempotency_key",
                "idempotency_key is required",
            )
        )
    policy = value.get("conflict_policy")
    if policy not in CONFLICT_POLICIES:
        errors.append(
            ContractValidationError(
                ContractErrorCode.UNKNOWN_CONFLICT_POLICY,
                "deduplication.conflict_policy",
                f"conflict_policy must be one of {sorted(CONFLICT_POLICIES)}",
            )
        )


def _check_privacy(data: dict[str, Any], errors: list[ContractValidationError]) -> None:
    value = data.get("privacy")
    if not isinstance(value, dict):
        errors.append(
            ContractValidationError(
                ContractErrorCode.EMPTY_FIELD, "privacy", "privacy must be an object"
            )
        )
        return
    tier = value.get("privacy_tier_default")
    if not isinstance(tier, int) or tier < 1 or tier > 5 or isinstance(tier, bool):
        errors.append(
            ContractValidationError(
                ContractErrorCode.INVALID_PRIVACY_TIER,
                "privacy.privacy_tier_default",
                "privacy_tier_default must be an integer in 1..5",
            )
        )
    sensitivity = value.get("sensitivity_class_default")
    if sensitivity not in SENSITIVITY_CLASSES:
        errors.append(
            ContractValidationError(
                ContractErrorCode.UNKNOWN_SENSITIVITY_CLASS,
                "privacy.sensitivity_class_default",
                f"sensitivity_class_default must be one of {sorted(SENSITIVITY_CLASSES)}",
            )
        )


def _check_projection_families(
    data: dict[str, Any], errors: list[ContractValidationError]
) -> None:
    value = data.get("projection_families")
    if not isinstance(value, list) or len(value) == 0:
        errors.append(
            ContractValidationError(
                ContractErrorCode.EMPTY_FIELD,
                "projection_families",
                "projection_families must be a non-empty list",
            )
        )
        return
    for entry in value:
        if entry not in PROJECTION_FAMILIES:
            errors.append(
                ContractValidationError(
                    ContractErrorCode.UNKNOWN_PROJECTION_FAMILY,
                    "projection_families",
                    f"unknown projection family: {entry}",
                )
            )


def _check_operational_families(
    data: dict[str, Any], errors: list[ContractValidationError]
) -> None:
    value = data.get("operational_families")
    if not isinstance(value, list) or len(value) == 0:
        errors.append(
            ContractValidationError(
                ContractErrorCode.EMPTY_FIELD,
                "operational_families",
                "operational_families must be a non-empty list",
            )
        )
        return
    for entry in value:
        if entry not in OPERATIONAL_FAMILIES:
            errors.append(
                ContractValidationError(
                    ContractErrorCode.UNKNOWN_OPERATIONAL_FAMILY,
                    "operational_families",
                    f"unknown operational family: {entry}",
                )
            )


def _check_extraction_eligibility(
    data: dict[str, Any],
    errors: list[ContractValidationError],
    warnings: list[ContractValidationWarning],
) -> None:
    value = data.get("extraction_eligibility")
    if not isinstance(value, dict):
        errors.append(
            ContractValidationError(
                ContractErrorCode.EMPTY_FIELD,
                "extraction_eligibility",
                "extraction_eligibility must be an object",
            )
        )
        return
    default = value.get("default")
    if default not in EXTRACTION_DEFAULTS:
        errors.append(
            ContractValidationError(
                ContractErrorCode.INVALID_EXTRACTION_DEFAULT,
                "extraction_eligibility.default",
                f"default must be one of {sorted(EXTRACTION_DEFAULTS)}",
            )
        )
    participant = value.get("participant_third_party")
    if not isinstance(participant, bool):
        errors.append(
            ContractValidationError(
                ContractErrorCode.INVALID_PARTICIPANT_THIRD_PARTY,
                "extraction_eligibility.participant_third_party",
                "participant_third_party must be a boolean",
            )
        )
        return
    if participant and default != "disabled":
        warnings.append(
            ContractValidationWarning(
                "extraction_eligibility",
                "participant_third_party=true with non-disabled default; double-check the RFC 0050 third-party gate",
            )
        )


def _check_raw_retention(data: dict[str, Any], errors: list[ContractValidationError]) -> None:
    value = data.get("raw_retention")
    if not isinstance(value, dict):
        errors.append(
            ContractValidationError(
                ContractErrorCode.EMPTY_FIELD, "raw_retention", "raw_retention must be an object"
            )
        )
        return
    required = value.get("required")
    if not isinstance(required, list) or len(required) == 0 or not all(
        isinstance(entry, str) and entry.strip() != "" for entry in required
    ):
        errors.append(
            ContractValidationError(
                ContractErrorCode.INVALID_RAW_RETENTION,
                "raw_retention.required",
                "raw_retention.required must be a non-empty list of non-empty strings",
            )
        )


def _check_provenance(data: dict[str, Any], errors: list[ContractValidationError]) -> None:
    value = data.get("provenance")
    if not isinstance(value, dict):
        errors.append(
            ContractValidationError(
                ContractErrorCode.EMPTY_FIELD, "provenance", "provenance must be an object"
            )
        )
        return
    required = value.get("required")
    if not isinstance(required, list) or len(required) == 0 or not all(
        isinstance(entry, str) and entry.strip() != "" for entry in required
    ):
        errors.append(
            ContractValidationError(
                ContractErrorCode.INVALID_PROVENANCE,
                "provenance.required",
                "provenance.required must be a non-empty list of non-empty strings",
            )
        )


def _check_rebuild(data: dict[str, Any], errors: list[ContractValidationError]) -> None:
    value = data.get("rebuild")
    if not isinstance(value, dict):
        errors.append(
            ContractValidationError(
                ContractErrorCode.EMPTY_FIELD, "rebuild", "rebuild must be an object"
            )
        )
        return
    for key in ("projection_generation", "reproject_from_raw", "stale_projection_policy"):
        if _empty_or_missing(value.get(key)):
            errors.append(
                ContractValidationError(
                    ContractErrorCode.MISSING_FIELD,
                    f"rebuild.{key}",
                    f"rebuild.{key} is required",
                )
            )


def _check_tests(data: dict[str, Any], errors: list[ContractValidationError]) -> None:
    value = data.get("tests")
    if not isinstance(value, list) or len(value) == 0:
        errors.append(
            ContractValidationError(
                ContractErrorCode.EMPTY_FIELD, "tests", "tests must be a non-empty list"
            )
        )
        return
    for entry in value:
        if entry not in KNOWN_TEST_NAMES:
            errors.append(
                ContractValidationError(
                    ContractErrorCode.UNKNOWN_TEST_NAME,
                    "tests",
                    f"unknown test name: {entry}",
                )
            )


# Allow importer code or future tooling to read the contracts directory path
# from an env var without hardcoding it.
SOURCE_CONTRACTS_DIR = Path(
    os.environ.get("ENGRAM_SOURCE_CONTRACTS_DIR", "docs/source-contracts")
)
