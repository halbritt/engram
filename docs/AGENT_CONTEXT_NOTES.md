# Agent Context Notes

This file is the durable handoff for every agent session in the Engram repo.
It exists because per-session auto-memory does not cross session boundaries
— so when context resets, the next agent reads this instead of starting cold.
Treat it as live state: keep it current, fold in new lessons, retire entries
that turn out to be wrong.

The contents are split into:

1. **Operator discipline** — behavioral rules that must not be violated.
2. **Active project context** — what is happening right now in the repo.
3. **References** — pointers to external state the agent may need.
4. **How to maintain this file.**

Companion docs to read alongside (per `AGENTS.md`): `README.md`,
`HUMAN_REQUIREMENTS.md`, `DECISION_LOG.md`, `BUILD_PHASES.md`,
`ROADMAP.md`, `SPEC.md`, `docs/schema/README.md`, plus
[`STRIATUM_MEMORY_E2E_BACKLOG.md`](../STRIATUM_MEMORY_E2E_BACKLOG.md) for
the current work plan.

## 1. Operator discipline (do-not-violate rules)

### Never fabricate review provenance

Do not author review artifacts under another model's byline (e.g.
`REVIEW_claude.md`, `REVIEW_gemini.md`) unless that model actually
produced the content. Do not write workflow state, manifests, or
"synthesis" documents that imply lanes ran which did not run. Do not
unilaterally promote an RFC, mark a spec accepted, or claim a review
pass happened — those are operator decisions, not author decisions.

**Why:** Engram's architecture is built on provenance, confidence, and
stability class (per `AGENTS.md`). Falsified bylines destroy the audit
chain the project depends on. The May 2026 `c4a48ab` incident was
caused by exactly this and forced an entire suspect-work audit RFC.

**How to apply:**

- When writing into `docs/reviews/<topic>/REVIEW_<lane>.md`, only sign
  as a lane that actually executed. If Claude Code is writing locally,
  that file is a Claude lane and should be labeled accordingly — never
  as `REVIEW_gemini.md` or `REVIEW_codex.md`.
- When a workflow expects multiple lanes, surface the multi-lane
  requirement to the user and ask how to satisfy it; do not synthesize
  the missing lanes.
- Do not edit `DECISION_LOG.md`, `BUILD_PHASES.md`, the RFC index
  status column, or spec promotion state without explicit operator
  instruction. Authoring an RFC is fine; promoting it is not.
- Do not create a self-audit artifact under a different name to make
  one's own work look third-party-reviewed. The legitimate multi-lane
  runner is Striatum — see § 3 references.

### Subprocess delegation means *actually* delegating

When the user picks a coordinator-with-subprocess-workers pattern (or
any "I drive the loop; the lanes are subprocesses" equivalent):

- **Actually run the subprocesses.** Smoke-testing once and then doing
  the work inline because "subprocess output may be malformed" is
  overriding the user's stated preference. The tradeoff is theirs.
- **If the first subprocess invocation produces bad output, surface it
  before doing more inline.** They may want to fix the prompt, switch
  CLIs, or accept the cost.
- **Inline execution costs cross-model diversity.** All "reviewers"
  becoming one Claude context defeats the multi-agent pattern: every
  review then carries the same blind spots.

**Why:** during an RFC 0030 design review, the user picked subprocess
delegation and 6 of 8 reviews ran inline anyway. Token budget burned,
diversity lost, downstream phases starved.

**How to apply:**

- When a workflow.json specifies `lane_id` other than the active
  session, the default execution path is the lane's `command:` array
  via subprocess, not the agent writing the artifact inline.
- Inline execution is appropriate only when (a) the session matches
  the lane, or (b) the role is coordinator-side (ledger, synthesis,
  final_review, author/apply for the lane being run).
- If subprocess paths fail in practice, escalate explicitly. Do not
  silently fall back.

### Supervisor watchdogs must catch heartbeat stalls

When operating as Striatum operator with `striatum supervise` driving
lane processes, watchdogs must catch silent hangs early. An idle
`until <artifacts exist>` poll loop will sit through any hang —
including hangs the supervisor itself doesn't notice — until the
supervisor process group dies.

**Why:** during the 2026-05-14 / 05-15 promotion run, four codex
author lanes hung in `ep_poll` on stdin for 4h42m because the watchdog
only exited on "all artifacts written" or "all supervisors dead." The
30-min lease was already long expired. See
[striatum#18](https://github.com/halbritt/striatum/issues/18) for the
stdin-EOF root cause and
[striatum#20](https://github.com/halbritt/striatum/issues/20) for the
gap of the runner not detecting stalls.

**How to apply:**

- The watchdog must include heartbeat-stall as a terminal condition:
  e.g. `current_time - heartbeat_at > 2 * lease_seconds`. Lease info
  comes back from `claim-next` (`heartbeat_after_seconds`).
- For long-running supervised work, set ScheduleWakeup (or a tight
  Monitor) to re-check supervisor heartbeats periodically even if the
  user is away.
- If a supervisor reports `liveness=alive` but `wchan=ep_poll` on
  stdin and the lane hasn't heartbeated in lease_seconds, treat it
  as a hang — stop the supervisor, capture state, surface to the
  user. Do not wait for the supervisor to notice on its own.

### Branch policy for doc-only changes

Simple documentation changes (markdown edits, CHANGELOG entries, typo
fixes, small how-to additions) may be committed directly to `master`
rather than a feature branch. Code changes, RFC drafts, scaffolds, and
anything that touches schema, CLI, or tests should still go through a
feature branch — or at minimum land as a coherent commit on master if
the user has explicitly invited that pattern.

**Why:** the user said directly, "I don't prefer that all changes go
to branches, simple doc changes are fine." Defaulting to a feature
branch for a typo fix is friction.

## 2. Active project context

### Source-ingestion expansion (2026-05-15 late)

After the Striatum-memory e2e pipeline (Layers 1-5) landed and was
committed to master, the user invoked a sequenced "scaffold + build"
plan from `docs/design/source-ingestion-expansion-proposal-2026-05-15.md`:

1. Scaffold and run a multi-lane research workflow to produce a usable
   Engram RFC — landed as **RFC 0050** at
   `docs/rfcs/0050-source-ingestion-expansion.md` (850 lines, proposal
   status). Workflow at
   `striatum/source-ingestion-rfc-research-2026-05-15/`.
2. Author a layered execution backlog — landed at
   `SOURCE_INGESTION_BACKLOG.md`.
3. Build all six layers on the branch `engram/source-ingestion-rfc-research`:
   Layer 1 source contract + git importer; Layer 2 build-artifact
   importer; Layer 3 Markdown importer; Layer 4 EG-SI gates; Layer 5
   exact-reference retrieval extension; Layer 6 `source_audits` +
   EG-SI-090 reconstruction.
4. Full suite at branch tip: `make test` 702 passed (was 626 at the
   start of the session). 76 new tests across the six layers.

The RFC is proposal status only; promotion to accepted requires an
operator-recorded decision in `DECISION_LOG.md`. The branch has not
been merged into master in this session.

### Striatum-memory e2e pivot (2026-05-15 — earlier)

On 2026-05-15 the user pivoted off the RFC 0045-0049 promotion / spec
paperwork track and onto building the e2e Striatum-memory pipeline
incrementally. The active plan is
[`STRIATUM_MEMORY_E2E_BACKLOG.md`](../STRIATUM_MEMORY_E2E_BACKLOG.md):
five sequenced layers — projection, retrieval, packet builder, gates,
e2e MCP smoke — each shipping as working code with tests on master.

**Done so far on the new track:**

- RFC 0044 Phase 1 read-only API was already implemented before the
  pivot (migration 014, `MemoryService`, `engram-mcp-stdio`,
  `engram ingest-striatum`).
- AL-D001 / EG-000 hardening baseline closed. Evidence at
  `docs/reviews/eg-000-evidence-2026-05-15/EG_000_EVIDENCE.md`.
  Committed non-private fixture at `tests/fixtures/striatum_eg000/`.
- Implementation checkpoint `25decf4` (`Build Striatum memory retrieval
  layers`) landed Layer 1 projection, Layer 2 exact-reference retrieval,
  Layer 3 packet building, first Layer 4 gates, and the Layer 5 MCP smoke.
  Verification before that commit: `make test` 626 passed,
  `make eval-gates` 12 passed, and `make e2e-striatum` 1 passed.
- Current handoff is in `OPERATOR_REPORT.md`. The backlog doc is now partly
  stale where it describes Layers 1-3 and the e2e smoke as future work; use
  it as design/order reference until it is reconciled.
- Remaining near-term work: refresh generated schema docs if desired, add the
  real-bundle Striatum e2e runbook, complete the remaining named Layer 4
  gates, and then decide whether to start source-ingestion expansion with the
  source contract template plus local git/build-artifact importers.

**Important:** treat RFC 0045-RFC 0049 as design *reference*, not as
contract gates. The acceptance decisions (AL-D002, AL-D003, AL-D004)
are recorded as humans review working code, not as conditions on
shipping more paper. The promotion-workflow scaffold at
`striatum/striatum-memory-rfc-promotion-2026-05-14/` is deferred-
canceled (run `run_c16bd15778f6473e800af5378d609449`); do not restart
it until [striatum#18](https://github.com/halbritt/striatum/issues/18)
lands or the workflow lane command is moved off stdin.

### Striatum daemon/MCP/Postgres transition is rocky

Striatum is mid-transition from repo-local SQLite to a long-lived
daemon backed by PostgreSQL and a daemon MCP interface. The user
described the transition as a "trainwreck" — the daemon, MCP, and
Postgres pieces were not sequenced well, and operators hit compounding
integration bugs.

**Current working configuration on Engram (updated 2026-05-15 late):**

- Striatum CLI is at 1.54.0 (engram venv + `~/.local/bin`). Source at
  `~/git/striatum` HEAD `dd9f0b2` is the up-to-date checkout.
- The systemd-managed daemon (`striatumd.service`) is healthy on
  PostgreSQL schema v5; daemon doctor returns ok.
- The engram repo is registered with the daemon as
  `repo_b63673a288c64bb987d29bafffaed578`. The daemon-side `striatumd.
  clients` table was re-bootstrapped this session; the admin client
  token cache lives at `/run/user/1000/striatum/client-token`.
- Workflow lifecycle verbs (`run prepare`, `claim-next`,
  `publish-artifact`, `complete`, `release`, `verdict`) are still
  SQLite-backed in striatum 1.54.0 (`daemon doctor --explain` shows
  `run.prepare: pg_backed=false` with a `sqlite_fallback_route`). The
  engram repo therefore continues to use `.striatum/state.sqlite3` for
  workflow state, even though the repo is registered with the daemon.
  The 2026-05-14 attempt to migrate workflow state to Postgres still
  fails on the same `sessions_repository_id_parent_session_id_fkey`
  insert-ordering bug; v1.54.0 did not close it.
- Operating mode is therefore: `STRIATUM_DAEMON_REQUIRED=0
  STRIATUM_TEST_HARNESS=1` for engram-side striatum verbs, plus a
  healthy daemon for daemon-global verbs (`repo list`, `daemon
  status/doctor/health`).
- The 2026-05-14 stale SQLite backup is at
  `.striatum/state.sqlite3.bak-20260515-140014` (2.9 MB, pre-RFC-0050
  state). The fresh SQLite from this session is the active state.

**How to apply:**

- Do not retry the daemon migration (`daemon migrate-repo-local --from
  sqlite --to pg`) on engram until striatum upstream closes the
  `sessions_repository_id_parent_session_id_fkey` ordering bug AND ports
  `run.prepare` / `claim-next` / `publish-artifact` to PG. Today the
  migration succeeds for the table copy but downstream verbs cannot
  execute against the resulting PG state.
- Do not kick off a Striatum run that uses `cmd ... -` (stdin) lane
  commands until issue #18 is fixed. Use positional-prompt or temp-
  file delivery, or drive the lanes inline without `striatum supervise`.
- Do not silently restart the cancelled promotion run.
- The driver script at
  `striatum/source-ingestion-rfc-research-2026-05-15/drive_lane.sh` is a
  durable reference for driving multi-lane workflows by hand via
  `register-session` → `claim-next` → `ack` → run subprocess →
  `publish-artifact` → `complete`. It reads the work packet's
  `write_scope.allowed_paths` / `forbidden_paths` and the
  `expected_artifacts[0].kind` dynamically, and uses
  `--allow-no-process-execution --override-rationale` to bypass the
  RFC 0046 lane-evidence guard when not running under `striatum supervise`.

**Test database:** `postgresql:///engram_test` exists with the
`vector` extension already created as superuser. Tests run with
`ENGRAM_TEST_DATABASE_URL="postgresql:///engram_test"`. The `conn`
fixture in `tests/conftest.py` drops + recreates the schema per test.

### Pipeline state at handoff (2026-05-15)

- Phase 1 raw evidence: complete (ChatGPT, Claude, Gemini, Striatum
  bundle).
- Phase 2 segmentation + embedding: complete on the AI-conversation
  corpus (7916 conversations, 11266 active embedded segments; last
  activation 2026-05-08).
- Phase 3 claim extraction + belief consolidation: primary run
  complete (43812 claims, 42558 beliefs; last extraction 2026-05-07).
  Residual: 149 unextracted active segments, 22 failed extractions.
- ROADMAP says Step 5 (gold-set authoring) is the active step;
  TODO.md mirrors it. Step 5 is owner-only and cannot be delegated.
- Striatum-memory e2e: see `STRIATUM_MEMORY_E2E_BACKLOG.md` for the
  layered plan.

### RFC 0027 web UI polish is deferred

The interview Web UI is functional end-to-end (verdict commit,
evidence expansion, Origin allowlist) but visually rough by the
user's own assessment ("yeesh, this UI" — 2026-05-09 first session of
real use over Tailscale).

**How to apply:**

- Do not claim or imply the UI is polished. When discussing RFC 0027
  status, separate "schema + invariants are solid" from "UI is v1
  functional minimum, polish deferred."
- Do not pre-build refactors. The user explicitly deferred polish.
- Expected future scope when the user revisits: visual design pass,
  replace the custom 174-line htmx shim with the upstream bundle or
  Alpine, keyboard-shortcut discoverability, possibly inline-strata-
  strip layout, possibly a Tier-2 read-only mode.

### Predicate-intent polish queued for the interview process

The Engram predicate vocabulary has implicit subject-type expectations
that are not enforced or surfaced today.

- `has_name` has `stability_class=identity`, gloss "legal or preferred
  name" (db: `predicate_vocabulary.description`). Intent is persons-
  only. Neither the extractor prompt nor the interview UI shows that
  gloss prominently.
- `src/engram/extractor.py::build_extraction_prompt` enumerates each
  predicate as
  `- has_name: stability=identity, cardinality=single_current, object_kind=text, required_object_keys=none`
  — the description column is omitted. The LLM never learns
  `has_name` is for persons specifically.
- Migration 012 added `subject_kind_hint` advisory metadata; the hint
  is not yet surfaced to the extractor prompt or operator UI.

User observation (2026-05-09): "Odessa Rye -[has_name]-> Odessa rye"
(bread name) and "Hobnob -[has_name]-> Hobnob" (restaurant name) were
both extracted because the prompt did not carry "persons only."

**User said:** "that should be cleaned up in the interview process,
make a note."

**Cleanup scope (queued, not designed):**

1. Surface `predicate_vocabulary.description` (and `subject_kind_hint`)
   prominently in the interview UI (CLI + web).
2. Include the description in the extractor prompt so the LLM gets
   first-class subject-type guidance.
3. Broaden the `false` rationale prompt label; current "correct value
   > " over-fits the predicate-right-object-wrong case.
4. Optional: structured "this verdict says the predicate is wrong;
   the right one is X" capture surface for re-extraction.

**How to apply:** Do not pre-build. When the user revisits interview
UX or extractor prompt versioning (RFC 0017), surface this note. If
RFC 0021 § Open Questions is being amended, this note belongs there
as an explicit open question.

## 3. References

### Striatum source and docs

Local checkout: `~/git/striatum` (`/home/halbritt/git/striatum`).

Use this checkout for authoritative behavior of `striatum` verbs, RFC
numbers (D006/D009/D028/D036, RFC 0008 worktrees, RFC 0009
supervision, etc.), and the workflow-author conventions referenced by
the in-repo skills under `.claude/skills/striatum-*`.

The user runs a Striatum test-harness web server (port 8088) and a
tmux Striatum daemon — these are their workflow. Do not kill them.

### Striatum upstream bugs to track

- [striatum#18](https://github.com/halbritt/striatum/issues/18):
  supervisor never closes the lane stdin write end, blocking
  `codex exec ... -` and any other `cmd -` lane on EOF.
- [striatum#20](https://github.com/halbritt/striatum/issues/20):
  runner should detect heartbeat stalls / lease expiration and raise
  blockers; operators should not have to roll their own watchdog.

### Engram canonical docs (per AGENTS.md "Start Here")

Read in order: `README.md` → `HUMAN_REQUIREMENTS.md` →
`DECISION_LOG.md` → `BUILD_PHASES.md` → `ROADMAP.md` → `SPEC.md` →
`docs/schema/README.md`.

For the current work, also read
[`STRIATUM_MEMORY_E2E_BACKLOG.md`](../STRIATUM_MEMORY_E2E_BACKLOG.md)
(the active plan) and skim the most recent `CHANGELOG.md` Unreleased
section.

## 4. How to maintain this file

This file is the *agent-readable* equivalent of per-session memory and
should be updated under the same rules.

**When to update:**

- The user explicitly says "remember this" or "save that for next
  time" → append the rule under § 1 or § 2.
- The user pivots strategy or pauses an initiative → revise the
  relevant § 2 entry; date the change inline.
- A friction or bug recurs and an artifact captures the fix → add a
  pointer here.
- Something turns out to be wrong → remove or revise the entry. Do
  not leave stale claims in place.

**When NOT to update:**

- One-off task details, in-progress work, conversation context that
  is captured by git, the OPERATOR_REPORT, or the backlog doc.
- Code conventions, file paths, project structure — those are
  discoverable from the current code.
- Anything already covered by `AGENTS.md`, `BUILD_PHASES.md`,
  `ROADMAP.md`, or the canonical RFC set.

**Style:**

- Lead each rule or context entry with the rule itself, then a
  **Why:** line and a **How to apply:** line. Knowing why lets the
  next agent judge edge cases instead of blindly following.
- Prefer named, durable references (`§ 1`, `OPERATOR_REPORT`,
  `STRIATUM_MEMORY_E2E_BACKLOG.md`) over file paths that may move.
- Convert relative dates to absolute (`Thursday` → `2026-03-05`) so
  entries stay legible.

When this file grows past ~300 lines, retire stale entries before
adding new ones.
