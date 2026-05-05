# Phase 3 D063 Limit-10 Repair Review Synthesis

Date: 2026-05-05
Coordinator verdict: repaired, pending same-model Codex re-review
Bounded post-build expansion may proceed: no

## Review Inputs

- `docs/reviews/phase3/PHASE_3_D063_LIMIT10_REPAIR_REVIEW_codex_gpt5_5_2026_05_05.md`
- `docs/reviews/phase3/PHASE_3_D063_LIMIT10_REPAIR_REVIEW_claude_opus_4_7_2026_05_05.md`
- `docs/reviews/phase3/PHASE_3_D063_LIMIT10_REPAIR_REVIEW_gemini_pro_3_1_2026_05_05.md`

Verdicts:

- Codex GPT-5.5: `reject_for_revision`
- Claude Opus 4.7: `accept_with_findings`
- Gemini Pro 3.1: `accept_with_findings`

The Codex rejection is respected. No next-bound run may proceed until the same
model re-reviews the corrected repair.

## Findings And Disposition

### Failed extraction batches could re-enter the same failure

Disposition: accepted and fixed.

`run_extract_batches` now stops immediately after any failed extraction batch.
The regression test uses a full failed batch (`batch_size=1`, `limit=3`) so it
would fail if the loop only exited because a batch was short.

### Chunked relaxed-schema fallback could lose chunk-local evidence bounds

Disposition: accepted and fixed.

Each chunk output is now salvaged against that chunk's own message ids before
it is merged back into the segment-level output. Dropped chunk claims are
carried into the final extraction payload so the dropped-claim accounting
remains visible.

### Marker supersession was path-only instead of marker-identity aware

Disposition: accepted and fixed.

`scripts/phase3_tmux_agents.sh` now treats post-build markers as stateful
front-matter records. A ready marker can suppress a blocker only when it
explicitly names the blocker in `supersedes`, is not itself a blocked gate, is
newer when the blocker has a timestamp, and shares `issue_id` and `family` for
front-matter markers. Legacy flat markers without front matter may still be
superseded by explicit path to preserve existing provenance.

The script also now treats a `.ready.md` marker with `gate: blocked` as an
active blocker. `scripts/phase3_tmux_agents.sh next` currently blocks on the
Codex reject marker, which is the intended state.

### Extraction continued within the current internal batch after one failure

Disposition: accepted and fixed.

`extract_pending_claims` now stops processing the internal candidate list after
the first failed segment. This prevents avoidable same-command work in a
conversation that is already disqualified from consolidation.

### Recursive split paths reused the full retry budget

Disposition: accepted and fixed.

Adaptive child splits now receive a reduced retry budget. The root request
keeps the configured retry behavior; recursive leaves do not multiply the same
retry count across every split node.

### Same-bound report did not include dropped-claim rate

Disposition: accepted for the next run report.

The next same-bound and expansion reports must include dropped-claim counts and
rates, using aggregate counts only. No raw claims, belief values, prompt
payloads, model completions, conversation titles, or message text should be
written to tracked artifacts.

## Verification

- Focused repair tests: passed.
- `make test`: `119 passed`.
- `bash -n scripts/phase3_tmux_agents.sh`: passed.
- `git diff --check`: passed.
- Home-directory path scan over touched files: no matches.
- `scripts/phase3_tmux_agents.sh next`: blocks on the Codex reject marker.

## Next Step

Run a fresh Codex GPT-5.5 re-review against the corrected repair. If Codex
accepts, rerun the same-bound `pipeline-3 --limit 10` gate before expanding.
