# Phase 3 Post-Build Runtime Slice: Limit 10

Date: 2026-05-05

Command:

```bash
.venv/bin/python -m engram.cli pipeline-3 --extract-batch-size 5 --consolidate-batch-size 5 --limit 10
```

## Verdict

`blocked_for_expansion`

The bounded slice exercised the live local corpus and found a real runtime
issue. Do not expand to a larger Phase 3 run until the failed large-segment
extraction path is addressed or explicitly accepted for further testing.

This report has been redacted under RFC 0013 review findings. It keeps IDs,
counts, error classes, and schema-level diagnostics, but removes corpus-derived
summaries and extracted belief values from the tracked artifact.

## Baseline Counts

Before the run:

- `claim_extractions`: 1
- `claims`: 3
- `beliefs`: 3
- `belief_audit`: 3
- `contradictions`: 0
- failed extractions: 0

After the run:

- `claim_extractions`: 18
- `claims`: 121
- `beliefs`: 118
- `belief_audit`: 119
- `contradictions`: 1
- failed extractions: 1

## Runtime Summary

The command exited with code `1`.

CLI summary:

- extract: 118 claims created / 17 segments processed / 1 failed
- consolidate: 10 conversations processed / 115 beliefs created / 1 superseded
  / 1 contradiction

The failure was not a migration/preflight failure. It was one large segment that
returned invalid JSON after two extractor attempts:

- conversation: `003a1e2c-3a8b-4550-b695-f88d0377c576`
- segment: `83e4fd32-6474-42fb-b4b9-3bc7b4956ad9`
- segment size: 33 messages, 10,952 content characters
- segment summary: redacted private corpus-derived summary
- failure kind: `parse_error`
- last error: extractor returned invalid JSON, expecting a comma at line 723,
  column 26
- attempt max tokens: `[8192, 8192]`

## Diagnostics

Dropped claims across successful/failed extraction rows: 22.

Dropped-claim reasons:

- `predicate requires object_json`: 8
- `exactly one of object_text or object_json is required`: 5
- `object_json missing required key: name`: 3
- `object_json missing required key: action`: 2
- `object_json missing required key: project`: 2
- `object_json missing required key: species`: 1
- `predicate requires non-empty object_text`: 1

One contradiction was auto-resolved. Corpus-derived subject and values are
redacted from this tracked report.

- detection kind: `same_subject_predicate`
- resolution status: `auto_resolved`

## Runtime Finding And Repair

The slice exposed an orchestration bug: `pipeline-3` consolidated a conversation
even when one of that conversation's segment extractions failed. That risks
promoting partial-evidence beliefs before all active segments in the selected
conversation have extractable claims.

Repair applied after this run:

- `pipeline-3` now skips consolidation for a conversation when its extraction
  batch reports any failures.
- The skip path records a failed `consolidator` progress row for the affected
  conversation instead of leaving a stale completed state.
- Added a regression test for this behavior.

Verification after the repair:

- Focused migration and Phase 3 tests: `28 passed`.
- Full test suite: `108 passed`.
- Live Phase 3 schema preflight: passed.
- `pipeline-3 --limit 0`: passed with no work and reported `0 skipped`.

The live progress ledger was updated for the affected conversation:

- stage: `consolidator`
- status: `failed`
- error count: 1
- last error: `post-build limit10: partial consolidation quarantined after
  extraction failure`

## Data Note

The run wrote derived Phase 3 rows only. Raw evidence was not mutated. The
partial derived beliefs from the affected conversation remain visible in the
derived tables. Under RFC 0013 review findings, progress-ledger state alone is
not considered an enforceable quarantine for active derived rows. The
`03_LIMIT10_RUN.blocked.md` marker remains in force until those rows are repaired
or excluded by explicit query rules with proof queries.

## Next Step

Do not start `--limit 50` yet. The next bounded action should be a targeted
repair decision for the failed large segment, such as reducing extraction output
pressure, splitting oversized active segments, or manually rerunning the failed
conversation after a prompt/runtime adjustment.
