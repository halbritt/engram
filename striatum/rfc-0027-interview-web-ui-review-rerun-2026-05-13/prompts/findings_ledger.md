# RFC 0027 Findings Ledger — Task

Read the three independent reviews under `docs/reviews/rfc0027-rerun-2026-05-13/`:

- `RFC_0027_INTERVIEW_WEB_UI_REVIEW_claude.md`
- `RFC_0027_INTERVIEW_WEB_UI_REVIEW_codex.md`
- `RFC_0027_INTERVIEW_WEB_UI_REVIEW_gemini.md`

Normalize them into a stable findings ledger.

## Rules

1. Assign IDs `F001` upward in the order findings first appear (claude
   → codex → gemini).
2. A finding raised by multiple reviewers is one ledger entry with a
   `Sources: [...]` list and a `merged_from:` block.
3. Merge near-duplicates that cite the same risk axis and the same
   route, template, render boundary, schema field, or CLI subcommand.
4. Preserve highest severity across merged sources.
5. Do not decide whether findings are accepted, deferred, or rejected.

## Output

Write to `docs/reviews/rfc0027-rerun-2026-05-13/RFC_0027_INTERVIEW_WEB_UI_FINDINGS_LEDGER.md`:

```md
# RFC 0027 Interview Web UI Findings Ledger

Status: ledger
Date: <YYYY-MM-DD>
Sources:
  - RFC_0027_INTERVIEW_WEB_UI_REVIEW_claude.md
  - RFC_0027_INTERVIEW_WEB_UI_REVIEW_codex.md
  - RFC_0027_INTERVIEW_WEB_UI_REVIEW_gemini.md

## Findings

### F001 — <title>
Severity: <blocking | major | minor | nit>
Sources: [claude, codex]
Affects: <route / template / render boundary / schema / CLI / test>
Rationale: <one sentence>
merged_from:
  - claude § F003
  - codex § F002

## Counts

- Total findings: N
- Severity breakdown: blocking=X, major=Y, minor=Z, nit=W
- Per-reviewer contributions: claude=A, codex=B, gemini=C
```

Do not edit the source review files. Do not modify any RFC, migration,
Makefile, or code.
