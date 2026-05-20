# Context Serving And Eval V1 Contract

Status: accepted for first real eval loop by
[D087](../../DECISION_LOG.md#d087).

This spec records the narrow contract accepted for the architecture follow-up
serving/eval slice. It is intentionally smaller than a future full product
spec.

## `context_for` V1

The current V1 request/output shape is accepted as the compatibility target:

- request implementation: `src/engram/context.py::ContextForRequest`
- result implementation: `src/engram/context.py::ContextForResult`
- CLI surface: `engram context-for`
- MCP surface: `engram.context_for`

The V1 output includes:

- `context_id`
- `compiler_version`
- `status`
- `sections`
- `citations`
- `omissions`
- `source_belief_ids`
- `source_segment_ids`
- `source_reference_ids`
- `rendered_context`
- optional snapshot metadata: `snapshot_id`, `memory_epoch`, `request_hash`

Future changes should be additive or versioned.

## Context Eval Dataset

The owner-authored real eval dataset is private local data and is not committed
to this repo. The repository carries only:

- the public item schema:
  `docs/schemas/context_eval_item.v1.schema.json`;
- Python validation in `src/engram/context_eval.py`;
- synthetic fixtures under `tests/fixtures/context_eval/`.

`tests/fixtures/context_eval/gold.jsonl` is the public starter dataset. It has
matching synthetic corpus setup in `tests/test_context_eval.py`, which verifies
the real `engram eval context` CLI/compiler path without committing owner data.

`tests/fixtures/context_eval/synthetic_e2e/` is the preferred e2e harness. Its
`corpus.json` seeds synthetic beliefs, recent captures, and local
web-search-style entity grounding rows that distinguish ambiguous proper nouns
as products, people, or places. `make e2e-context-synthetic` runs the real
context eval CLI/compiler path and verifies local-only `engram.ground_entity`
lookup. The harness intentionally avoids live network search; any real web
grounding has to be captured first into local `entity_grounding_evidence`.

Dataset discovery:

- `engram eval context --dataset-path PATH` accepts a JSONL file or a directory
  containing `context_eval.gold.jsonl`;
- `ENGRAM_EVAL_DATASET_PATH` provides the same path when `--dataset-path` is
  absent;
- legacy `--gold-set PATH` remains supported for direct JSONL compatibility.

The accepted item schema version is `context_eval.item.v1`.
