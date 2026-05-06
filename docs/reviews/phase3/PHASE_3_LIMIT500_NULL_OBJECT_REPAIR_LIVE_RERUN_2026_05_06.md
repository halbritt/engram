# Phase 3 Limit-500 Null-Object Repair Live Rerun

Date: 2026-05-06

Related repair:

- `docs/reviews/phase3/PHASE_3_LIMIT500_NULL_OBJECT_REPAIR_SPEC_2026_05_06.md`
- `docs/reviews/phase3/PHASE_3_LIMIT500_NULL_OBJECT_REPAIR_REVIEW_claude_opus_4_7_2026_05_06.md`
- `docs/reviews/phase3/PHASE_3_LIMIT500_NULL_OBJECT_REPAIR_REVIEW_SYNTHESIS_2026_05_06.md`

Related blocker:

- `docs/reviews/phase3/postbuild/markers/20260506_limit500_run/01_RUN.blocked.md`

## Redaction Boundary

This report follows RFC 0013. It contains commands, counts, ids, status values,
predicate names, object-shape diagnostics, and aggregate error classes only.
It does not include raw message text, segment text, prompt payloads, model
completions, conversation titles, claim values, belief values, private names,
or corpus-derived prose summaries.

## Verdict

`blocked_for_expansion`

The null-object repair fixed the previously failed selected-scope segment, but
the same-bound `pipeline-3 --limit 500` rerun hit a new schema-level extractor
failure class early in the run. The run was stopped by the coordinator after
the gate had already failed.

The pinned ready marker
`docs/reviews/phase3/postbuild/markers/20260506_limit500_run/05_REPAIR_VERIFIED.ready.md`
was not written.

## Runtime Context

The local model server was already running with `--ubatch-size 512`:

- model server process included `--ubatch-size 512`
- host: `127.0.0.1`
- port: `8081`
- no cloud or hosted model API was used

## Commands Run

Push repair commit:

```bash
git push origin master
```

No-work gate:

```bash
.venv/bin/python -m engram.cli pipeline-3 --limit 0
```

Targeted failed-scope extraction:

```bash
.venv/bin/python -m engram.cli extract \
  --requeue \
  --conversation-id 0488c023-1b5a-44b6-8a8d-454283fb3b07 \
  --batch-size 5
```

Targeted failed-scope consolidation:

```bash
.venv/bin/python -m engram.cli consolidate \
  --conversation-id 0488c023-1b5a-44b6-8a8d-454283fb3b07 \
  --batch-size 1 \
  --limit 1
```

Same-bound rerun:

```bash
.venv/bin/python -m engram.cli pipeline-3 \
  --extract-batch-size 5 \
  --consolidate-batch-size 5 \
  --limit 500
```

The same-bound rerun was stopped after two extractor failures were observed.

## Step Results

### Step 1 - Push

Result: passed.

Repair commit pushed:

- `0ae061c Repair Phase 3 null-object extraction`

### Step 2 - No-Work Gate

Result: passed.

Output:

- extract: 0 claims created / 0 segments processed / 0 failed
- consolidate: 0 conversations processed / 0 skipped / 0 beliefs created /
  0 superseded / 0 contradictions

### Step 3 - Targeted Failed Scope

Result: passed.

Targeted segment:

- `7bf2896a-00ab-4f75-a0ed-1ae684a2b4e9`

Targeted conversation:

- `0488c023-1b5a-44b6-8a8d-454283fb3b07`

Extraction result:

- 1 segment processed
- 0 claims created
- 0 failed
- latest v6 status: `extracted`
- latest v6 claim count: 0

Consolidation result:

- 1 group processed
- 0 beliefs created
- 0 superseded
- 0 contradictions

### Step 4 - Same-Bound Limit-500 Gate

Result: blocked.

Pre-run selected-scope boundary:

- selected conversations: 500
- first selected conversation id:
  `0014d635-f280-4e68-a762-6a8e5b5920ef`
- last selected conversation id:
  `1140b58f-ff3b-4bde-8df2-7a6c1a949360`
- active segments in selected scope: 723

Latest v6 selected-scope status after coordinator stop:

- latest v6 rows: 6
- latest v6 extracted: 4
- latest v6 failed: 2
- missing latest v6 extractions: 717
- latest v6 claim count: 0
- latest v6 final dropped claims: 0
- latest v6 validation-repair prior drops: 0
- active beliefs with orphan claim ids: 0
- in-flight claim extractions after stop: 0

Failed v6 extraction rows:

- segment `012134de-6554-4241-be24-0e3c64d5b1e5`
  - conversation `0030fb7d-d9a2-48e2-9a70-c19281cbb520`
  - status: `failed`
  - failure kind: `retry_exhausted`
  - last error: `claim 0 does not match the schema`
  - attempts: 1
  - attempt max tokens: 8192
  - dropped claims: 0
  - validation-repair prior drops: 0
  - model response stored as JSON null
  - source kind: `chatgpt`
  - segment sequence index: 0
  - message count: 7
  - summary length: 393
  - content length: 6657
  - privacy tier: 1
- segment `19ba6674-6166-456a-b740-52175a8a4ba5`
  - conversation `00394f4c-0794-4807-9853-b3117385e82e`
  - status: `failed`
  - failure kind: `retry_exhausted`
  - last error: `claim 0 does not match the schema`
  - attempts: 1
  - attempt max tokens: 8192
  - dropped claims: 0
  - validation-repair prior drops: 0
  - model response stored as JSON null
  - source kind: `gemini`
  - segment sequence index: 0
  - message count: 2
  - summary length: 78
  - content length: 57
  - privacy tier: 1

Failed progress rows after coordinator stop:

- extractor `conversation:0030fb7d-d9a2-48e2-9a70-c19281cbb520`
  - error count: 1
  - last error: `claim 0 does not match the schema`
- consolidator `conversation:0030fb7d-d9a2-48e2-9a70-c19281cbb520`
  - error count: 1
  - last error: `skipped after 1 extraction failure(s)`
- extractor `conversation:00394f4c-0794-4807-9853-b3117385e82e`
  - error count: 1
  - last error: `claim 0 does not match the schema`

The gate failed because latest selected-scope extraction failures are nonzero,
latest selected-scope extractions are missing, and failed progress rows are
present.

## Throughput Note

The previous interrupted limit-500 run processed about 594 extraction rows in
roughly 115 minutes, about 5.2 segments/minute end-to-end.

This repair-verification run is not a useful speed benchmark:

- targeted extraction and same-bound extraction were mixed in the same v6
  provenance window;
- the same-bound gate failed after only a handful of segments;
- the two schema-level failures dominated wall time.

Observed current rates:

- v6 rows including the targeted rerun: 6 rows over 268.5 seconds, about
  1.3 rows/minute
- same-bound-only visible rows: 5 rows over roughly 123 seconds, about
  2.4 rows/minute

No conclusion should be drawn about the `--ubatch-size 512` throughput benefit
from this failed early sample.

## Current Assessment

The original null-object failure class is repaired for the known failed
segment. The new blocker is a stricter-schema interaction:

- the model/backend returned an output rejected at schema validation;
- the error is `claim 0 does not match the schema`;
- no model response payload was retained beyond JSON null;
- Python salvage and validation repair did not run because parsing failed
  before claim drafts existed.

This is still a prompt/schema/model contract problem, but it is a different
failure class from the original null/null object-channel sweep.

## Required Next Step

Investigate the strict `oneOf` schema rejection path before another same-bound
rerun. Likely next questions:

- Which claim-field shape violates the strict schema?
- Does the local backend expose enough validation detail to identify the field
  without storing raw model output?
- Should parse/schema failures get a bounded redacted retry similar to
  validation repair?
- Should exact-one enforcement move back out of the model-facing schema if the
  backend rejects common recoverable output shapes too aggressively?

Full-corpus Phase 3 remains blocked by:

`docs/reviews/phase3/postbuild/markers/20260506_limit500_run/01_RUN.blocked.md`
