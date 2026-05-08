# RFC 0025 Command-Names Synthesis

author: synthesizer-claude-opus-001
Status: synthesis
Date: 2026-05-08
RFC refs: RFC-0025
Decision refs: D016, D020, D074, D077
Phase refs: PHASE-0002, PHASE-0003, PHASE-0004, PHASE-0005, PHASE-SMOKE

## Findings outcome

| ID | Outcome | Reason |
|----|---------|--------|
| F001 | accepted | Generic sibling Make targets carry the same operator-safety risk as `make pipeline` and need explicit treatment. |
| F002 | accepted | Phase 4 Make targets for refresh and entity build are additive surface and should be called out as such. |
| F003 | accepted | The fail-closed command must be tested before any database connection to preserve the safety property. |
| F004 | accepted | The RFC cannot leave the `run` versus `pipeline` verb choice open while proposing `phaseN run`. |
| F005 | accepted | The nested argparse migration is feasible but should be implemented incrementally. |
| F006 | accepted | Docs, help text, and warning copy are part of the behavior change, not follow-up polish. |
| F007 | accepted | Review consensus supports the phase-scoped taxonomy as aligned with the canonical phase boundaries. |
| F008 | accepted | Phase 4 should expose `smoke` and specific verbs, not a premature full `phase4 run`. |
| F009 | accepted | Phase 1 ingest commands can remain source-named outside this RFC. |

## Open decisions

### O001 - Which phase-local verb is canonical?

- Option A - Standardize on `engram phaseN run` and `make phaseN-run`.
- Option B - Standardize on `engram phaseN pipeline` and `make phaseN-pipeline`.
- Recommended: A
- Rationale: `run` is shorter, avoids preserving the overloaded top-level noun,
  and matches RFC 0025's proposal, examples, and acceptance criteria. The RFC
  should remove the open question and state that `pipeline` is not the
  phase-local verb for mutating phase execution.

### O002 - What happens to generic Make siblings?

- Option A - Fail closed for `pipeline`, `pipeline-docker`, and
  `pipeline-isolated` in the same implementation.
- Option B - Fail closed only for `pipeline`, while generic sibling targets warn
  for one compatibility window.
- Recommended: A
- Rationale: All three targets use the generic noun for Phase 2 writes. Keeping
  `pipeline-docker` or `pipeline-isolated` runnable preserves the exact class of
  operator error RFC 0025 is trying to remove. Add phase-scoped replacements
  such as `phase2-run`, `phase2-run-docker`, and `phase2-run-isolated`.

### O003 - Should Phase 4 gain a generic run command now?

- Option A - Add only `phase4 smoke`, `phase4 refresh-current-beliefs`,
  `phase4 build-entities`, and `phase4 review-belief`.
- Option B - Also add `phase4 run` as a broader aggregate command.
- Recommended: A
- Rationale: D077 and RFC 0024 require Tier 0, Tier 1, and Tier 2 gates before a
  full-corpus Phase 4 run. A generic `phase4 run` would create a new ambiguous
  mutating command before the project has accepted the full Phase 4 execution
  contract.

### O004 - How should the implementation be sequenced?

- Option A - Add nested phase commands and phase-scoped Make targets first,
  then make only generic pipeline commands fail closed, then warn on remaining
  legacy commands.
- Option B - Refactor the whole CLI and remove or hide all legacy commands in
  one change.
- Recommended: A
- Rationale: The current CLI uses a single argparse layer. An incremental
  sequence limits blast radius while preserving a testable acceptance path:
  nested commands dispatch to existing helpers, fail-closed commands assert no
  database connection, and warning copy can be shared by CLI and Make targets.

## Recommendation

revise-rfc

RFC 0025's core direction is correct and should proceed, but the RFC should be
amended before acceptance. The required amendments are narrow: close the
`run` versus `pipeline` question in favor of `run`, include all generic
pipeline Make siblings in the fail-closed migration, explicitly keep Phase 4
without a generic `run` command, and add an implementation sequence for nested
argparse, Make targets, help text, and warning copy. After those edits, the RFC
should be accepted and implemented as a focused command-surface change with
tests for fail-closed behavior.

## Risks the synthesis carries

- The synthesis recommends failing closed for `pipeline-docker` and
  `pipeline-isolated` immediately. The ledger supports this as safer, but it may
  break an untracked local script sooner than a warning-only migration would.
- The synthesis recommends no `phase4 run` command. This is consistent with
  D077, but a later accepted Phase 4 execution RFC may deliberately add one.
