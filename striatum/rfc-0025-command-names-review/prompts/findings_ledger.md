# RFC 0025 Findings Ledger — Task

Read the three independent reviews under `docs/reviews/rfc0025/`:

- `RFC_0025_COMMAND_NAMES_REVIEW_claude.md`
- `RFC_0025_COMMAND_NAMES_REVIEW_codex.md`
- `RFC_0025_COMMAND_NAMES_REVIEW_gemini.md`

Normalize them into a stable findings ledger. The ledger is a flat list of
unique findings with stable IDs that downstream synthesis can reference.

## Rules

1. Assign IDs `F001` upward in the order findings first appear (claude →
   codex → gemini).
2. A finding raised by multiple reviewers is one ledger entry with a
   `sources: [claude, codex]` list.
3. Merge near-duplicates when they cite the same risk axis and the same
   command surface, file, or RFC section.
4. Preserve the highest severity reported across merged sources.
5. Do not decide whether findings are accepted, deferred, or rejected.

## Output

Write to `docs/reviews/rfc0025/RFC_0025_COMMAND_NAMES_FINDINGS_LEDGER.md`:

```md
# RFC 0025 Command-Names Findings Ledger

Status: ledger
Date: <YYYY-MM-DD>
Sources:
  - RFC_0025_COMMAND_NAMES_REVIEW_claude.md
  - RFC_0025_COMMAND_NAMES_REVIEW_codex.md
  - RFC_0025_COMMAND_NAMES_REVIEW_gemini.md

## Findings

### F001 — <title>
Severity: <blocking | major | minor | nit>
Sources: [claude, codex]
Affects: <file path, command name, or RFC section>
Rationale: <one sentence>
merged_from:
  - claude § F003
  - codex § F002

## Counts

- Total findings: N
- Severity breakdown: blocking=X, major=Y, minor=Z, nit=W
- Per-reviewer contributions: claude=A, codex=B, gemini=C
```

Do not edit the source review files. Do not modify any RFC, Makefile, or code.
