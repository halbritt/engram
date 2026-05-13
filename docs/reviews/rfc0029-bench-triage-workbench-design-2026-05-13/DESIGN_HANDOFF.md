# RFC 0029 Bench Triage Workbench Design Handoff
author: operator [self-declared: rfc0029-design-author-codex]

Status: draft
Date: 2026-05-13
RFC refs: RFC-0029
Decision refs: D020, D074
Phase refs: PHASE-0003-FOLLOWON, PHASE-0004

## Summary

Drafted RFC 0029 as a fresh local-only proposal for a benchmark triage
workbench that helps the operator validate extraction and re-extraction deltas
without relying on tracked Markdown artifacts containing private corpus text.
The proposal keeps review state scratch-local, leaves production data
unchanged, follows the RFC 0027 FastAPI/Jinja2/htmx posture, and exports only
redacted summaries on explicit CLI command.

## Files changed

- `docs/rfcs/0029-bench-triage-workbench.md`
- `docs/rfcs/README.md`
- `docs/reviews/rfc0029-bench-triage-workbench-design-2026-05-13/DESIGN_HANDOFF.md`

## Design highlights

- Defines `engram phase3 bench-review {serve,status,export}` as the v1 CLI
  surface.
- Uses private SQLite review state under `.scratch/benchmarks/extraction-review/`.
- Materializes `segment_queue` separately from `segment_reviews` so undecided
  rows, blockers, and readiness can be computed without sentinel decisions.
- Separates data-availability states from risk classification so missing,
  malformed, redacted, zeroed, and ambiguous rows are not collapsed.
- Provides queue tabs for zeroed, newly nonzero, count changes, predicate-mix
  changes, high drops, provenance anomalies, schema/parse anomalies, and all
  items.
- Treats promotion readiness as a derived signal, not as promotion itself.
- States that scratch run decisions are review evidence only; D074 gate state
  still belongs in Striatum/docs.

## Privacy notes

The RFC preserves the no-egress constraint: loopback-only bind, no CDN, no
telemetry, no hosted storage, no browser asset fetch, and no non-loopback
outbound HTTP/DNS/socket access from the corpus-reading process. Production
Postgres access is mechanically read-only via a read-only role and/or read-only
transactions. The UI may display private text locally, but scratch review state
stores only identifiers, derived queue tags, decisions, confidence, timestamps,
and notes. Tracked exports omit raw segment text, message text, claim text,
prompts, completions, private values, home-directory absolute paths, local
model filesystem paths, and operator-chosen raw artifact filenames.

## Tests / validation run

- Ran four read-only sub-agent checks for design coverage, privacy/local-first,
  CLI/export, and UX/routes. Accepted deltas were folded into the RFC.
- `git diff --check` passed.
- Targeted `rg` check found no stale RFC 0029 quarantine/spec/implemented
  metadata. Remaining matches were unrelated RFC index rows or explicit
  negative export language.
- No unit tests were run; this was a documentation-only RFC/index/handoff
  change.

## Known open questions

- Whether scratch SQLite remains the long-term home for benchmark-review
  decisions or later graduates to an append-only Postgres table.
- Whether candidate claim text should be emitted by the benchmark harness for
  local display as scratch-only data.
- The exact migration/operator path for provisioning the read-only Postgres
  role required by the workbench.
- Whether Phase 4 eventually gets a `phase4 bench-review` alias.
- Whether `candidate_redacted` items can ever be semantically accepted without
  a local source excerpt.
