---
loop: postbuild
issue_id: 20260506_full_corpus_run
family: run
scope: phase3 pipeline-3 full corpus
bound: full_corpus
state: blocked
gate: blocked_for_expansion
classes: [prompt_or_model_contract_failure, upstream_runtime_failure, data_repair_needed]
created_at: 2026-05-06T18:27:06Z
linked_report: docs/reviews/phase3/PHASE_3_FULL_RUN_EXTRACTOR_PARSE_FAILURE_FINDINGS_2026_05_06.md
corpus_content_included: none
---

# Phase 3 Full-Corpus Run Blocked

Verdict: `blocked_for_expansion`

The unbounded Phase 3 run and deferred resume hit extractor parse failures.
Each corresponding conversation was skipped by consolidation while later
conversations continued.

Blocking conditions:

- 3 latest v8 extraction failures
- 3 failed extractor progress rows
- 3 failed consolidator progress rows
- 0 in-flight latest v8 extraction rows after coordinator stop

Report:

- `docs/reviews/phase3/PHASE_3_FULL_RUN_EXTRACTOR_PARSE_FAILURE_FINDINGS_2026_05_06.md`

Next expected step:

Targeted retries for the three failed conversation scopes listed in the linked
findings report. If any repeats the same parse-error shape, specify and review
a narrow extractor repair before treating full corpus as complete.
