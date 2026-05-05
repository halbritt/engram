# Phase 3 Limit-10 Repair Review - codex_gpt5_5

Date: 2026-05-05
Reviewer: codex_gpt5_5
Verdict: reject_for_revision
Bounded post-build runs may proceed: no

## Findings

### High: Failed extraction batches can still continue and reselect in the same command

The D063 contract says `run_extract_batches` stops after a failed batch, and the repair report repeats that claim in `docs/reviews/phase3/PHASE_3_POSTBUILD_LIMIT10_REPAIR_2026_05_05.md:44`. The current loop in `src/engram/cli.py:763` through `src/engram/cli.py:785` accumulates `result.failed` but only breaks when the batch is empty or shorter than `batch_limit`. If a failed batch is full, the loop keeps going. Because `src/engram/extractor.py:1330` through `src/engram/extractor.py:1337` only excludes `extracting` and `extracted` rows, the failed segment remains eligible until the progress error count reaches its cap.

I reproduced this without model or database work by faking `extract_pending_claims`: with `batch_size=1`, `limit=3`, and each fake batch returning `processed=1, failed=1`, `run_extract_batches` made three extraction calls and returned three failures. The existing focused test at `tests/test_phase3_claims_beliefs.py:1360` through `tests/test_phase3_claims_beliefs.py:1389` misses the bug because it uses `batch_size=10`, so the loop exits for the unrelated short-batch condition.

Proposed fix: after committing a batch result, break immediately when `result.failed > 0`. Add a regression test with `batch_size=1` or any full failed batch, and assert only one `extract_pending_claims` call occurs. Then rerun the same-bound gate before allowing expansion.

### Medium: Chunk-level provenance is not enforced after relaxed-schema fallback

Strict chunk calls pass the chunk's own `allowed_message_ids` into the local extractor at `src/engram/extractor.py:748` through `src/engram/extractor.py:756`, and normal chunking removes the segment summary before building chunk prompts at `src/engram/extractor.py:1159` through `src/engram/extractor.py:1171`. That is the right default shape.

The gap is the fallback path. `call_extractor_with_retries` can switch to relaxed schema after a schema-construction failure at `src/engram/extractor.py:624` through `src/engram/extractor.py:648`. After chunk outputs are merged at `src/engram/extractor.py:679` through `src/engram/extractor.py:731`, `extract_claims_from_segment` validates all claims against the whole segment at `src/engram/extractor.py:491`, and `validate_claim_draft` only checks that evidence IDs are a subset of the original segment IDs at `src/engram/extractor.py:927` through `src/engram/extractor.py:938`. A relaxed-schema chunk result can therefore cite another message from the same segment, even though that message was not present in that chunk request.

Proposed fix: validate or salvage each chunk against that chunk's own message IDs before merging, or carry chunk provenance with each draft and validate against the recorded chunk. Add a test where relaxed-schema fallback on a chunk returns a claim citing a different chunk's message ID; the claim should be dropped or the extraction should fail.

### Medium: Marker supersession is path-only, not RFC 0013 precedence

RFC 0013 requires marker state to be computed by `issue_id` and `family`, and a newer ready marker may resolve an older blocked marker only when it shares that identity and explicitly names the older marker in `supersedes` (`docs/rfcs/0013-development-operational-issue-loop.md:194` through `docs/rfcs/0013-development-operational-issue-loop.md:198`). The script currently gathers every ready marker's `supersedes` value at `scripts/phase3_tmux_agents.sh:86` through `scripts/phase3_tmux_agents.sh:95` and suppresses a blocked marker by path equality alone at `scripts/phase3_tmux_agents.sh:98` through `scripts/phase3_tmux_agents.sh:105`.

That means an unrelated ready marker can unblock a blocked marker if it names the path, with no check for `issue_id`, `family`, `state`, `gate`, or marker ordering. `scripts/phase3_tmux_agents.sh next` currently returns `complete`, so the automation is being trusted for expansion even though it does not implement RFC 0013's precedence rule.

Proposed fix: parse `issue_id`, `family`, `state`, `gate`, and `created_at` from both markers; require same `issue_id` and compatible family before suppressing a blocker; and make newer `blocked` or `human_checkpoint` markers win over older ready markers. Add script-level tests or a fixture-driven shell check for unrelated supersedes, same-loop supersedes, and newer-blocked-after-ready cases.

## Non-Findings

Failed and superseded extraction rows are retained as audit history rather than deleted. The schema allows `failed` and `superseded` statuses on `claim_extractions`, has an active unique index only for `extracting` and `extracted`, and blocks deletion or identity-changing updates in `migrations/006_claims_beliefs.sql:104` through `migrations/006_claims_beliefs.sql:128` and `migrations/006_claims_beliefs.sql:297` through `migrations/006_claims_beliefs.sql:328`.

Old extraction rows are not in the active claim set used by consolidation. `src/engram/consolidator/__init__.py:335` through `src/engram/consolidator/__init__.py:371` selects only the latest `status = 'extracted'` row per active segment, and Decision Rule 0 rejects or recomputes active beliefs whose claim IDs leave that active set at `src/engram/consolidator/__init__.py:403` through `src/engram/consolidator/__init__.py:438`.

The repair and run reports are redacted in the dimensions I checked. I did not find raw message text, segment text, prompt payloads, model completion payloads, claim values, belief values, exact titles, or machine-specific absolute paths in the reviewed artifacts.

I did not inspect raw private corpus content, database rows, model prompts, or model completions. I did not run `pipeline-3`, `extract`, or `consolidate`.

## Checks Run

- `git status --short` before writing; the worktree was already dirty with existing Phase 3 changes and untracked artifacts.
- `bash -n scripts/phase3_tmux_agents.sh` passed.
- `git diff --check` passed.
- `scripts/phase3_tmux_agents.sh next` exited 0 and printed `complete`.
- `pytest -q tests/test_phase3_claims_beliefs.py::test_run_extract_batches_stops_after_failed_batch` failed because `pytest` is not on `PATH`.
- `.venv/bin/python -m pytest -q tests/test_phase3_claims_beliefs.py::test_run_extract_batches_stops_after_failed_batch` passed.
- Ad hoc in-memory fake for `run_extract_batches(batch_size=1, limit=3, health_smoke=False)` showed three extraction calls after repeated full-batch failures.

## Files Read

- `AGENTS.md`
- `README.md`
- `HUMAN_REQUIREMENTS.md`
- `DECISION_LOG.md`
- `BUILD_PHASES.md`
- `ROADMAP.md`
- `SPEC.md`
- `docs/schema/README.md`
- `docs/process/multi-agent-review-loop.md`
- `docs/process/project-judgment.md`
- `docs/process/phase-3-agent-runbook.md`
- `docs/rfcs/0013-development-operational-issue-loop.md`
- `docs/rfcs/0014-operational-artifact-home.md`
- `docs/reviews/phase3/PHASE_3_POSTBUILD_RUN_LIMIT10_2026_05_05.md`
- `docs/reviews/phase3/PHASE_3_POSTBUILD_LIMIT10_REPAIR_2026_05_05.md`
- `docs/reviews/phase3/postbuild/markers/03_LIMIT10_RUN.blocked.md`
- `docs/reviews/phase3/postbuild/markers/20260505_limit10_runtime_repair/05_REPAIR_VERIFIED.ready.md`
- `src/engram/extractor.py`
- `src/engram/cli.py`
- `src/engram/consolidator/__init__.py`
- `scripts/phase3_tmux_agents.sh`
- `tests/test_phase3_claims_beliefs.py`
- `migrations/006_claims_beliefs.sql`
