# RFC 0027 Web UI Implementation — Source List

Status: scaffolded
Date: 2026-05-08

## Implementation Contract

- `docs/specs/0027-interview-web-ui-spec.md` — the buildable spec.

## Provenance (read-only here)

- `docs/rfcs/0027-interview-web-ui.md` — the promoted RFC.
- `docs/reviews/rfc0027/RFC_0027_INTERVIEW_WEB_UI_SYNTHESIS.md`.
- `docs/reviews/rfc0027/RFC_0027_INTERVIEW_WEB_UI_FINDINGS_LEDGER.md`.

## Decision Log

- **D080** — RFC 0027 acceptance + spec promotion.
- **D079** — RFC 0021 acceptance.
- **D078** — phase-scoped CLI shape.
- **D044 / D069** — gold labels stay advisory; web must not auto-flip.
- **D020** — local-first, no outbound network.
- **D016** — eval gate sequencing.

## Source Modules

- `src/engram/cli.py` — interactive interview loop with helpers to extract.
- `src/engram/interview/agent.py` — `InterviewAgent.record_verdict()`.
- `src/engram/interview/sampler.py` — `GoldLabelSampler`.
- `src/engram/interview/storage.py` — session + label INSERT helpers.

## Schema Baselines

- `migrations/010_gold_labels.sql` — append-only triggers and view to
  preserve. Migration 011 is additive.
- `tests/conftest.py` — real-DB `conn` fixture; extend the schema-drop
  list with `gold_label_session_targets`.

## Test Surface

- `tests/test_interview_cli.py` — extend (no behavior change expected).
- `tests/test_interview_render.py` — NEW.
- `tests/test_interview_web.py` — NEW.
- `tests/test_migrations.py` — extend with 011 tests.

## Process

- `docs/process/multi-agent-review-loop.md` — RFC-to-spec promotion;
  this is the implementation phase.
- `docs/process/project-judgment.md` — taste rules.
