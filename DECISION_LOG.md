# Decision Log

Status: post round-1 synthesis
Date: 2026-04-27

This file records architecture decisions after review. Keep decisions short,
explicit, and reversible where possible.

Status values:

```text
proposed
accepted
deferred
rejected
superseded
```

## Decisions

| ID | Status | Decision | Reason | Consequences | Revisit Trigger |
|----|--------|----------|--------|--------------|-----------------|
| D001 | accepted | `context_for(conversation)` is the primary product surface. | Engram is only useful if it improves the next AI interaction. | Retrieval, ranking, temporal modeling, and graph work judged by context quality. | Revisit only if another product surface becomes primary. |
| D002 | accepted | Three-tier separation: immutable raw evidence → claims → beliefs. | Mixing extraction and synthesis is the core hallucination amplifier. | Boundary enforced from first migration. Derived projections rebuildable from raw evidence. | Revisit only if a graph-native canonical store becomes the explicit architecture. |
| D003 | accepted | Accepted beliefs must cite at least one raw evidence id. | Provenance is the central circuit breaker. Synthesis-of-synthesis without grounding is forbidden. | `evidence_ids` NOT NULL on accepted beliefs. Beliefs without evidence cannot leave the candidate / provisional state. | Revisit only if a reliable human approval workflow replaces evidence citation. |
| D004 | accepted | Bitemporal validity replaces naive age decay. | Old facts may remain true; fresh facts may be wrong. Confidence and time are orthogonal. | `valid_from`, `valid_to`, `observed_at`, `recorded_at`, `superseded_by`. Close-and-insert on contradiction; never UPDATE in place. | Revisit if temporal evals show the model is too complex to maintain. |
| D005 | accepted | Topic segments are the main embedding and extraction unit. | Single turns lack context; whole conversations are too broad. | LLM-driven segmentation before extraction. Raw messages preserved for provenance. | Revisit after segment-level vs turn-level retrieval evals. |
| D006 | accepted | Defer auto Obsidian wiki writeback in v1. Ship a belief review queue instead. | Wiki auto-generation can amplify bad synthesis into human-facing documentation. A review queue preserves HITL without bidirectional sync. | CLI / thin web view for accept / reject / correct on newly extracted beliefs. No wiki pages written to vault in v1 except possibly a single index page. | Revisit if review queue proves insufficient against eval harness, or if Gemini's HITL argument wins on data. |
| D007 | accepted | No graph backend in v1. Relational `entity_edges` only. | Personal scale is well within recursive-CTE territory. Operational overhead of separate graph stores is not justified. | Apache AGE remains the eventual answer if SQL becomes ugly because it stays inside Postgres. | Revisit when 10+ retrieval queries are demonstrably valuable and slow in SQL. |
| D008 | accepted | Stability class assigned at extraction time. | Recency alone is the wrong currency signal. Lifespan needs to be tagged when the LLM still has full context. | `stability_class` enum: identity, preference, project_status, goal, task, mood, relationship. Required field on accepted beliefs. | Revisit after measuring auto-classifier drift on a manually labeled subset. |
| D009 | accepted | Vector index holds topic segments and accepted beliefs. Raw turns are not embedded. | Raw conversational filler poisons the index. Synthesized assertions and topic-coherent segments are what retrieval should target. | Two embedding sources, both pgvector. Raw messages remain in Postgres for provenance and rendering. | Revisit if dual-source retrieval distorts recall calibration. |
| D010 | accepted | Belief audit log is mandatory. | Without it, rolling back damage from a bad extraction prompt requires throwing everything away. | `belief_audit` table records model, prompt_version, input_claim_ids, evidence_episode_ids, score_breakdown, created_at on every belief operation. | Revisit only if storage cost becomes prohibitive. |
| D011 | accepted | Simple weighted scorer for live ranking in v1. | Live latency budget rules out an LLM cross-encoder reranker. Weighted scoring is inspectable and tunable. | Score = relevance × currentness × confidence × specificity × source_quality × recurrence × task_fit − redundancy − stale_penalty. | Revisit if eval gain from an offline LLM reranker exceeds latency cost. |
| D012 | accepted | Eval harness lands before full-corpus consolidation. | Running consolidation on 3,400 conversations without a gold set wastes local-inference time and contaminates beliefs. | 25–50 prompt gold set runs against a 100-conversation subset before the full ChatGPT corpus is consolidated. | Revisit only if the eval set itself proves miscalibrated. |
| D013 | accepted | v1 sources: ChatGPT export + Obsidian vault + MCP capture. | Each new source is new edge cases. ChatGPT + notes + capture covers the high-signal personal corpus. | Defer Claude export, Gemini Takeout, and bulk Evernote → Obsidian migration. Same pipeline shape, easy to add later. | Revisit after v1 evals stabilize and adding sources is the next-leverage move. |
| D014 | accepted | Cut hypotheses, failure pattern detection, causal links, patterns, and goal progress inference from v1. | Highest-risk hallucination amplifiers. None has a v1 product use that justifies the contamination risk. | Pipeline stages 3, 4, 6, 7, 8 all deleted from build order. Goals only enter via manual capture. | Revisit individually only after eval harness can bound unsupported-belief rate. |
| D015 | accepted | `context_feedback` capture ships in v1 alongside `context_for`. | Live "this-is-wrong / stale / irrelevant / useful" feedback is the live-path companion to the review queue. | Annotated context outputs flow into `context_feedback` with the belief ids and segment ids that produced them. | Revisit if the signal proves too sparse to drive ranking changes. |

## Deferred Decisions

| ID | Status | Decision | Reason | Revisit Trigger |
|----|--------|----------|--------|-----------------|
| F001 | deferred | Apache AGE / Neo4j / Kuzu graph backend. | Relational entity edges sufficient for v1. | 10+ retrieval queries are valuable and slow in SQL. |
| F002 | deferred | Auto wiki writeback to Obsidian. | Risk of amplifying bad synthesis. Review queue covers HITL in v1. | Review queue insufficient against eval harness, or stable beliefs warrant rendered docs. |
| F003 | deferred | LLM cross-encoder reranker in live path. | Latency cost vs. v1 ranking quality. | Offline experiment shows precision gain exceeds latency cost. |
| F004 | deferred | Adversarial re-extraction sweeps. | Useful research probe, not a v1 product. | After v1 eval harness can measure falsification gain. |
| F005 | deferred | Negative-space catalog (e.g., "user has no kids"). | Manual standing facts cover v1. | After observing recurring negative-fact omissions in context_for outputs. |
| F006 | deferred | Bidirectional Obsidian sync. | Single-direction read is enough for v1 ingestion. | After wiki layer ships and edits accumulate. |
| F007 | deferred | Async precompute of context packages per active project. | Synchronous serve is simpler and exposes latency reality. | If live latency exceeds tolerance after ranking is implemented. |
| F008 | deferred | Multi-source ingestion: Claude export, Gemini Takeout, Evernote bulk. | Same pipeline shape as ChatGPT — incremental, not architectural. | After v1 evals stabilize. |
| F009 | deferred | Goal progress inference, failure pattern detection, hypotheses, causal links, patterns. | All hallucination-amplifier risk. | Re-evaluate per stage after eval harness bounds unsupported-belief rate. |
| F010 | deferred | Cross-model judge for eval gold-set construction. | v1 starts with hand-written prompts and human gold answers. | After hand-written gold set hits coverage limits. |

## Rejected Decisions

| ID | Status | Decision | Reason |
|----|--------|----------|--------|
| R001 | rejected | Naive SQL age decay with soft-delete threshold. | Old facts may remain true. Confidence and time are orthogonal axes. Superseded by D004. |
| R002 | rejected | One episode per human+assistant turn as the canonical embedding/extraction unit. | Sub-segment context loss; LLM cannot ground claims in fragments. Superseded by D005. |
| R003 | rejected | Passive MCP tools (`search`, `recall`) as the live serving path. | LLMs cannot meta-cognize their own knowledge gaps. `context_for` is the active compiler. Superseded by D001. |
| R004 | rejected | Synthesized facts feeding back into the consolidation pipeline. | Hallucination compounding without exogenous grounding. Superseded by D002 / D003. |
| R005 | rejected | Schema borrowed wholesale from Stash's 20 migrations (`patterns`, `causal_links`, `hypotheses`, `failures`, `contradictions`, `contexts` as v1 tables). | Most are v2+ ambitions; including them in v1 means tuning prompts that produce ungrounded synthesis. Schema is rebuilt around the three-tier model. Superseded by D002 / D014. |

## Open Decisions

| ID | Question | Options | Needed Evidence | Target Round |
|----|----------|---------|-----------------|--------------|
| O001 | Single claim-extraction prompt or split by belief type (identity / preference / project_status / relationship)? | one universal; per-type; hierarchical (universal then per-type refinement) | Comparative extraction quality on a 20-segment sample, per stability class | Temporal / extraction specialist |
| O002 | Same vs. separate pgvector tables for segments and beliefs? | shared table with `kind` discriminator; two tables with two HNSW indexes | Recall calibration test against gold prompts; index size / query latency | Context_for specialist |
| O003 | Entity canonicalization strategy. | deterministic alias matching only; embedding clustering only; deterministic + LLM tiebreak | Precision/recall on a hand-labeled entity set (~200 entities) | Graph maximalist / graph skeptic |
| O004 | Sync vs. async `context_for`. | live synchronous; async precompute per active project; hybrid (precompute standing + live retrieve) | Latency measurement on local Qwen3.6:35B + pgvector at corpus scale | Context_for specialist |
| O005 | Belief review queue feedback richness. | binary accept/reject; full primitives (correct / promote-to-pinned / demote-to-historical / recategorize) | User trial on 50 reviewed beliefs; correction-rate signal | V1 scope killer |
| O006 | Topic-segmentation safety. | LLM segmentation only; LLM + rule-based fallback; LLM + summary-consistency check | Segmentation drift on a 50-conversation eval; downstream claim-quality delta | Temporal / extraction specialist |
| O007 | Which belief types must NEVER auto-promote to `accepted`? | none; identity beliefs about user; relationship beliefs about third parties; both | Failure analysis on a deliberately adversarial extraction batch | Temporal / extraction specialist |
| O008 | Eval gold-set authorship model. | user manual; LLM judge over user-confirmed subsets; both | Inter-rater agreement between user gold and LLM judge on 25 prompts | Eval specialist |
| O009 | Stale-memory adversarial example generation without polluting the eval set. | held-out human labels only; cross-model adversarial generator; user-curated historical corpus | Generator-extractor failure-mode overlap analysis | Eval specialist |
| O010 | When (and whether) to revive hypotheses, causal links, and patterns. | never; after eval harness bounds unsupported-belief rate; opportunistic per use case | v1 eval results; specific retrieval queries that demand them | V1 scope killer (post-v1) |

## Revisit Triggers (summary)

These decisions are accepted but should not be treated as permanent:

- **D006 (defer wiki writeback)** — revisit if review queue feedback is too
  sparse or eval shows extraction errors that only entity-page composition
  would catch.
- **D007 (no graph backend)** — revisit when 10+ valuable graph-shaped
  queries are slow / ugly in SQL.
- **D008 (stability class enum)** — revisit if the 7-class enum proves
  unstable; collapse to 3 buckets if needed.
- **D009 (segments + beliefs in vector index)** — revisit if dual-source
  retrieval distorts recall calibration.
- **D011 (simple weighted scorer)** — revisit if offline LLM reranker eval
  gain exceeds live latency cost.
- **D013 (v1 sources)** — revisit after v1 evals stabilize.
- **D014 (cut stages 3/4/6/7/8)** — revisit per stage after eval harness
  bounds unsupported-belief rate.
