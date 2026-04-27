# Consensus Review

Status: synthesis of round 1 reviews
Date: 2026-04-27
Inputs: BRAINSTORM.md, README.md, SPEC.md, TODO.md, CODEX_REVIEW.md,
DESIGN_REVIEW_GEMINI.md, REVIEW_claude-opus-4-7.md,
claw-review.md (self-hosted Qwen3.6:35B-MOE).

## Context To Preserve

- Local hardware. Offline token burn is acceptable.
- Live context must remain concise, precise, and useful.
- The corpus is complex; "single-user means simple" is not assumed.
- Engram is both a personal memory system and a research lab for graph
  retrieval, temporal memory, and context engineering.
- The primary product surface is `context_for(conversation)`.

## Consensus Points

All four reviewers converged on the following:

1. **No graph backend in v1.** Postgres + pgvector + relational edge tables are
   sufficient for personal scale. Apache AGE is the correct *eventual* answer
   if SQL becomes ugly because it stays inside Postgres. Neo4j / FalkorDB /
   Kuzu add a separate process for marginal gain.
2. **Temporal validity replaces confidence decay.** Every belief carries
   `valid_from` / `valid_to` (when it was true in the world) plus
   `observed_at` and `recorded_at`. Contradictions close the prior validity
   window and insert a new belief — never UPDATE in place. This is SCD2 /
   bitemporal modeling. Naive age decay is rejected.
3. **Provenance is the central circuit breaker.** Every accepted belief must
   cite at least one raw evidence id (episode / message / note / capture).
   Beliefs derived only from other beliefs are not allowed to enter the
   accepted state. This is the single most important invariant.
4. **`context_for` is an active compiler, not passive search.** Multi-lane
   candidate generation, explicit ranking features, sectioned token-budgeted
   output. Passive MCP `search` / `recall` tools are not the live serving
   path — the LLM cannot meta-cognize its own gaps.
5. **Cut most of the 8-stage pipeline for v1.** Hypotheses, failure pattern
   detection, causal links, patterns, and goal progress inference are all
   deferred. They are the highest-risk hallucination amplifiers.
6. **Topic-segmented chunks beat raw turns** as the embedding and extraction
   unit. Three reviewers explicitly recommend topic segments; the fourth
   (claw) recommends whole conversations with topic segmentation as
   fallback for long conversations — same direction, slightly coarser
   default.
7. **Evidence remains immutable.** Episodes / messages / notes / captures
   never get deleted or rewritten. Derived projections (vector index, entity
   graph, wiki, current_beliefs view, context packages) are rebuildable from
   evidence-backed state.
8. **Eval harness lands before full-corpus consolidation.** Running the
   pipeline on 3,400 conversations without a gold set is a guaranteed way
   to ship contaminated beliefs and waste local-inference time.

## Important Disagreements

1. **Wiki output layer in v1.** Gemini argues the wiki is *the* HITL control
   plane and substitutes for missing engagement signals — defer it and you
   lose your only correction loop. Codex defers to a single index page.
   Claude Opus 4.7 cuts entirely; reading assembled context packages is the
   v1 validation surface. Claw keeps a minimal entity-page wiki.
   *Resolution:* defer auto Obsidian writeback, but ship a belief review
   queue (CLI or simple web view) so the user can accept / reject / correct
   newly extracted beliefs. This preserves Gemini's HITL control plane
   without bidirectional Obsidian sync.

2. **Stage 2 (entity edges) in v1.** Codex / Gemini / claw keep entity edges
   in v1 because mentioned-entity neighborhood expansion is a strong
   candidate lane. Claude Opus 4.7 defers Layer-3 entity expansion until
   retrieval shows gaps.
   *Resolution:* keep `entities` and `entity_edges` in v1 schema, but treat
   the entity-neighborhood candidate lane as conditional on retrieval
   evals — only ship live if it improves precision.

3. **What goes into the vector index.** Gemini: never raw turns, only
   synthesized claims and concise summaries — raw conversational filler
   poisons the index. Codex: segments and beliefs. Opus 4.7: segments. Claw:
   ambiguous.
   *Resolution:* embed topic segments and accepted beliefs. Do not embed
   single raw turns. Keep raw messages in Postgres for provenance and
   rendering, not for retrieval.

4. **Topic-segment vs whole-conversation as the canonical chunk.**
   Codex / Gemini / Opus 4.7 want topic segments. Claw defaults to whole
   conversations.
   *Resolution:* topic segments. Short conversations may produce a single
   segment; the segmentation prompt should be a no-op when content is
   already coherent. Storing both `conversation_id` and `segment_id`
   preserves coarser fallback if segment-level extraction underperforms.

5. **Live ranking: simple weighted vs. LLM reranker.** Gemini wants an LLM
   cross-encoder reranker as a quality gate. Codex / Opus 4.7 prefer a
   simple weighted scorer first.
   *Resolution:* simple weighted scorer for v1; an LLM reranker is an
   offline experiment that can graduate to live serving after eval results
   justify the latency cost.

6. **Stability / lifespan classification.** Opus 4.7 most explicitly: tag
   each fact as `permanent` / `slow-changing` / `transient` at extraction
   so the ranker can weight differently. Codex proposes `stability_class`
   with a longer enum (`identity`, `preference`, `project_status`, `goal`,
   `task`, `mood`, `relationship`). Gemini / claw don't address it.
   *Resolution:* required field at extraction. Use the enum from Codex; it
   carries more retrieval signal than three buckets.

7. **Negative-space facts.** Opus 4.7 raises this — facts you'd want in
   context but no query will retrieve ("user has no kids", "does not use
   Twitter"). Other reviewers don't address.
   *Resolution:* not a v1 schema decision, but flag for adversarial round.
   Standing context can carry hand-curated negative facts initially.

## Hard-To-Reverse Decisions

These structurally constrain everything downstream. Get them right before
writing the first migration.

1. **Bitemporal columns on beliefs.** `valid_from`, `valid_to`,
   `observed_at`, `recorded_at`, `superseded_by`. Backfilling temporal
   intent into a flat fact table after the fact is approximately
   impossible — the LLM no longer has the original evidence chain to
   reason about validity windows.
2. **Provenance constraint.** `evidence_ids` NOT NULL on accepted beliefs.
   Adding this constraint after beliefs already exist forces a rebuild.
3. **Three-tier separation: episodes → claims → beliefs.** Once a stage
   reads from a stage that itself contains synthesis, you have a
   hallucination amplifier. The boundary must be enforced from the first
   migration.
4. **Stability class at extraction time.** The model that extracted the
   belief had the most context about its lifespan — re-classifying years
   later from text alone is much worse.
5. **Belief audit log.** `model`, `prompt_version`, `input_claim_ids`,
   `evidence_episode_ids`, `score_breakdown`, `created_at`. Without this,
   rolling back damage from a bad extraction prompt requires throwing
   everything away.
6. **Episodes / messages / notes / captures are immutable.** No deletes,
   no in-place edits. Re-segmentation and re-extraction must be
   non-destructive.

## Deferrable Decisions

Safe to push out without compromising future optionality.

- Graph backend (Apache AGE / Neo4j / Kuzu) — relational edges support the
  eventual move to AGE inside the same Postgres instance.
- LLM cross-encoder reranker — offline experiment, promote on eval signal.
- Negative-space catalog — manual standing facts cover v1.
- Wiki auto-writeback to Obsidian — ship review queue first.
- Goal progress inference, failure pattern detection, hypotheses, causal
  links, patterns.
- Bidirectional Obsidian sync.
- Adversarial re-extraction sweeps — useful research probe, not v1 product.
- Async precompute of context packages per active project.
- Multi-source ingestion beyond ChatGPT + Obsidian + capture.

## Recommended V1 Architecture

**Pipeline shape**

```text
sources
  → conversations / notes / captures        (immutable raw evidence)
  → messages                                (immutable raw evidence)
  → segments                                (topic-segmented, embedded)
  → claims                                  (LLM-extracted, evidence_ids required)
  → beliefs                                 (bitemporal, status-tracked, stability-classed)
  → current_beliefs (view)
  → context_for(conversation)               (multi-lane compiler, sectioned output)
```

**Schema primitives**

```text
sources
conversations
messages
notes
captures
segments
claims
beliefs
entities
entity_edges
embedding_cache
context_feedback
belief_audit
```

**Belief shape (required fields on accepted state)**

```text
id
subject_entity_id
predicate
object_entity_id | value_text | value_json
valid_from
valid_to            (NULL = currently valid)
observed_at
recorded_at
superseded_by
status              (candidate | provisional | accepted | superseded | rejected)
stability_class     (identity | preference | project_status | goal | task | mood | relationship)
confidence
evidence_ids        (NOT NULL — at least one raw episode id)
prompt_version
model_version
```

**Vector index policy**

- Embed: topic segments, accepted beliefs (text form).
- Do not embed: raw single turns, ad-hoc messages without segment context.
- Keep raw messages in Postgres for provenance and rendering only.

**`context_for` shape**

```text
Standing Context           (~300-800 tokens — identity, active goals/projects)
Active Projects / Goals    (~700 tokens)
Relevant Beliefs           (~1200 tokens — current_beliefs filtered by query)
Recent Signals             (~600 tokens — last N days of activity)
Entity Context             (~900 tokens — mentioned-entity neighborhood, conditional)
Raw Evidence Snippets      (~1000 tokens — citations supporting Relevant Beliefs)
Uncertain / Conflicting    (only when topic-relevant)
```

Every section has an explicit token budget. Defaults to current beliefs
(`valid_to IS NULL`); historical beliefs surface only when the conversation
asks for history or an old belief scores high enough with explicit historical
labeling.

**Ranking (v1)**

Simple weighted scorer over candidate set:

```text
score =
    relevance
  * currentness
  * confidence
  * specificity
  * source_quality
  * recurrence
  * task_fit
  - redundancy
  - stale_penalty
```

`currentness` and `stale_penalty` are computed against `stability_class` —
identity beliefs get near-flat decay, transient beliefs decay fast.

**Sources (v1)**

ChatGPT export + Obsidian vault + MCP capture. Defer Claude / Gemini exports
and bulk Evernote migration — same pipeline shape, no new architectural
signal, easy to add later.

**HITL feedback (v1)**

A belief review queue (CLI or thin web view) surfaces newly accepted
beliefs for accept / reject / correct / promote-to-pinned. This replaces the
wiki as the v1 control plane. Plus a one-keystroke "this context was wrong"
annotation on `context_for` outputs that flows into `context_feedback`.

**Eval harness (v1)**

25-50 hand-written prompts covering current-project continuation, past
decision recall, person/entity recall, style preference, active goals,
failure avoidance, historical self-state, stale-fact suppression. Metrics:
precision, recall of known-important memories, stale fact rate, unsupported
belief rate, contradiction rate, token waste, human usefulness rating. Eval
set runs on a small ChatGPT subset (e.g., last 100 conversations) before
full-corpus consolidation.

**Build order**

```text
1.  PostgreSQL + pgvector baseline
2.  ChatGPT ingest into raw conversations/messages (immutable)
3.  Topic segmentation
4.  Segment embeddings
5.  Claim extraction with evidence_ids
6.  Belief consolidation (bitemporal + stability_class)
7.  Entity canonicalization + entity_edges
8.  current_beliefs materialized view
9.  Belief review queue (CLI accept / reject / correct)
10. context_for candidate generation (multi-lane)
11. Ranking + sectioned token packing
12. MCP exposure of context_for
13. context_feedback capture (this-is-wrong / stale / irrelevant / useful)
14. Small-batch evals (100 conversations) before full-corpus run
15. Full-corpus consolidation
16. Add Obsidian as a source after evals stabilize
```

## Recommended Research / Experimental Architecture

This is also a local research lab. Things worth running offline against the
live store, not gating v1:

1. **Adversarial re-extraction sweeps.** Take high-confidence accepted
   beliefs and run a falsification prompt: "what evidence would contradict
   this — search episodes for it." Surface conflicts as new contradictions.
   Substitute for engagement signals.
2. **Prompt-version replay.** Re-run claim extraction at prompt version
   N+1 against a frozen segment set; diff resulting belief sets; measure
   regression. Audit log makes this cheap.
3. **LLM-as-judge reranker.** Train / prompt a cross-encoder over
   (conversation, candidate belief) pairs; promote into live ranking only
   if eval gain exceeds latency cost.
4. **Apache AGE experiment.** Mirror `entity_edges` into AGE; benchmark
   path queries that are ugly in SQL (e.g., "shared topic between person
   A and project B over 3 hops"). Promote only if 10+ retrieval queries
   are demonstrably valuable and slow in SQL.
5. **Negative-space catalog.** A separate hand-curated table of facts that
   should appear in standing context but no query will retrieve. Treat
   as a research probe before deciding on a synthesis approach.
6. **Stability-class auto-classifier eval.** Compare LLM-tagged stability
   against a manually labeled subset; measure drift over time.
7. **Hypothesis revival.** Reintroduce hypotheses only after the eval
   harness can bound unsupported-belief rate; they remain too dangerous
   without that backstop.

## Decision Matrix

| Decision | Options | Model Positions | Risk | Recommendation | Reversibility |
|----------|---------|-----------------|------|----------------|---------------|
| Canonical memory store | flat facts; episodes → claims → beliefs separated; event sourcing | Codex: separate. Gemini: separate (raw → claims → wiki state). Opus: separate (episodes → facts with provenance). claw: separate (raw episodes only feed stage 1). | Mixing extracts and synthesis is the core hallucination amplifier. | Three-tier: immutable raw → claims → beliefs. Episodes never edited. | LOW — locked in for v1, but boundary itself is durable. |
| Graph backend | none / relational; Apache AGE; Neo4j; FalkorDB; Kuzu | All four: none for v1. Codex / Opus: AGE later if needed. | Operational overhead, polyglot persistence. | None. Relational `entity_edges`. AGE on same Postgres if and when 10+ queries are gnarly. | HIGH — easy to add later. |
| Temporal model | naive age decay; bitemporal validity (SCD2); event sourcing; entity snapshots | All four: validity. Opus / Gemini / Codex explicit on `valid_from`/`valid_to`. | Backfilling temporal intent is approximately impossible. | Bitemporal: `valid_from`, `valid_to`, `observed_at`, `recorded_at`, `superseded_by`. Close-and-insert on contradiction. | LOW — structural for v1. |
| Ingestion granularity | turn; whole conversation; topic segment | Codex / Gemini / Opus: segment. claw: conversation, segment if long. | Sub-segment = bad facts. Over-segment = bad coreference. | Topic segments via LLM segmentation. Short conversations may yield one segment. Raw messages preserved. | MED — re-segmentable but expensive. |
| Vector index content | raw turns; segments; beliefs; segments + beliefs | Gemini: never raw. Codex: segments + beliefs. Opus: segments. claw: ambiguous. | Embedding raw turns wastes index quality. | Embed topic segments + accepted beliefs. No raw turn embeddings. | LOW — re-embed offline. |
| Context ranking | passive search; simple weighted scorer; LLM cross-encoder reranker | All four: active assembly. Codex / Opus: simple weighted first. Gemini: LLM reranker. | LLM reranker = live latency + serving cost. | Simple weighted scorer for v1. LLM reranker as offline experiment. | LOW. |
| Wiki output timing | v1 essential; v1 partial (index page only); v1 deferred | Gemini: essential (HITL control plane). Codex: index page only. Opus: cut entirely. claw: minimal entity pages. | Gemini's argument: without HITL the system drifts. Counter-risk: bad beliefs amplified into Markdown. | Defer auto Obsidian writeback. Ship belief review queue (CLI/web) as v1 substitute. | LOW — wiki can be added on top of stable beliefs. |
| Goal / failure / hypothesis inference | infer from facts; manual capture only; defer entirely | All four: defer. | Synthesis-of-synthesis without grounding. | Defer. Goals only when manually declared via capture. | LOW. |
| Eval harness timing | post-MVP; before full corpus run | Codex / Opus explicit: before full corpus. | 3,400 conversations consolidated without evals = wasted weeks + contaminated beliefs. | Eval set lands before full-corpus consolidation step in build order. | LOW. |
| Stability tagging | tag at extraction; infer later; none | Opus: 3 buckets. Codex: 7-class enum. Gemini / claw: silent. | Without it, recency is the only currency signal. | `stability_class` column, set at extraction by LLM. Use Codex enum. | MED — re-classification feasible. |
| Provenance enforcement | `evidence_ids` NOT NULL on accepted beliefs; advisory | All four: enforce. | Without it, hallucinations cascade silently. | NOT NULL constraint. Belief cannot enter `accepted` without at least one episode id. | LOW — cheap to enforce up front; expensive to backfill. |
| HITL feedback primitive | wiki bidirectional sync; review queue + this-is-wrong; engagement telemetry; none | Gemini: wiki sync. Opus: this-is-wrong on wiki. Codex: feedback log table. claw: implicit. | Without HITL, the system has no correction signal. | Belief review queue + `context_feedback` table for live "wrong / stale / irrelevant / useful" annotations. | LOW. |
| v1 sources | ChatGPT only; ChatGPT + Obsidian; ChatGPT + Claude + Gemini; all five | Codex: ChatGPT + Obsidian. Opus: ChatGPT + Obsidian + capture. Gemini: scope unspecified. claw: implicit broad. | Each new source = new edge cases. | ChatGPT + Obsidian + capture. Defer Claude / Gemini export and Evernote bulk migration. | LOW. |

## Top 10 Questions For Adversarial Rounds

1. Is one segment-level claim-extraction prompt sufficient, or should
   extraction be split by belief type (identity, preference, project_status,
   relationship) so each prompt has a tighter schema?
2. Should the embedding index hold segments and beliefs in the same
   pgvector column / table, or in separate tables with separate HNSW
   indexes — and does dual-source retrieval hurt recall calibration?
3. What is the minimum entity canonicalization v1 needs to make
   `entity_edges` useful? Deterministic alias matching + LLM tiebreak,
   embedding-based clustering, or both?
4. Should `context_for` run synchronously inside the live MCP path, or
   should it precompute context packages async per active project /
   running conversation and serve from cache?
5. Without bidirectional wiki sync, is "review queue + `context_feedback`"
   a rich enough HITL signal? Or do we need richer feedback primitives
   (correct / promote-to-pinned / demote-to-historical / recategorize)?
6. How do we prevent the topic-segmentation prompt from itself becoming
   a hallucination source — the LLM inventing topic boundaries that
   distort downstream extraction? Validation set? Compare-against-
   conversation-summary check?
7. Which belief types should NEVER auto-promote to `accepted` and must
   always pass through human review (e.g., relationship beliefs about
   third parties, identity beliefs about the user)?
8. How many beliefs / segments can local Qwen3.6:35B-MOE realistically
   score in a synchronous `context_for` call before live latency exceeds
   the user's tolerance? What is that tolerance?
9. For the eval harness: who writes the gold answers? The user manually,
   an LLM judge over user-confirmed corpus subsets, or both? How do we
   prevent the judge from sharing failure modes with the extractor?
10. For stale-memory tests: how do we generate adversarial "true in 2022,
    wrong now" examples without polluting the eval set with the same
    model that wrote the wrong fact? Held-out human labels, or
    cross-model adversarial generation?

## Strongest Dissent Against The Recommendation

The deferred wiki layer is the most credible counter-position, championed
by Gemini.

> *Without the wiki, you have no human grounding signal. "This-is-wrong"
> feedback on retrieved context is far thinner than a human reading and
> editing a synthesized entity page. The eval set tests retrieval, not
> extraction — by the time you build the wiki in v2, your `beliefs` table
> is contaminated, and you face exactly the migration problem you tried
> to avoid by deferring it. The HITL signal is structural, not cosmetic.*

The recommended path mitigates this with a belief review queue, but the
review queue is narrower than a wiki: the user reviews beliefs in
isolation, not as composed entity narratives. Reading a synthesized
"Person Y" page exposes incoherence between beliefs that no
per-belief review will catch.

If the review queue proves insufficient against the eval harness,
promoting wiki output ahead of full-corpus consolidation is the right
escalation. The hard requirement is that wiki pages remain a derived
projection — never canonical — so they can be regenerated after belief
corrections without losing fidelity.
