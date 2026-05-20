#!/usr/bin/env python3
"""Check small repo-authority invariants that commonly drift."""

from __future__ import annotations

import argparse
import re
import sys
import tomllib
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

ACCEPTED_REFERENCE_RFC_IDS: tuple[str, ...] = ("0046", "0047", "0048", "0049", "0050")
REQUIRED_RFC_STATUS = "accepted_as_design_reference"
REQUIRED_SCHEMA_TABLES: tuple[str, ...] = (
    "git_commits",
    "git_commit_paths",
    "build_artifacts",
    "build_artifact_findings",
    "markdown_files",
    "markdown_file_chunks",
    "markdown_file_links",
    "source_audits",
)


@dataclass(frozen=True)
class AuthorityFinding:
    """One lint finding emitted by the authority checker."""

    code: str
    message: str


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def parse_project_dependencies(pyproject_path: Path) -> set[str]:
    """Return normalized direct runtime dependency names."""
    with pyproject_path.open("rb") as handle:
        parsed = tomllib.load(handle)

    project = parsed.get("project")
    if not isinstance(project, dict):
        return set()
    dependencies = project.get("dependencies")
    if not isinstance(dependencies, list):
        return set()

    names: set[str] = set()
    for dependency in dependencies:
        if not isinstance(dependency, str):
            continue
        name_match = re.match(r"\s*([A-Za-z0-9_.-]+)", dependency)
        if name_match is not None:
            names.add(name_match.group(1).lower().replace("_", "-"))
    return names


def parse_rfc_index_statuses(index_text: str) -> dict[str, str]:
    """Parse RFC status values from docs/rfcs/README.md."""
    statuses: dict[str, str] = {}
    row_re = re.compile(r"^\| \[(\d{4})\]\([^)]*\) \| ([^|]+) \|", re.MULTILINE)
    for match in row_re.finditer(index_text):
        statuses[match.group(1)] = match.group(2).strip()
    return statuses


def parse_rfc_header_status(rfc_text: str) -> str | None:
    """Parse the Status row from an RFC metadata table."""
    status_match = re.search(r"^\| Status \| ([^|]+) \|", rfc_text, re.MULTILINE)
    if status_match is None:
        return None
    return status_match.group(1).strip()


def check_pyyaml_dependency(root: Path) -> list[AuthorityFinding]:
    """Check that PyYAML is declared as a direct runtime dependency."""
    dependencies = parse_project_dependencies(root / "pyproject.toml")
    if "pyyaml" in dependencies:
        return []
    return [
        AuthorityFinding(
            "PYPROJECT_MISSING_PYYAML",
            "pyproject.toml must declare PyYAML as a direct runtime dependency",
        )
    ]


def check_rfc_status_consistency(root: Path) -> list[AuthorityFinding]:
    """Check accepted-design-reference RFC status in index and file headers."""
    findings: list[AuthorityFinding] = []
    index_path = root / "docs" / "rfcs" / "README.md"
    index_statuses = parse_rfc_index_statuses(_read_text(index_path))

    for rfc_id in ACCEPTED_REFERENCE_RFC_IDS:
        index_status = index_statuses.get(rfc_id)
        if index_status != REQUIRED_RFC_STATUS:
            findings.append(
                AuthorityFinding(
                    "RFC_INDEX_STATUS_DRIFT",
                    f"RFC {rfc_id} index status is {index_status!r}, expected "
                    f"{REQUIRED_RFC_STATUS!r}",
                )
            )

        matches = sorted((root / "docs" / "rfcs").glob(f"{rfc_id}-*.md"))
        if not matches:
            findings.append(
                AuthorityFinding("RFC_FILE_MISSING", f"RFC {rfc_id} file is missing")
            )
            continue
        header_status = parse_rfc_header_status(_read_text(matches[0]))
        if header_status != index_status:
            findings.append(
                AuthorityFinding(
                    "RFC_HEADER_INDEX_STATUS_DRIFT",
                    f"RFC {rfc_id} header status is {header_status!r}, index status is "
                    f"{index_status!r}",
                )
            )
    return findings


def check_schema_docs(root: Path) -> list[AuthorityFinding]:
    """Check generated schema docs mention current source-ingestion tables."""
    schema_text = _read_text(root / "docs" / "schema" / "README.md")
    findings: list[AuthorityFinding] = []
    for table_name in REQUIRED_SCHEMA_TABLES:
        if table_name not in schema_text:
            findings.append(
                AuthorityFinding(
                    "SCHEMA_DOC_TABLE_MISSING",
                    f"docs/schema/README.md does not mention table {table_name}",
                )
            )
    return findings


def run_checks(root: Path) -> list[AuthorityFinding]:
    """Run all authority checks for ``root``."""
    findings: list[AuthorityFinding] = []
    findings.extend(check_pyyaml_dependency(root))
    findings.extend(check_rfc_status_consistency(root))
    findings.extend(check_schema_docs(root))
    return findings


def format_findings(findings: Iterable[AuthorityFinding]) -> list[str]:
    """Format findings for CLI output."""
    return [f"{finding.code}: {finding.message}" for finding in findings]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parent.parent,
        help="repository root to check",
    )
    args = parser.parse_args(argv)

    findings = run_checks(args.root.resolve())
    if findings:
        for line in format_findings(findings):
            print(line, file=sys.stderr)
        return 1

    print("authority lint passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
