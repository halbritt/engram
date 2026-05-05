---
loop: postbuild
issue_id: 20260505_limit50_run
family: run
scope: phase3 pipeline-3 limit50
bound: limit50
state: blocked
gate: blocked
classes: [prompt_or_model_contract_failure, downstream_partial_state, data_repair_needed]
created_at: 2026-05-05T23:55:00Z
linked_report: docs/reviews/phase3/PHASE_3_POSTBUILD_RUN_LIMIT50_2026_05_05.md
corpus_content_included: none
---

# Phase 3 Limit-50 Run Blocked

Verdict: `blocked_for_expansion`

The bounded `--limit 50` run exited with code `1`.

Blocking conditions:

- 3 extraction failures
- 3 consolidation skips
- dropped-claim rate: 20.2%

Report:

- `docs/reviews/phase3/PHASE_3_POSTBUILD_RUN_LIMIT50_2026_05_05.md`

Next expected step:

Repair extraction validation/salvage behavior, then rerun the same `--limit 50`
bound before any further expansion.
