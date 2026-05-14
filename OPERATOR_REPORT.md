# Operator Report

Last updated: 2026-05-14

## Live Operator Addendum: RFC 0044 And Checkpoint Cleanup

- Main worktree: `/home/halbritt/git/engram`, branch `master`. The local
  Engram venv reports `striatum 1.35.0`.
- RFC 0038 UI rework is already pushed to `origin/master` through `ad09a99`
  (`Implement RFC 0038 operator UI rework`).
- RFC 0044 original run `run_322110269dfb4ec98fc6f7ea818448c0` is complete.
  The capability-boundary repair run
  `run_1aadc5c6bc00434497bc6d9754358a62` completed, the operator decision
  `dec_e26bc9506a6842e7944134ed0eeb9c2d` accepted the repair with follow-up,
  and original checkpoint `blk_603d77b8a1364075994f2bf8565478b7` was resolved.
- RFC 0044 recovery artifacts now include
  `REPAIR_SYNTHESIS_AND_OPERATOR_DECISION.md`,
  `OPERATOR_DECISION_RFC0044_REPAIR.md`,
  `REVIEW_correctness_repair_resolution_codex.md`,
  `REVIEW_operator_gemini_verdict_recovery.md`, `FINDINGS_LEDGER.md`, and
  `FINAL_SYNTHESIS.md`. The final synthesis outcome is
  `accept_with_findings`.
- RFC 0028 prompt-literal checkpoint
  `blk_80898b6f841d44d3a37bd8877ac3e60e` was cleared by a narrow operator
  override using accepted re-review evidence
  `verdict_48068fa5f263453796852c638324d219`; the replacement verdict on the
  original focused review is `verdict_05e30e6695ad451eab60cec132c510da`.
  This does not promote RFC 0028 and does not accept D082.
- RFC 0027 web-state checkpoint `blk_4d7be5151bec4e18ae6aea672269998f` was
  cleared by a narrow operator override using accepted re-review evidence
  `verdict_a4d97e72583e487095afa4e4f8598367`; the replacement verdict on the
  recovery review is `verdict_9c64e8b2cd98405bb5e2d480f21ebd4b`.
  Striatum still reports process-adapter blocker
  `blk_6dd92e18a3da4cc5ac2c4f1445755b99` for the completed re-review job; this
  remains tracked as https://github.com/halbritt/striatum/issues/7.
- Historical RFC 0028 missing-verdict blockers
  `blk_b17b8f9d745845e7871c3c58e627016d`,
  `blk_21f692125f53493f9c378a3865e51be8`, and
  `blk_857ee9425c734fcd8eeccb4a6b09ebfa` were resolved as terminal no-op
  recovery on completed run `run_66ba248f6e4f47e49c130bca866e383f`.
- Focused review ledgers completed:
  `docs/reviews/rerun-backlog-focused-reviews-2026-05-13/FOCUSED_REVIEW_LEDGER.md`
  (`art_49c87c7f54f04ed7b02885b99a848afb`) and
  `docs/reviews/rerun-backlog-focused-reviews-2026-05-13/FOCUSED_REVIEW_RECOVERY_LEDGER.md`
  (`art_586fab95a6b64707909b09cfe39a6ea7`).
- Current Striatum status: no human checkpoints and no running, stale-running,
  lost, or timed-out processes. The only open blocker is
  `blk_6dd92e18a3da4cc5ac2c4f1445755b99`. Seven old RFC 0030 review/adversary
  jobs remain claimable in run `run_68de8953cfe049da8b2216a328fd8e36`, and
  older downstream jobs remain blocked behind those reviews and an old Phase 4
  spec-review run.
- Final local pre-push verification passed: `git diff --check`;
  RFC 0044-focused tests (`11 passed in 9.37s`); adjacent RFC 0044 regression
  set (`17 passed in 10.09s`); `make check-refs` (`0 error(s), 5 warning(s),
  181 check(s) ok`); and `make test` (`590 passed in 276.30s`).

## Live Operator Addendum: RFC 0038 UI Rework

- Worktree: `/home/halbritt/git/engram-worktrees/ui-rework-rfc`
- Branch: `engram/rfc0038-ui-rework`
- Scaffold commit: `19651c8` (`Scaffold RFC 0038 UI rework workflow`)
- Source handoff: `ENGRAM_UI_REWORK_HANDOFF.md`
- RFC scaffold: `docs/rfcs/0038-operator-ui-rework.md`
- Workflow scaffold:
  `striatum/rfc-0038-operator-ui-rework-2026-05-13/workflow.json`
- Striatum version used: `1.37.0`
- Validation:
  - `workflow validate` passed.
  - `git diff --check` passed.
  - `make check-refs` passed with 0 errors and the repository's 5 existing
    warnings after adding the standard `rfc-0038` anchor.
- Run: `run_468b22aff5e54a9280a867d3c81314e6`, state `running`.
- Completed implementation lanes:
  - Shared substrate: session `sess_699349c08fd548a08f575a2095603600`,
    lease `lease_b808ef8a167a46a180889c84828c94f4`, adapter PTY `91046`,
    exited cleanly.
  - Interview UI: session `sess_92950903e9c04c8cacde58bc935fa061`,
    lease `lease_a25463c3f57d42bb89258650f2201a0f`, adapter PTY `63126`,
    exited cleanly.
  - Bench-review UI: session `sess_5c68c5939f664f488a636009aa85c030`,
    lease `lease_a876cbf4a23c448e92807f3d587f7dd4`, adapter PTY `53330`,
    exited cleanly.
- Completed RFC 0038 integration evidence lane: session
  `sess_7ddcec9d456040a98ac7ea9e89df63de`, lease
  `lease_575a6137b7164f5ab917b319882a6d80`, adapter PTY `21973`,
  exited cleanly.
- Active RFC 0038 review lanes:
  - Ergonomics design review: session
    `sess_005afad28a9444f4b66421e921d8bd08`, lease
    `lease_994521563935486293fba9602dfa7816`, adapter PTY `39392`.
  - Local-first/security review: session
    `sess_909725e511d0445782496d2e9dd2cf39`, lease
    `lease_3b572adeb39342808a51273cd3e8b29c`, adapter PTY `37250`.
  - Correctness review: session `sess_af6e44a62f8d4b2ba52e08ce8d9c2a54`,
    lease `lease_8768022de40d4e138f0c05fedf08573a`, adapter PTY `33225`.
  - Operator contract review first attempt: session
    `sess_c588367b37e5498fa1df895101da8b6c`, lease
    `lease_852f1873edee420fb4d0da766323f3cd`, adapter PTY `93521`, failed
    because `gemini-3.1-pro-preview` quota was exhausted for about 15 hours.
    The job was retried with `gemini-2.5-flash`.
  - Operator contract review retry: session
    `sess_5fdd40f164a34165860301feba345fac`, lease
    `lease_2b283eeac36748488185310fa48131ea`, adapter PTY `42484`.
- Next planned RFC 0038 jobs after all reviews complete: findings ledger and
  final synthesis.
- RFC 0038 review outcome: correctness and ergonomics returned
  `needs_revision`; the Gemini operator-review retry exited without a recorded
  verdict/artifact, so the original run is blocked. Repair workflow
  `run_90da3a4eae2449f6bb394ff6612064ad` is active from
  `striatum/rfc-0038-operator-ui-rework-repair-2026-05-13/workflow.json`.
- Active RFC 0038 repair lanes:
  - Shared/test dependency repair: session
    `sess_2065a99cf9b94969a2d18fc4bde17549`, lease
    `lease_6b266aa870c54121b2faead7c1217425`, adapter PTY `37927`.
  - Interview repair: session `sess_296b50fb90ab4e7493a76d2a77980416`,
    lease `lease_429e142e095c4ab7989494fd45974079`, adapter PTY `28603`.
  - Bench repair: session `sess_550d9a10237049cda1faf6b18ea021d1`, lease
    `lease_cc7070b51db34f1a8de634224218ac95`, adapter PTY `22311`.
- Resume checkpoint: after context compaction, all three RFC 0038 repair
  lanes were still running and quiet. A later status check showed
  `repair_shared_and_tests` completed; `repair_evidence` remains blocked on
  the interview and bench repair lanes.
- Repair progress update: the interview and bench repair adapters later exited
  cleanly and Striatum made `repair_evidence` claimable. The evidence lane is
  running as session `sess_5bd74654738b48a5a566747630a38c6e`, lease
  `lease_d80297364e984240a192380f391fc6d6`, adapter PTY `93733`.
- Repair evidence outcome: `run_90da3a4eae2449f6bb394ff6612064ad`
  completed, but `REPAIR_EVIDENCE.md` reported a remaining DB-backed
  interview route test failure caused by a predicate/stability seed rejection.
  Follow-up workflow `run_4b77214f5dc8478ca8e46073804d55d2` is active from
  `striatum/rfc-0038-operator-ui-rework-followup-2026-05-13/workflow.json`.
  The first follow-up implementer lane is running as session
  `sess_8dc6ed47a7aa4466b57835ea3c42784c`, lease
  `lease_15e6d5d702dc42a086684f726ff1394d`, adapter PTY `55322`.
- Follow-up progress update: the DB-route repair implementer exited cleanly.
  Follow-up evidence is running as session
  `sess_7b81c95c0598459a9a133dca6694bbc1`, lease
  `lease_982c403f72444dcbb1da3f051c2f0a7e`, adapter PTY `43522`.
- Follow-up evidence outcome: `REPAIR_FOLLOWUP_EVIDENCE.md` reports `pass`;
  DB-backed interview route tests, focused interview/bench route tests,
  shared tests, no-CDN/static checks, Ruff checks, `git diff --check`, and
  `make check-refs` passed. Three follow-up review lanes are active:
  correctness session `sess_e64874a3a638469ea23d60ba1dbdf875` / PTY `9219`,
  security session `sess_d3b8ae49d447451497379d31dac344d5` / PTY `86412`,
  and ergonomics session `sess_5aad5e73b02948a080a9e2a459e1c548` / PTY
  `25007`.
- Follow-up review workflow defect: the three first follow-up review packets
  omitted `REPAIR_FOLLOWUP_EVIDENCE.md` and `REPAIR_DB_ROUTE_HANDOFF.md`,
  causing stale-evidence `needs_revision` reviews. Corrected review-only
  workflow `striatum/rfc-0038-corrected-followup-review-2026-05-13/workflow.json`
  was scaffolded with repo-level review access and explicit current evidence
  inputs.
- Corrected review pass: run `run_3151de7bf05f46fca0ff4398764ae9bf` is
  active. Corrected correctness review session
  `sess_0d9f97c4f3ad40079cd899a3e9622689` runs on PTY `9191`; corrected
  security review session `sess_5b0f4fe95b164d5fb2e70bc7428562da` runs on
  PTY `56098`; corrected ergonomics review session
  `sess_7c545cdd96bd4826ab0e0c96cfefd24b` runs on PTY `59694`.
- Corrected review outcome: run `run_3151de7bf05f46fca0ff4398764ae9bf`
  completed with three `accept_with_findings` verdicts. Correctness carries
  only the stale active-venv `httpx` environment gap; security carries minor
  follow-ups for interview shared origin/tier helper unification and audit
  footer bind-source truthfulness; ergonomics carries the interview-to-bench
  cross-surface link plus minor polish follow-ups.
- Accept-with-findings follow-up workflow
  `striatum/rfc-0038-accept-findings-followup-2026-05-13/workflow.json`
  was scaffolded to drive the remaining corrected-review findings as three
  disjoint implementation lanes plus evidence and re-review.
- Accept-with-findings run `run_fc8fa866026748408cb70809ec7e5129` is active.
  Interview follow-up session `sess_7025aeef44104da095feaf2d442fb284` runs
  on PTY `8533`; bench follow-up session
  `sess_80ca96389efb4e3182b51df4a5bb0202` runs on PTY `14235`; shared cleanup
  session `sess_9ca9e0986e50449ab198fa8a071b3636` runs on PTY `51487`.
- Accept-with-findings implementation progress: bench and shared cleanup lanes
  exited cleanly first, then interview exited cleanly. `accept_findings_evidence`
  is now claimable.
- Accept-with-findings evidence is running as session
  `sess_f3d1d09e288e43b99675754577562ace`, lease
  `lease_70a7a92227d546b59cf1687c074c9ef8`, adapter PTY `88399`.
- Accept-with-findings evidence completed with `pass`, then three review lanes
  completed. Security and ergonomics returned `accept`; correctness returned
  `needs_revision` for two blockers: bench still exposed FastAPI-generated
  `/docs`, `/redoc`, and `/openapi.json` routes with CDN-backed assets, and
  interview accepted `::1` as a bind host while rejecting same-origin IPv6
  loopback POSTs. Striatum opened human checkpoint
  `blk_d0f5b81301da4f52b60a31d2695c20d1` because that workflow had no matching
  revision cycle.
- Second repair workflow
  `striatum/rfc-0038-accept-findings-second-repair-2026-05-13/workflow.json`
  was scaffolded and validated. It queues two disjoint implementation lanes for
  the AC001/AC002 blockers, followed by evidence and parallel correctness,
  security, and ergonomics re-review.
- Second repair outcome: run `run_73e7e77f8e8d4880b5e222210707b646`
  completed all six jobs with no open blockers. Bench FastAPI-generated
  `/docs`, `/redoc`, and `/openapi.json` routes are disabled; configured
  interview IPv6 loopback POSTs are accepted without widening the default
  Origin allowlist. `SECOND_REPAIR_EVIDENCE.md` passed; correctness, security,
  and ergonomics reviews all returned `accept`.
- Second repair residuals: the active `.venv` still lacks `httpx`, so route
  tests use the already-local
  `/home/halbritt/.local/lib/python3.12/site-packages` workaround. Reviews also
  carry non-blocking IPv6 display polish for unbracketed `::1:8765` style
  expected-origin/bind-address text and previously tracked UI polish items.
- Concurrent background work in `/home/halbritt/git/engram`: RFC 0044 repair
  workflow `run_1aadc5c6bc00434497bc6d9754358a62` completed with focused
  correctness verdict `accept`; focused RFC 0044 tests passed with 11 tests.

## Live Operator Addendum: RFC 0044

- Main worktree: `/home/halbritt/git/engram`, branch `master`.
- RFC 0044 run: `run_322110269dfb4ec98fc6f7ea818448c0`.
  - Terminology handoff completed earlier in session
    `sess_9df14cab59fa497092ecae8e91adfc9b`.
  - Implementation lane `sess_249af81e42bc4940879e566c66fda54d`
    / lease `lease_df0e7b19fc4a411fa5d265fc54d7f94a` exited cleanly
    from adapter PTY `8704`.
  - Capability-boundary tests are active in session
    `sess_08538c90bce143bf94c224ebd1286565` / lease
    `lease_3ae8f3f221344e7c834e142c2b5797d8` / adapter PTY `58196`;
    the adapter exited cleanly.
  - RFC 0044 review lanes are active: boundary/security PTY `72569`,
    correctness PTY `80970`, and operator-contract Gemini PTY `37152`.
- UI worktree: `/home/halbritt/git/engram-worktrees/ui-rework-rfc`,
  branch `engram/rfc0038-ui-rework`.
  - Scaffold commit `19651c8` added RFC 0038 and its Striatum workflow.
  - RFC 0038 run `run_468b22aff5e54a9280a867d3c81314e6` completed the
    shared substrate, interview UI, bench-review UI implementation lanes, and
    integration evidence.
  - Four RFC 0038 review lanes are active: ergonomics PTY `39392`, security
    PTY `37250`, correctness PTY `33225`, and operator-contract retry PTY
    `42484`.
- Gemini quota repair: `gemini-3.1-pro-preview` is quota-exhausted until about
  2026-05-14 12:55 UTC. `gemini-2.5-flash` was verified with a no-data probe
  and active workflow snapshots plus scaffold files were repaired to use it for
  the Gemini review lanes.
- RFC 0044 review outcome: correctness returned `needs_revision` for a
  single-pair serving-path capability bypass; Gemini review retries exited
  without recorded verdicts. Repair workflow
  `run_1aadc5c6bc00434497bc6d9754358a62` is active from
  `striatum/rfc-0044-capability-boundary-repair-2026-05-13/workflow.json`.
- Active RFC 0044 repair lane: session
  `sess_2e1a2fb1c93f4857b1350488be2f44c2`, lease
  `lease_e9eab74e81ba4c8fad87661363f1daa2`, adapter PTY `59335`.
- RFC 0038 repair workflow is also active in the UI worktree with repair PTYs
  `37927`, `28603`, and `22311`.
- Resume checkpoint: after context compaction, RFC 0044 repair implementation
  was still running and quiet. `repair_boundary_tests` and
  `repair_correctness_review` remain blocked on that lane.
- Repair progress update: the RFC 0044 repair implementation later exited
  cleanly. `repair_boundary_tests` is running as session
  `sess_50db16a2144b4c2893d18ba8b11d7720`, lease
  `lease_31a9e25cb00c418a9d8ee4ae90879a77`, adapter PTY `13200`.
- Repair re-review update: `repair_boundary_tests` exited cleanly and
  produced `REPAIR_CAPABILITY_EVIDENCE.md`. Focused correctness re-review is
  running as session `sess_e0ff277ec73f407db841b4d023826e9f`, lease
  `lease_9c21ac29eb794adfbde0a1ea2f2bd1e2`, adapter PTY `11163`.
- RFC 0044 repair outcome: focused correctness re-review completed with
  verdict `accept`; no findings were recorded. The main worktree was then
  rebased/fast-forwarded onto `origin/master` at `6e80938`, adding
  `ENGRAM_UI_REWORK_HANDOFF.md`; autostash reapplied the local RFC 0044 batch.
- Operator verification after rebase: `git diff --check` passed; focused
  RFC 0044 tests passed with
  `PYTHONDONTWRITEBYTECODE=1 ENGRAM_TEST_DATABASE_URL=postgresql:///engram_test .venv/bin/python -m pytest -p no:cacheprovider -q tests/test_striatum_ingest.py tests/test_mcp_stdio.py`
  reporting `11 passed in 10.14s`.
- Later closeout: RFC 0038 was completed and pushed to `origin/master` through
  `ad09a99`; RFC 0044 completed final synthesis in the main worktree.
- Workflow repair during active runs: Striatum SQLite migration v16 left
  `runs_new` behind in both active repo-local DBs. The local editable Striatum
  checkout was patched to use the existing FK-safe `rebuild_table` helper, both
  DBs migrated successfully afterward, and the issue was filed as
  https://github.com/halbritt/striatum/issues/8.

## Current State

- Repo: `/home/halbritt/git/engram`
- Branch: `master`
- Current objective: land the RFC 0044 Engram memory Phase 1 implementation,
  repair artifacts, final synthesis, and focused-review checkpoint cleanup as
  one operator checkpoint.
- Current checkpoint: RFC 0038 UI work is pushed to `origin/master` through
  `ad09a99`; the current uncommitted batch sits on top of that commit and
  includes RFC 0044 implementation files, repair workflow artifacts, final
  synthesis/ledger artifacts, focused-review ledgers, and operator
  report/changelog updates.
- Sync status: main was fast-forwarded to `origin/master` before the local RFC
  0044 batch was restored. Fetch/rebase again immediately before push.
- Current local batch: RFC 0044 Engram memory Phase 1 implementation and MCP
  stdio surface, RFC 0044 repair artifacts and final synthesis, focused
  RFC 0027/RFC 0028 ledger cleanup, and current operator report/changelog
  updates.

## Verified Work

- `make migrate` passed after adding migration `013_interview_active_learning_state.sql`.
- `make schema-docs` regenerated `docs/schema/README.md`.
- Focused touched-area tests passed for the current batch: RFC 0028/render prompt tests (`45 passed`), RFC 0027 web/storage tests (`50 passed`), and the repaired interview CLI/storage target (`14 passed`).
- Full Docker-backed suite passed after the test-fixture repair: `make test-docker` reported `517 passed in 37.97s`.
- Full Docker-backed suite passed again after the RFC 0027 recovery repair and rebase onto `origin/master`: `make test-docker` reported `523 passed in 51.89s`.
- Local `make test` before the repair reached `516 passed / 1 failed`; the failure was `tests/test_interview_cli.py::test_phase3_interview_start_writes_session_targets` and is fixed in the current worktree.
- `git diff --check` passed.
- `make check-refs` passed after rebase: 0 errors, 5 existing warnings, 179 checks ok.
- RFC 0027 focused web/storage tests passed after the recovery repair: `ENGRAM_TEST_DATABASE_URL="postgresql://engram:engram@127.0.0.1:54329/engram_test" .venv/bin/python -m pytest tests/test_interview_web.py tests/test_interview_storage.py` reported `56 passed in 11.94s`.
- RFC 0028 prompt/render focused tests passed after the prompt-literal repair: `PYTHONPATH=src .venv/bin/python -m pytest tests/test_interview_render.py tests/test_phase3_claims_beliefs.py::test_extraction_prompt_version_has_governed_artifact tests/test_phase3_claims_beliefs.py::test_build_extraction_prompt_surfaces_predicate_intent` reported `45 passed in 0.09s`.
- Fresh Striatum workflow validation passed for the seven 2026-05-13 workflows before the first execution probe and again after the lane-command repair.
- RFC 0044 tenant-aware Engram memory Phase 1 scaffold validation passed with
  `STRIATUM_DAEMON_REQUIRED=0 STRIATUM_TEST_HARNESS=1 .venv/bin/striatum --repo . workflow validate striatum/rfc-0044-engram-memory-phase1-tenant-isolation-2026-05-13/workflow.json --json`; `workflow plan` also passed for the same file. No prepare/start/run command was executed.
- Rerun backlog focused-review scaffold validation passed with
  `STRIATUM_DAEMON_REQUIRED=0 STRIATUM_TEST_HARNESS=1 .venv/bin/striatum --repo . workflow validate striatum/rerun-backlog-focused-reviews-2026-05-13/workflow.json --json`; `workflow plan` also passed and shows five parallel review jobs followed by a ledger.
- Striatum workflow skills were refreshed for the project Codex and Claude profiles from Striatum `1.14.0` templates to the then-current Engram venv `striatum 1.37.0`; skill-bundle doctor warnings are gone. The main worktree venv now reports `striatum 1.35.0`.
- Striatum status currently reports no human checkpoints and no running,
  stale-running, lost, or timed-out processes. The only open blocker is
  `blk_6dd92e18a3da4cc5ac2c4f1445755b99`, tracked as Striatum issue #7.
- Historical RFC 0028 terminal-run blockers from
  `run_66ba248f6e4f47e49c130bca866e383f` were resolved as terminal no-op
  recovery; RFC 0027/RFC 0028 focused review checkpoints were reconciled
  with narrow accepted re-review evidence and no promotion decision.
- RFC 0044 final synthesis completed with outcome `accept_with_findings`;
  focused review ledgers for `run_6d6d3c3ce51f4b4286bfefad6d4ed09e` and
  `run_6f98dedd6ce04282984b4931421659a9` completed.
- Final local pre-push verification for the current RFC 0044/checkpoint batch
  passed: `git diff --check`; RFC 0044-focused tests (`11 passed in 9.37s`);
  adjacent RFC 0044 regression set (`17 passed in 10.09s`); `make check-refs`
  (`0 error(s), 5 warning(s), 181 check(s) ok`); and `make test`
  (`590 passed in 276.30s`).

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
   - Additional workflow-friction issue filed for completed review jobs that retain nonzero process-adapter blockers without a usable recovery path: https://github.com/halbritt/striatum/issues/7
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
   - In progress: backlog scaffold created under `docs/reviews/rerun-backlog-2026-05-13/`.
   - Done: five parallel worker lanes completed RFC 0028 implementation fixes, RFC 0027 web/privacy fixes, RFC 0021 contract revision, RFC 0029 design revision, and Phase 4 evidence-fix scaffold.
   - Done: a narrow implementation repair fixed the only full-suite failure by making the interview CLI test fixture seed real parent claim/belief rows that match the storage guard's version-triple contract.
   - Done: RFC 0044 tenant-aware Engram memory Phase 1 scaffold was prepared,
     run, repaired, reviewed, ledgered, and synthesized. The original run
     `run_322110269dfb4ec98fc6f7ea818448c0` is complete.
   - Done with follow-up recovery: focused review workflow
     `run_6d6d3c3ce51f4b4286bfefad6d4ed09e` completed its review lanes, then
     narrow recovery/re-review workflows cleared the RFC 0028 prompt-literal
     finding and RFC 0027 web-state findings with fresh accepted review
     evidence. Original historical checkpoints remain documented rather than
     silently waived.

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
- `striatum/phase-4-evidence-fix-2026-05-13/workflow.json` (validated with `STRIATUM_DAEMON_REQUIRED=0 STRIATUM_TEST_HARNESS=1`)
- `striatum/rfc-0044-engram-memory-phase1-tenant-isolation-2026-05-13/workflow.json` (validated with `STRIATUM_DAEMON_REQUIRED=0 STRIATUM_TEST_HARNESS=1` because local Striatum requires daemon mode by default)
- `striatum/rerun-backlog-focused-reviews-2026-05-13/workflow.json` (validated with `STRIATUM_DAEMON_REQUIRED=0 STRIATUM_TEST_HARNESS=1`)

## Focused-Review Run

- Workflow: `striatum/rerun-backlog-focused-reviews-2026-05-13/workflow.json`
- Run: `run_6d6d3c3ce51f4b4286bfefad6d4ed09e`
- Branch record: `master` via `branch confirm --use-current`; no branch switch.
- Launch note: first adapter launch attempt parsed the wrong `claim-next` JSON fields and passed `null` leases. The jobs had been claimed successfully, so the operator recovered the session/job/lease mapping from Striatum state and relaunched adapters with the correct leases.
- Jobs:
  - RFC 0027 focused review: session `sess_30de27567d5340d3826d9ca2028ccb3f`, lease `lease_539c56b5d0d3465fbeabe812a5ff7a3e`, lane `claude`.
  - Phase 4 evidence-fix scaffold review: session `sess_2ab298025ed24409befd5873e01c247a`, lease `lease_66cadce0ff084b329c6b073997797141`, lane `claude`.
  - RFC 0021 contract re-review: session `sess_91a5390915704f87b5d3468558a30130`, lease `lease_cc5992706bf14113a5f457bba92ceff7`, lane `codex`.
  - RFC 0028 focused review: session `sess_926e4bd8bf0740899715749621adc28b`, lease `lease_3ac0843ab50d48a5bb7d6a77a545c0be`, lane `codex`.
  - RFC 0029 design re-review: session `sess_e3f2d6c9b9744a5abc0538f0b5c45c0a`, lease `lease_cd50bcb83e114fd480ba950ee560cfe2`, lane `gemini`.
- Current outcomes:
  - RFC 0029 design re-review completed `accept`.
  - RFC 0021 contract re-review completed `accept_with_findings`.
  - RFC 0027 focused review completed `accept_with_findings` after operator remediation: the Claude artifact was already written, then published and given the artifact's stated verdict.
  - Phase 4 evidence-fix scaffold review completed `accept_with_findings` after operator remediation: the Claude artifact was already written, front matter severity was normalized from `major` to schema-valid `medium`, then published and given the artifact's stated verdict.
  - RFC 0028 focused review completed `needs_revision` with one prompt-artifact mismatch: the v9 artifact used f-string escaped double braces for the zero-claim JSON literal. This opened checkpoint `blk_80898b6f841d44d3a37bd8877ac3e60e`.

## Focused-Review Recovery Run

- Workflow: `striatum/rerun-backlog-focused-review-recovery-2026-05-13/workflow.json`
- Run: `run_6f98dedd6ce04282984b4931421659a9`
- Reason: recover only the two original Claude output-missing blockers with separate honest provenance. The recovery run does not complete or reinterpret the original Claude jobs.
- Branch record: `master` via `branch confirm --use-current`; no branch switch.
- Local Striatum control commands now require both `STRIATUM_DAEMON_REQUIRED=0` and `STRIATUM_TEST_HARNESS=1` because the editable Striatum checkout narrowed the bare daemon opt-out.
- Jobs:
  - RFC 0027 focused review recovery: session `sess_b1d33ff0ada745ed9db7baea1b321419`, lease `lease_588cfd9efd994e9a9b50da0ab72250f2`, lane `codex`.
  - Phase 4 evidence-fix scaffold review recovery: session `sess_74acecccf66948b29ca2b5af2536488c`, lease `lease_0c739c5001e046e591c5c3f53423c918`, lane `gemini`.
- Current outcomes:
  - RFC 0027 focused review recovery completed `needs_revision` and opened checkpoint `blk_4d7be5151bec4e18ae6aea672269998f`. Findings F001-F005 were assigned to repair worker `019e2298-de69-73b3-817b-41f34dc228d6`, implemented, and then cleared by the fresh RFC 0027 web-state re-review below.
  - Phase 4 evidence-fix scaffold review recovery completed `accept`.

## RFC 0028 Prompt-Literal Recovery

- Workflow: `striatum/rfc-0028-focused-review-recovery-2026-05-13/workflow.json`
- Run: `run_04a31d05bb1945dc8f92f22f032b4243`
- Reason: fresh re-review after the RFC 0028 prompt artifact repair changed the governed v9 artifact to the rendered runtime zero-claim literal `{"claims":[]}` and tests now assert the escaped f-string source literal is absent.
- Current outcome: `rfc0028_prompt_literal_re_review` completed `accept`.

## RFC 0027 Web-State Re-Review

- Workflow: `striatum/rfc-0027-focused-repair-re-review-2026-05-13/workflow.json`
- Run: `run_9cadfc4d2e4646848e2d6539c23322b2`
- Reason: fresh re-review after RFC 0027 recovery findings F001-F005 were implemented.
- Current outcome: `rfc0027_web_state_re_review` published `docs/reviews/rerun-backlog-focused-reviews-2026-05-13/RFC0027_WEB_STATE_RE_REVIEW.md` and recorded verdict `accept`; the artifact confirms F001-F005 are resolved.
- Workflow friction: the process adapter exited code 1 after `artifact.published`, `queue.acked`, `verdict.recorded`, and `job.completed`. Striatum then opened blocker `blk_6dd92e18a3da4cc5ac2c4f1445755b99` even though `missing_artifact_paths` was empty and `review_verdict_missing` was false. `recovery resume --force --complete` cannot resolve it because the completed job has no current lease. Filed as `https://github.com/halbritt/striatum/issues/7`; keep the blocker visible in Striatum state rather than mutating state by hand.

## Active Subagents

- No active implementation subagents. `019e2298-de69-73b3-817b-41f34dc228d6` (`Lovelace`) completed RFC 0027 recovery fixes; focused web/storage tests passed with `56 passed`.
- Completed read-only operator audit subagents:
  - `019e22a3-f0f1-78f3-9bb0-bb6c82939385`: incomplete/deferred work audit.
  - `019e22a3-f112-7592-9dfb-8e117af6818c`: changelog/history audit.
- Completed read-only integration-risk audit: `019e22a3-f133-7013-89e0-cff8d8f76da1` reported low Git conflict risk. The only shared tracked path with `origin/master` is `docs/rfcs/README.md`; preserve the local RFC 0021 status update and upstream RFC 0033-0037 rows when rebasing.

## Remaining Operator Work

- Git integration: fetch/rebase onto `origin/master`, commit this batch as one
  checkpoint, and push.
- Striatum workflow friction: keep
  `blk_6dd92e18a3da4cc5ac2c4f1445755b99` visible until Striatum issue #7
  provides a clean recovery path for completed-job process blockers.
- RFC 0030: old run `run_68de8953cfe049da8b2216a328fd8e36` has seven
  claimable review/adversary jobs and a canceled Claude review that blocks
  downstream ledger/synthesis work. Quarantine or rerun this in a later
  operator pass before treating it as current evidence.
- Older Phase 4 spec-review run `run_7a59159ec4f8442481e62eefc035b515` still
  has downstream jobs blocked behind incomplete review evidence.
- Phase 4: continue only on the evidence-fix path. The fresh gate package is bounded, privacy-safe evidence; it does not promote Phase 4 or authorize full-corpus execution.
- RFC 0044 follow-ups: final synthesis accepted Phase 1 with findings; treat
  any further expansion beyond the read-only Phase 1 MCP surface as new scoped
  work.
- D082/RFC 0028 remains proposed only. The accepted prompt-literal re-review
  cleared a narrow checkpoint; it is not a promotion decision.

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
- `D082` is currently only `proposed`; RFC 0028 now has the governed extraction-prompt artifact and accepted focused prompt-literal re-review, but still lacks an accepted decision binding or full promotion review.
- Phase 4 full-corpus execution remains blocked. The completed multi-lane gate accepted only a bounded evidence package and requires an evidence-fix pass before any bounded Tier 2 preflight.
- Older Striatum runs still need quarantine or rerun if their provenance cannot be verified.
- The local Engram venv reports `striatum 1.35.0`. The standalone Striatum repo currently has unrelated dirty work; do not revert or fold that work into the Engram commit.
- Local Striatum daemon-default behavior requires `STRIATUM_DAEMON_REQUIRED=0 STRIATUM_TEST_HARNESS=1` for scaffold-only validation/plan/status commands in this repo until the operator is ready to use daemon-backed execution. This is validation friction only.
- Striatum process-adapter recovery has an open bug: `https://github.com/halbritt/striatum/issues/7`. The accepted RFC 0027 re-review evidence exists, but Striatum doctor will continue reporting blocker `blk_6dd92e18a3da4cc5ac2c4f1445755b99` until the tooling can resolve completed-job process blockers.
