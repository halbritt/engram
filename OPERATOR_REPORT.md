# Operator Report

Last updated: 2026-05-13

## Current State

- Repo: `/home/halbritt/git/engram`
- Branch: `master`
- Current objective: recover and promote the RFC 0028/RFC 0029 work through legitimate review, rerun Phase 4 gate review with multi-lane evidence, audit older Striatum provenance gaps, and then scaffold/execute the backlog with maximum useful parallelism.
- Current checkpoint: RFC 0032 recovery implementation is committed as `4c59259` (`Recover RFC 0032 audit findings`); fresh quarantine/rerun scaffolds are committed as `d56cef7` (`Scaffold attested review reruns`); lane-command repair is committed as `6d537cc` (`Fix Striatum lane commands`); Gemini trust automation is committed as `6590970` (`Trust Gemini automation worktrees`); fresh rerun artifacts have been cherry-picked onto `master` through `98509f0` (`Add Phase 4 multilane gate evidence`).
- Sync status: fetched and rebased against `origin/master` during the rerun batch; final doc update, rebase, and push remain pending for this checkpoint.
- Current uncommitted batch: changelog/operator-report accuracy update after merging fresh rerun artifacts, plus a proposed `D082` reservation row so RFC 0028 review artifacts remain mechanically auditable without granting promotion authority.

## Verified Work

- `make migrate` passed after adding migration `013_interview_active_learning_state.sql`.
- `make schema-docs` regenerated `docs/schema/README.md`.
- Focused touched-area tests passed: 190 tests.
- Full suite passed: `505 passed in 227.47s`.
- `git diff --check` passed.
- Fresh Striatum workflow validation passed for the seven 2026-05-13 workflows before the first execution probe and again after the lane-command repair.
- Fresh Striatum status checks show no running, stale-running, lost, or timed-out processes for the landed second-wave runs. RFC 0021, RFC 0027, RFC 0028, and RFC 0029 design remain open only because human checkpoints block downstream jobs after substantive `needs_revision` verdicts.

## Completed In Current Checkpoint

- Quarantined suspect RFC 0028/RFC 0029 review artifacts and Striatum workflow scaffolds.
- Demoted unauthorized RFC 0028/RFC 0029 promotion claims and removed the unauthorized decision row.
- Removed stale root-level Striatum guide exports.
- Repaired bench-review host trust and CLI exception handling.
- Implemented Phase 3 interview active-learning/session-target persistence and resume/history behavior.
- Hardened interview web reachability and rationale validation.
- Added Phase 4 preflight/current-belief refresh behavior.
- Refreshed user docs, RFC index, schema docs, and changelog entries touched by this recovery.

## Active Plan

1. Audit `CHANGELOG.md` against git history, RFC statuses, and decision log.
   - Done for the first pass; unreleased/current-state and Phase 1/2 historical corrections are applied in the worktree.
2. Create a GitHub issue in `~/git/striatum` for lane-output provenance hardening.
   - Done: https://github.com/halbritt/striatum/issues/5
3. Keep fetching/rebasing onto `origin/master` between batches.
4. Keep `OPERATOR_REPORT.md` current before long workflow runs and compaction risk.
5. Audit pre-suspect Striatum runs for RFC 0021/RFC 0027 provenance gaps.
   - Done for the first pass: RFC 0021/RFC 0027 review bylines are unattested by `process_executions`; quarantine notices are applied.
6. Re-scaffold and rerun legitimate multi-lane reviews for RFC 0028, RFC 0029, and Phase 4 gate evidence.
   - Fresh validated scaffolds exist for RFC 0021 rerun, RFC 0027 rerun, RFC 0028 promotion, RFC 0029 design/spec/implementation, and Phase 4 multi-lane gate.
   - First execution probes were canceled after Codex/Claude exited without required artifacts or verdicts and Gemini exited nonzero in review lanes. The workflow command arrays have been patched to use explicit noninteractive write-capable launch modes before restarting from clean worktrees.
   - Second-wave runs executed in clean worktrees created from `6d537cc`.
   - Second-wave Gemini review lanes initially exited nonzero because Gemini headless mode requires trusted worktrees. Fresh scaffolds now pass `--skip-trust`; already-prepared active runs retried Gemini lanes with `GEMINI_CLI_TRUST_WORKSPACE=true`.
   - Several reruns now have substantive `needs_revision` verdicts. Treat these as real work items, not Striatum infrastructure failures.
   - The Phase 4 multi-lane gate completed all jobs and landed its evidence package under `docs/operations/phase4-build/tiered-gate-multilane-2026-05-13/`.
7. Synthesize review outcomes into concrete backlog work. Do not promote RFC 0021, RFC 0027, RFC 0028, RFC 0029 design, or Phase 4 full-corpus execution without resolving the checkpoint blockers or recording an explicit operator decision.
8. Scaffold backlog workflows and drive independent implementation lanes in parallel.

## Completed Parallel Audits

- Changelog accuracy audit.
- Pre-suspect RFC 0021/RFC 0027 Striatum provenance audit.
- Striatum rerun command/scaffold audit for RFC 0028, RFC 0029, and Phase 4.
- Phase 4 multi-lane gate evidence audit.
- Backlog dependency and first-wave workflow audit.

## Validated Fresh Workflows

- `striatum/rfc-0021-gold-set-review-rerun-2026-05-13/workflow.json`
- `striatum/rfc-0027-interview-web-ui-review-rerun-2026-05-13/workflow.json`
- `striatum/rfc-0028-predicate-intent-promotion-2026-05-13/workflow.json`
- `striatum/rfc-0029-bench-triage-workbench-design-2026-05-13/workflow.json`
- `striatum/rfc-0029-bench-triage-workbench-spec-2026-05-13/workflow.json`
- `striatum/rfc-0029-bench-triage-workbench-implementation-2026-05-13/workflow.json`
- `striatum/phase-4-tiered-gate-multilane-2026-05-13/workflow.json`

## Canceled Probe Runs

- RFC 0021 rerun: `run_a8994ff32b614b59b71ee4d43539b7e7`
- RFC 0027 rerun: `run_f7856857ed344130883055fefa2f53d6`
- RFC 0028 promotion: `run_f4561ec6212342438e6b51ae9bac8e9a`
- RFC 0029 design: `run_ea044aa6d5c5454b976997cf47b94e9d`
- Phase 4 gate: `run_a56aaa4a9ff14b028c4bce105618704e`

## Second-Wave Run Outcomes

- RFC 0021 rerun in `/home/halbritt/git/engram-worktrees/rfc0021-rerun`:
  `run_a42b3f16e8504fff9a9688d90e9efde9`
  - Claude review: `sess_f5529b631b2540e5aac8b5abcba1796e`, lease `lease_a73d2263c8de48d18381c7df1f5b9e84`
  - Codex review: `sess_7bd6adc29a3444ccb4cf35dac8ad330e`, lease `lease_74fa1e74917c4cb291dd0f3a4058ed67`
  - Gemini initial review: `sess_4997481fa993447ea8e9209156a3cc74`, lease `lease_2481d05d6d7f4040b4cfcb19e66e62ad`, exited nonzero on trust gate and released.
  - Gemini trusted retry: `sess_5b605b4efd224ee089aef2ba94464862`, lease `lease_0d89d26d57f2455e93df2a8fa1a38d66`
  - Current state: Claude completed `accept_with_findings`; Gemini retry completed `accept_with_findings`; Codex completed `needs_revision` and opened a human checkpoint. Striatum process health reports zero running/stale/lost/timed-out processes; downstream ledger, synthesis, and final-review jobs are blocked.
  - Landed artifacts: `docs/reviews/rfc0021-rerun-2026-05-13/`
- RFC 0027 rerun in `/home/halbritt/git/engram-worktrees/rfc0027-rerun`:
  `run_91107d8cb1094166806a93f446dfa243`
  - Claude review: `sess_62c7f3c7ea414190b40fb05520a00f32`, lease `lease_49920a71f0de47a99a42baeb81197929`
  - Codex review: `sess_644864b83f1547f6b7fcea7f214ebcc9`, lease `lease_d0e28d05f5414767a4c3d4ebe2e79a4f`
  - Gemini initial review: `sess_9fc3b94b532b4c839fb67a05d3623438`, lease `lease_8571c481cf704ac1b04453ab8774f77b`, exited nonzero on trust gate and released.
  - Gemini trusted retry: `sess_5cbf352db3d94549aa65605bb46dd380`, lease `lease_a1dba1a2173b47b4bc6d691b9c0843f8`
  - Current state: Claude and Gemini completed; Codex completed `needs_revision` and opened a human checkpoint. Striatum process health reports zero running/stale/lost/timed-out processes; downstream ledger, synthesis, and final-review jobs are blocked.
  - Landed artifacts: `docs/reviews/rfc0027-rerun-2026-05-13/`
- RFC 0028 promotion in `/home/halbritt/git/engram-worktrees/rfc0028-promotion`:
  `run_d7a2a36954be46f98e2ce022e71ca336`
  - Codex author: `sess_c9c3f4ec22994abab7d3fcf05c729e3b`, lease `lease_c565c389622141eca2a6a44f9b317211`, completed and closed.
  - Claude review: `sess_6cf0e69dcdbe4cbba9787d55271f3f38`, lease `lease_653a44c6dcba4a449beedcdb23d08144`
  - Codex review: `sess_f653460fc9ea4366b732fcf2e2fd8cbc`, lease `lease_05e5f9e9758a485c81ccc93668458f4a`
  - Gemini review: `sess_323ac273490f4e1ea33a0975d04308cc`, lease `lease_6e719a710403472298877ea175ebc91f`, exited nonzero after Gemini model-capacity 429s.
  - Current state: Claude completed `accept_with_findings`; Codex completed `needs_revision`; Gemini remains blocked by model-capacity `process_exit_nonzero`; ledger, revision synthesis, apply-findings, and final-review jobs are blocked.
  - Landed artifacts: `docs/reviews/rfc0028-predicate-intent-promotion-2026-05-13/`
- RFC 0029 design in `/home/halbritt/git/engram-worktrees/rfc0029-design`:
  `run_5ad589fe9f82497e9f8d508589ea343e`
  - Codex author: `sess_ac5071c9db554c31bc687097ca55aff0`, lease `lease_2815107fd55044c0ab37f17006af7742`, completed and closed.
  - Claude review: `sess_7b0cda59ff764b949bdaeb9f4924fed3`, lease `lease_2d85a44f89974616bf31ba28d862df71`
  - Codex review: `sess_10c38d3e36a84fb2a4124ff9911c5165`, lease `lease_92ee2e63494d458c9ad2e4fc65e36c09`
  - Gemini review: `sess_d3937c8f2cc74196a5a1880e4f57d1d6`, lease `lease_6443b80aa62247689e021e1e39542f18`
  - Codex usability adversary: `sess_7b19dd8ead49424289b94231486b7e2b`, lease `lease_3047a0de71aa4778966e1b495c9bef39`
  - Current state: author plus all four design reviews completed; usability adversary completed `needs_revision`, opening a human checkpoint and blocking the ledger/revision/final cycle.
  - Landed artifacts: `docs/reviews/rfc0029-bench-triage-workbench-design-2026-05-13/`
- Phase 4 gate in `/home/halbritt/git/engram-worktrees/phase4-gate`:
  `run_ebabb539d62f4f62a192783cd9704140`
  - Codex Tier 0 operator: `sess_9f737b9bbd464b9fb77cab2fa8f02958`, lease `lease_e250bcd8db634bb592d5872b6ebed013`, completed.
  - Codex Tier 1 operator: `sess_5f7cae5a6ca74cba9a47928d0d53c73d`, lease `lease_07262098c5bb48de97d7be65a85f3279`, completed.
  - Codex Tier 2 operator: `sess_bddb170daa9c48d9a48e1f34b3521e49`, lease `lease_c2a50df7e9144763a62ccf5af9946449`, completed.
  - Claude entity-quality review: `sess_d161532841734437b3943dc8e40a4290`, completed.
  - Codex invariants review: `sess_afb79c09b4704e47ab9788ad4d6cacf9`, completed.
  - Gemini privacy/provenance review: `sess_4f95773771d347a88f6c5027f262b16c`, completed.
  - Codex findings ledger: `sess_83abe9839d2942d0bfcba38a80925735`, completed.
  - Codex promotion synthesis: `sess_d09b0338fb4b4f5199cc603b6db6e718`, completed.
  - Codex final gate review: `sess_08eb16611da94997840c30c6a4909082`, completed.
  - Current state: Striatum run completed all 9 jobs. Final gate review accepts the Tier 0/Tier 1/Tier 2 scaffold, ledger, and synthesis only as a privacy-safe bounded evidence package; it explicitly does not promote Phase 4 or authorize full-corpus execution.
  - Landed artifacts: `docs/operations/phase4-build/tiered-gate-multilane-2026-05-13/`

## Execution Constraints

- Do not run all seven workflows concurrently in the same worktree. Use separate git worktrees for workflow-level parallelism.
- RFC 0029 design precedes RFC 0029 spec, which precedes RFC 0029 implementation.
- RFC 0028 promotion and RFC 0029 implementation both touch overlapping code surfaces; avoid concurrent writes in one worktree.
- Phase 4 evidence collection is serial through Tier 0-2, then fans out to independent reviews; the completed 2026-05-13 gate accepted bounded evidence only and left full-corpus execution blocked.
- Backlog first wave can run in parallel as design/planning work: RFC 0030 design, RFC 0022 design, RFC 0018 Stage 1/2 planning, RFC 0023 validation planning, and RFC 0012/0015 focused quality follow-ups.

## Open Risks

- The repo is currently on `master`; `origin/master` is the remote default branch.
- RFC 0021/RFC 0027 reruns surfaced legitimate `needs_revision` findings. Their historical promotion claims should not be treated as newly cleared until those findings are resolved or explicitly waived.
- RFC 0028/RFC 0029 can only be promoted again after fresh legitimate review clears the `needs_revision` findings or an explicit operator decision records the carried risk.
- `D082` is currently only `proposed`; RFC 0028 still needs the governed extraction-prompt artifact and accepted decision binding, or a version/comment change away from a decision-tagged prompt version.
- Phase 4 full-corpus execution remains blocked. The completed multi-lane gate accepted only a bounded evidence package and requires an evidence-fix pass before any bounded Tier 2 preflight.
- Older Striatum runs still need quarantine or rerun if their provenance cannot be verified.
- The local Striatum CLI reports `striatum 1.36.0` from the editable checkout. The Striatum worktree has pre-existing dirty files; this Engram pass has not modified them.
