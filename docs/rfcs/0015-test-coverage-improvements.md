# RFC 0015: Test Coverage Improvements

Status: proposal
Date: 2026-05-05

This is an idea-capture RFC, not an accepted architecture decision. It records
a coverage-gap audit of the current test suite under `tests/` and proposes a
prioritized set of additions. Promoting any item here into a binding plan
should happen via `BUILD_PHASES.md` or a phase prompt.

## Background

The Engram suite is database-integration-heavy: every test depends on a live
Postgres via the `conn` fixture (`tests/conftest.py:14`), which drops and
re-runs migrations per test. That gives strong end-to-end confidence on the
canonical tables, but leaves wide gaps in unit-level coverage and around code
that isn't on a happy-path SQL trace.

Test counts per file (as of this RFC):

| Test file | Tests |
|---|---|
| `test_phase1_raw.py` (ChatGPT) | 6 |
| `test_phase1_claude.py` | 6 |
| `test_phase1_gemini.py` | 4 |
| `test_phase2_segments.py` | 30 |
| `test_phase2_embeddings.py` | 6 |
| `test_benchmark_segmentation.py` | 28 |

Source surface vs coverage:

| Module | LOC | Tests | Status |
|---|---|---|---|
| `segmenter.py` | 1915 | 30 + 28 benchmark | Heavy on windowing/retries; gaps in helpers |
| `embedder.py` | 568 | 6 | Cache + resume covered; HTTP / error paths thin |
| `chatgpt_export.py` | 468 | 6 | Happy path + conflicts |
| `claude_export.py` | 470 | 6 | Dir + zip happy path + conflicts |
| `gemini_export.py` | 470 | 4 | Smallest coverage of the three loaders |
| `cli.py` | 343 | 0 | No tests at all |
| `migrations.py` | 36 | indirect via `conn` | No idempotency / sequence test |
| `progress.py` | 60 | indirect | `consolidation_progress` increment logic untested |
| `db.py` | 16 | indirect | OK given size |

## Gaps, ranked by risk

### 1. CLI is entirely untested (`src/engram/cli.py`)

All subcommands — `migrate`, `ingest-chatgpt`, `ingest-claude`,
`ingest-gemini`, `segment`, `embed`, `pipeline` — have zero coverage of
argument parsing, exit codes, or error formatting. This is the operator-facing
surface; a regression here breaks Step 4B in `ROADMAP.md` silently.

Proposed: add `tests/test_cli.py` that drives `main()` via `argparse` for each
subcommand, asserts exit codes, and checks that `--batch-size`, `--limit`,
`--source-id` are wired through to the underlying calls.

### 2. `canonicalize_embeddable_text()` has no test

This function in `segmenter.py` decides what bytes get hashed and embedded —
a silent change here invalidates the embedding cache and breaks resumability.

Proposed: lock its output with a table-driven test of normalization cases
(whitespace, code fences, attachments, unicode classes).

### 3. Sanitization pipeline is untested in isolation

`sanitize_model_string`, `sanitize_model_json`, and `sanitize_segment_draft`
are the trust boundary for LLM output. They are exercised only through full
`segment_pending` runs, so a regression that *accepts* malformed model output
won't fail loudly.

Proposed: unit tests with adversarial fixtures (control chars, oversized
fields, type coercions, unexpected nesting).

### 4. Embedder error paths

`embedder.py` covers cache hits, miss, model coexistence, and resume after
failure, but `OllamaEmbeddingClient`, `http_json()`, `vector_literal()`, and
dimension-mismatch handling aren't directly tested. With Ollama as the only
embedding backend, HTTP timeouts and non-200 responses are realistic failure
modes.

Proposed: mock the HTTP layer and exercise timeouts, 4xx/5xx, malformed JSON,
and dimension-mismatch responses.

### 5. Gemini ingest is thinner than ChatGPT / Claude

Only 4 tests (vs 6 each for the others), and `TextHTMLParser` — Gemini's
HTML-to-text path — has no direct test. Gemini exports are HTML-rich; this is
where parse drift will land.

Proposed: fixtures with nested formatting, code blocks, and Gemini-specific
activity-id edge cases.

### 6. Loader helpers are entirely untested

`chatgpt_export`, `claude_export`, and `gemini_export` each have ~13 helper
functions (manifest building, conversation parsing, content extraction)
reachable only through `ingest_*`. Malformed-input tests would catch parser
drift earlier and faster than the current end-to-end tests.

Proposed: unit tests for each loader's content-extraction and conversation-
parsing helpers, with malformed inputs.

### 7. Migration safety

`conftest.py` runs `migrate()` on a clean schema every test, so we test the
*combined* migration result, never the *sequence*.

Proposed: a test that runs migrations one-by-one against a previously-migrated
DB to verify idempotency, and that 002–004 work against a 001-only baseline.
Also assert the immutability triggers fire (Phase 1 acceptance criterion in
`BUILD_PHASES.md`).

### 8. `consolidation_progress` increment logic

`progress.py:upsert_progress` governs resumability for Step 4B. Currently only
schema is verified.

Proposed: tests for monotonic counters, status transitions, and concurrent
writes.

### 9. Adaptive splitting / context budget assertions

`assert_context_budget`, `estimate_segmenter_prompt_tokens`,
`should_adaptively_split_window`, and `split_message_window` are tested only
via integration. A unit test on token math would prevent silently exceeding
model context.

Proposed: isolated unit tests on the token-budget math with synthetic message
windows.

### 10. Smoke / pipeline integration test

There's no test that runs `ingest → segment → embed` end-to-end on a tiny
fixture corpus, even though `BUILD_PHASES.md` D016 calls for it.

Proposed: a small (~3 conversation) golden-pipeline test that catches wiring
regressions between phases without needing the 200-conversation smoke gate.

## Recommended ordering

If picking three to do first:

1. `tests/test_cli.py` covering all subcommands (gap 1).
2. Unit tests for `canonicalize_embeddable_text` and the `sanitize_*` family
   (gaps 2–3).
3. A tiny end-to-end pipeline test (gap 10).

These three close, respectively: the operator surface, the embedding-stability
surface, and the phase-seam surface — all of which are load-bearing for the
current Step 4B work. Items 4–9 are higher-leverage once the foundation above
is in place.

## Out of scope

This RFC does not propose:

- A coverage-percentage target or coverage gate in CI.
- A switch from integration-style tests to a mocked-DB unit style; the
  `conn` fixture is fine for Phase 1/2 as-is.
- New fixtures or test infrastructure beyond what each item above needs.

Those are separate questions that should be revisited only if the additions
proposed here run into friction.
