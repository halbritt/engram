# Project Instructions

Engram is a local-first personal memory layer. Preserve the core constraint:
no cloud dependency and no user data leaving the machine unless explicitly
requested.

## Start Here

Read these first, in order:

1. README.md
2. HUMAN_REQUIREMENTS.md
3. DECISION_LOG.md
4. BUILD_PHASES.md
5. ROADMAP.md
6. SPEC.md
7. docs/schema/README.md

Treat older review, brainstorm, and prior-art docs as context, not current
architecture, unless they are referenced from the canonical docs.

## Architecture Principles

- Raw evidence is immutable and should not be overwritten in place.
- Derived tables and projections should be rebuildable from canonical evidence.
- Preserve provenance, confidence, stability class, and auditability.
- Prefer boring local infrastructure: Python, PostgreSQL, pgvector, and local
  model runtimes.
- Do not introduce hosted services, cloud APIs, telemetry, or external
  persistence without explicit approval.

## Development

Use the existing Makefile targets:

- `make install`
- `make migrate`
- `make migrate-docker`
- `make test`
- `make test-docker`
- `make segment`
- `make embed`
- `make pipeline`

Python source lives under `src/engram`.
Tests live under `tests`.
Database migrations live under `migrations`.

## Change Discipline

- Keep changes phase-aligned with BUILD_PHASES.md and ROADMAP.md.
- Update DECISION_LOG.md when making architectural decisions.
- Add or update tests for behavior changes.
- Avoid broad refactors unless needed for the requested change.
- Do not rewrite generated schema docs by hand; use `make schema-docs`.

## Python Coding Standard

Python under `src/engram` and `tests` follows the standard proposed in
`docs/rfcs/0012-python-agentic-coding-standard.md`. Read that RFC before
non-trivial Python changes. Highlights:

- Type hints on all signatures; `from __future__ import annotations`; no
  `Any` without a one-line reason.
- No bare `except:`; per-stage exception families subclass a domain root
  (see `SegmentationError` in `src/engram/segmenter.py`).
- Tunables live behind `ENGRAM_`-prefixed environment variables read at
  module top.
- Workers follow the `(input_id, version) -> idempotent commit` contract
  (RFC 0001); raw evidence tables stay append-only.
- Tests are deterministic; no live LLM calls in unit tests; one behavior
  per test.
- Toolchain (when wired): `ruff` for lint and format, `pyright` for type
  checking, `pytest` for tests. Adoption is green-on-touch, not bulk
  reformat — see RFC 0012 § Adoption Plan.

## Multi-Agent Review

For substantial artifacts that use one agent to create and another agent to
review, follow `docs/process/multi-agent-review-loop.md`: feedback lands under
`docs/reviews/`, the originating agent synthesizes it, accepted deltas update
the source artifact, and fresh execution contexts are preferred after synthesis.

## Coordinator Judgment

Use `docs/process/project-judgment.md` for process and priority guidance. It is
not product architecture; it captures scope-control taste, attention-management
rules, and model-handoff preferences for coordinating work.
