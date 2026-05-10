# Phase 4 Tier 2 Bounded Preflight Scaffold
author: operator-codex-gpt-5.5-003

Status: scaffold
Date: 2026-05-09
RFC refs: RFC-0024
Decision refs: D020, D044, D052, D074, D077
Phase refs: PHASE-0004

## Summary

Prepared the Tier 2 bounded production preflight scaffold. This artifact does
not authorize full-corpus Phase 4. It preserves the Tier 1 blocker: human
entity precision/recall and review-queue UX evidence remain missing and must
be supplied through RFC 0021/operator review before promotion.

## Dry-Run Evidence

```text
make -n phase4-smoke LIMIT=500
```

Expands to:

```text
ENGRAM_DATABASE_URL="postgresql:///engram" .venv/bin/python -m engram.cli phase4 smoke --limit 500
```

```text
make -n phase4-build-entities LIMIT=500
```

Expands to:

```text
ENGRAM_DATABASE_URL="postgresql:///engram" .venv/bin/python -m engram.cli phase4 build-entities --limit 500
```

```text
.venv/bin/python -m engram.cli phase4 smoke --help
```

Result:

```text
usage: engram phase4 smoke [-h] [--limit LIMIT]
```

```text
.venv/bin/python -m engram.cli phase4 build-entities --help
```

Result:

```text
usage: engram phase4 build-entities [-h] [--limit LIMIT]
```

```text
.venv/bin/python -m engram.cli phase4 run
```

Result: failed closed with exit 2. The command is intentionally absent; valid
subcommands are `refresh-current-beliefs`, `build-entities`, `smoke`, and
`review-belief`.

## Bounded Command Plan

Tier 2 should run only after the missing human-label/UX blockers are resolved:

```text
make phase4-smoke LIMIT=500
```

Then, if the smoke output is clean and no failed/in-flight jobs remain:

```text
make phase4-build-entities LIMIT=500
```

The expected report destination is an aggregate-only tracked artifact under
`docs/operations/phase4-build/tiered-gate/`. Scratch logs may contain local
paths or private operational detail, but the tracked report must stay redacted.

## Required Assumptions

- Production database is the intended local database, accessed through
  `ENGRAM_DATABASE_URL=postgresql:///engram` unless the operator explicitly
  chooses another local DSN.
- Local model endpoint assumptions, if any Phase 4 tiebreaker path is enabled,
  must be recorded before the run. The current deterministic Phase 4 path does
  not require remote services.
- No hosted service, telemetry, CDN, or cloud persistence is permitted.
- Striatum state remains the gate authority per D074.

## Required Checks For The Tier 2 Report

- no failed or in-flight Phase 4 jobs after completion;
- no duplicate active canonical entities for the same canonical key;
- every new entity and edge carries provenance/version metadata required by
  D021 and RFC 0024;
- `current_beliefs` refreshes cleanly after the run;
- review queue size and distribution are human-operable;
- all correction actions remain queued for reprocessing, not silent mutation;
- bounded 1-2 hop entity-neighborhood query p95 latency is reported;
- human-label and review-queue UX blockers are either resolved or explicitly
  preserved as blockers.

## Aggregate Report Shape

The tracked Tier 2 report may include:

- command lines;
- run IDs and Striatum job IDs;
- aggregate status counts;
- entity/edge created/reused counts;
- current-belief and review-queue counts;
- duplicate-active-entity counts;
- p50/p95 query latencies;
- error classes and counts;
- explicit blockers.

It must not include raw corpus text, model prompts or completions containing
private data, conversation titles, belief values, claim values, entity names,
relationship labels, or home-directory absolute paths.

## Gate Statement

This scaffold is ready, but Tier 2 should not be executed as a promotion gate
until the deferred human-label and review-queue UX evidence is available. This
artifact does not authorize full corpus.
