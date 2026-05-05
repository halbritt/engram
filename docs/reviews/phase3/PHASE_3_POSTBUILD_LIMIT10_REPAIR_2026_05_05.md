# Phase 3 Post-Build Limit-10 Repair

Date: 2026-05-05

Related blocker:
`docs/reviews/phase3/postbuild/markers/03_LIMIT10_RUN.blocked.md`

Related report:
`docs/reviews/phase3/PHASE_3_POSTBUILD_RUN_LIMIT10_2026_05_05.md`

## Verdict

`ready_for_next_bounded_step`

The limit-10 operational blocker has a verified repair. The originally failed
large segment now has a successful latest extraction, the affected conversation
has been reconsolidated from a complete active claim set, and the same-bound
`pipeline-3 --limit 10` rerun completed with no extraction failures and no
consolidation skips.

This report is redacted under RFC 0013. It contains IDs, counts, commands,
status values, and error classes only. It does not include raw message text,
segment text, claim values, belief values, conversation titles, or
corpus-derived summaries.

## Issue Classes

- `prompt_or_model_contract_failure`
- `upstream_runtime_failure`
- `orchestration_bug`
- `downstream_partial_state`
- `data_repair_needed`

## Repairs Applied

Code and process changes:

- `src/engram/extractor.py`
  - bumped the extractor prompt/profile metadata;
  - extracts large segments through bounded message/content windows;
  - adaptively splits a failed extraction chunk before marking the segment
    failed;
  - records chunk diagnostics in `claim_extractions.raw_payload`.
- `src/engram/cli.py`
  - stops `run_extract_batches` after a failed batch so the same failed segment
    is not immediately selected again in the same command.
- `scripts/phase3_tmux_agents.sh`
  - honors explicit `supersedes:` links from ready post-build markers instead
    of requiring old blocked markers to be deleted.
- `DECISION_LOG.md`
  - added D063 for bounded/adaptive Phase 3 extraction and explicit retry
    control.

Raw evidence was not modified. Failed derived extraction rows were retained as
audit history; no `claim_extractions`, `claims`, `beliefs`, `belief_audit`, or
`contradictions` rows were deleted.

## Targeted Repair Run

First targeted extraction command:

```bash
.venv/bin/python -m engram.cli extract --conversation-id 003a1e2c-3a8b-4550-b695-f88d0377c576 --batch-size 2
```

Result:

- exit code: `1`
- 161 claims created / 9 segments processed / 2 failed
- original failed segment `83e4fd32-6474-42fb-b4b9-3bc7b4956ad9`: repaired,
  latest extraction created 31 claims
- newly exposed issue: segment
  `a2fbd482-d705-4e27-95fa-f85bf37adc11` failed twice because the same failed
  segment was selected again inside the same command

Second targeted extraction command after adaptive split and same-run retry
guard:

```bash
.venv/bin/python -m engram.cli extract --requeue --conversation-id 003a1e2c-3a8b-4550-b695-f88d0377c576 --batch-size 1
```

Result:

- exit code: `0`
- 63 claims created / 1 segment processed / 0 failed
- remaining failed segment repaired with adaptive chunking

Targeted consolidation command:

```bash
.venv/bin/python -m engram.cli consolidate --conversation-id 003a1e2c-3a8b-4550-b695-f88d0377c576 --batch-size 10
```

Result:

- exit code: `0`
- 1 conversation processed
- 197 beliefs created / 2 superseded / 2 contradictions

Affected conversation proof query results:

- active segments: 8
- latest extracted segments: 8
- missing latest extractions: 0
- latest failed extractions: 0
- latest claim count: 224
- active beliefs with orphan claim IDs: 0

## Same-Bound Rerun

Command:

```bash
.venv/bin/python -m engram.cli pipeline-3 --extract-batch-size 5 --consolidate-batch-size 5 --limit 10
```

Result:

- exit code: `0`
- extract: 43 claims created / 10 segments processed / 0 failed
- consolidate: 10 conversations processed / 0 skipped / 45 beliefs created /
  4 superseded / 4 contradictions

Limit-10 proof query results after the same-bound rerun:

- active segments in the first 10 conversations: 18
- latest extracted segments: 18
- missing latest extractions: 0
- latest failed extractions: 0
- latest claim count: 267
- extractor progress rows: 10 completed / 0 failed
- consolidator progress rows: 10 completed / 0 failed
- active beliefs with orphan claim IDs: 0

## Verification

- Focused Phase 3 tests: `31 passed`
- Full test suite: `112 passed`
- Live no-work gate:
  `.venv/bin/python -m engram.cli pipeline-3 --limit 0` passed
- Same-bound rerun:
  `.venv/bin/python -m engram.cli pipeline-3 --extract-batch-size 5 --consolidate-batch-size 5 --limit 10`
  passed
- Shell syntax:
  `bash -n scripts/phase3_tmux_agents.sh` passed
- Whitespace:
  `git diff --check` passed
- Path hygiene:
  home-directory path scan returned no matches

## Current Gate

The legacy blocked marker is superseded by:

`docs/reviews/phase3/postbuild/markers/20260505_limit10_runtime_repair/05_REPAIR_VERIFIED.ready.md`

The post-build limit-10 blocker is resolved for same-bound repair purposes and
for the next bounded post-build step. Larger expansion should still proceed
incrementally; this report does not authorize a full-corpus Phase 3 run.
