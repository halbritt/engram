# Prior Art

Engram's core idea is not that no one has tried "LLM memory." The important
claim is narrower: many systems implement pieces of durable agent memory, but
Engram keeps stricter boundaries between raw evidence, model-derived claims,
consolidated beliefs, provenance, privacy, evaluation, and re-derivation.

Engram's intended pipeline:

```text
immutable raw evidence -> segments -> claims -> beliefs -> context_for
```

## Summary

Prior art strongly supports Engram's premise that useful long-running AI systems
need durable state outside the context window. The work falls into several
clusters:

- classic belief / truth-maintenance systems
- retrieval-augmented generation
- LLM agent memory architectures
- reflection / skill / tool-using agents
- graph and knowledge-graph RAG
- commercial product memories
- long-term memory benchmarks

Engram's distinction is not novelty of "memory" in the abstract. It is the
combination of:

- immutable raw evidence as the source of truth
- LLM-derived claims as untrusted interpretations
- beliefs as adjudicated, temporal, confidence-bearing state
- provenance from beliefs back to raw rows
- non-destructive re-derivation across prompt/model versions
- local-first operation and structural corpus/network separation
- privacy-tier inheritance and invalidation on retrieval-visible rows
- gold-set evaluation before relying on the memory layer

## Classic Belief Maintenance

### Truth Maintenance Systems

Truth Maintenance Systems (TMS) predate LLMs by decades. They maintain beliefs
along with the reasons for those beliefs, and revise belief state when
assumptions are contradicted.

Relevant work:

- Jon Doyle, "A Truth Maintenance System" (1979):
  https://www.sciencedirect.com/science/article/pii/0004370279900080

Engram distinction:

- TMS gives Engram the philosophical frame: beliefs need justifications.
- Engram applies that idea to messy personal corpora with LLM extraction,
  immutable raw evidence, temporal validity, privacy tiers, and vector retrieval.
- Engram does not let the LLM's interpretation become the source of truth; it
  remains a derivation from raw evidence.

## Retrieval-Augmented Generation

### RAG

RAG established the now-standard pattern of pairing parametric model knowledge
with retrieved non-parametric memory.

Relevant work:

- Lewis et al., "Retrieval-Augmented Generation for Knowledge-Intensive NLP
  Tasks" (2020): https://arxiv.org/abs/2005.11401

Engram distinction:

- RAG retrieves documents/passages to support generation.
- Engram's retrieval target is not raw documents alone; it is a curated memory
  substrate of segments and accepted beliefs.
- RAG typically treats retrieved text as context. Engram treats retrieved items
  as provenance-bearing objects with privacy, versioning, and lifecycle state.

### Self-RAG and reflective retrieval

Self-RAG adds model-side decisions about when to retrieve and how to critique
retrieved evidence and generated answers.

Relevant work:

- Asai et al., "Self-RAG: Learning to Retrieve, Generate, and Critique through
  Self-Reflection" (2023): https://arxiv.org/abs/2310.11511

Engram distinction:

- Self-RAG improves generation-time behavior.
- Engram focuses on the corpus-side memory layer: what durable state exists,
  how it was derived, and whether it can be rebuilt or invalidated.
- Engram may later use self-critique at extraction or serving time, but the
  memory objects must remain auditable outside one model invocation.

## LLM Agent Memory Architectures

### Generative Agents

Generative Agents stores observations, retrieves memories, synthesizes
reflections, and uses planning to produce believable behavior.

Relevant work:

- Park et al., "Generative Agents: Interactive Simulacra of Human Behavior"
  (2023): https://arxiv.org/abs/2304.03442

Engram distinction:

- Generative Agents validates the observation/reflection/planning pattern.
- Engram is less interested in simulating an agent and more interested in
  building an auditable personal memory substrate.
- Reflections in agent systems can become model-authored memory. Engram splits
  that into claims and beliefs with evidence and review.

### MemoryBank

MemoryBank explores long-term memory for LLM companions, including storing and
retrieving prior interactions.

Relevant work:

- Zhong et al., "MemoryBank: Enhancing Large Language Models with Long-Term
  Memory" (2023): https://arxiv.org/abs/2305.10250

Engram distinction:

- MemoryBank is close to the personal-companion use case.
- Engram adds stricter raw/derived separation, provenance, temporal belief
  management, privacy inheritance, and non-destructive reprocessing.

### MemGPT / Letta

MemGPT introduced an OS-style memory hierarchy for LLM agents: limited
in-context memory plus larger recall/archival memory outside the context
window. Letta continues that line as an open-source agent platform.

Relevant work:

- Packer et al., "MemGPT: Towards LLMs as Operating Systems" (2023):
  https://arxiv.org/abs/2310.08560
- Letta memory management docs:
  https://docs.letta.com/concepts/memory-management
- Letta MemGPT architecture docs:
  https://docs.letta.com/guides/agents/architectures/memgpt

Engram distinction:

- MemGPT/Letta centers agentic memory management: the agent can decide what to
  keep in core, recall, or archival memory.
- Engram centers evidence discipline: the memory layer is built by a supervised
  derivation pipeline, not by unconstrained self-editing.
- Engram can serve agents, but the corpus-reading process is deliberately
  separated from network/action-taking processes.

## Reflection, Tools, and Skill Memory

### ReAct and Toolformer

ReAct interleaves reasoning and acting. Toolformer trains language models to
call external tools.

Relevant work:

- Yao et al., "ReAct: Synergizing Reasoning and Acting in Language Models"
  (2022): https://arxiv.org/abs/2210.03629
- Schick et al., "Toolformer: Language Models Can Teach Themselves to Use
  Tools" (2023): https://arxiv.org/abs/2302.04761

Engram distinction:

- These works inform how a consumer model might use Engram.
- Engram is not itself an action loop. It is the memory substrate that an action
  loop can query through `context_for`.
- Tool use increases the importance of keeping corpus access and network egress
  separate.

### Reflexion and Voyager

Reflexion stores verbal feedback to improve future agent attempts. Voyager
builds an executable skill library while interacting with Minecraft.

Relevant work:

- Shinn et al., "Reflexion: Language Agents with Verbal Reinforcement Learning"
  (2023): https://arxiv.org/abs/2303.11366
- Wang et al., "Voyager: An Open-Ended Embodied Agent with Large Language
  Models" (2023): https://arxiv.org/abs/2305.16291

Engram distinction:

- Reflexion and Voyager are about learning from action outcomes.
- Engram's near-term memory is biographical and factual, not procedural skill
  acquisition.
- Future Engram phases could add procedural memory, but it should remain a
  separate belief/skill layer with provenance and feedback.

## Graph and Knowledge-Graph RAG

### GraphRAG / GRAG / LightRAG

Graph-based RAG systems try to overcome flat vector retrieval by adding entity,
relation, or community structure.

Relevant work:

- Microsoft GraphRAG project:
  https://www.microsoft.com/en-us/research/project/graphrag/
- Hu et al., "GRAG: Graph Retrieval-Augmented Generation" (2024):
  https://arxiv.org/abs/2405.16506
- Guo et al., "LightRAG: Simple and Fast Retrieval-Augmented Generation" (2024):
  https://arxiv.org/abs/2410.05779

Engram distinction:

- GraphRAG improves retrieval over connected corpora.
- Engram defers graph complexity until the claim/belief layer is grounded.
- When Engram adds entity canonicalization and edges, those graph facts should
  remain derived and rebuildable, not a second source of truth.

### HippoRAG

HippoRAG uses graph-like indexing inspired by hippocampal memory to support
long-term knowledge integration.

Relevant work:

- Gutiérrez et al., "HippoRAG: Neurobiologically Inspired Long-Term Memory for
  Large Language Models" (2024): https://arxiv.org/abs/2405.14831

Engram distinction:

- HippoRAG is a retrieval architecture.
- Engram's first problem is not just retrieving related information; it is
  deciding what the system is allowed to believe, when it was true, and why.

### Zep temporal knowledge graph

Zep is especially relevant because it explicitly frames agent memory around a
temporal knowledge graph extracted from episodes.

Relevant work:

- "Zep: A Temporal Knowledge Graph Architecture for Agent Memory" (2025):
  https://blog.getzep.com/content/files/2025/01/ZEP__USING_KNOWLEDGE_GRAPHS_TO_POWER_LLM_AGENT_MEMORY_2025011700.pdf

Engram distinction:

- Zep is one of the closest known systems: episodes, extracted facts, temporal
  graph memory, and retrieval for agents.
- Engram's differentiators are local-first operation, raw immutability,
  privacy-tier invalidation, explicit claim-vs-belief staging, and
  non-destructive model/prompt re-derivation.

## Commercial Product Memory

### ChatGPT, Claude, Gemini

Major assistants now expose user-facing memory features.

Relevant product docs:

- OpenAI ChatGPT Memory FAQ:
  https://help.openai.com/en/articles/8590148-memory-faq
- Anthropic Claude memory announcement:
  https://www.anthropic.com/news/memory
- Anthropic memory tool docs:
  https://docs.claude.com/en/docs/agents-and-tools/tool-use/memory-tool
- Google Gemini saved info docs:
  https://support.google.com/gemini/answer/16035369

Engram distinction:

- Product memories validate that persistent personalization matters.
- Their internals are mostly opaque to the user and not portable across
  providers.
- Engram's memory is local, inspectable, exportable, and versioned.
- Engram's goal is not just "remember this preference"; it is to maintain a
  provenance-carrying belief layer that can be corrected, re-derived, and served
  to multiple consumers.

## Long-Term Memory Evaluation

### LoCoMo

LoCoMo evaluates long-term conversational memory across long, temporally
structured dialogues.

Relevant work:

- Maharana et al., "Evaluating Very Long-Term Conversational Memory of LLM
  Agents" (2024): https://arxiv.org/abs/2402.17753

Engram distinction:

- LoCoMo is useful background for long-term memory tasks: single-hop,
  multi-hop, temporal, summarization, and adversarial questions.
- Engram's gold set should be subject-authored and grounded in the actual
  corpus, because the target is one person's real memory, not a synthetic
  benchmark distribution.

### LongMemEval

LongMemEval evaluates information extraction, multi-session reasoning,
temporal reasoning, updates, and abstention in chat assistants.

Relevant work:

- Wu et al., "LongMemEval: Benchmarking Chat Assistants on Long-Term
  Interactive Memory" (2024): https://arxiv.org/abs/2410.10813

Engram distinction:

- LongMemEval's categories map well to Engram's planned gold set.
- Engram should include abstention / missing-data prompts, stale-fact prompts,
  temporal-update prompts, and contradiction prompts.
- Engram's gold set should test retrieval *and* belief correctness, not just
  whether the right old conversation can be found.

### Memory mechanism surveys

Survey papers confirm that LLM-agent memory is now an active research area with
many storage, retrieval, and update strategies.

Relevant work:

- Zhang et al., "A Survey on the Memory Mechanism of Large Language Model based
  Agents" (2024): https://arxiv.org/abs/2404.13501
- "On the Structural Memory of LLM Agents" (2024):
  https://arxiv.org/abs/2412.15266

Engram distinction:

- Surveys show the design space is broad: buffers, summaries, vector stores,
  graphs, episodic memory, semantic memory, procedural memory, and reflective
  memory.
- Engram deliberately starts narrower: raw evidence, topic segments, claims,
  beliefs, and `context_for`.
- The narrower start is a safety feature. It avoids creating many memory types
  before the system can evaluate whether any of them are correct.

## Where Engram Fits

Engram is closest to the intersection of:

- truth maintenance
- long-term conversational memory
- graph/RAG memory
- local-first personal knowledge management
- auditable data pipelines

The bet is that durable LLM memory should be treated less like a chat feature
and more like a data system:

- raw data is immutable
- derivations are versioned
- accepted beliefs require evidence
- retrieval-visible rows carry privacy and activation state
- failures are diagnosable
- evals decide whether the layer is useful

## Open Questions For Engram

This survey suggests several questions to keep live:

1. **How much graph structure is actually needed?** GraphRAG/Zep suggest value,
   but Engram should not add graph complexity until the claim/belief layer is
   stable.
2. **Should procedural memory exist?** Reflexion/Voyager suggest value, but
   procedural memory should be distinct from biographical beliefs.
3. **Can belief consolidation be conservative enough?** Product memories are
   useful partly because they are lightweight; Engram must avoid becoming too
   slow or too manual.
4. **What should the gold set measure?** LoCoMo and LongMemEval suggest useful
   categories, but Engram's oracle must be the subject's real corpus and
   expectations.
5. **How much should consumers see?** `context_for` should expose confidence,
   recency, provenance, and gaps without overwhelming downstream models.

## Working Hypothesis

The missing link for useful LLM memory is not merely "more context" or "better
retrieval." It is structured, provenance-carrying, revisable context.

Prior systems show the value of memory. Engram's bet is that an auditable
claim/belief layer can make that memory more trustworthy, portable, and
reviewable than raw chat recall, opaque product memory, or model-edited
summaries alone.
