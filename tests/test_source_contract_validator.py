"""Tests for the RFC 0050 source contract validator."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml  # type: ignore[import-not-found]

from engram.source_contract import (
    ContractErrorCode,
    SOURCE_CONTRACTS_DIR,
    validate_contract,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
CONTRACTS_DIR = REPO_ROOT / SOURCE_CONTRACTS_DIR


def _git_yaml() -> Path:
    return CONTRACTS_DIR / "git.yaml"


def _build_artifact_yaml() -> Path:
    return CONTRACTS_DIR / "build_artifact.yaml"


def test_template_present() -> None:
    template = CONTRACTS_DIR / "README.md"
    assert template.is_file(), f"contract template missing: {template}"


def test_git_contract_valid() -> None:
    result = validate_contract(_git_yaml())
    assert result.is_valid, result.errors


def test_build_artifact_contract_valid() -> None:
    result = validate_contract(_build_artifact_yaml())
    assert result.is_valid, result.errors


def test_missing_field_codes(tmp_path: Path) -> None:
    base_yaml = _git_yaml().read_text(encoding="utf-8")
    base = yaml.safe_load(base_yaml)
    for required in (
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
    ):
        mutated = {k: v for k, v in base.items() if k != required}
        path = tmp_path / f"missing_{required}.yaml"
        path.write_text(yaml.safe_dump(mutated, sort_keys=False), encoding="utf-8")
        result = validate_contract(path)
        codes = [error.code for error in result.errors]
        assert (
            ContractErrorCode.MISSING_FIELD in codes
        ), f"expected MISSING_FIELD for {required}: {codes}"


def test_unknown_projection_family(tmp_path: Path) -> None:
    base = yaml.safe_load(_git_yaml().read_text(encoding="utf-8"))
    base["projection_families"] = ["generated_product"]
    path = tmp_path / "bad_projection.yaml"
    path.write_text(yaml.safe_dump(base, sort_keys=False), encoding="utf-8")
    result = validate_contract(path)
    codes = [error.code for error in result.errors]
    assert ContractErrorCode.UNKNOWN_PROJECTION_FAMILY in codes


def test_unknown_sensitivity_class(tmp_path: Path) -> None:
    base = yaml.safe_load(_git_yaml().read_text(encoding="utf-8"))
    base["privacy"]["sensitivity_class_default"] = "super_secret"
    path = tmp_path / "bad_sensitivity.yaml"
    path.write_text(yaml.safe_dump(base, sort_keys=False), encoding="utf-8")
    result = validate_contract(path)
    codes = [error.code for error in result.errors]
    assert ContractErrorCode.UNKNOWN_SENSITIVITY_CLASS in codes


@pytest.mark.parametrize("tier", [0, 6, -1, "1"])
def test_invalid_privacy_tier(tmp_path: Path, tier: object) -> None:
    base = yaml.safe_load(_git_yaml().read_text(encoding="utf-8"))
    base["privacy"]["privacy_tier_default"] = tier
    path = tmp_path / f"bad_tier_{tier!r}.yaml"
    path.write_text(yaml.safe_dump(base, sort_keys=False), encoding="utf-8")
    result = validate_contract(path)
    codes = [error.code for error in result.errors]
    assert ContractErrorCode.INVALID_PRIVACY_TIER in codes


def test_participant_third_party_must_be_bool(tmp_path: Path) -> None:
    base = yaml.safe_load(_git_yaml().read_text(encoding="utf-8"))
    base["extraction_eligibility"]["participant_third_party"] = "false"
    path = tmp_path / "bad_participant.yaml"
    path.write_text(yaml.safe_dump(base, sort_keys=False), encoding="utf-8")
    result = validate_contract(path)
    codes = [error.code for error in result.errors]
    assert ContractErrorCode.INVALID_PARTICIPANT_THIRD_PARTY in codes


def test_unknown_network_policy(tmp_path: Path) -> None:
    base = yaml.safe_load(_git_yaml().read_text(encoding="utf-8"))
    base["raw_artifact_boundary"]["network_policy"] = "allow outbound"
    path = tmp_path / "bad_network.yaml"
    path.write_text(yaml.safe_dump(base, sort_keys=False), encoding="utf-8")
    result = validate_contract(path)
    codes = [error.code for error in result.errors]
    assert ContractErrorCode.UNKNOWN_NETWORK_POLICY in codes


def test_unknown_source_family(tmp_path: Path) -> None:
    base = yaml.safe_load(_git_yaml().read_text(encoding="utf-8"))
    base["source_family"] = "spaceship_telemetry"
    path = tmp_path / "bad_family.yaml"
    path.write_text(yaml.safe_dump(base, sort_keys=False), encoding="utf-8")
    result = validate_contract(path)
    codes = [error.code for error in result.errors]
    assert ContractErrorCode.UNKNOWN_SOURCE_FAMILY in codes


def test_contract_file_not_found(tmp_path: Path) -> None:
    result = validate_contract(tmp_path / "missing.yaml")
    codes = [error.code for error in result.errors]
    assert codes == [ContractErrorCode.CONTRACT_FILE_NOT_FOUND]
    assert not result.is_valid


def test_contract_not_yaml(tmp_path: Path) -> None:
    path = tmp_path / "bad.yaml"
    path.write_text(": : : not yaml", encoding="utf-8")
    result = validate_contract(path)
    codes = [error.code for error in result.errors]
    assert ContractErrorCode.CONTRACT_NOT_YAML in codes


def test_contract_not_object(tmp_path: Path) -> None:
    path = tmp_path / "list.yaml"
    path.write_text("- not\n- a\n- mapping\n", encoding="utf-8")
    result = validate_contract(path)
    codes = [error.code for error in result.errors]
    assert ContractErrorCode.CONTRACT_NOT_OBJECT in codes
