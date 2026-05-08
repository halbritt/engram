# Final Review RFC 0021 Implementation

Review the completed implementation against RFC 0021 (revised), D079, and
the verification report. Do not modify implementation files.

Prioritize:

1. **Append-only enforcement.** Trigger `fn_gold_labels_append_only`
   exists, raises `P0001` on UPDATE/DELETE, and the test for it actually
   exercises the failure path (not a mock).
2. **Polymorphic FK guard.** Trigger `fn_gold_labels_validate_target`
   refuses dangling `(target_kind, target_id)` references; tested with
   missing parent + wrong-kind cases.
3. **Privacy-tier carry.** `fn_gold_labels_carry_privacy_tier` copies
   the parent's `privacy_tier`; operator-supplied disagreement is
   rejected.
4. **Fail-closed export ceiling.** `engram phase3 interview export` with
   no `--privacy-tier-max` defaults to 1; tested.
5. **Phase-scoped CLI placement.** No bare `engram interview` namespace;
   all subcommands live under `engram phase3 interview` per D078.
6. **D044 / D052 invariants.** Loader does not call
   `engram.consolidator.transitions`; verdicts do not flip
   `beliefs.status`.
7. **Prompt template versioning.** Filenames match
   `prompt_template_version` strings stored in `gold_labels` rows per
   RFC 0017.
8. **Cooldown defaults via env vars.** `ENGRAM_GOLD_COOLDOWN_*` env
   vars are read at module top per the Python coding standard.
9. **Test coverage.** No live LLM calls; deterministic fixtures only;
   each trigger has at least one negative test.

Write `docs/reviews/rfc0021-gold-set-implementation/FINAL_REVIEW.md`
with the exact lowercase `author:` line from the work packet. Lead with
findings ordered by severity. Use `accept` only if the implementation
is ready to land; use `needs_revision` for blocking behavioral or
safety gaps. The cycle declared in `workflow.json` returns the run to
`implement_gold_set` once on `needs_revision`.
