# Pre-Phase-2 Adversarial Review — Round 2 (post-D027/D028)

Date: 2026-04-30
Reviewer: claude-opus-4-7
Scope: D026 pre-Phase-2 boundary. Gemini's D027/D028 deltas are assumed accepted
(see `PRE_PHASE_2_ADVERSARIAL_2026_04_30.md`); this round looks for what those
deltas don't fix.

## 1. Blocking before Phase 2

### 1.1 Long-conversation context overflow has no plan

**Decision / doc touched:** `prompts/P007_phase_2_segments_embeddings.md` §3
(Segmenter), `BUILD_PHASES.md` Phase 2, `DECISION_LOG.md` (new sub-decision
under D005).

**Failure mode.** `segment_conversation` "pulls the conversation + ordered
messages, builds the prompt, calls ik-llama." Qwen3.6:35B-MOE has a finite
context. The corpus already has ChatGPT 3,437 + Claude 78 + Gemini 4,401 =
7,916 conversations (SPEC.md §"What it ingests"); the long tail in this corpus
is ~100+-turn coding sessions and Gemini Bard runs that easily exceed 32k
tokens of cleaned text, let alone with role markers. The plan has no
chunk-and-stitch, sliding-window, or pre-summarize fallback. The first long
conversation hit during full-corpus segmentation either truncates silently
(worst — invisible context loss, still produces "valid" segments), errors out
(then the poison-pill counter quarantines the conversation forever), or loops
(if the agent retries with the same input). All three outcomes corrupt the
corpus before the gold set can detect anything.

**Proposed delta.**
1. Phase 2 prompt: state explicitly that the segmenter must (a) probe the
   model's effective context window, (b) define a per-conversation budget under
   that, (c) when the conversation exceeds the budget, fall back to *windowed*
   segmentation: slide a window of N messages with K-message overlap, segment
   within each window, then merge segments whose first/last message overlaps.
   Segments at window boundaries must be marked so a later phase can review.
2. Add `segments.window_strategy TEXT NOT NULL` (`'whole'|'windowed'`) so
   retrieval can downweight cross-window seams, and so re-segmentation under a
   larger context model can specifically target windowed conversations.
3. `consolidation_progress.position` schema must accommodate intra-conversation
   cursors (last completed window index), not just last conversation_id.

**Disproof.** Run the Phase 2 segmenter prompt against the largest single
conversation in the live corpus (`SELECT id FROM conversations c JOIN messages
m USING (conversation_id) GROUP BY c.id ORDER BY sum(length(m.content_text))
DESC LIMIT 1`). If it segments cleanly inside the model's context, downgrade to
non-blocking. If it truncates / errors / loops, blocking.

**Cost of being wrong.** Either invisible truncation (which contaminates
downstream claim extraction precisely on the highest-signal long sessions) or
pipeline halts that quarantine real evidence. Both are expensive to discover
after consolidation runs.

---

### 1.2 No partial unique constraint on `(conversation_id, sequence_index) WHERE is_active`

**Decision / doc touched:** `prompts/P007_phase_2_segments_embeddings.md` §2
(segments indexes), migration `004_segments_embeddings.sql`.

**Failure mode.** The plan describes `(conversation_id, sequence_index)` as a
partial *index* `WHERE is_active=true`, but does not require it to be
**UNIQUE**. With supersession-by-`is_active`, two active rows could collide on
`sequence_index` if a re-segmentation transaction is interrupted between
insert-new and deactivate-old (see 1.3) or if two workers ever segment the same
conversation. Downstream ranking and snapshot citation can't tolerate ambiguous
"the 3rd segment of conv X."

**Proposed delta.** `CREATE UNIQUE INDEX segments_conv_seq_active_uidx ON
segments (conversation_id, sequence_index) WHERE is_active = true;` (and the
analogous form for note/capture parents, even though they're not populated
yet). Make this part of the migration in this phase, not a TODO.

**Disproof.** Inspect any plausible pgvector / Postgres workload where a single
conversation has two active segments at the same `sequence_index`. If you
can't construct a query that's safe under that ambiguity, the constraint is
required.

**Cost of being wrong.** Subtle ranking bugs and non-deterministic snapshot
rendering that only manifest after re-segmentation.

---

### 1.3 Atomicity of "insert new generation, then deactivate prior" is under-specified

**Decision / doc touched:** `prompts/P007_phase_2_segments_embeddings.md` §3
(Re-segmentation), `BUILD_PHASES.md` Phase 2 acceptance.

**Failure mode.** The plan says "inserts new rows, then marks prior `segments`
and their `segment_embeddings` rows `is_active=false` in the same transaction."
Good — but there is a gap *between* segmenter commit and embedder run.
Re-segmentation creates new active segments; their `segment_embeddings` rows
do not exist yet under the new model_version. Until the next `embed` run
completes, the conversation has active segments with no active embedding row
(D027 puts the vector on `segment_embeddings`, not `segments`). Retrieval that
joins `segments` to `segment_embeddings` will therefore return *nothing* for
the affected conversation during the gap. The gap is "however long the embed
batch takes," which on a 7,900-conversation re-embed is hours.

**Proposed delta.** One of:
- **Option A** (preferred): keep the prior generation's `segment_embeddings`
  `is_active=true` until the new generation's embeddings exist. Document that
  during a generation cutover, both generations of `segment_embeddings` are
  active (briefly), and that retrieval may briefly see duplicates. Then a
  second transaction deactivates the prior generation's `segment_embeddings`.
- **Option B**: hold a session-level advisory lock on the affected
  conversation_id during re-segment+re-embed; live retrieval skips locked
  conversations. Higher complexity, blocks readers.

The Phase 2 prompt must pin which option. Tests must cover the cutover gap
explicitly (today they cover only steady state).

**Disproof.** Simulate: bump segmenter version, run segment, do *not* run
embed, query similarity. If the affected conversation's segments still surface
with the prior model_version's embedding rows, fine. If they vanish, blocking.

**Cost of being wrong.** A simple version bump silently blanks a slice of the
corpus from retrieval until the next embed run finishes. This will look like a
regression in eval, attributed to the wrong cause.

---

### 1.4 `message_ids UUID[]` has no integrity guard

**Decision / doc touched:** `prompts/P007_phase_2_segments_embeddings.md` §2
(segments schema), migration.

**Failure mode.** PostgreSQL arrays don't enforce FKs. Nothing in the schema
rejects a segment whose `message_ids` includes UUIDs that (a) don't exist in
`messages`, (b) belong to a different conversation than
`segments.conversation_id`, or (c) are out of order with
`messages.sequence_index`. The segmenter is a local LLM emitting JSON; "the
segmenter wrote down a UUID that's almost-but-not-the-right-message" is
exactly the failure mode the rest of the design treats as load-bearing
(provenance is the central circuit breaker, D003). A bad message_id corrupts
evidence chains for every claim that later cites this segment.

**Proposed delta.** Add a Phase-2 trigger on segments INSERT that enforces:
- every UUID in `message_ids` exists in `messages`;
- every referenced message has `conversation_id = segments.conversation_id`;
- the array is ordered by `messages.sequence_index` ASC;
- the array is non-empty when `conversation_id IS NOT NULL`.

This is a write-side guard; reads stay cheap. Pin it in the migration and in
tests (`tests/test_phase2_segments.py::test_segment_message_ids_must_belong_to_conversation`,
`::test_segment_message_ids_must_exist`).

**Disproof.** Try to argue a benign reason a segment would cite a message from
another conversation, or a non-existent UUID. There isn't one.

**Cost of being wrong.** Phase 3 claims will inherit the corruption. The
provenance contract (D003) appears intact at the schema level (a segment id is
cited; a message id is cited) but is silently broken at the data level. This
is the worst kind of failure — looks correct on inspection.

---

### 1.5 D028 cascade scope is wrong: should be conversation/note/capture, not "source"

**Decision / doc touched:** `DECISION_LOG.md` D028 wording,
`prompts/P007_phase_2_segments_embeddings.md` §3 (reclassification handling),
`BUILD_PHASES.md` Phase 2 cross-cutting.

**Failure mode.** D028 and the Phase 2 prompt both say "queue the parent
**source** for re-segmentation and re-embedding." A `source` for ChatGPT is
the entire export — 3,437 conversations. Reclassifying one message in one
conversation cannot trigger re-segmentation of 3,436 unaffected ones. This is
also wasteful enough to discourage actually running reclassifications, which
silently undermines D023 in practice.

**Proposed delta.**
- Reword D028 and the Phase 2 prompt: "deactivate affected `segments` and
  `segment_embeddings`, then queue the parent **conversation** (or note /
  capture) for re-segmentation."
- Add a Phase-2 mechanism for "queue": a row in `consolidation_progress` with
  `stage='segmenter'`, `scope='conversation:<uuid>'`, `status='pending'`, plus
  a marker on `segments` (`invalidated_at TIMESTAMPTZ NULL`) so the next
  `engram segment` run knows which conversations have had their active rows
  deactivated and need new segments. Without an explicit marker, "all
  conversations with no active segment row under the current versions" picks
  them up automatically — verify this is the intended trigger and pin it in
  tests.

**Disproof.** Trace through the steps: a `capture_type='reclassification'`
arrives targeting one message. Walk the system. Does the conversation
containing that message get re-segmented on the next batch run, while no
other conversation does? If the answer needs a paragraph to explain, the
contract is too implicit.

**Cost of being wrong.** Either reclassification is so expensive nobody runs
it (D023 dies in practice), or the wrong scope is invalidated and
conversations re-process unnecessarily — multi-hour re-segmentation of
unaffected data. Worse: if "queue" is undefined, a deactivated segment never
gets a replacement and the conversation is silently absent from retrieval
forever.

---

### 1.6 Privacy-tier inheritance must include `conversations.privacy_tier`, not only message tiers

**Decision / doc touched:** `prompts/P007_phase_2_segments_embeddings.md` §2
(segments.privacy_tier), `DECISION_LOG.md` D019 (or D028 amendment).

**Failure mode.** The plan says "max() across the message set if they diverge
(D019)." But `conversations.privacy_tier` exists and defaults to 1
independently of message tiers (`migrations/001_raw_evidence.sql`). A user who
set `conversations.privacy_tier = 3` on a sensitive conversation but did not
promote the individual messages will see `segments.privacy_tier = 1`. The
segment is then retrievable at Tier 1 even though the conversation is Tier 3.
This is exactly the scenario D019 is supposed to prevent.

**Proposed delta.** Define inheritance precisely:

```text
segments.privacy_tier = max(
  conversations.privacy_tier,
  max(messages.privacy_tier for m in message_set)
)
```

For note/capture parents: `max(notes/captures.privacy_tier, max(constituent
rows if any))`. Pin this in the prompt's segmenter contract, not just in
tests.

**Disproof.** Find any scenario where the conversation was promoted but
messages were not. If you can't, the simplification is fine; if you can, the
inheritance must include the parent.

**Cost of being wrong.** Privacy leak with the same shape as the one D028 is
meant to fix, but introduced at first segmentation rather than after
reclassification.

---

### 1.7 `embedding_cache` UNIQUE conflict has no specified resolution

**Decision / doc touched:** `prompts/P007_phase_2_segments_embeddings.md` §4
(Embedder), migration.

**Failure mode.** The Phase-2 spec implies serial execution but the corpus is
~7,900 conversations × N segments. Practically, the agent will parallelize
embed calls across workers/connections to keep Ollama busy. Two workers seeing
the same input text both miss the cache, both call Ollama, both attempt INSERT
into `embedding_cache`. The `UNIQUE (input_sha256, embedding_model_version)`
constraint will fire and one transaction aborts. The plan does not specify
`ON CONFLICT DO NOTHING` / `RETURNING` or a SELECT-then-INSERT pattern, and
`embedding_cache` is fully immutable per the trigger — meaning even an
`ON CONFLICT DO UPDATE` no-op is rejected. Without explicit handling, parallel
embedding crashes intermittently.

**Proposed delta.** Pin the embedder's cache lookup as: `INSERT … ON CONFLICT
(input_sha256, embedding_model_version) DO NOTHING RETURNING id`; on
null-returning (conflict), `SELECT id FROM embedding_cache WHERE …`. Verify
the immutability trigger does not fire on `ON CONFLICT DO NOTHING` (it
shouldn't — no row UPDATE happens — but test it). Add a test for concurrent
insertion of the same `(text, model_version)`.

**Disproof.** Run two concurrent embedder workers on overlapping segments. If
one crashes on UNIQUE violation, blocking. If both produce one cache row and
two `segment_embeddings` rows, fine.

**Cost of being wrong.** Embed batch flaps under any non-trivial parallelism.
Worst case the agent disables parallelism and the full re-embed becomes 4×
longer.

---

### 1.8 `embedding vector(768)` hardcoded is incompatible with the stated multi-model story

**Decision / doc touched:** `prompts/P007_phase_2_segments_embeddings.md` §2,
`DECISION_LOG.md` D021 (consequences), `HUMAN_REQUIREMENTS.md` §"Embeddings
are versioned, not replaced".

**Failure mode.** D021 and HUMAN_REQUIREMENTS commit explicitly to "multiple
`embedding_model_version`s can coexist on a segment" and "the corpus survives
the model." But the plan hardcodes `embedding vector(768)` on both
`embedding_cache` and `segment_embeddings`. The next embedder won't be 768d
(e.g., qwen3 embed 1024d, or anything BGE-large at 1024d, or future
1536/3072d models). When that day arrives, this Phase-2 schema actively
prevents the coexistence it promised — you can't insert a 1024d vector into a
`vector(768)` column.

**Proposed delta.** Pick one before coding:
- **A.** Drop the dimension from the column type: `embedding vector NOT NULL`,
  dimension constrained per row by `embedding_dimension INT`, plus partial
  HNSW indexes per `(embedding_model_version, embedding_dimension)`. Each new
  model gets its own partial index. This matches the "multiple coexisting
  versions" promise.
- **B.** One physical table per `embedding_dimension`, with a view union for
  query convenience. Higher migration cost when a new dimension lands, but
  keeps each index simple.

The current plan picks neither; pin one in the migration. The Phase 2
prompt's "verify pgvector supports HNSW; else ivfflat fallback" is also too
breezy — ivfflat needs a `lists` parameter and trained centroids; specify
both or constrain pgvector ≥ 0.5.

**Disproof.** Try `INSERT INTO embedding_cache (embedding) VALUES ('[...1024
floats...]')` against the proposed `vector(768)` column. It rejects. The
proof is the column DDL.

**Cost of being wrong.** Either D021's "model portability" is a docs-only
commitment, or the first non-768d embedder triggers a destructive migration
that violates raw-immutability spirit (you keep raw, but lose the embedding
generation history that lives on the same table type).

---

## 2. Non-blocking but document now

### 2.1 Define the exact bytes hashed for `input_sha256`

The plan says SHA256 of "the exact embedded text." But `content_text` per the
segmenter "with role/source markers as the segmenter chose" is
implementation-discretion. Two equivalent segmenter prompts producing
different role-marker styles produce different cache keys for semantically
identical content. Pin: "the SHA256 input is precisely the byte string
passed to the embedder API, in UTF-8 NFC, no trailing newline normalization
beyond what the embedder client already does." Document this in
`docs/segmentation.md` so a future re-implementation doesn't silently drift.

**Cost of being wrong.** Cache hit rate worse than expected on re-embed; not
a correctness problem.

### 2.2 Multimodal / tool-use messages: contract for `content_text IS NULL` and bracketed markers

ChatGPT messages can have `content_text=NULL` (image-only, tool-output-only).
Claude/Gemini ingest synthesizes `[tool_use:X]`, `[tool_result:X]`, `[image]`
placeholders into `content_text`
(`src/engram/claude_export.py` `extract_content_text`/`content_part_text`).
The Phase 2 prompt is silent on:
- whether NULL-content messages are *included* in `message_ids` (provenance
  preserved) but *excluded* from the embedded text;
- whether bracketed placeholders are kept verbatim in `segments.content_text`
  (will pollute embeddings — `[tool_use:bash]` is a high-frequency token
  across the Claude corpus and will dominate cosine similarity for tool-heavy
  conversations);
- whether segments composed *entirely* of tool placeholder content should be
  created at all.

**Proposed delta.** Add a "Message canonicalization" section to the Phase 2
prompt: include NULL-content messages in `message_ids` for provenance only,
strip bracketed placeholders before embedding, allow zero-content segments
only as no-op markers (or skip entirely and record the gap in
`consolidation_progress`). Document that this canonicalization is part of
the segmenter prompt version — changes to it bump
`segmenter_prompt_version`.

### 2.3 Segmentation eval hook before full-corpus run

O006 ("topic-segmentation safety") is still open. The plan's only validation
is "smoke retrieval returns sensible neighbors" — that fires after Phase 5.
Phase 2 needs at least a 10–25 conversation labeled subset (segmenter
author labels, not gold-set), with golden segment boundaries, so
prompt-version bumps can A/B without going through full embedding +
extraction. Add a `tests/eval/segmenter_subset/` fixture and a
`make segment-eval` target. This is non-blocking *if* the project accepts
that the first segmentation run on the corpus is the eval; it's blocking if
the cost of "discover bad segmentation after Phase 5" is unacceptable.

### 2.4 `notes.privacy_tier` does not exist

`migrations/001_raw_evidence.sql` omits `privacy_tier` on `notes`. Phase 2
schema lays `note_id` columns now even though no notes are populated, and
D019 says `privacy_tier` lives on raw rows. Phase 1.5 should have added it;
it didn't. Capture this gap before the Obsidian path lights up — otherwise
the segmenter for notes will face the same conversation-vs-message
inheritance question as 1.6, except worse (no parent tier to fall back on).

### 2.5 Re-embed-on-supersession is operator-driven; surface it loudly

Phase 2 explicitly defers auto re-embed on segment supersession ("the new
generation embeds on the next `embed` run"). This is a footgun in
combination with finding 1.3: if an operator bumps
`segmenter_prompt_version` and forgets to run `embed`, the corpus becomes
unretrievable on the cutover slice. Add a `make pipeline` invariant:
`pipeline` must always run `segment` then `embed`. Add a CLI warning when
`engram segment` produces deactivations whose new active rows lack
`segment_embeddings` for any active model version: `WARNING: 4,231 active
segments lack embeddings under model_version=nomic-embed-text:0.5; run
\`engram embed\``.

---

## 3. Defer

### 3.1 Sub-message character spans (Gemini 2.1 / 3.2)

Already raised. Stays deferred. Don't build until the first eval failure
that's clearly attributable to coarse provenance.

### 3.2 Unified vector index across segments + beliefs

Two HNSW indexes is fine for V1. Revisit when `context_for` ranking shows
recall calibration issues.

### 3.3 Segment-level `summary_text` as a second embedded surface

Two embeddings per segment (content + summary, weighted in retrieval) is
interesting research but not a Phase 2 schema gate. Keep `summary_text TEXT
NULL` so a later phase can opt in without a migration.

### 3.4 Cross-conversation segment merging

Multi-conversation segments (e.g., a project arc spanning 30 conversations)
is a real long-arc use case but explicitly out of scope. The schema's
`conversation_id NOT NULL` for message-derived segments correctly forecloses
it for now; revisit when entity context shows it's needed.

---

## 4. Concrete schema deltas

```sql
-- 4.1 Partial unique on active segment ordering (Finding 1.2)
CREATE UNIQUE INDEX segments_conv_seq_active_uidx
  ON segments (conversation_id, sequence_index)
  WHERE is_active = true AND conversation_id IS NOT NULL;
CREATE UNIQUE INDEX segments_note_seq_active_uidx
  ON segments (note_id, sequence_index)
  WHERE is_active = true AND note_id IS NOT NULL;
CREATE UNIQUE INDEX segments_capture_seq_active_uidx
  ON segments (capture_id, sequence_index)
  WHERE is_active = true AND capture_id IS NOT NULL;

-- 4.2 message_ids integrity trigger (Finding 1.4)
CREATE OR REPLACE FUNCTION segments_validate_message_ids()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF NEW.conversation_id IS NULL THEN RETURN NEW; END IF;
  IF array_length(NEW.message_ids, 1) IS NULL THEN
    RAISE EXCEPTION 'segment for conversation must have non-empty message_ids';
  END IF;
  PERFORM 1 FROM unnest(NEW.message_ids) AS mid
    LEFT JOIN messages m ON m.id = mid
    WHERE m.id IS NULL OR m.conversation_id <> NEW.conversation_id;
  IF FOUND THEN
    RAISE EXCEPTION
      'segments.message_ids contains UUIDs not in conversation %',
      NEW.conversation_id;
  END IF;
  -- ordering check (strict-monotonic by messages.sequence_index)
  -- one approach pinned in migration; sketch only here.
  RETURN NEW;
END $$;
CREATE TRIGGER segments_message_ids_check
  BEFORE INSERT ON segments FOR EACH ROW
  EXECUTE FUNCTION segments_validate_message_ids();

-- 4.3 Invalidation marker for D028 cascade (Finding 1.5)
ALTER TABLE segments
  ADD COLUMN invalidated_at TIMESTAMPTZ NULL,
  ADD COLUMN invalidation_reason TEXT NULL;
-- Update the segments immutability trigger: allow is_active true→false AND
-- invalidated_at NULL→TIMESTAMPTZ in the same UPDATE; reject everything else.

-- 4.4 Window strategy column (Finding 1.1)
ALTER TABLE segments
  ADD COLUMN window_strategy TEXT NOT NULL DEFAULT 'whole'
  CHECK (window_strategy IN ('whole','windowed'));

-- 4.5 Drop hardcoded vector dimension (Finding 1.8) — Option A
--   embedding vector NOT NULL  (no length constraint)
-- with HNSW index per partial:
--   CREATE INDEX ... USING hnsw (embedding vector_cosine_ops)
--     WHERE is_active=true AND embedding_model_version='nomic-embed-text:v1.5'
-- per active model.

-- 4.6 notes.privacy_tier (Finding 2.4)
ALTER TABLE notes ADD COLUMN privacy_tier INT NOT NULL DEFAULT 1;
```

---

## 5. Concrete prompt / implementation-contract deltas

In `prompts/P007_phase_2_segments_embeddings.md`:

1. Insert a new "Long-conversation handling" section between current §3.1 and
   §3.2: define windowed strategy, intra-conversation cursor in
   `consolidation_progress.position`, and the merge rule for cross-window
   segments.
2. Replace the privacy-tier sentence in §2 with the explicit formula from
   finding 1.6.
3. Replace D028 wording in §3 from "queue the parent source" to "queue the
   parent conversation (or note/capture)." Define "queue" explicitly: insert
   or update a `consolidation_progress` row keyed by `stage='segmenter'`,
   `scope='conversation:<uuid>'`, `status='pending'`.
4. Add "Atomicity of generation cutover": pin Option A or B from finding 1.3
   and add the corresponding test.
5. Add "Concurrent embedder workers": pin `INSERT … ON CONFLICT DO NOTHING
   RETURNING id`; SELECT-fallback pattern (finding 1.7).
6. Add "Message canonicalization for embedding": NULL-content treatment,
   placeholder stripping, what counts as embeddable text (finding 2.2).
7. Add "Dimension policy": pin 4.5A or 4.5B and what model_version metadata
   is required on every cache row (finding 1.8).
8. §7 tests must add: cutover gap test (1.3), message_ids integrity tests
   (1.4), cross-conversation reclassification scope test (1.5),
   conversation-tier inheritance test (1.6), parallel-embedder UNIQUE test
   (1.7), windowed-segmentation test (1.1).

---

## 6. Minimal experiments / inspections before coding

1. **Largest conversation segmentation probe (1.1).** Find the longest
   conversation by total `content_text` length. Run the proposed segmenter
   prompt against it on the live ik-llama endpoint. Record: did it complete,
   did it truncate, how many segments did it emit, how long did it take.
2. **Concurrent embedder probe (1.7).** Two terminals, each `python -c "from
   engram.embedder import embed_text; embed_text('the same text',
   'nomic-embed-text:v1.5')"`. Verify behavior under simulated cache-miss
   race (delete the cache row between SELECT and INSERT in one worker).
3. **Cutover-gap probe (1.3).** Create one segment + embedding, bump
   `segmenter_prompt_version`, re-segment without re-embedding, run a
   similarity query against the affected conversation. Record whether
   retrieval finds anything.
4. **Tier inheritance probe (1.6).** Insert a conversation with
   `privacy_tier=3` and messages with `privacy_tier=1`. Segment it. Inspect
   resulting `segments.privacy_tier`. The current plan says 1; the corrected
   plan says 3.
5. **Reclassification scope probe (1.5).** Insert a
   `capture_type='reclassification'` for one message. Walk the segmenter's
   "what to invalidate" logic. Verify it's per-conversation, not per-source.

These are five small probes; together they take a half day and they are the
cheapest possible disproof of the entire blocking list.

---

## 7. Recommendation

**Do not proceed to Phase 2 implementation as currently specified.**

Gemini's D027/D028 deltas fix the two structural correctness bombs (vector
index placement, supersession topology). They do not fix:

- the long-conversation overflow path (1.1) — the corpus has conversations
  that will hit it on day one;
- the cutover atomicity gap (1.3) — every version bump silently blanks
  retrieval until embed completes;
- the `message_ids` integrity hole (1.4) — the provenance contract the rest
  of the architecture treats as load-bearing has no enforcement at the
  schema level;
- the D028 cascade scope (1.5) — currently invalidates 3,437 conversations
  to fix one;
- the dimension-hardcode (1.8) — directly contradicts D021 /
  HUMAN_REQUIREMENTS' model-portability commitment.

Items 1.2, 1.6, 1.7 are smaller but cheap to fix now and prohibitively
expensive to retrofit (especially 1.6, which is a privacy contract).

**Land items 4.1–4.6 in `migrations/004_segments_embeddings.sql`. Land prompt
deltas 5.1–5.8 in `prompts/P007_phase_2_segments_embeddings.md`. Add D029 (cutover
atomicity policy) and D030 (D028 cascade scope correction) to
`DECISION_LOG.md`. Run probes 6.1–6.5. Then proceed.**

Total work to clear the gate: roughly half a day of doc/schema changes and
half a day of probes — small relative to the multi-week consolidation run
that comes after.
