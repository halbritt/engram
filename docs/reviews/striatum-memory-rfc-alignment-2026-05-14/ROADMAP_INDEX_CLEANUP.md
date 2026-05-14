# Striatum Memory Roadmap Index Cleanup
author: operator [self-declared: alignment-rfc0049]

Status: cleanup
Date: 2026-05-14
Run ID: run_169531d5568248ff8f0dfc803d955311
Job: cleanup_roadmap_index

## Changed Files

- `STRIATUM_MEMORY_ROADMAP.md`
- `docs/rfcs/README.md`
- `docs/reviews/striatum-memory-rfc-alignment-2026-05-14/ROADMAP_INDEX_CLEANUP.md`

## Cleanup Rationale

The roadmap still said the immediate next step was to scaffold RFC 0045 even
though RFC 0045-RFC 0049 now exist as proposal and review provenance. The
cleanup replaces that stale next-step wording with the current follow-up order:
RFC alignment cleanup, RFC 0044 hardening and EG-000 evidence, then a separate
recorded decision or accepted spec handoff before implementation treats the
proposal package as binding.

The RFC index already kept RFC 0045-RFC 0049 in `proposal | none` state. The
cleanup updates the index sweep date and adds a narrow note that those RFCs do
not authorize implementation, migrations, runtime behavior, or default-on
Striatum memory.

The requested `FINAL_SYNTHESIS.md` and `FINDINGS_LEDGER.md` were read from
`docs/reviews/striatum-memory-roadmap-rfcs-2026-05-14/`, because that is where
the committed synthesis and ledger artifacts for the Striatum memory roadmap
RFC package live.

## Validation

- Read-only sub-agent checks completed for roadmap wording, RFC index wording,
  and cleanup constraints.
- `git diff --check -- STRIATUM_MEMORY_ROADMAP.md docs/rfcs/README.md docs/reviews/striatum-memory-rfc-alignment-2026-05-14/ROADMAP_INDEX_CLEANUP.md`
  passed with exit code 0 and no output for tracked allowed-path changes.
- `git diff --check --no-index -- /dev/null docs/reviews/striatum-memory-rfc-alignment-2026-05-14/ROADMAP_INDEX_CLEANUP.md`
  emitted no whitespace or conflict-marker output for the new handoff artifact.
  Exit code 1 is expected for a no-index diff against `/dev/null`.
- `make check-refs` passed with exit code 0. Summary: 0 errors, 5 warnings,
  191 checks ok. The warnings were outside the changed files.

## Remaining Stale-Doc Risks

- F017 remains in source RFC bodies because this cleanup job explicitly forbids
  editing source RFC bodies.
- Broader RFC index status mismatches, if any, remain outside this Striatum
  roadmap/index cleanup scope.
- Other noncanonical review or brainstorming documents may still describe the
  pre-alignment state and should remain historical context unless referenced by
  canonical docs.
