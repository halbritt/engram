# Phase 3 Limit-10 Repair Review - claude_opus_4_7

Date: 2026-05-05
Reviewer: claude_opus_4_7
Verdict: accept_with_findings
Bounded post-build runs may proceed: only after findings addressed

The D063 / limit-10 repair correctly addresses the orchestration bug (D061),
introduces a defensible bounded/adaptive extraction path, preserves immutable
raw evidence, and produces a clean same-bound rerun with proof queries showing
zero orphan claim IDs across the first ten conversations. The repair is
substantively sound and the next `--limit 10` rerun is safe.

However, three findings should be addressed before expansion to the next
bound (`--limit 50`):

1. The repair report's claim that `run_extract_batches` "stops after a failed
   batch" is not implemented in code as written; the behavior is incidental and
   the regression test does not exercise the asserted invariant.
2. The same-bound rerun report omits the dropped-claim count, so the RFC 0013
   §9 expansion gate ("dropped-claim rate above 10%") cannot be verified from
   the tracked artifact.
3. The per-loop marker directory has a verified ready marker without the
   intervening `02_REPAIR_PLAN`, `03_REVIEW_<model_slug>`, or `04_SYNTHESIS`
   markers required by RFC 0013 §4 ordering and §6 multi-agent review.

None of these undermine the same-bound result; they constrain expansion.

## Findings

### Major: `run_extract_batches` does not explicitly stop after a failed batch

`PHASE_3_POSTBUILD_LIMIT10_REPAIR_2026_05_05.md` and D063 both assert that
`run_extract_batches` was changed to "stop after a failed batch so the same
failed segment is not immediately selected again in the same command." The
actual loop in `src/engram/cli.py:745-785` has only the natural exit condition
`if result.processed == 0 or result.processed < batch_limit: break`. The
parallel `run_segment_batches` at `src/engram/cli.py:708-709` does have the
explicit `if result.failed: break`, but no equivalent guard was added to the
extract path.

In the limit-10 scenario the natural exit fires only because each conversation
yields fewer pending segments than `extract-batch-size` once the failing
segment is recorded as `failed`. `fetch_pending_segments` in
`src/engram/extractor.py:1308-1350` excludes only segments whose latest
extraction is `extracting` or `extracted`, so a `failed` segment remains
selectable until the conversation's progress `error_count` reaches
`MAX_EXTRACTION_ERROR_COUNT = 3`. With `pipeline-3` calling
`run_extract_batches` per conversation with `limit=None`, a conversation with
many active segments could re-run the same failed segment up to three times
inside one command.

The regression test `test_run_extract_batches_stops_after_failed_batch` in
`tests/test_phase3_claims_beliefs.py:1360-1390` uses `batch_size=10` with a
fake that returns `processed=1, failed=1`. The assertion that
`extract_pending` is called exactly once is satisfied by the unrelated
`processed (1) < batch_limit (10)` exit, not by any failure-driven break. The
test would still pass if the failure-related logic were absent entirely.

Proposed fix: add `if result.failed: break` to `run_extract_batches` after the
totals update, mirroring `run_segment_batches`. Tighten the test to use a
configuration where `processed == batch_limit` so the failed-batch break is
the only mechanism that ends the loop (e.g., `batch_size=1, limit=2` with two
fake results and assert only one is consumed).

### Major: same-bound rerun report omits dropped-claim rate

RFC 0013 §9 lists "dropped-claim rate is above 10% of inserted plus dropped
claims" as a default blocker for `ready_for_next_bound`. The original
`PHASE_3_POSTBUILD_RUN_LIMIT10_2026_05_05.md` reported 22 dropped claims and
118 inserted, a 15.7% dropped rate. The repair `Same-Bound Rerun` section in
`PHASE_3_POSTBUILD_LIMIT10_REPAIR_2026_05_05.md` records only `43 claims
created / 10 segments processed / 0 failed` and omits the dropped count.
Without it, no reader of the tracked artifact can confirm the 10% gate is now
met.

Proposed fix: extend the same-bound rerun report to include
`SUM(jsonb_array_length(raw_payload->'dropped_claims'))` over the rerun's
`claim_extractions` rows, and a computed dropped-rate. If the rate is still
above 10%, the gate stays at `ready_for_same_bound_rerun`, not
`ready_for_next_bound`, and the repair report should say so.

### Major: RFC 0013 §4 / §6 review ordering not represented in the per-loop marker directory

`docs/reviews/phase3/postbuild/markers/20260505_limit10_runtime_repair/`
contains only `05_REPAIR_VERIFIED.ready.md`. RFC 0013 §4 requires the loop to
write artifacts in the order `01_RUN`, `02_REPAIR_PLAN`, `03_REVIEW`,
`04_SYNTHESIS`, `05_REPAIR_VERIFIED`, and §6 requires the multi-agent review
loop for non-trivial changes including those that affect derived-state repair
behavior or let downstream stages proceed past upstream failure. The current
state declares `repair_verified` before any tracked review marker for this
loop has been written, including the present P035 review.

The legacy `03_LIMIT10_RUN.blocked.md` is correctly preserved as audit
provenance and is correctly named in the new marker's `supersedes:` field, so
the script-level supersession works. The structural concern is that the
marker chain implies "verification preceded review."

Proposed fix: keep the `05_REPAIR_VERIFIED.ready.md` file as-is (per the
"do not delete markers" rule), but add the missing intervening markers in
this loop's directory once each artifact lands (this review and any sibling
reviews, plus a synthesis). Until then, the repair-loop marker chain should
be treated as in-progress, not closed.

### Minor: chunked extraction can split a single message by character offset, fragmenting context

`src/engram/extractor.py:1174-1196` `split_extraction_chunk` falls back to
splitting a single message at `len(content) // 2` when no further
message-level split is possible. Both halves keep the same `message.id`, so
provenance is not falsified — the schema enum constrains
`evidence_message_ids` correctly, and the salvage check at
`src/engram/extractor.py:937-938` confirms the cited IDs are a subset of the
original segment. However, the model sees only half of the message text in
each sub-chunk and the split is by raw character index, which can land
mid-token, mid-sentence, or mid-code-fence. Claims extracted from such halves
may be partial or context-stripped, and the consolidator has no way to know
the chunk boundary distorted the evidence.

Severity is minor because:

- max recursion depth is 4, so most failures recover at the message-level
  split before hitting content split;
- the `multi_current` belief group and `subject_normalized + predicate +
  group_object_key` index dedupe identical claims across halves;
- the affected segment's repair run (`extract --requeue ... --batch-size 1`)
  succeeded with 63 claims and the proof query was clean.

Proposed fix or watch item: emit a structured warning in
`claim_extractions.raw_payload.parse_metadata.chunks` when `split_depth >= 2`
or when content-only split is reached, and surface a count in the same-bound
rerun report. This gives the next reviewer a signal that "claims from this
extraction were derived from sub-message text fragments." No change to
provenance is required; the affected claim count just needs to be visible.

### Minor: tmux script supersession is path-string only, not (issue_id, family)

`scripts/phase3_tmux_agents.sh:71-106` reads the `supersedes:` front-matter
value and compares the path string of each blocked marker against the value.
RFC 0013 §5 specifies that "a newer ready marker resolves an older blocked
marker only when it shares the same `issue_id` and `family` and explicitly
names the older marker in `supersedes`." The script does not check
`issue_id` or `family`. In this loop the legacy `03_LIMIT10_RUN.blocked.md`
has no front matter at all, so `issue_id`/`family` cannot be checked anyway.

For now the path-string match is acceptable because the supersession is
unambiguous and the legacy marker predates the front-matter requirement. The
weakness is that a future ready marker from an unrelated `issue_id` could
resolve a blocked marker by accident if the path string collides. This is
unlikely while paths embed dates and slugs, but the rule is looser than the
RFC text.

Proposed fix or watch item: when both markers have YAML front matter, also
require matching `issue_id` and `family` before treating supersession as
valid. Pure legacy paths (no front matter on the blocked side) should remain
path-string supersedeable as a transition allowance.

### Minor: cross-version belief cleanup is implicit, not asserted

The repair bumped `EXTRACTION_PROMPT_VERSION` to
`extractor.v2.d046.universal-vocab.chunked-windows` and the request profile
to `ik-llama-json-schema.d034.v4.extractor-8192-adaptive-chunked-windows`.
The first `--limit 10` run produced 118 beliefs under the previous prompt
version. After the same-bound rerun the proof query reports `active beliefs
with orphan claim IDs: 0` and `45 beliefs created / 4 superseded`. The
cleanup of the prior 118 beliefs relies on Decision Rule 0 (D049) firing
inside `consolidate_beliefs` for every conversation re-visited by
`pipeline-3`. That works for the first ten conversations, which were
re-extracted under the new prompt, so the consolidator visited each one and
rejected orphan beliefs.

The blind spot is conversations that:

- were consolidated under the old prompt,
- are not re-extracted in the next bounded run because the run window does
  not cover them,
- still contain active beliefs whose `claim_ids` point to now-superseded
  claim_extractions.

If a future run uses `pipeline-3 --limit N` where the candidate set excludes
a previously-consolidated conversation, that conversation's stale beliefs
remain active. Phase 3's
`active_beliefs_with_other_consolidator_version` warning prints to stderr
but does not block the run, and a prompt-version bump is not the same as a
consolidator-version bump.

Severity is minor for this repair because the affected scope is exactly the
ten conversations the rerun re-visited. It becomes load-bearing at
`--limit 50` and beyond.

Proposed fix or watch item: before `--limit 50`, add a one-shot proof query
that counts active beliefs whose claim_ids reference non-`extracted`
claim_extractions globally (not only in the candidate window), and either
require zero or document a quarantine plan. The query already exists in
spirit in the affected-conversation proof query; lifting it to global scope
is the work.

## Non-Findings

- Adaptive chunking provenance: chunk-level `allowed_message_ids` is enforced
  via `extraction_json_schema` (`src/engram/extractor.py:266-318`), and
  `validate_claim_draft` (`src/engram/extractor.py:927-950`) re-checks the
  citation set against the original segment's `message_ids`. False provenance
  is not reachable through chunking.
- Tool-message redaction in chunks: `chunk_segment_payload` carries the same
  `SegmentMessage` records, and `format_message_for_prompt` retains the
  D038 placeholder for `role == 'tool'`. Tool message bodies are not exposed
  to the model regardless of chunk position.
- Extraction row reuse: `extract_claims_from_segment` only reuses an existing
  extraction row when its status is `extracting`; otherwise it inserts a new
  row. This preserves audit history of failed attempts under the new prompt
  version.
- Prompt-version bump for non-destructive re-derivation: D021 / D045 are
  satisfied; the bumped prompt version causes prior rows to be superseded
  rather than mutated, and the audit trail remains in
  `claim_extractions.raw_payload.superseded_by_extraction_id`.
- Redaction in tracked artifacts: both
  `PHASE_3_POSTBUILD_RUN_LIMIT10_2026_05_05.md` and
  `PHASE_3_POSTBUILD_LIMIT10_REPAIR_2026_05_05.md` keep IDs, counts, and
  error classes only. The `corpus_content_included: none` field on the new
  marker matches the artifact body.
- Old marker preservation: `03_LIMIT10_RUN.blocked.md` and the
  `01_CHANGE_REVIEW_*` / `04_RFC0013_DRAFT.ready.md` lineage are retained.
  No history rewriting was performed.
- Path hygiene (D060): no machine-specific home-directory paths appear in
  the repair report or marker; commands use `.venv/bin/python` and
  repository-relative paths.
- Adaptive split termination: `EXTRACTION_ADAPTIVE_SPLIT_MAX_DEPTH = 4`
  bounds recursion; failed leaves still call `attach_chunk_diagnostics`
  before re-raising, so `claim_extractions.raw_payload.chunk_index /
  chunk_count / split_depth / split_path / chunk_message_count` is
  populated on terminal failure (verified by
  `test_chunked_extraction_failure_writes_chunk_diagnostics_without_claims`).
- Same-bound rerun integrity: `consolidator progress rows: 10 completed / 0
  skipped` plus the orphan-claim proof query for the first ten conversations
  shows the repair did not promote stale partial state for the rerun's
  scope.

## Checks Run

- `git status --short` to confirm working tree state before writing.
- Read of `src/engram/extractor.py` (full file) to trace
  `extract_segment_chunks`, `extract_chunk_adaptively`,
  `extraction_prompt_chunks`, `split_extraction_chunk`,
  `chunk_segment_payload`, `extraction_json_schema`, `salvage_claims`,
  `validate_claim_draft`, `fetch_pending_segments`, and
  `mark_extraction_failed`.
- Read of `src/engram/cli.py` (full file) to verify
  `run_extract_batches`, `run_segment_batches`,
  `phase3_schema_preflight`, and the `pipeline-3` per-conversation skip path.
- `Grep -n 'if result.failed' src/engram/cli.py` to confirm only
  `run_segment_batches` has the explicit failed-batch break.
- Read of `tests/test_phase3_claims_beliefs.py` (full file) to inspect
  `test_large_segment_extraction_uses_bounded_message_chunks`,
  `test_chunked_extraction_failure_writes_chunk_diagnostics_without_claims`,
  `test_adaptive_chunk_split_recovers_from_oversized_chunk_parse_error`,
  `test_pipeline3_skips_consolidation_after_extraction_failure`, and
  `test_run_extract_batches_stops_after_failed_batch`.
- Read of `scripts/phase3_tmux_agents.sh` (full file) to verify
  `marker_front_matter_value`, `superseded_operational_marker_paths`,
  `is_operational_marker_superseded`, and `blocked_operational_markers`.
- Listing of `docs/reviews/phase3/postbuild/markers/` to confirm
  per-loop directory contents and the legacy flat marker layout.
- Read of `docs/rfcs/0013-development-operational-issue-loop.md`,
  `docs/rfcs/0014-operational-artifact-home.md`, and
  `docs/process/phase-3-agent-runbook.md` to confirm gate, marker
  precedence, redaction, and review-loop expectations.
- No live database query, no `pipeline-3` / `extract` / `consolidate` run,
  no inspection of raw corpus content, no external service calls.

## Files Read

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
