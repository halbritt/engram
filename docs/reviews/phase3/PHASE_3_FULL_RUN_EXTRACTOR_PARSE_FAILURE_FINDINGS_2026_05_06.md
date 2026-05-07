<a id="review-0023"></a>
# Phase 3 Full-Run Extractor Parse Failure Findings

Review ID: REVIEW-0023
Status: findings
Date: 2026-05-06
RFC refs:
  - RFC-0013
Decision refs:
  - none
Phase refs:
  - PHASE-0003

Date: 2026-05-06
Updated: 2026-05-07

## Redaction Boundary

This findings document follows RFC 0013. It contains commands, counts, ids,
status values, and aggregate error classes only. It does not include raw
message text, segment text, prompt payloads, model completions, conversation
titles, claim values, belief values, private names, or corpus-derived prose
summaries.

## Context

After the `--limit 500` Phase 3 run completed and the consolidator null
group-key repair passed targeted retry, the unbounded Phase 3 run was
restarted.

Command:

```bash
.venv/bin/python -m engram.cli pipeline-3 --extract-batch-size 5 --consolidate-batch-size 5
```

The run was intentionally stopped after a hard extractor failure was observed.

## Failure

- Stage: `extractor`
- Scope: `conversation:54c017c3-6e55-467f-a407-8b26648aec09`
- Failed segment: `4e59a697-16e1-4110-9a7e-0906e357b802`
- Status: `failed`
- Failure kind: `parse_error`
- Last error: `extractor returned invalid JSON: Unterminated string starting at: line 685 column 20 (char 24161)`
- Elapsed time before failure: `379.4s`
- Split path: `[3, 1, 1, 1, 1]`
- Split depth: `4`
- Root chunk count: `14`
- Root chunk index: `3`
- Leaf chunk message count: `1`
- Attempts recorded for the failed leaf: `1`
- Failed model-response payload length: `27064` characters

The Phase 3 coordinator then marked the corresponding consolidator scope as
failed with `skipped after 1 extraction failure(s)`.

## Current State

After stopping the first run:

- Active AI-conversation conversations: `7777`
- Completed extractor conversation scopes: `2525`
- Completed consolidator conversation scopes: `2525`
- Remaining unconsolidated conversations: `5252`
- Failed Phase 3 progress rows: `2`
- Latest v8 extracted rows: `3642`
- Latest v8 failed extraction rows: `1`
- Latest v8 in-flight extraction rows: `0`

## Deferred-Resume Failure

The full-corpus run was resumed with the original failed conversation deferred
so the rest of the corpus could continue. During that deferred resume, a second
extractor failure was observed and the supervisor continued past it.

- Stage: `extractor`
- Scope: `conversation:82dbc95d-76a4-4972-82d9-47477fa066b0`
- Failed segment: `e9aaa914-1831-410b-a248-b4a2162d78e5`
- Status: `failed`
- Failure kind: `parse_error`
- Last error: `all extracted claims failed pre-validation`
- Validation-repair error: `extractor returned invalid JSON: Expecting property name enclosed in double quotes: line 840 column 9 (char 22195)`
- Elapsed time before failure: `100.9s`
- Chunked: `false`
- Chunk count: `1`
- Split path: `[1]`
- Chunk message count: `2`
- Dropped claims before repair: `48`
- Dropped claims after repair: `0`
- Failed model-response payload length: `16093` characters

The Phase 3 resume supervisor marked the corresponding consolidator scope as
failed with `skipped after 1 extraction failure(s)` and continued processing
subsequent conversations.

## Additional Deferred-Resume Failure

During the same deferred full-corpus pass, a third extractor failure was
observed after a long generation. The supervisor again marked only that
conversation's consolidator scope failed and continued processing subsequent
conversations.

- Stage: `extractor`
- Scope: `conversation:8d7a5f1f-38e8-4611-abf1-2ebdb020c6af`
- Failed segment: `66b55936-c5b5-4df4-8eab-4dc383fad63f`
- Failed extraction row: `f8eb8b72-30b6-4471-a305-9d614c93e103`
- Status: `failed`
- Failure kind: `parse_error`
- Last error: `extractor returned invalid JSON: Unterminated string starting at: line 667 column 7 (char 26664)`
- Elapsed time before failure: `589.1s`
- Split path: `[1, 2, 1, 2, 2]`
- Split depth: `4`
- Root chunk count: `1`
- Root chunk index: `1`
- Leaf chunk message count: `1`
- Attempts recorded for the failed leaf: `1`
- Attempt max tokens: `[8192]`
- Dropped claims recorded before failure: `0`
- Failed model-response payload length: `29594` characters

## Fourth Deferred-Resume Failure

During the same deferred full-corpus pass, a fourth extractor failure was
observed. The supervisor marked only that conversation's consolidator scope
failed and continued processing subsequent conversations.

- Stage: `extractor`
- Scope: `conversation:ba53064d-53f3-44a7-8998-e38eead0b260`
- Failed segment: `6da61ec8-35b3-45a6-b4e8-1117edfe630c`
- Failed extraction row: `22339403-4d25-428f-977c-5d601796f7da`
- Status: `failed`
- Failure kind: `parse_error`
- Last error: `all extracted claims failed pre-validation`
- Validation-repair error: `extractor returned invalid JSON: Unterminated string starting at: line 796 column 7 (char 22798)`
- Elapsed time before failure: `106.8s`
- Chunked: `false`
- Chunk count: `1`
- Dropped claims before repair: `54`
- Dropped claims after repair: `0`
- Dropped-claim error class: `exactly one of object_text or object_json is required`
- Failed model-response payload length: `18172` characters

## Fifth Deferred-Resume Failure

During the same deferred full-corpus pass, a fifth extractor failure was
observed after a long generation. The supervisor marked only that
conversation's consolidator scope failed and continued processing subsequent
conversations.

- Stage: `extractor`
- Scope: `conversation:d01adc57-3353-4ac9-8c49-5ddef6876492`
- Failed segment: `f2c48148-8e7e-44bb-9681-1bea5189353f`
- Failed extraction row: `d1b3bf23-ce26-4ece-9b26-205c82531bd6`
- Status: `failed`
- Failure kind: `parse_error`
- Last error: `extractor returned invalid JSON: Unterminated string starting at: line 790 column 7 (char 21980)`
- Elapsed time before failure: `353.2s`
- Split path: `[1, 1, 2, 2, 1]`
- Split depth: `4`
- Root chunk count: `1`
- Root chunk index: `1`
- Leaf chunk message count: `1`
- Attempts recorded for the failed leaf: `1`
- Attempt max tokens: `[8192]`
- Dropped claims recorded before failure: `0`
- Failed model-response payload length: `25183` characters

## Findings

### F1 - Blocker: full-corpus expansion hit an extractor prompt/model contract failure

The local extractor returned malformed JSON for one adaptive leaf chunk after a
long generation. The malformed response failed before Python could parse,
salvage, or validate any claims from that leaf.

Impact:

- the selected conversation has one failed extraction row;
- consolidation for that conversation was correctly skipped;
- the full-corpus run cannot be treated as complete;
- the next full-corpus run must resume only after targeted repair or accepted
  operator handling of the failed scope.

### F2 - Major: the failed scope remains retryable under current progress semantics

The code can reattempt this conversation: failed `claim_extractions` rows do
not block a new extraction row, and the failed conversation has
`error_count=1` under the cap of `3`. The likely operational repair is a
targeted rerun of that conversation, possibly with a deeper adaptive split
budget if the same chunk fails again.

### F3 - Major: the failure exhausted adaptive split depth on a one-message leaf

The failed leaf reached the current adaptive split max depth of `4`.
Diagnostics show the failure occurred on a one-message leaf under root chunk
`3` of `14`. This means normal message-count subdivision had already bottomed
out. A targeted rerun may succeed transiently, but a repeat failure would point
to either:

- increasing the adaptive split depth for pathological long model responses;
- reducing extraction chunk size defaults; or
- adding a more specific malformed-response retry path before declaring the
  conversation blocked.

### F4 - Major: a second deferred scope failed because validation repair produced malformed JSON

The second failure has a different shape from F1. The extractor produced claims,
but all `48` were dropped by pre-validation because each violated the same
object payload invariant: exactly one of `object_text` or `object_json` is
required. The validation-repair pass then attempted recovery, but returned
malformed JSON instead of a valid repaired claim set.

Impact:

- this is not an adaptive split-depth exhaustion case;
- the failed scope remains suitable for targeted rerun after the corpus pass;
- if the same shape repeats, the repair should focus on validation-repair
  output constraints or on treating all-dropped claim sets as a bounded
  zero-claim extraction rather than a corpus-blocking failure.

### F5 - Major: a third deferred scope repeated the long-generation parse failure shape

The third deferred failure is closer to F1 than F4. It failed with malformed
JSON after a long generation on a one-message adaptive leaf at split depth `4`.
No dropped-claim validation set was recorded before the parse failure.

Impact:

- this adds a third targeted rerun candidate after the main corpus pass;
- the repeated shape strengthens the case for a narrow extractor repair if the
  targeted rerun fails again;
- likely repair candidates are deeper adaptive split budget for pathological
  leaves, more constrained retry on unterminated JSON, or both.

### F6 - Major: validation-repair failure has now repeated

The fourth deferred failure repeats the F4 shape. The extractor produced claims,
but all `54` were dropped by pre-validation because each violated the same
object payload invariant: exactly one of `object_text` or `object_json` is
required. The validation-repair pass then attempted recovery, but returned
malformed JSON instead of a valid repaired claim set.

Impact:

- this is a repeated repair-path failure mode, not a one-off isolated miss;
- the failed scope remains suitable for targeted rerun after the corpus pass;
- if either validation-repair-shaped failure repeats during targeted rerun,
  the next repair should focus on enforcing the `object_text`/`object_json`
  invariant before repair output is accepted, or on treating an all-dropped
  repair miss as a bounded zero-claim extraction when that is semantically
  safer than blocking the corpus.

### F7 - Major: long-generation parse failure has now repeated across three deferred scopes

The fifth deferred failure repeats the F1/F5 shape. It failed with malformed
JSON after a long generation on a one-message adaptive leaf at split depth `4`.
No dropped-claim validation set was recorded before the parse failure.

Impact:

- this adds a fifth targeted rerun candidate after the main corpus pass;
- the repeated shape makes a transient retry less certain than it was after the
  first occurrence;
- if any of the long-generation parse failures repeat during targeted rerun,
  the next repair should focus on deeper adaptive split budget for pathological
  leaves, a constrained malformed-JSON retry path, or both.

## Recommended Next Step

Allow the deferred full-corpus pass to complete, then run targeted retries for:

- `conversation:54c017c3-6e55-467f-a407-8b26648aec09`
- `conversation:82dbc95d-76a4-4972-82d9-47477fa066b0`
- `conversation:8d7a5f1f-38e8-4611-abf1-2ebdb020c6af`
- `conversation:ba53064d-53f3-44a7-8998-e38eead0b260`
- `conversation:d01adc57-3353-4ac9-8c49-5ddef6876492`

If any targeted retry repeats the same failure shape, stop and specify a
narrow extractor repair for that shape before treating the corpus run as
complete.

## Targeted Rerun Outcome

Update: `2026-05-07`.

The deferred full-corpus pass completed with five deferred extractor scopes.
Normal targeted retries were then run for all five conversations. All five
normal retries repeated their prior failure classes.

A second bounded targeted repair was run only for the three long-generation
parse-failure scopes, using a deeper adaptive split budget and a higher retry
budget:

```bash
ENGRAM_EXTRACTOR_ADAPTIVE_SPLIT_MAX_DEPTH=6 ENGRAM_EXTRACTOR_RETRIES=3 \
.venv/bin/python -m engram.cli extract --conversation-id <conversation_id> --batch-size 5
```

Outcome:

- `conversation:54c017c3-6e55-467f-a407-8b26648aec09` succeeded: `769`
  claims created across `27` segments; consolidation created `737` beliefs,
  superseded `136`, and recorded `31` contradictions.
- `conversation:8d7a5f1f-38e8-4611-abf1-2ebdb020c6af` succeeded: `119`
  claims created across `2` segments; consolidation created `118` beliefs,
  superseded `3`, and recorded `3` contradictions.
- `conversation:d01adc57-3353-4ac9-8c49-5ddef6876492` succeeded: `9`
  claims created across `4` segments; consolidation created `9` beliefs,
  superseded `1`, and recorded `0` contradictions.

The two validation-repair-shaped failures remained deferred:

- `conversation:82dbc95d-76a4-4972-82d9-47477fa066b0`
- `conversation:ba53064d-53f3-44a7-8998-e38eead0b260`

Final progress state after targeted reruns:

- Completed extractor conversation scopes: `7775`
- Failed extractor conversation scopes: `2`
- Completed consolidator conversation scopes: `7775`
- Failed consolidator conversation scopes: `2`

Next repair should focus on the repeated validation-repair failure shape rather
than further split-depth tuning.
