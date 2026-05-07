<a id="phase-3-cross-corpus-dryrun-template"></a>
# Phase 3 Cross-Corpus Dry-Run Findings — TEMPLATE

Status: template
RFC refs:
  - RFC-0017
Decision refs:
  - D040
Phase refs:
  - PHASE-0003

This file is a *template only*. The harness at
`scripts/cross_corpus_dryrun.py` writes a real, dated copy under
`docs/reviews/phase3/PHASE_3_CROSS_CORPUS_DRYRUN_<YYYYMMDD>.md`. Do not fill
this template with operator data; the corpus is private, only aggregates
travel.

The dry-run procedure and outcome categories live in
RFC-0017 § Part 3 (`docs/rfcs/0017-extraction-prompt-versioning.md`).

## Run summary

- Date: <YYYY-MM-DD>
- Sample size: <N segments>
- Source: Obsidian vault (operator-private; not committed)
- Extraction prompt version: <EXTRACTION_PROMPT_VERSION>
- Extractor model version: <model>
- Self-test mode: <true|false>

## Aggregate counts

- Segments processed: <N>
- Segments with 0 claims: <count> (<pct>%)
- Total claims emitted: <N>
- Predicate distribution (top-10): <table>
- Stability-class distribution: <table>
- Contradictions emitted: <N>

## Checklist verdicts

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
