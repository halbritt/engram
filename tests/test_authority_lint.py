"""Tests for the lightweight repo authority lint."""

from __future__ import annotations

from pathlib import Path

from scripts.authority_lint import (
    REQUIRED_RFC_STATUS,
    check_pyyaml_dependency,
    check_rfc_status_consistency,
    parse_project_dependencies,
    parse_rfc_header_status,
    parse_rfc_index_statuses,
    run_checks,
)

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_parse_project_dependencies_normalizes_names() -> None:
    dependencies = parse_project_dependencies(REPO_ROOT / "pyproject.toml")

    assert "pyyaml" in dependencies


def test_parse_rfc_status_helpers() -> None:
    index_text = (
        "| [0050](0050-source-ingestion-expansion.md) | "
        "accepted_as_design_reference | landed | Topic |\n"
    )
    header_text = (
        "| Field | Value |\n"
        "|-------|-------|\n"
        "| Status | accepted_as_design_reference |\n"
    )

    assert parse_rfc_index_statuses(index_text)["0050"] == REQUIRED_RFC_STATUS
    assert parse_rfc_header_status(header_text) == REQUIRED_RFC_STATUS


def test_pyyaml_dependency_check_passes() -> None:
    assert check_pyyaml_dependency(REPO_ROOT) == []


def test_rfc_status_consistency_passes() -> None:
    assert check_rfc_status_consistency(REPO_ROOT) == []


def test_authority_lint_passes_repo() -> None:
    assert run_checks(REPO_ROOT) == []
