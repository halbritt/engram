# Phase 4 Tiered Gate Sources

Required sources:

- `docs/rfcs/0024-phase-4-pre-full-corpus-benchmark-gate.md`
- `DECISION_LOG.md` (`D077`, `D078`)
- `docs/rfcs/0021-gold-set-interview-curation.md`
- `migrations/009_phase4_entities_review.sql`
- `src/engram/phase4.py`
- `src/engram/cli.py`
- `tests/test_phase4_entities_review.py`
- `Makefile`

Privacy boundary:

- Committed reports may include aggregate counts, timings, command lines,
  redacted ids, and error classes.
- Committed reports must not include raw corpus text, model prompts or
  completions containing private data, conversation titles, belief values,
  claim values, entity names, relationship labels, or home-directory absolute
  paths.
