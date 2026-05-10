# Spec 0029 Bench Triage Workbench Review - Gemini
author: reviewer-gemini-3.1-pro-preview-001

Status: review
Date: 2026-05-09
RFC refs: RFC-0029
Spec refs: SPEC-0029
Decision refs: D020, D074, D082
Phase refs: PHASE-0003-FOLLOWON, PHASE-0004

## Findings

### F001 - Candidate versions missing from review_sessions schema
Severity: minor
Source: Scratch SQLite State
Rationale: The `review_sessions` table schema explicitly records `prior_prompt_version`, `prior_model_version`, and `prior_request_profile_version`, but does not record the corresponding candidate versions. While these can be read from the candidate run artifact referenced by `run_path`, including the candidate versions directly in the session schema would make the review session metadata entirely self-contained and robust against the candidate artifact being deleted or relocated.

### F002 - Forward-compatibility with engramd (RFC 0022) is unspecified
Severity: nit
Source: Architecture > Modules
Rationale: Spec 0027 explicitly discusses forward-compatibility with RFC 0022's `engramd` binary, detailing how its FastAPI routes will eventually become thin clients to `engramd`. Spec 0029 introduces a similar standalone FastAPI app for bench review (`src/engram/bench_review/web.py`) but omits this migration path. A brief note confirming a similar transition strategy would align it with Spec 0027's architectural trajectory.

## Open questions

None.

verdict: accept_with_findings
