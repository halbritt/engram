# Phase 4 Findings Ledger — Task

Read the three independent reviews under `docs/reviews/phase4/`:

- `PHASE_4_SPEC_REVIEW_claude.md`
- `PHASE_4_SPEC_REVIEW_codex.md`
- `PHASE_4_SPEC_REVIEW_gemini.md`

Normalize them into a stable findings ledger. The ledger is a flat list of
unique findings with stable IDs that downstream synthesis (and any future
revision cycles) can reference.

## Rules

1. Assign IDs `F001` upward in the order findings first appear (claude →
   codex → gemini, then any unique findings raised only by later reviewers).
2. A finding raised by multiple reviewers is one ledger entry with a
   `sources: [claude, codex]` list, not three duplicates.
3. Two findings are near-duplicates and merge into one ID when both:
   - cite the same primary risk axis (schema, view, HITL, query plan,
     disambiguation, provenance, audit, local-first, missing-coverage)
   - point at the same file or section (same `BUILD_PHASES.md` row, same
     `D###`, same RFC).
4. Preserve the highest severity reported across merged sources.
5. Do **not** decide whether findings are accepted, deferred, or rejected.
   That's the synthesis job's call.

## Output

Write to `docs/reviews/phase4/PHASE_4_SPEC_FINDINGS_LEDGER.md`:

```md
# Phase 4 Build-Spec Findings Ledger

Status: ledger
Date: <YYYY-MM-DD>
Sources:
  - PHASE_4_SPEC_REVIEW_claude.md
  - PHASE_4_SPEC_REVIEW_codex.md
  - PHASE_4_SPEC_REVIEW_gemini.md

## Findings

### F001 — <title>
Severity: <blocking | major | minor | nit>
Sources: [claude, codex]
Affects: <file path or DECISION_LOG D###>
Rationale: <one sentence>
merged_from:
  - claude § F003
  - codex § F002

[... more findings ...]

## Counts

- Total findings: N
- Severity breakdown: blocking=X, major=Y, minor=Z, nit=W
- Per-reviewer contributions: claude=A, codex=B, gemini=C
```

Do not edit the source review files. Do not modify any RFC or
`BUILD_PHASES.md`.
