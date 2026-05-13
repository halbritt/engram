# Focused Review Recovery Runbook

Status: scaffolded
Date: 2026-05-13

## Goal

Recover the two focused-review jobs from
`run_6d6d3c3ce51f4b4286bfefad6d4ed09e` whose Claude adapters exited zero
without publishing required artifacts or verdicts.

This workflow does not reinterpret the original Claude jobs and does not
publish artifacts under their sessions. It records fresh substitute review
artifacts with honest provenance, then summarizes the recovery lane.

## Scope

Only these missing reviews are in scope:

- RFC 0027 web/privacy/session-state focused review.
- Phase 4 evidence-fix scaffold focused review.

Acceptance of these review artifacts is not promotion authority.
