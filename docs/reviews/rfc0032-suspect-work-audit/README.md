# RFC 0032 — Suspect Autonomous Work Audit

This directory contains the audit artifacts produced under
[RFC 0032](../../rfcs/0032-suspect-autonomous-work-recovery.md).

The audit examines commit `c4a48ab` ("Checkpoint suspect autonomous work for
audit") and its merge `eb87392`. RFC 0031 was authored inside the suspect
commit and is superseded; it is preserved unchanged as quarantined evidence.

## Audit author

Every document under this directory is authored by **Claude Code** (the
Anthropic CLI agent) acting as the recovery lane. No document signs under a
different model name or claims multi-lane execution evidence it cannot
produce.

If a future Striatum-orchestrated re-review is performed, that review will
land at a sibling directory with its own provenance, not by overwriting
files here.

## Artifacts

| File | Block | Purpose |
|------|-------|---------|
| `INVENTORY.md` | A | File-by-file inventory of `c4a48ab` + `eb87392`, grouped by category. |
| `PROVENANCE_AUDIT.md` | B | Per-byline classification (`verified` / `local-codex-mislabeled` / `falsified` / `unverified`) with evidence-or-none. |
| `CODE_REVIEW_RFC0028.md` | C | Independent review of the RFC 0028 (predicate-intent surfacing) implementation diff. |
| `CODE_REVIEW_RFC0029.md` | C | Independent review of the RFC 0029 (bench triage workbench) RFC, spec, and implementation. |
| `CODE_REVIEW.md` | C | Cross-cutting findings: migration 012, `make test` status, Striatum scaffolds, root-level guide files. |
| `ARTIFACT_DISPOSITION.md` | D | Per-artifact recommendation: `accept` / `repair` / `quarantine` / `supersede` / `revert`. |
| `FINAL_DECISION.md` | D | One-page operator summary: what is trusted, what remains suspect, what was reverted. |
| `FORWARD_PATH.md` | D | Pointer to unimplemented ideas worth sequencing after the audit. Not a binding plan. |
