---
loop: postbuild
issue_id: 20260505_limit10_runtime
family: review
scope: phase3 pipeline-3 limit10 runtime repair
bound: limit10
state: ready
gate: ready_for_same_bound_rerun
classes: [prompt_or_model_contract_failure, upstream_runtime_failure, orchestration_bug, downstream_partial_state, data_repair_needed]
created_at: 2026-05-05T22:30:00Z
linked_report: docs/reviews/phase3/PHASE_3_D063_LIMIT10_REPAIR_REVIEW_claude_opus_4_7_2026_05_05.md
supersedes:
corpus_content_included: none
---

# Phase 3 Limit-10 Repair Review - claude_opus_4_7

Verdict: `accept_with_findings`.

The D063 / limit-10 repair is substantively sound. The same-bound `--limit 10`
rerun is safe. Expansion to `--limit 50` should wait until three findings are
addressed.

Review file:

- `docs/reviews/phase3/PHASE_3_D063_LIMIT10_REPAIR_REVIEW_claude_opus_4_7_2026_05_05.md`

Files read:

- `AGENTS.md`
- `README.md`
- `HUMAN_REQUIREMENTS.md`
- `DECISION_LOG.md`
- `docs/process/phase-3-agent-runbook.md`
- `docs/rfcs/0013-development-operational-issue-loop.md`
- `docs/rfcs/0014-operational-artifact-home.md`
- `docs/reviews/phase3/PHASE_3_POSTBUILD_RUN_LIMIT10_2026_05_05.md`
- `docs/reviews/phase3/PHASE_3_POSTBUILD_LIMIT10_REPAIR_2026_05_05.md`
- `docs/reviews/phase3/postbuild/markers/03_LIMIT10_RUN.blocked.md`
- `docs/reviews/phase3/postbuild/markers/20260505_limit10_runtime_repair/05_REPAIR_VERIFIED.ready.md`
- `src/engram/extractor.py`
- `src/engram/cli.py`
- `scripts/phase3_tmux_agents.sh`
- `tests/test_phase3_claims_beliefs.py`

Checks run:

- `git status --short` before writing.
- Code trace: `run_extract_batches` vs `run_segment_batches` failed-batch break.
- Code trace: chunk provenance constraint via JSON-schema enum and salvage.
- Code trace: adaptive split recursion bound and content-only split path.
- Marker layout review against RFC 0013 §4 / §5 / §6.
- Tmux script `supersedes:` parsing and superseded-marker filtering.
- No DB query, no `pipeline-3` / `extract` / `consolidate` run, no raw corpus
  inspection, no external service calls.

Findings (summarized in linked review):

- Major: `run_extract_batches` does not actually `break` on `result.failed`;
  the regression test passes for an unrelated reason. Add the explicit break
  and a tighter test.
- Major: same-bound rerun report omits the dropped-claim count, so the
  RFC 0013 §9 10% gate cannot be verified.
- Major: per-loop marker chain went `03_LIMIT10_RUN.blocked` →
  `05_REPAIR_VERIFIED.ready` without the intervening `02_REPAIR_PLAN`,
  `03_REVIEW`, or `04_SYNTHESIS` markers. Multi-agent review should land in
  this directory before claiming the loop is closed.
- Minor: single-message content split fragments context; emit a chunk
  diagnostic when `split_depth >= 2` so the next reviewer sees it.
- Minor: tmux supersession is path-string only; tighten to also match
  `issue_id` / `family` when both markers carry front matter.
- Minor: cross-version belief cleanup is implicit; before `--limit 50`, run a
  global proof query for active beliefs whose `claim_ids` reference
  non-`extracted` claim_extractions.

Next expected step:

1. Sibling reviews from other models for this loop, written as
   `06_REPAIR_REVIEW_<model_slug>.ready.md` in this directory.
2. A `07_REPAIR_REVIEW_SYNTHESIS.ready.md` (or equivalent) that classifies
   the findings as accepted / accepted with modification / deferred /
   rejected.
3. Apply accepted findings in code, tests, and the same-bound rerun report
   (especially the dropped-claim rate).
4. Optional: reaffirm `05_REPAIR_VERIFIED.ready.md` only after step 3, or
   leave it as-is and add a follow-up `08_REPAIR_VERIFIED_V2.ready.md` that
   names this review in `supersedes:` if the report is amended.
5. Do not start `pipeline-3 --limit 50` until the dropped-claim rate is
   explicitly under the RFC 0013 §9 10% gate in a tracked report.
