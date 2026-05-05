# Phase 3 Limit-10 Repair Review - gemini_pro_3_1

Date: 2026-05-05
Reviewer: gemini_pro_3_1
Verdict: accept_with_findings
Bounded post-build runs may proceed: yes

## Findings

### Low: Adaptive split applies full retries to every subchunk

In `src/engram/extractor.py`, `extract_chunk_adaptively` propagates the top-level `retries` parameter to every recursive subchunk. With `EXTRACTION_ADAPTIVE_SPLIT_MAX_DEPTH = 4` and `retries = 1`, a consistently failing chunk (e.g., due to persistent formatting limits) will trigger an exponential number of model calls (2 + 4 + 8 + 16 + 32 = 62 calls). While local, this could severely delay error reporting and tie up the inference server.

**Proposed fix:** Pass `retries=0` to the recursive `extract_chunk_adaptively` calls, preserving retries only for the top-level chunk.

### Low: `extract_pending_claims` continues batch processing after a failure

In `src/engram/extractor.py`, `extract_pending_claims` processes a batch of candidates in a `for` loop. If an extraction fails, it increments `failed` but continues to process the remaining segments in the batch. The `break` inside `run_extract_batches` in `src/engram/cli.py` only stops *subsequent* batches. The repair successfully stops the *same* failed segment from being immediately selected again, but up to `batch_size - 1` segments will still be processed after the first failure in a batch.

**Proposed fix:** This may be acceptable operational behavior to isolate failures to the segment level. However, if the strict intent is to stop immediately upon the *first* failure to prevent inference thrashing, add `if result.status == "failed": break` inside the candidate loop in `extract_pending_claims`.

## Non-Findings

- **Correctness of bounded/adaptive Phase 3 extraction:** The chunking and adaptive fallback logic correctly scales the extraction window and handles the recursive merging of generated claims.
- **Provenance and duplicate claims:** Claims extract cleanly per subchunk and are successfully grouped. Evidence message IDs are correctly constrained to the specific subchunk bounds.
- **Retry behavior:** Retries are appropriately limited, and `run_extract_batches` successfully breaks out of the loop after a batch reports a failure.
- **Auditability and poison prevention:** Failed derived extraction rows are retained as audit history (`status='failed'`). The `consolidator` correctly skips conversations with failed extractions, preventing downstream poisoning.
- **Marker precedence:** `scripts/phase3_tmux_agents.sh` successfully parses the `supersedes:` front matter value and filters out the legacy blocked marker `03_LIMIT10_RUN.blocked.md`.
- **RFC 0013 compliance:** No raw corpus content was found in the generated artifacts. The tracked repair report and markers use only IDs, counts, error classes, and status values.

## Checks Run

- `pytest tests/test_phase3_claims_beliefs.py`
- Checked diff of pending limit-10 repair code changes.
- Checked `scripts/phase3_tmux_agents.sh` for `supersedes:` string matching and precedence rules.
- Reviewed `docs/reviews/phase3/PHASE_3_POSTBUILD_LIMIT10_REPAIR_2026_05_05.md` for redaction compliance.
- Reviewed `05_REPAIR_VERIFIED.ready.md` front-matter structure.

## Files Read

- `docs/process/phase-3-agent-runbook.md`
- `docs/process/multi-agent-review-loop.md`
- `docs/rfcs/0013-development-operational-issue-loop.md`
- `docs/rfcs/0014-operational-artifact-home.md`
- `docs/reviews/phase3/PHASE_3_POSTBUILD_RUN_LIMIT10_2026_05_05.md`
- `docs/reviews/phase3/PHASE_3_POSTBUILD_LIMIT10_REPAIR_2026_05_05.md`
- `docs/reviews/phase3/postbuild/markers/20260505_limit10_runtime_repair/05_REPAIR_VERIFIED.ready.md`
- `src/engram/extractor.py`
- `src/engram/cli.py`
- `scripts/phase3_tmux_agents.sh`
- `tests/test_phase3_claims_beliefs.py`