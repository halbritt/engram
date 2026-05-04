# Project Judgment

This is coordinator guidance, not Engram product architecture. It exists to
capture steering taste that is otherwise easy to keep in volatile human memory.

The canonical product principles still live in `HUMAN_REQUIREMENTS.md`,
`DECISION_LOG.md`, `BUILD_PHASES.md`, `ROADMAP.md`, and `SPEC.md`. This document
is a reminder about how to move work through the project without letting good
ideas dilute attention.

## Default Posture

- Finish the active phase before widening the system.
- Treat human attention as scarce. State belongs in files, not in memory.
- Prefer reversible, additive changes until eval or review says otherwise.
- Keep process improvements small during critical path implementation.
- Do not confuse a good idea with a ready task.

## Scope Control

- RFCs are parking lots for ideas that need review, not permission to execute.
- If a prompt encodes unresolved decisions, it is not a prompt yet.
- If a task would change architecture, create or update an RFC before writing
  the execution handoff.
- If a proposed change makes Engram more impressive but less local, reject it.
- If a proposal mostly improves documentation hygiene, ask whether it helps the
  current phase or should be parked.

## Model Use

- Use strong synthesis models for architecture, review, and judgment-heavy
  work.
- Use Codex-on-box for implementation, local runs, tests, and benchmark
  execution.
- Use large-context models for broad consistency passes across docs.
- Prefer fresh execution contexts after synthesis for non-trivial
  implementation.
- Keep the originating context responsible for synthesis unless explicitly
  handing off ownership.

## Review And Decisions

- Architecture changes need adversarial review.
- Accepted review deltas update the artifact that was reviewed.
- Binding architecture changes update `DECISION_LOG.md`.
- Sequencing changes update `BUILD_PHASES.md` or `ROADMAP.md`.
- Rejected and deferred findings stay recorded; they are provenance, not waste.

## Single-Maintainer Mode

- GitHub is remote persistence by default, not the coordination layer.
- Pull requests are optional ceremony while all agents operate on the same local
  codebase and the project has one human owner.
- Prefer local worktrees, `docs/reviews/`, synthesis docs, commits, and pushes
  over PR threads for current Engram work.
- Use PRs when they add a real boundary: external contributors, required CI,
  permission separation, public review history, or release governance.
- Do not create a PR just to simulate review. Review artifacts already provide
  the audit trail.

## Attention Traps

- Do not turn process hygiene into a side quest while Phase 2 is active.
- Do not broaden V1 because the schema can imagine V2.
- Do not promote meta-work ahead of benchmark, segmentation, extraction, or eval
  work unless the meta-work removes an immediate blocker.
- Do not let several ready prompts live only as a remembered queue. Put order,
  status, and dependencies in filenames, headers, `ROADMAP.md`, or phase docs.

## Human Checkpoints

Some work should keep a human checkpoint even if a coordinator model can manage
the queue:

- choosing priority when two good paths compete,
- accepting or rejecting architectural taste calls,
- deciding what is "good enough" to move on,
- authoring gold-set answers from lived experience,
- approving any relaxation of local-first, privacy, or egress constraints.

The goal is not to replace judgment. The goal is to make enough of its outputs
visible that agents can carry the queue between check-ins.
