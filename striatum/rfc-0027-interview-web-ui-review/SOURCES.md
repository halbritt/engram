# RFC 0027 Interview Web UI Review — Source List

Status: scaffolded
Date: 2026-05-08

## RFC Under Review

- `docs/rfcs/0027-interview-web-ui.md` — proposed FastAPI + htmx web UI
  over the gold-set interview surface.

## Upstream RFCs

- `docs/rfcs/0021-gold-set-interview-curation.md` — gold-set schema,
  sampler, agent, CLI v1; the contract this UI renders.
- `docs/rfcs/0022-server-binary-api-mcp.md` — server-binary precedent
  for localhost-bound HTTP services in Engram.

## Schema Baseline

- `migrations/010_gold_labels.sql` — append-only gold-label tables and
  triggers the web UI must respect.

## Source Modules

- `src/engram/cli.py` — interactive interview loop, `_fetch_target_display`,
  `_fetch_evidence_excerpts`, `_pick_question`, `_RATIONALE_PROMPT_BY_VERDICT`,
  `_VERDICT_PROMPT`, `_VERDICT_VALID`. The render.py extraction unifies
  these for CLI + web reuse.
- `src/engram/interview/agent.py` — `InterviewAgent.render_question()`
  and `record_verdict()`.
- `src/engram/interview/sampler.py` — `GoldLabelSampler`.
- `src/engram/interview/storage.py` — `insert_session`, `insert_label`,
  `mark_session_completed`, `list_sessions`.

## Tests

- `tests/test_interview_cli.py`, `tests/test_interview_sampler.py`,
  `tests/test_interview_storage.py` — current test surface.
- New `tests/test_interview_web.py` is the v1 deliverable.

## Constraints

- `HUMAN_REQUIREMENTS.md` — local-first, privacy-tier ceilings,
  no-egress.
- `DECISION_LOG.md` — D016 (eval gates), D020 (no outbound network),
  D044 (no auto-promotion), D069 (audit cascade advisory), D074
  (Striatum SQLite is authoritative), D079 (RFC 0021 acceptance).

## Operator Docs

- `docs/howto/gold-set-interview.md` — operator guide; the web UI
  becomes a new section once landed.

## Process

- `docs/process/multi-agent-review-loop.md` — RFC-to-spec promotion
  pattern.
- `docs/process/project-judgment.md` — taste rules.
