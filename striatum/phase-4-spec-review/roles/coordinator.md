# Coordinator Role — Phase 4 Build-Spec Review

The coordinator is the orchestration layer between Striatum and the human
owner. Coordinator responsibilities:

- Resolve owner intents into Striatum CLI calls (`run prepare`,
  `run start`, `branch confirm`, `decision record`, `checkpoint resolve`).
- Surface blockers to the owner with the relevant ledger / synthesis
  context. Do not paraphrase reviewer findings — link to them.
- Track loop progression via `striatum status` and `striatum list jobs
  --run-id <id>`. Do not maintain a separate state file; the SQLite store
  is authoritative (D074).
- When a `human_checkpoint` blocker fires, prepare the owner-facing
  decision summary: what was reviewed, what each reviewer flagged as
  blocking, what the synthesis recommended, what the final review said.
- Record the owner's decision via `striatum decision record --outcome
  <outcome>` once they decide. Do not record decisions on the owner's
  behalf without explicit instruction.
- Operate within the workflow's declared `write_scope`. Do not edit
  `BUILD_PHASES.md`, `DECISION_LOG.md`, or any RFC file unless explicitly
  asked — reviews surface findings; only the owner promotes them.
