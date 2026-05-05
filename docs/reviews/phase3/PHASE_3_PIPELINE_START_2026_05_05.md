# Phase 3 Pipeline Start

Date: 2026-05-05
Operator: Codex GPT-5.5 (`codex_gpt5_5`)
Prompt ordinal: P031
Worktree: `~/git/engram`

## Verdict

A bounded local Phase 3 smoke run was started, but the system is **not ready**
for a larger run.

The live corpus database has a stale Phase 3 schema even though
`schema_migrations` records `006_claims_beliefs.sql` as applied. The migration
runner therefore no-ops by filename while the current code expects columns and
tables that are absent from the live DB. No full-corpus run was started.

## Readiness Marker

`docs/reviews/phase3/markers/10_BUILD_REVIEW_SYNTHESIS.ready.md` existed before
pipeline work began.

## Worktree And Commit

Commands:

```text
git status --short
git rev-parse HEAD
git branch --show-current
```

Current commit:

```text
8cbffa517adfb65e9f7aecf8f86b8fd6b14d4d64
```

Branch:

```text
master
```

The worktree was already dirty before this operator wrote the report. Existing
changes included Phase 3 implementation, review, prompt, migration, and schema
artifacts. This operator added only this report and the
`11_PIPELINE_STARTED.ready.md` marker.

## Initial Corpus Counts

Command:

```text
psql postgresql:///engram -Atc "SELECT 'conversations', count(*) FROM conversations UNION ALL SELECT 'segments', count(*) FROM segments UNION ALL SELECT 'active_segments', count(*) FROM segments WHERE is_active UNION ALL SELECT 'claim_extractions', count(*) FROM claim_extractions UNION ALL SELECT 'claims', count(*) FROM claims UNION ALL SELECT 'beliefs', count(*) FROM beliefs UNION ALL SELECT 'belief_audit', count(*) FROM belief_audit UNION ALL SELECT 'contradictions', count(*) FROM contradictions UNION ALL SELECT 'progress_extractor', count(*) FROM consolidation_progress WHERE stage='extractor' UNION ALL SELECT 'progress_consolidator', count(*) FROM consolidation_progress WHERE stage='consolidator'"
```

Counts before the smoke run:

```text
conversations|7916
segments|16163
active_segments|11169
claim_extractions|0
claims|0
beliefs|0
belief_audit|0
contradictions|0
progress_extractor|0
progress_consolidator|0
```

## Migrations

Command:

```text
/usr/bin/time -p make migrate
```

Result:

```text
ENGRAM_DATABASE_URL="postgresql:///engram" .venv/bin/python -m engram.cli migrate
No migrations to apply.
real 0.16
user 0.14
sys 0.02
```

Migration ledger:

```text
001_raw_evidence.sql
002_capture_reclassification.sql
003_source_kind_claude.sql
004_segments_embeddings.sql
004_source_kind_gemini.sql
005_source_kind_gemini.sql
006_claims_beliefs.sql
```

Important finding: `schema_migrations` stores only `filename` and `applied_at`.
The live DB records `006_claims_beliefs.sql`, but the schema is not the current
Phase 3 schema.

Observed stale-schema examples:

```text
predicate_vocabulary: missing
claims.extraction_id: missing
belief_audit.evidence_message_ids: missing; stale evidence_episode_ids exists
beliefs.subject_normalized: missing
```

## Tests

Focused Phase 3 test command without test DB env was accidentally non-useful:

```text
/usr/bin/time -p .venv/bin/python -m pytest tests/test_phase3_claims_beliefs.py -q
```

Result:

```text
4 passed, 15 skipped in 0.05s
real 0.26
user 0.24
sys 0.02
```

Focused Phase 3 test command against the test DB:

```text
/usr/bin/time -p env ENGRAM_TEST_DATABASE_URL=postgresql:///engram_test .venv/bin/python -m pytest tests/test_phase3_claims_beliefs.py -q
```

Result:

```text
19 passed in 10.55s
real 10.76
user 0.43
sys 0.05
```

Full test target:

```text
/usr/bin/time -p make test
```

Result:

```text
99 passed in 35.69s
real 35.93
user 1.10
sys 0.10
```

## Local LLM Health Smoke

Command:

```text
/usr/bin/time -p timeout 180s .venv/bin/python -c "from engram.extractor import IK_LLAMA_BASE_URL, IkLlamaExtractorClient, default_extractor_model_id, run_extractor_health_smoke, EXTRACTION_REQUEST_PROFILE_VERSION; c=IkLlamaExtractorClient(); m=default_extractor_model_id(); print(f'base_url={IK_LLAMA_BASE_URL}'); print(f'model={m}'); print(f'request_profile={EXTRACTION_REQUEST_PROFILE_VERSION}'); run_extractor_health_smoke(c, model_id=m); print('health_smoke=ok')"
```

Result:

```text
base_url=http://127.0.0.1:8081
model=~/models/Qwen_Qwen3.6-35B-A3B-IQ4_XS.gguf
request_profile=ik-llama-json-schema.d034.v2.extractor-8192
health_smoke=ok
real 0.70
user 0.14
sys 0.01
```

The health smoke stayed local and used the Phase 3 structured request profile.

## Bounded Pipeline Slice

Candidate check for the `pipeline-3 --limit 1` selection showed the first
selected conversation was small:

```text
conversation_id=0014d635-f280-4e68-a762-6a8e5b5920ef
active_segments=1
evidence_message_refs=2
first_seq=0
last_seq=0
```

Smoke command:

```text
/usr/bin/time -p timeout 600s .venv/bin/python -m engram.cli pipeline-3 --extract-batch-size 1 --consolidate-batch-size 1 --limit 1
```

Result: exit code `1`.

Key output:

```text
extract segment=567c77ce-b09e-498e-ad50-a129d971129a
extract segment=567c77ce-b09e-498e-ad50-a129d971129a failed elapsed=14.6s
extract segment=567c77ce-b09e-498e-ad50-a129d971129a
extract segment=567c77ce-b09e-498e-ad50-a129d971129a failed elapsed=14.1s
extract segment=567c77ce-b09e-498e-ad50-a129d971129a
extract segment=567c77ce-b09e-498e-ad50-a129d971129a failed elapsed=14.1s
consolidate conversation=0014d635-f280-4e68-a762-6a8e5b5920ef
psycopg.errors.UndefinedColumn: column c.extraction_id does not exist
real 43.08
user 0.16
sys 0.01
```

The extractor exhausted the parent error budget with `failure_kind =
'retry_exhausted'` and `last_error = 'claim 0 must have exactly one object
value'`. Consolidation then failed because the live `claims` table lacks the
current `extraction_id` column. The consolidator also attempted to write its
failure progress row while the transaction was already aborted, producing
`psycopg.errors.InFailedSqlTransaction`; no consolidator progress row was
persisted.

## Post-Smoke Counts

Command:

```text
psql postgresql:///engram -Atc "SELECT 'claim_extractions', count(*) FROM claim_extractions UNION ALL SELECT 'claims', count(*) FROM claims UNION ALL SELECT 'beliefs', count(*) FROM beliefs UNION ALL SELECT 'belief_audit', count(*) FROM belief_audit UNION ALL SELECT 'contradictions', count(*) FROM contradictions UNION ALL SELECT 'extractor_progress', count(*) FROM consolidation_progress WHERE stage='extractor' UNION ALL SELECT 'consolidator_progress', count(*) FROM consolidation_progress WHERE stage='consolidator'"
```

Counts:

```text
claim_extractions|3
claims|0
beliefs|0
belief_audit|0
contradictions|0
extractor_progress|1
consolidator_progress|0
```

Extractor progress row:

```text
stage=extractor
scope=conversation:0014d635-f280-4e68-a762-6a8e5b5920ef
status=failed
position={"segment_id": "567c77ce-b09e-498e-ad50-a129d971129a", "conversation_id": "0014d635-f280-4e68-a762-6a8e5b5920ef"}
error_count=3
last_error=claim 0 must have exactly one object value
```

Failure diagnostic rows:

```text
claim_extractions rows: 3
status: failed
claim_count: 0
failure_kind: retry_exhausted
attempts per row: 2
attempt_max_tokens: [8192, 8192]
attempt_errors: ["claim 0 must have exactly one object value", "claim 0 must have exactly one object value"]
model_response: null
```

No `claims`, `beliefs`, `belief_audit`, or `contradictions` rows were created.
Contradiction behavior was therefore not applicable in the live smoke. The
focused and full test runs did exercise Phase 3 consolidator and contradiction
behavior against the current test schema.

## Larger-Run Readiness

Ready for a larger run: **no**.

Blocking conditions:

1. The live corpus DB must be reconciled with the current Phase 3 migration.
   Filename-only `schema_migrations` says `006_claims_beliefs.sql` is applied,
   but the live schema is stale.
2. The local extractor produced schema-invalid claims on the first real segment
   and exhausted the parent retry budget. This may be segment-specific, but it
   should be investigated after the DB schema is reconciled.
3. Consolidator failure diagnostics did not persist after the SQL error because
   the progress write happened in an aborted transaction.

No full-corpus Phase 3 run was started or approved.
