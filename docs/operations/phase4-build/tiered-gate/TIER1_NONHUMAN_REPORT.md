# Phase 4 Tier 1 Non-Human Report
author: operator-codex-gpt-5.5-002

Status: findings
Date: 2026-05-09
RFC refs: RFC-0024, RFC-0021
Decision refs: D020, D044, D052, D074, D077
Phase refs: PHASE-0004

## Summary

Collected non-human RFC 0024 Tier 1 evidence without asking for human labels
and without authorizing full-corpus Phase 4. The bounded live smoke at
`LIMIT=200` produced a useful idempotency signal: the first run created bounded
derived Phase 4 rows, and the second run reused them.

Tier 1 is not complete for promotion because human-labeled entity
precision/recall and review-queue UX feedback remain deferred to RFC 0021 /
operator review.

## Commands Run

```text
.venv/bin/python -m pytest tests/test_phase4_entities_review.py -rs
```

Result: 4 skipped because `ENGRAM_TEST_DATABASE_URL` is not configured.

```text
.venv/bin/python -m pytest tests/test_cli.py -k phase4
```

Result: 2 passed, 23 deselected.

```text
make -n phase4-build-entities LIMIT=200
```

Result:

```text
ENGRAM_DATABASE_URL="postgresql:///engram" .venv/bin/python -m engram.cli phase4 build-entities --limit 200
```

```text
make -n phase4-smoke LIMIT=200
```

Result:

```text
ENGRAM_DATABASE_URL="postgresql:///engram" .venv/bin/python -m engram.cli phase4 smoke --limit 200
```

```text
make phase4-smoke LIMIT=200
```

First result:

```text
phase4 smoke: current_beliefs=30700 review_queue_items=30700 beliefs_processed=200 entities_created=243 entities_reused=157 edges_created=175 edges_reused=25 neighborhood_rows=2
```

Second result:

```text
phase4 smoke: current_beliefs=30700 review_queue_items=30700 beliefs_processed=200 entities_created=0 entities_reused=400 edges_created=0 edges_reused=200 neighborhood_rows=2
```

## Non-Human Evidence

| Check | Evidence | Status |
| --- | --- | --- |
| deterministic entity idempotency | second `LIMIT=200` smoke created 0 entities and 0 edges, reused 400 entities and 200 edges | positive |
| current-beliefs projection | `current_beliefs=30700`; direct status count returned `candidate=30700` | positive for current local state |
| review queue size | `review_queue_items=30700`; direct count matched | positive |
| superseded/rejected filtering | direct query found 0 `current_beliefs` rows with `valid_to IS NOT NULL`, `closed_at IS NOT NULL`, or status in `rejected`/`superseded` | positive |
| duplicate active entities | direct query found no active canonical keys with count greater than 1 | positive |
| recursive neighborhood query | `EXPLAIN ANALYZE` completed in 0.380 ms on the bounded active edge set | positive |
| review action audit behavior | isolated DB tests exist but skipped without `ENGRAM_TEST_DATABASE_URL`; no live review action was applied | gap |
| correction-as-capture behavior | isolated DB tests exist but skipped without `ENGRAM_TEST_DATABASE_URL`; no live correction was applied | gap |
| human-labeled entity precision/recall | requires operator labels | deferred_until_rfc0021 |
| review-queue UX feedback | requires operator use | deferred_until_rfc0021 |

## Local Corpus Counts

Belief statuses:

| Status | Count |
| --- | ---: |
| candidate | 30,700 |
| rejected | 4,870 |
| superseded | 6,988 |

Phase 4 derived table counts after the bounded run:

| Table | Active rows |
| --- | ---: |
| entities | 281 |
| entity_edges | 200 |
| belief_review_queue | 30,700 |

## Query Plan Evidence

The bounded 1-2 hop query over the first active entity used existing Phase 4
indexes and completed quickly:

```text
Index Scan using entities_status_kind_idx on entities
Index Only Scan using entity_edges_active_unique_idx on entity_edges
Planning Time: 0.609 ms
Execution Time: 0.380 ms
```

## Gate Statement

Non-human Tier 1 evidence is sufficient to prepare the Tier 2 bounded
preflight scaffold, but not sufficient to promote Phase 4. Human-labeled
entity precision/recall and review-queue UX feedback remain explicitly
deferred to RFC 0021/operator review.
