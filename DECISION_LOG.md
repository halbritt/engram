# Decision Log

Status: template

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
| D001 | proposed | Treat `context_for(conversation)` as the primary product surface. | The system is only useful if it improves the next AI interaction. | Retrieval, ranking, temporal modeling, and graph work should be judged by context quality. | Revisit if another product surface becomes primary. |
| D002 | proposed | Separate canonical memory from derived projections. | Graphs, wiki pages, vector indexes, and context packages should be rebuildable from evidence-backed state. | More schema discipline up front; lower long-term migration risk. | Revisit if a graph-native store becomes the canonical architecture by explicit decision. |
| D003 | proposed | Require accepted beliefs to cite raw evidence. | Prevents LLM synthesis from becoming ungrounded truth. | Adds audit and provenance overhead. | Revisit only if a reliable human approval workflow replaces evidence citation. |
| D004 | proposed | Use temporal validity rather than naive age decay. | Old facts may remain true, and fresh facts may be wrong. | Requires claim/belief lifecycle and supersession handling. | Revisit after temporal evals show the model is too complex. |
| D005 | proposed | Use topic segments as the main embedding and extraction unit. | Single turns are often under-contextualized; whole conversations are too broad. | Requires segmentation before extraction. | Revisit after comparing segment-level vs turn-level retrieval quality. |
| D006 | proposed | Defer automatic broad wiki writeback until belief quality is measured. | Wiki output can amplify bad synthesis into human-facing documentation. | Start with previews or a controlled index page. | Revisit after evals show low unsupported-belief and stale-memory rates. |

## Open Decisions

| ID | Question | Options | Needed Evidence | Target Round |
|----|----------|---------|-----------------|--------------|
| O001 | Should v1 include a real graph backend? | relational edges, Apache AGE, Neo4j, FalkorDB, Kuzu | Graph retrieval evals and operational complexity comparison | Graph maximalist / graph skeptic |
| O002 | What is the exact belief lifecycle? | claims -> beliefs, event sourcing, bitemporal tables, temporal edges | Temporal/provenance review and rollback design | Temporal specialist |
| O003 | What does `context_for` return? | flat bullet list, sectioned package, typed JSON plus rendered markdown | Context evals and client integration needs | Context_for specialist |
| O004 | What feedback loop replaces production engagement signals? | manual labels, eval set, LLM judge, usage telemetry | Evaluation review | Eval specialist |
| O005 | Which sources are v1? | ChatGPT only, ChatGPT + Obsidian, plus Claude/Gemini | Ingestion effort vs context value | V1 scope killer |

