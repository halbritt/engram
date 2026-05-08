# Phase 4 Final Review — Task

Read `PHASE_4_SPEC_SYNTHESIS.md` plus `PHASE_4_SPEC_FINDINGS_LEDGER.md`
plus the Phase 4 inputs (`BUILD_PHASES.md`, `HUMAN_REQUIREMENTS.md`).

The synthesis is the artifact the owner will read to decide how to
proceed. Your job is to audit it: is it internally supported by the
ledger, does it surface human-checkpoint decisions appropriately, and
does it preserve the local-first / no-egress contract.

## Audit checklist

1. **Synthesis-to-ledger consistency.** For each accepted/deferred/rejected
   ledger ID, does the synthesis's reason align with the ledger's
   severity and rationale? Flag mismatches.
2. **Open-decision completeness.** Did the synthesis surface every open
   decision the ledger raised, or were any quietly resolved without
   owner review?
3. **Recommendation grounding.** Does the recommended outcome
   (`author-rfc` / `author-spec` / `revise-build-phases` /
   `pause-and-resolve`) match what the ledger supports? Flag if the
   synthesis recommends a stronger or weaker action than the findings
   warrant.
4. **Carry of risks.** Did the synthesis flag the places where it chose
   a resolution the ledger did not unambiguously support?
5. **Local-first invariant.** Does anything in the synthesis or
   recommended next step imply network egress, cloud APIs, or external
   data movement?
6. **Provenance carry.** Are `RFC-####`, `D###`, and `PHASE-####`
   references used per `docs/process/artifact-id-conventions.md`?

## Output

Write to `docs/reviews/phase4/PHASE_4_SPEC_FINAL_REVIEW.md`:

```md
# Phase 4 Build-Spec Final Review

Status: final-review
Date: <YYYY-MM-DD>
RFC refs: ...
Decision refs: ...
Phase refs: PHASE-0004

## Audit findings

### A001 — <one-line title>
Severity: <blocking | major | minor | nit>
Source: <synthesis section or ledger ID>
Rationale: <one paragraph>

[...]

verdict: <accept | accept_with_findings | needs_revision | reject>
```

A `needs_revision` verdict triggers the workflow's revision cycle: the
synthesis job runs again with this final-review's audit findings as input.
Use it sparingly — only when the synthesis materially mis-states the
ledger or recommends an outcome the ledger does not support.

A `reject` verdict means the synthesis is so off the ledger that the
review cycle itself needs to be re-run from independent reviews. Reserve
for cases where the synthesis fundamentally mis-frames the input.

Do not modify any other file.
