# Segmentation Benchmark Harness

This directory is a reviewable skeleton for the RFC 0006 segmentation
benchmark. The benchmark is intended to compare segmentation model profiles and
cheap deterministic baselines before any change to the production Phase 2
segmenter contract.

The initial work here is specification and scaffolding only. There is no live
benchmark runner yet.

## Purpose

- Measure whether candidate segmenters produce valid, provenance-safe segment
  JSON.
- Measure whether segment boundaries preserve the claims that make segments
  useful downstream.
- Compare current Qwen, candidate Qwen, optional Gemma, fixed token windows,
  and message-group strategies under one local-only harness.
- Keep P-FRAG benchmark work separate from the deployed Phase 2 schema per
  D039.

## Non-Goals

- Do not mutate `segment_generations`, `segments`, `segment_embeddings`, or any
  production table.
- Do not replace the Phase 2 runner, prompt, schema, or migrations.
- Do not call ik-llama, Ollama, Hugging Face, or any external service from this
  skeleton.
- Do not create a large fixture set before the fixture schema is reviewed.
- Do not treat benchmark-only claim extraction metrics as Phase 3 readiness
  evidence.

## Local-Only Constraint

All benchmark execution must preserve Engram's local-first rule: no user data
leaves the machine unless explicitly requested. Public datasets, if used later,
are downloaded and license-accepted outside the corpus-reading runtime, stored
outside production state, and referenced only by local snapshot identifiers.

## Relationship To Phase 2

Phase 2 remains the production AI-conversation segmentation and embedding path.
This benchmark is a scratch-only development tool for evaluating model/profile
changes and P-FRAG ideas without redefining deployed `window_strategy` values
or activating retrieval-visible rows.

The harness may later reuse validation and prompt-boundary ideas from
`src/engram/segmenter.py`, but it must not write benchmark outputs into active
production generations.

## Layout

```text
benchmarks/segmentation/
  README.md
  SPEC.md
  fixtures/
    synthetic_parents.example.jsonl
    expected_claims.example.jsonl
  strategies.py
  scoring.py
  run_benchmark.py
```

The Python files are intentionally lightweight stubs. They define review
anchors for the future implementation and avoid model, database, or network
side effects.
