#!/usr/bin/env python3
"""Cross-corpus dry-run harness for RFC-0017 Part 3.

Walks an Obsidian-style markdown export, builds synthetic
``SegmentPayload`` objects (no DB round-trip), runs them through the live
local extractor, and writes an aggregate findings doc that contains
only counts and hashed references — never raw corpus content.

The corpus is operator-private. Only the operator should run this against
real Obsidian content. The committed artifact is the harness and the
template, not any output. See ``docs/rfcs/0017-extraction-prompt-versioning.md``
§ Part 3 for procedure and outcome categories.

CLI shape::

    python scripts/cross_corpus_dryrun.py \\
        --input-dir <obsidian-export-dir> \\
        [--limit N] \\
        [--output-dir docs/reviews/phase3] \\
        [--self-test]

``--self-test`` swaps in a deterministic fake extractor and is suitable
for end-to-end smoke runs without a live LLM.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import sys
import uuid
from collections import Counter
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

# The harness only needs four things from ``engram``:
# - the live ``EXTRACTION_PROMPT_VERSION`` (for the report)
# - ``SegmentPayload`` / ``SegmentMessage`` to feed ``build_extraction_prompt``
# - ``build_extraction_prompt`` to render the user message
# - ``IkLlamaExtractorClient`` to call the local LLM
#
# We avoid ``extract_claims_from_segment`` because it round-trips through
# Postgres. The synthetic segments never touch the DB; they exist only to
# exercise the extractor's prompt and parse path.
from engram.extractor import (
    EXTRACTION_PROMPT_VERSION,
    ClaimDraft,
    ExtractorClient,
    ExtractorModelOutput,
    IkLlamaExtractorClient,
    SegmentMessage,
    SegmentPayload,
    build_extraction_prompt,
    default_extractor_model_id,
)
from engram.segmenter import IK_LLAMA_BASE_URL, ensure_local_base_url

# --------------------------------------------------------------------------
# Constants
# --------------------------------------------------------------------------

DEFAULT_LIMIT = 50
"""RFC-0017 § Part 3 sample shape — ~50 segments."""

DEFAULT_OUTPUT_DIR = Path("docs/reviews/phase3")

H2_HEADING_RE = re.compile(r"^##\s+\S", re.MULTILINE)

NAMESPACE_DRYRUN = uuid.UUID("e0e0e0e0-0000-4000-8000-000000000017")
"""Stable UUID namespace for synthetic segment/message ids in this run."""

SKIP_DIR_NAMES: frozenset[str] = frozenset(
    {".obsidian", ".git", ".trash", "__pycache__", ".venv"}
)


class CrossCorpusDryRunError(RuntimeError):
    """Raised for unrecoverable harness failures."""


# --------------------------------------------------------------------------
# Synthetic-segment construction
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class SyntheticSegment:
    """A ``SegmentPayload`` plus a hashed source reference for reporting."""

    payload: SegmentPayload
    source_hash: str
    section_index: int


def _stable_uuid(*parts: str) -> str:
    return str(uuid.uuid5(NAMESPACE_DRYRUN, "::".join(parts)))


def _hash_path(path: Path, root: Path) -> str:
    rel = path.resolve().relative_to(root.resolve())
    digest = hashlib.sha256(str(rel).encode("utf-8")).hexdigest()
    return digest[:12]


def iter_markdown_files(root: Path) -> Iterator[Path]:
    """Yield ``.md`` files under ``root``; skip hidden dirs and ``.obsidian/``."""
    if not root.is_dir():
        raise CrossCorpusDryRunError(f"--input-dir is not a directory: {root}")
    for dirpath, dirnames, filenames in os.walk(root):
        # Mutate dirnames in place to prune walk.
        dirnames[:] = [
            d for d in dirnames
            if not d.startswith(".") and d not in SKIP_DIR_NAMES
        ]
        for name in sorted(filenames):
            if name.startswith("."):
                continue
            if not name.lower().endswith(".md"):
                continue
            yield Path(dirpath) / name


def split_on_h2(text: str) -> list[str]:
    """Split markdown ``text`` into sections at H2 headings.

    The text before the first ``##`` heading (the "preamble") is kept as a
    section *only* if it contains non-whitespace content. Each subsequent
    section starts at a ``##`` heading.
    """
    matches = list(H2_HEADING_RE.finditer(text))
    if not matches:
        return [text] if text.strip() else []

    sections: list[str] = []
    preamble = text[: matches[0].start()]
    if preamble.strip():
        sections.append(preamble)
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        sections.append(text[m.start() : end])
    return [s for s in sections if s.strip()]


def _summary_for_section(section_text: str) -> str:
    for line in section_text.splitlines():
        line = line.strip()
        if not line:
            continue
        return line[:200]
    return "(empty)"


def build_synthetic_segments(
    md_path: Path,
    *,
    root: Path,
    section_splits: bool = True,
) -> list[SyntheticSegment]:
    """Convert one markdown file into one or more ``SyntheticSegment``s."""
    try:
        text = md_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise CrossCorpusDryRunError(f"unable to read {md_path}: {exc}") from exc

    if section_splits:
        sections = split_on_h2(text)
    else:
        sections = [text] if text.strip() else []

    if not sections:
        return []

    source_hash = _hash_path(md_path, root)
    out: list[SyntheticSegment] = []
    for index, section in enumerate(sections):
        segment_id = _stable_uuid("segment", source_hash, str(index))
        message_id = _stable_uuid("message", source_hash, str(index))
        generation_id = _stable_uuid("generation", source_hash)
        # ``conversation_id`` is required by the dataclass even though Obsidian
        # notes have no conversation; we feed a stable synthetic id. The
        # extractor's prompt builder does not consult this field.
        conversation_id = _stable_uuid("conversation", source_hash)
        message = SegmentMessage(
            id=message_id,
            sequence_index=0,
            role="note",
            content_text=section,
        )
        payload = SegmentPayload(
            id=segment_id,
            generation_id=generation_id,
            conversation_id=conversation_id,
            source_kind="note",
            message_ids=[message_id],
            content_text=section,
            summary_text=_summary_for_section(section),
            privacy_tier=2,
            messages=[message],
        )
        out.append(
            SyntheticSegment(
                payload=payload,
                source_hash=source_hash,
                section_index=index,
            )
        )
    return out


def discover_segments(
    input_dir: Path,
    *,
    limit: int,
    section_splits: bool = True,
) -> list[SyntheticSegment]:
    """Walk ``input_dir`` and return up to ``limit`` synthetic segments."""
    segments: list[SyntheticSegment] = []
    for md_path in iter_markdown_files(input_dir):
        if len(segments) >= limit:
            break
        for synth in build_synthetic_segments(
            md_path, root=input_dir, section_splits=section_splits
        ):
            segments.append(synth)
            if len(segments) >= limit:
                break
    return segments


# --------------------------------------------------------------------------
# Extraction
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class SegmentExtractionResult:
    source_hash: str
    section_index: int
    claim_count: int
    predicates: list[str]
    stability_classes: list[str]
    error: str | None = None


@dataclass
class AggregateCounts:
    segments_processed: int = 0
    segments_with_zero_claims: int = 0
    total_claims: int = 0
    predicate_counter: Counter[str] = field(default_factory=Counter)
    stability_counter: Counter[str] = field(default_factory=Counter)
    extraction_errors: int = 0
    contradictions: int = 0  # always 0 — consolidation is intentionally skipped


class FakeExtractorClient:
    """Deterministic fake used by ``--self-test``.

    Returns an empty claim list for every call. The harness's value is the
    wiring + reporting; the real extractor has its own test coverage.
    """

    def __init__(self) -> None:
        self.calls: int = 0

    def extract(
        self,
        prompt: str,
        *,
        model_id: str,
        max_tokens: int,
        allowed_message_ids: list[str] | None = None,
        relaxed_schema: bool = False,
    ) -> ExtractorModelOutput:
        self.calls += 1
        return ExtractorModelOutput(
            claims=[],
            model_response='{"claims":[]}',
            parse_metadata={"self_test": True},
            relaxed_schema=relaxed_schema,
        )


def run_extraction(
    segments: list[SyntheticSegment],
    *,
    client: ExtractorClient,
    model_id: str,
    max_tokens: int = 8192,
) -> tuple[list[SegmentExtractionResult], AggregateCounts]:
    """Run ``client.extract`` once per synthetic segment and aggregate."""
    results: list[SegmentExtractionResult] = []
    counts = AggregateCounts()
    for synth in segments:
        prompt = build_extraction_prompt(synth.payload)
        try:
            output = client.extract(
                prompt,
                model_id=model_id,
                max_tokens=max_tokens,
                allowed_message_ids=list(synth.payload.message_ids),
            )
        except Exception as exc:  # noqa: BLE001 — surface error class name only
            counts.segments_processed += 1
            counts.extraction_errors += 1
            results.append(
                SegmentExtractionResult(
                    source_hash=synth.source_hash,
                    section_index=synth.section_index,
                    claim_count=0,
                    predicates=[],
                    stability_classes=[],
                    error=type(exc).__name__,
                )
            )
            continue

        claims: list[ClaimDraft]
        if isinstance(output, ExtractorModelOutput):
            claims = list(output.claims)
        else:
            # ``ExtractorClient.extract`` may return ``list[ClaimDraft]``.
            claims = list(output)

        predicates = [c.predicate for c in claims]
        stability_classes = [c.stability_class for c in claims]
        counts.segments_processed += 1
        counts.total_claims += len(claims)
        if not claims:
            counts.segments_with_zero_claims += 1
        counts.predicate_counter.update(predicates)
        counts.stability_counter.update(stability_classes)
        results.append(
            SegmentExtractionResult(
                source_hash=synth.source_hash,
                section_index=synth.section_index,
                claim_count=len(claims),
                predicates=predicates,
                stability_classes=stability_classes,
            )
        )
    return results, counts


# --------------------------------------------------------------------------
# Reporting
# --------------------------------------------------------------------------


def _pct(numerator: int, denominator: int) -> str:
    if denominator == 0:
        return "n/a"
    return f"{(100.0 * numerator / denominator):.1f}%"


def _format_top_predicates(counter: Counter[str], n: int = 10) -> str:
    if not counter:
        return "(none)"
    rows = ["| predicate | count |", "| --- | --- |"]
    for predicate, count in counter.most_common(n):
        rows.append(f"| {predicate} | {count} |")
    return "\n".join(rows)


def _format_stability_table(counter: Counter[str]) -> str:
    if not counter:
        return "(none)"
    rows = ["| stability_class | count |", "| --- | --- |"]
    for stability_class, count in sorted(counter.items()):
        rows.append(f"| {stability_class} | {count} |")
    return "\n".join(rows)


def render_findings_doc(
    *,
    run_date: date,
    counts: AggregateCounts,
    extraction_prompt_version: str,
    model_id: str,
    self_test: bool,
) -> str:
    """Render the dated findings doc.

    The output is intentionally aggregate-only: no file paths, no source
    text, no claim subjects/objects. The dry-run is operator-private; the
    findings doc is the only artifact that travels.
    """
    zero_pct = _pct(counts.segments_with_zero_claims, counts.segments_processed)
    return f"""<a id="phase-3-cross-corpus-dryrun-{run_date.strftime('%Y%m%d')}"></a>
# Phase 3 Cross-Corpus Dry-Run Findings — {run_date.isoformat()}

Status: findings
RFC refs:
  - RFC-0017
Decision refs:
  - D040
Phase refs:
  - PHASE-0003

Generated by `scripts/cross_corpus_dryrun.py`. The corpus is operator-private;
this document contains only aggregate counts. See RFC-0017 § Part 3 for
procedure and outcome categories.

## Run summary

- Date: {run_date.isoformat()}
- Sample size: {counts.segments_processed} segments
- Source: Obsidian vault (operator-private; not committed)
- Extraction prompt version: {extraction_prompt_version}
- Extractor model version: {model_id}
- Self-test mode: {str(self_test).lower()}

## Aggregate counts

- Segments processed: {counts.segments_processed}
- Segments with 0 claims: {counts.segments_with_zero_claims} ({zero_pct})
- Total claims emitted: {counts.total_claims}
- Extraction errors: {counts.extraction_errors}
- Contradictions emitted: {counts.contradictions} (consolidation not run; cross-corpus contradiction check is operator-driven)

### Predicate distribution (top-10)

{_format_top_predicates(counts.predicate_counter)}

### Stability-class distribution

{_format_stability_table(counts.stability_counter)}

## Checklist verdicts

The four checklist questions below come from RFC-0017 § Part 3 procedure
step 3. Verdicts must be filled in by the operator; the harness only
provides the aggregate counts above as input.

### 1. Did the extractor produce 0 claims for any segment a human would consider claim-bearing?

- Verdict: <clean | tunable | blocking>
- Notes: <human-readable summary, NO raw corpus content>

### 2. Did the extractor force a stability_class onto narrative content that doesn't fit any of the existing classes?

- Verdict: <clean | tunable | blocking>
- Notes:

### 3. Did the predicate vocabulary look strained or AI-conversation-shaped when applied to subjective material?

- Verdict: <clean | tunable | blocking>
- Notes:

### 4. Did consolidation propose contradictions between Obsidian-derived claims and AI-conversation-derived claims that don't actually contradict?

- Verdict: <clean | tunable | blocking>
- Notes:

## Aggregate verdict

- Overall: <clean | tunable | blocking>
- Recommendation: <one line — proceed / prompt-edit / pause schema-dependent work>
"""


def write_findings_doc(
    output_dir: Path,
    *,
    run_date: date,
    counts: AggregateCounts,
    extraction_prompt_version: str,
    model_id: str,
    self_test: bool,
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    filename = f"PHASE_3_CROSS_CORPUS_DRYRUN_{run_date.strftime('%Y%m%d')}.md"
    out_path = output_dir / filename
    body = render_findings_doc(
        run_date=run_date,
        counts=counts,
        extraction_prompt_version=extraction_prompt_version,
        model_id=model_id,
        self_test=self_test,
    )
    out_path.write_text(body, encoding="utf-8")
    return out_path


# --------------------------------------------------------------------------
# Driver
# --------------------------------------------------------------------------


def _ensure_local_endpoint() -> None:
    """Refuse to run if the configured LLM endpoint is non-local."""
    try:
        ensure_local_base_url(IK_LLAMA_BASE_URL)
    except Exception as exc:  # SegmentationError, but we keep coupling loose
        raise CrossCorpusDryRunError(
            f"refusing to run: ENGRAM_IK_LLAMA_BASE_URL must be local-only; "
            f"got {IK_LLAMA_BASE_URL!r} ({exc})"
        ) from exc


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Cross-corpus dry-run harness for RFC-0017 Part 3. Runs the live "
            "extractor against synthetic segments built from an Obsidian "
            "markdown export and writes an aggregate findings doc."
        )
    )
    parser.add_argument(
        "--input-dir",
        type=Path,
        required=True,
        help="Directory of Obsidian-style markdown files to dry-run.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=DEFAULT_LIMIT,
        help=f"Max synthetic segments to process (default: {DEFAULT_LIMIT}).",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help=(
            "Where to write the dated findings doc "
            f"(default: {DEFAULT_OUTPUT_DIR})."
        ),
    )
    parser.add_argument(
        "--no-section-splits",
        action="store_true",
        help="Treat each markdown file as one segment instead of splitting on H2.",
    )
    parser.add_argument(
        "--self-test",
        action="store_true",
        help=(
            "Use a deterministic fake extractor instead of the local LLM. "
            "Useful for end-to-end smoke runs without a model service."
        ),
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=8192,
        help="Per-call max_tokens for the extractor (default: 8192).",
    )
    args = parser.parse_args(argv)

    if args.limit <= 0:
        print("[FAIL] --limit must be positive", file=sys.stderr)
        return 2

    if not args.self_test:
        try:
            _ensure_local_endpoint()
        except CrossCorpusDryRunError as exc:
            print(f"[FAIL] {exc}", file=sys.stderr)
            return 2

    try:
        segments = discover_segments(
            args.input_dir,
            limit=args.limit,
            section_splits=not args.no_section_splits,
        )
    except CrossCorpusDryRunError as exc:
        print(f"[FAIL] {exc}", file=sys.stderr)
        return 2

    if not segments:
        print(f"[FAIL] no markdown files found under {args.input_dir}", file=sys.stderr)
        return 2

    if args.self_test:
        client: ExtractorClient = FakeExtractorClient()
        model_id = "self-test-fake"
    else:
        client = IkLlamaExtractorClient()
        model_id = default_extractor_model_id()

    _, counts = run_extraction(
        segments,
        client=client,
        model_id=model_id,
        max_tokens=args.max_tokens,
    )

    out_path = write_findings_doc(
        args.output_dir,
        run_date=date.today(),
        counts=counts,
        extraction_prompt_version=EXTRACTION_PROMPT_VERSION,
        model_id=model_id,
        self_test=args.self_test,
    )

    print("Cross-corpus dry-run complete.")
    print(f"  Segments processed: {counts.segments_processed}")
    print(f"  Total claims emitted: {counts.total_claims}")
    print(f"  Segments with 0 claims: {counts.segments_with_zero_claims}")
    print(f"  Extraction errors: {counts.extraction_errors}")
    print(f"  Findings doc: {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
