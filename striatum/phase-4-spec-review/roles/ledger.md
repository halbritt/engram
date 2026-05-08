# Ledger Role — Phase 4 Build-Spec Findings Ledger

Normalize the three independent Phase 4 build-spec reviews into a stable
findings ledger. Preserve:

- finding ID (assigned `F001` upward, stable across revisions),
- severity (`blocking`, `major`, `minor`, `nit`),
- source reviewer(s) — list of `claude` / `codex` / `gemini` (a finding
  raised by multiple reviewers is one ledger entry with multiple sources),
- affected files / sections / decision IDs / RFC IDs,
- concise rationale (one sentence; the full reviewer prose lives in the
  individual review artifacts).

Do **not** decide whether findings are accepted or rejected. Do not
synthesize a recommendation. The ledger is a normalization layer; the
synthesis job consumes it.

Group near-duplicate findings under one ID with a `merged_from:` list so
the synthesis reader can trace back to each reviewer's framing. Two
findings are near-duplicates if they cite the same primary risk on the
same file or section, even if the framing differs.

Write only the expected ledger artifact at the path your job-packet
specifies. End with a counts summary: total findings, severity breakdown,
per-reviewer contribution count.
