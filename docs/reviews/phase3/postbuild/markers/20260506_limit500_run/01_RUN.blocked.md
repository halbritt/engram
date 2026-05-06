---
loop: postbuild
issue_id: 20260506_limit500_run
family: run
scope: phase3 pipeline-3 limit500
bound: limit500
state: blocked
gate: blocked
classes: [prompt_or_model_contract_failure, downstream_partial_state, data_repair_needed]
created_at: 2026-05-06T01:59:00Z
linked_report: docs/reviews/phase3/PHASE_3_POSTBUILD_RUN_LIMIT500_2026_05_06.md
corpus_content_included: none
---

# Phase 3 Limit-500 Run Blocked

Verdict: `blocked_for_expansion`

The bounded `--limit 500` run hit a prompt/model contract failure before
completion.

Blocking conditions:

- 1 latest selected-scope extraction failure
- 1 selected-scope consolidation skip
- selected-scope dropped-claim gate: 24.2%
- terminal command interrupted by coordinator after the gate failure was
  observed

Report:

- `docs/reviews/phase3/PHASE_3_POSTBUILD_RUN_LIMIT500_2026_05_06.md`

Next expected step:

Repair extraction validation/prompt behavior, then rerun the same `--limit 500`
bound before any full-corpus Phase 3 run.
