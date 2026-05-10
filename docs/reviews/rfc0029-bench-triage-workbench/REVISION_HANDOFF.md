# RFC 0029 Bench Triage Workbench Revision Handoff
author: author-codex-gpt-5.5-003

Status: revised
Date: 2026-05-09
RFC refs: RFC-0029
Decision refs: D020, D074, D082
Phase refs: PHASE-0003-FOLLOWON, PHASE-0004

## Changes Made

Revised `docs/rfcs/0029-bench-triage-workbench.md` to incorporate the
three-lane design review and adversarial usability findings.

Key edits:

- Required candidate segment records for normal triage mode and defined
  metadata-only fallback when they are missing or malformed.
- Replaced prompt-only prior comparison with the full extraction version
  identity: prompt, model, and request profile.
- Added typed data-availability states and disabled semantic acceptance when
  data is unavailable.
- Split candidate display into redacted mode and private-detail mode.
- Replaced `POST /export` with CLI-only export and hardened `--output` rules.
- Matched RFC 0027's loopback, Origin, `Sec-Fetch-Site`, Tier 1, vendored htmx,
  package-data, and no-CDN posture.
- Replaced "safe to promote" with promotion-readiness states plus an explicit
  run-level decision.
- Clarified verdict labels, skip/exclusion semantics, batch limits, keyboard
  shortcuts, and resumable UI state.
- Expanded acceptance tests to cover usability contracts, export path safety,
  no-CDN rendering, and deterministic resume.

## Findings Addressed

- L001 through L014 from `FINDINGS_LEDGER.md` are addressed in the revised RFC.
- The blocking usability concern about semantic zero versus missing/redacted
  data is now explicit in the Data availability section.
- The scratch-to-tracked boundary is now mechanical: web UI writes scratch
  state only; tracked Markdown export is CLI-only.

## Findings Deferred

- A dedicated read-only Postgres role remains an open question.
- A Phase 4 alias is deferred until Phase 4 benchmark artifacts exist.
- Segment ID redaction in tracked exports remains a future review concern; v1
  exports keep IDs but omit raw text and private values.

## Validation Run

- Targeted `rg` checks verified the revised RFC no longer uses the old
  `prior-version`, `POST /export`, `include-notes`, `Good drop`, or
  `safe to promote` contract language.
- A targeted non-ASCII dash check found no non-ASCII dash characters in the
  RFC.

## Residual Risk

This is still a proposal, not an accepted implementation contract. If the owner
accepts it, the next step should be promotion to a spec before code, mirroring
RFC 0027. The eventual implementation should receive another adversarial
usability review after the UI is usable, because the main risk is actual
operator load, not only architecture.
