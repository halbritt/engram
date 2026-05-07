#!/usr/bin/env python3
"""Validate artifact ID references across the Engram repo.

Implements the rules in `docs/process/artifact-id-conventions.md`: walks the
repo, harvests `RFC-NNNN`, `D###`, `PHASE-NNNN`, `REVIEW-NNNN`, and
`<id>#<slug>` references, and verifies that target artifacts and anchors
exist. No external dependencies; run locally or via `make check-refs`.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

SKIP_DIR_NAMES: frozenset[str] = frozenset({
    ".git", "__pycache__", ".venv", "node_modules",
    ".pytest_cache", ".mypy_cache", ".ruff_cache",
    ".scratch", ".agent_runner", "logs", "datasets", "benchmarks",
})
SKIP_RELATIVE_PATHS: tuple[str, ...] = ("agent-runner/.git",)
TEXT_SUFFIXES: frozenset[str] = frozenset({
    ".md", ".py", ".txt", ".yml", ".yaml", ".toml", ".cfg", ".ini", ".json",
})

RFC_RE = re.compile(r"\bRFC-(\d{4})\b")
DECISION_RE = re.compile(r"\bD(\d{3})\b")
PHASE_RE = re.compile(r"\bPHASE-([0-9A-Za-z\-]+)\b")
REVIEW_RE = re.compile(r"\bREVIEW-(\d{4})\b")
SUBREF_RE = re.compile(
    r"\b(RFC-\d{4}|D\d{3}|PHASE-[0-9A-Za-z\-]+|REVIEW-\d{4})#([a-z0-9][a-z0-9\-]*)"
)
ANCHOR_RE = re.compile(r'<a id="([^"]+)"></a>')

KNOWN_PHASE_TOKENS: frozenset[str] = frozenset({
    "0001", "0001-5", "0002", "0002-PRE",
    "0003", "0004", "0005", "SMOKE",
})


class RefCheckError(RuntimeError):
    """Raised for unrecoverable checker failures (not per-reference issues)."""


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class Reference:
    kind: str  # 'rfc' | 'decision' | 'phase' | 'review' | 'subref'
    target: str  # canonical ID, e.g. 'RFC-0007', 'D034'
    slug: str | None  # subref slug, else None
    file: Path
    lineno: int


@dataclass
class Findings:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    oks: list[str] = field(default_factory=list)


@dataclass
class RepoFacts:
    rfc_files: dict[str, Path]  # 'RFC-0007' -> file path
    rfc_index_links: set[str]  # RFC IDs linked from docs/rfcs/README.md
    decision_log_text: str
    decision_log_path: Path
    build_phases_text: str
    build_phases_path: Path
    review_registry_ids: set[str]
    review_anchor_files: dict[str, Path]  # 'REVIEW-0003' -> review doc path


# ---------------------------------------------------------------------------
# File walking
# ---------------------------------------------------------------------------


def iter_repo_files(root: Path) -> Iterable[Path]:
    """Yield candidate text files under ``root`` skipping noise directories."""
    root = root.resolve()
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        rel_parts = path.relative_to(root).parts
        if any(part in SKIP_DIR_NAMES for part in rel_parts):
            continue
        rel_str = "/".join(rel_parts)
        if any(rel_str.startswith(skip) for skip in SKIP_RELATIVE_PATHS):
            continue
        if path.suffix and path.suffix not in TEXT_SUFFIXES:
            continue
        yield path


def read_text(path: Path) -> str | None:
    """Read ``path`` as UTF-8; return ``None`` for binaries or generated files."""
    try:
        text = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return None
    head = "\n".join(text.splitlines()[:10]).lower()
    if "do not edit by hand" in head or "@generated" in head:
        return None
    if "generated" in head and "do not" in head:
        return None
    return text


# ---------------------------------------------------------------------------
# Reference harvesting
# ---------------------------------------------------------------------------


def harvest_references(path: Path, text: str) -> list[Reference]:
    refs: list[Reference] = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        for m in SUBREF_RE.finditer(line):
            refs.append(Reference("subref", m.group(1), m.group(2), path, lineno))
        for m in RFC_RE.finditer(line):
            refs.append(Reference("rfc", f"RFC-{m.group(1)}", None, path, lineno))
        for m in DECISION_RE.finditer(line):
            refs.append(Reference("decision", f"D{m.group(1)}", None, path, lineno))
        for m in PHASE_RE.finditer(line):
            tok = m.group(1)
            if tok in KNOWN_PHASE_TOKENS:
                refs.append(Reference("phase", f"PHASE-{tok}", None, path, lineno))
        for m in REVIEW_RE.finditer(line):
            refs.append(Reference("review", f"REVIEW-{m.group(1)}", None, path, lineno))
    return refs


# ---------------------------------------------------------------------------
# Repository fact-gathering
# ---------------------------------------------------------------------------


def collect_repo_facts(root: Path) -> RepoFacts:
    rfc_dir = root / "docs" / "rfcs"
    rfc_files: dict[str, Path] = {}
    if rfc_dir.is_dir():
        for path in sorted(rfc_dir.glob("*.md")):
            if path.name == "README.md":
                continue
            m = re.match(r"^(\d{4})-", path.name)
            if m:
                rfc_files[f"RFC-{m.group(1)}"] = path

    rfc_index_links: set[str] = set()
    rfc_readme = rfc_dir / "README.md"
    if rfc_readme.is_file():
        readme_text = rfc_readme.read_text(encoding="utf-8", errors="replace")
        for m in re.finditer(r"\(\s*(\d{4})-[^)\s]+\.md", readme_text):
            rfc_index_links.add(f"RFC-{m.group(1)}")

    decision_log_path = root / "DECISION_LOG.md"
    decision_log_text = (
        decision_log_path.read_text(encoding="utf-8", errors="replace")
        if decision_log_path.is_file() else ""
    )

    build_phases_path = root / "BUILD_PHASES.md"
    build_phases_text = (
        build_phases_path.read_text(encoding="utf-8", errors="replace")
        if build_phases_path.is_file() else ""
    )

    review_registry_path = root / "docs" / "artifacts" / "review-id-registry.md"
    review_registry_ids: set[str] = set()
    if review_registry_path.is_file():
        reg_text = review_registry_path.read_text(encoding="utf-8", errors="replace")
        for m in REVIEW_RE.finditer(reg_text):
            review_registry_ids.add(f"REVIEW-{m.group(1)}")

    review_anchor_files: dict[str, Path] = {}
    reviews_dir = root / "docs" / "reviews"
    if reviews_dir.is_dir():
        anchor_re = re.compile(r'<a id="review-(\d{4})"></a>')
        for path in reviews_dir.rglob("*.md"):
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            for m in anchor_re.finditer(text):
                review_anchor_files.setdefault(f"REVIEW-{m.group(1)}", path)

    return RepoFacts(
        rfc_files=rfc_files,
        rfc_index_links=rfc_index_links,
        decision_log_text=decision_log_text,
        decision_log_path=decision_log_path,
        build_phases_text=build_phases_text,
        build_phases_path=build_phases_path,
        review_registry_ids=review_registry_ids,
        review_anchor_files=review_anchor_files,
    )


def file_anchors(text: str) -> set[str]:
    return set(ANCHOR_RE.findall(text))


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------


def check_rfc_files_and_anchors(facts: RepoFacts, findings: Findings) -> None:
    for rfc_id, path in sorted(facts.rfc_files.items()):
        text = path.read_text(encoding="utf-8", errors="replace")
        head = "\n".join(text.splitlines()[:5])
        wanted = f'<a id="{rfc_id.lower()}"></a>'
        if wanted in head:
            findings.oks.append(f"RFC file anchor present: {rfc_id} ({path.name})")
        else:
            findings.errors.append(
                f"RFC file missing top-level anchor `{wanted}` in first 5 lines: {path}"
            )
        if rfc_id not in facts.rfc_index_links:
            findings.errors.append(
                f"RFC {rfc_id} is not linked from docs/rfcs/README.md (expected link to {path.name})"
            )


def check_rfc_references(refs: list[Reference], facts: RepoFacts, findings: Findings) -> None:
    for ref in _unique(refs, "rfc"):
        if ref.target in facts.rfc_files:
            findings.oks.append(f"RFC reference resolves: {ref.target}")
        else:
            findings.errors.append(
                f"RFC reference {ref.target} has no matching docs/rfcs/NNNN-*.md file"
                f" (first cited from {ref.file}:{ref.lineno})"
            )


def check_decision_references(refs: list[Reference], facts: RepoFacts, findings: Findings) -> None:
    for ref in _unique(refs, "decision", skip_filename="DECISION_LOG.md"):
        anchor = f'<a id="{ref.target.lower()}"></a>'
        row_start = f"| {ref.target} |"
        if anchor in facts.decision_log_text or row_start in facts.decision_log_text:
            findings.oks.append(f"Decision reference resolves: {ref.target}")
        else:
            findings.errors.append(
                f"Decision reference {ref.target} not found in DECISION_LOG.md"
                f" (first cited from {ref.file}:{ref.lineno})"
            )


def check_phase_references(refs: list[Reference], facts: RepoFacts, findings: Findings) -> None:
    for ref in _unique(refs, "phase"):
        token = ref.target[len("PHASE-"):].lower()
        anchor = f'<a id="phase-{token}"></a>'
        if anchor in facts.build_phases_text:
            findings.oks.append(f"Phase reference resolves: {ref.target}")
        else:
            findings.errors.append(
                f"Phase reference {ref.target} not found as `{anchor}` in BUILD_PHASES.md"
                f" (first cited from {ref.file}:{ref.lineno})"
            )


def check_review_references(refs: list[Reference], facts: RepoFacts, findings: Findings) -> None:
    for ref in _unique(refs, "review", skip_filename="review-id-registry.md"):
        in_registry = ref.target in facts.review_registry_ids
        in_review = ref.target in facts.review_anchor_files
        if in_registry and in_review:
            findings.oks.append(f"Review reference resolves: {ref.target}")
            continue
        if not in_registry:
            findings.errors.append(
                f"Review reference {ref.target} not listed in"
                f" docs/artifacts/review-id-registry.md"
                f" (first cited from {ref.file}:{ref.lineno})"
            )
        if not in_review:
            findings.errors.append(
                f"Review reference {ref.target} has no"
                f' `<a id="review-{ref.target[-4:]}"></a>` anchor under docs/reviews/'
                f" (first cited from {ref.file}:{ref.lineno})"
            )


def _resolve_subref_target(ref: Reference, facts: RepoFacts) -> Path | None:
    if ref.target.startswith("RFC-"):
        return facts.rfc_files.get(ref.target)
    if ref.target.startswith("D") and not ref.target.startswith("PHASE-"):
        # 'D###' decisions (PHASE- already filtered).
        return facts.decision_log_path if facts.decision_log_text else None
    if ref.target.startswith("PHASE-"):
        return facts.build_phases_path if facts.build_phases_text else None
    if ref.target.startswith("REVIEW-"):
        return facts.review_anchor_files.get(ref.target)
    return None


def check_subref_anchors(
    refs: list[Reference], facts: RepoFacts, findings: Findings, *, strict: bool
) -> None:
    anchor_cache: dict[Path, set[str]] = {}
    seen: set[tuple[str, str]] = set()
    for ref in refs:
        if ref.kind != "subref" or ref.slug is None:
            continue
        key = (ref.target, ref.slug)
        if key in seen:
            continue
        seen.add(key)
        target_path = _resolve_subref_target(ref, facts)
        if target_path is None or not target_path.is_file():
            findings.errors.append(
                f"Subref {ref.target}#{ref.slug} has no resolvable target file"
                f" (cited from {ref.file}:{ref.lineno})"
            )
            continue
        if target_path not in anchor_cache:
            try:
                txt = target_path.read_text(encoding="utf-8", errors="replace")
            except OSError as exc:
                raise RefCheckError(f"unable to read {target_path}: {exc}") from exc
            anchor_cache[target_path] = file_anchors(txt)
        if ref.slug in anchor_cache[target_path]:
            findings.oks.append(f"Subref resolves: {ref.target}#{ref.slug}")
            continue
        msg = (
            f"Subref {ref.target}#{ref.slug} not found as"
            f' `<a id="{ref.slug}"></a>` in {target_path}'
            f" (cited from {ref.file}:{ref.lineno})"
        )
        if strict:
            findings.errors.append(msg)
        else:
            findings.warnings.append(msg)


def check_prompt_ordinals(root: Path, findings: Findings, *, strict: bool) -> None:
    prompts_dir = root / "prompts"
    if not prompts_dir.is_dir():
        return
    by_ordinal: dict[str, list[Path]] = {}
    for path in sorted(prompts_dir.iterdir()):
        if not path.is_file():
            continue
        m = re.match(r"^(P\d{3})_", path.name)
        if m:
            by_ordinal.setdefault(m.group(1), []).append(path)
    duplicates = {k: v for k, v in by_ordinal.items() if len(v) > 1}
    if not duplicates:
        findings.oks.append("Prompt ordinals are unique")
        return
    for ordinal, paths in sorted(duplicates.items()):
        names = ", ".join(p.name for p in paths)
        msg = f"Prompt ordinal {ordinal} used by multiple files: {names}"
        if strict:
            findings.errors.append(msg)
        else:
            findings.warnings.append(msg)


def _unique(
    refs: list[Reference], kind: str, *, skip_filename: str | None = None
) -> Iterable[Reference]:
    seen: set[str] = set()
    for ref in refs:
        if ref.kind != kind:
            continue
        if skip_filename is not None and ref.file.name == skip_filename:
            continue
        if ref.target in seen:
            continue
        seen.add(ref.target)
        yield ref


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------


def run(root: Path, *, strict: bool, quiet: bool) -> int:
    if not root.is_dir():
        raise RefCheckError(f"--root {root} is not a directory")

    facts = collect_repo_facts(root)
    findings = Findings()

    check_rfc_files_and_anchors(facts, findings)

    all_refs: list[Reference] = []
    for path in iter_repo_files(root):
        text = read_text(path)
        if text is None:
            continue
        all_refs.extend(harvest_references(path, text))

    check_rfc_references(all_refs, facts, findings)
    check_decision_references(all_refs, facts, findings)
    check_phase_references(all_refs, facts, findings)
    check_review_references(all_refs, facts, findings)
    check_subref_anchors(all_refs, facts, findings, strict=strict)
    check_prompt_ordinals(root, findings, strict=strict)

    if not quiet:
        for line in findings.oks:
            print(f"[OK] {line}")
    for line in findings.warnings:
        print(f"[WARN] {line}")
    for line in findings.errors:
        print(f"[FAIL] {line}")

    print(
        f"\nSummary: {len(findings.errors)} error(s),"
        f" {len(findings.warnings)} warning(s),"
        f" {len(findings.oks)} check(s) ok."
    )
    return 0 if not findings.errors else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate Engram artifact ID references.")
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="Repo root (default: cwd).")
    parser.add_argument("--strict", action="store_true",
                        help="Treat missing subref anchors as errors instead of warnings.")
    parser.add_argument("--quiet", action="store_true",
                        help="Suppress [OK] lines; report warnings/errors and the summary only.")
    args = parser.parse_args(argv)

    try:
        return run(args.root.resolve(), strict=args.strict, quiet=args.quiet)
    except RefCheckError as exc:
        print(f"[FAIL] {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
