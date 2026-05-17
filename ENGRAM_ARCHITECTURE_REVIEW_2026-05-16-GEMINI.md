# Engram Architecture Assessment Report
Date: 2026-05-17

## 1. What the project is trying to be

### Product goals
Engram aims to be a local-first memory layer for one human life. Its primary purpose is to answer the question, "what should the next AI assistant know about me, this project, this relationship, or this preference?" without turning private history into an opaque remote service. It is designed to act as a time-indexed biography that provides context to downstream AI workflows via a `context_for(conversation)` serving surface.

### Core principles
- **Local-first and private:** No cloud dependency, no telemetry, and no outbound network egress from any corpus-reading process.
- **Evidence over summary:** Raw evidence is treated as ground truth. Synthesized outputs (claims/beliefs) must be grounded in raw evidence.
- **Honest uncertainty:** The system explicitly tracks confidence, provenance, explicit gaps, and contradictions rather than burying them in opaque representations.
- **Non-destructive derivation:** All extractions, segmentations, and embeddings are versioned and immutable. Newer operations supersede rather than overwrite historical derivations.

### Domain model
The system progresses through a highly structured, layered derivation pipeline:
1. **Raw Evidence:** Immutable sources (conversations, messages, captures, notes).
2. **Segments:** Topic-bounded, versioned, and embedded units of conversation history.
3. **Claims:** Atomic, LLM-extracted assertions securely linked to raw evidence IDs.
4. **Beliefs:** Deterministic, bitemporal consolidated state (with `valid_from`/`valid_to` and `observed_at`/`recorded_at` markers), tracking audit history and contradictions.
5. **Entities / Current Beliefs:** Phase 4 canonicalization and review layers.
6. **Context Packages:** Phase 5 compiled packages provided to the assistant.

### Intended operating model
Engram operates purely locally. It relies on PostgreSQL (with `pgvector`) for state and vector search, Ollama for local embeddings (`nomic-embed-text`), and `ik-llama` for local structured LLM extraction (`qwen3.6-35b-a3b`). The pipeline runs on the user's machine via CLI batch commands, with live queries being answered locally via an MCP stdio server. There is a strict local boundary using `tenant_id` and `corpus_id` to separate application memories (like Striatum) from core personal memory.

---

## 2. Current architecture

### Major components
- **Ingestion Pipelines:** Modular ingestion for ChatGPT, Claude, Gemini, and Striatum artifacts into the raw evidence layer.
- **Derivation Pipeline:** Phases for Segmentation, Embedding, Claim Extraction, and Belief Consolidation.
- **Striatum MCP Stdio Server:** An optional read-only memory boundary providing limited tools (`engram.search`, `engram.fetch_reference`).
- **Context Compiler:** The nascent `context_for()` mechanism that renders sections of beliefs, exact references, and gaps.

### Runtime/control-plane architecture
Engram primarily operates as a batch execution engine driven by the CLI (`python -m engram.cli`) and Makefile targets, chunking through phases limits (e.g., `--limit 500`). There is no persistent background daemon for pipeline derivation. Live retrieval is provided by the `engram-mcp-stdio` process, which responds to queries synchronously. 

### State/storage model
The state is managed in a single local PostgreSQL database using plain SQL migrations. The storage model is strictly layered:
- **Append-only:** Raw evidence is strictly append-only. Re-ingestion must be idempotent.
- **Bitemporal:** Beliefs track when they were true and when the system learned them, effectively appending new rows instead of `UPDATE`s on contradictions.
- **Supersession:** Derived tables maintain prompt/version metadata so newer derivations supersede older ones safely.

### CLI/API/daemon/web/MCP boundaries
- **CLI:** Operator commands (`phase2`, `phase3`, `ingest-*`) manage the heavy lifting.
- **MCP:** `engram-mcp-stdio` handles standard input/output JSON-RPC for external agent integration.
- **Web:** Lightweight local web UI routes (from RFC 0027) act as review/interview surfaces for operator interaction.
- **API:** There are no remote APIs or network-listening services. 

### Test and release posture
Release behavior is defined by strict multi-phase bounds (limit 10, limit 50, limit 500, full-corpus gates). The project leans on multi-model adversarial reviews (Claude, Codex, Gemini) for spec and implementation feedback. It employs `pytest` for unit and integration logic.

---

## 3. What is strong

### Good architectural decisions
- **Evidence -> Claim -> Belief Separation:** This prevents the dangerous failure mode where AI summaries become "fact" and subsequent summaries are based on them. If an extraction is wrong, the raw evidence is still perfectly intact.
- **Bitemporal Belief Modeling:** Maintaining `valid_from` / `valid_to` alongside recording timestamps is exactly the correct data shape for an evolving personal biography.

### Design principles worth preserving
- **No-Egress Philosophy:** Actively designing to assume the LLM reading your private life should never touch the network is critical for personal memory layer trust.
- **Postgres-First Simplicity:** Using standard RDBMS with `pgvector` avoids distributed system complexity (no graph databases or external caches are needed yet).
- **Refusal of False Precision:** Skipping LLM-based reranking at serving time in favor of a weighted lexical/semantic scorer ensures fast, inspectable, and predictable memory retrieval.

### Areas where the implementation matches the stated model
Phase 1 (ingestion), Phase 2 (segmentation), and Phase 3 (extraction/consolidation) operate exactly as specified. The strict isolation of Striatum memory from personal memory via tenant IDs is properly respected by the MCP server.

---

## 4. Architectural concerns

### Current risks
The primary product feature—`context_for(conversation)`—is not fully realized. Engram is currently an excellent ingestion and extraction engine, but without the final context compiler closing the loop, there is no real-world mechanism to empirically measure if the retrieved contexts actually improve assistant performance.

### Complexity hotspots
The Python package has outgrown its flat structure. Modules like `cli.py` (>2600 lines), `extractor.py` (>3100 lines), and `segmenter.py` (>1900 lines) are doing too much: combining parser definitions, prompt construction, client calls, retries, diagnostic logs, and orchestration logic.

### Coupling, duplication, migration debt, or unclear authority boundaries
- **Retrieval Hit Contract:** The contract is not uniform. Packet building assumes one shape, but exact-reference paths (git, build artifacts, markdown) return different dictionary structures. This leaks abstractions into the retrieval paths.
- **Second Raw Model:** Source-specific tables (like `git_commits`, `markdown_files`) are acting as disjoint raw layers rather than funneling into a generic evidence catalog. 
- **No-Egress is Only a Principle:** While no-egress is a core rule, it lacks OS-level executable enforcement (e.g., network namespaces or seccomp) to protect against accidental parser dependencies or subprocess network calls.

### Places where docs and implementation disagree
- Generated schema documentation (`docs/schema/README.md`) is out of date and missing recent migrations.
- PyYAML is used in source contracts but is completely missing from `pyproject.toml` dependency declarations.
- RFC index statuses occasionally drift from their actual applied states.

---

## 5. What you would do differently greenfield

### Preferred architecture
A greenfield version would model a stricter subsystem boundary:
**Source Adapters -> Evidence Vault -> Evidence Catalog -> Projection Registry -> Derivation Job System -> Beliefs -> Policy Engine -> Retrieval Compiler**

### Different technology or substrate choices
Instead of using Postgres to store large text bodies, logs, or future media, I would use an encrypted, local content-addressed blob vault on disk. Postgres would store the metadata, hashes, references, and derivation states.

### Different module boundaries
I would break the monolithic modules into explicit bounded Python packages:
- `engram.ingest.*`
- `engram.derive.*`
- `engram.belief.*`
- `engram.entity.*`
- `engram.retrieve.*`
- `engram.policy.*`

### Different runtime/control-plane model
Rather than ad-hoc pipeline CLIs running tight loops, I would introduce a generalized **Derivation Job System** (`derivation_jobs`, `derivation_attempts`, `derivation_outputs`). This allows segmentation, extraction, and future projection jobs to share the same operational semantics for leasing, idempotency, and bounded retries. 

I would also treat the **Entity Identity Service** as a standalone boundary with its own ledger of aliases, merges, splits, and external IDs, rather than a late-stage deterministic pass.

---

## 6. Recommended changes to the current project

**1. Unify the Retrieval Hit Contract (High Priority)**
- *Rationale:* Memory building paths are leaking source-specific implementation details.
- *Change:* Define a strict `MemoryHit` / `ReferenceHit` dataclass. Ensure Striatum, git, markdown, and all exact-ref retrievals return this exact shape.
- *Difficulty:* Low/Medium.

**2. Implement an OS-Level No-Egress Runner (High Priority)**
- *Rationale:* Disciplinary no-egress is brittle. 
- *Change:* Add `engram no-egress run -- <command>` utilizing Linux network namespaces, `unshare`, or Landlock to physically block network access during extraction.
- *Difficulty:* Medium.

**3. Formalize the `context_for` Slice (High Priority)**
- *Rationale:* The system needs an objective function. Without a context compiler, it is impossible to evaluate quality.
- *Change:* Ship the smallest possible `context_for` rendering engine merging current beliefs, exact references, and explicit gaps into markdown. 
- *Difficulty:* Low.

**4. Introduce a Generic Evidence/Reference Index (Medium Priority)**
- *Rationale:* Stop creating separate tables for every new data source.
- *Change:* Implement `reference_index` and `evidence_items` generic tables so all search queries act against a single interface regardless of origin.
- *Difficulty:* Medium/High (requires data migration).

**5. Centralized Policy Engine (Medium Priority)**
- *Rationale:* Privacy is handled via ad-hoc checks and table constraints.
- *Change:* Create a central policy module `authorize(actor, purpose, item_labels)` utilized by all context, search, and UI routes.
- *Difficulty:* Medium.

---

## 7. Functionality you would add

### Product capabilities
- **Gold-Set Eval Runner:** A command (`engram eval context`) that compiles contexts for a "gold prompt" and checks precision, recall, stale suppressions, and hallucinated token waste. 
- **Unified Packet Builder:** Allow packet building to seamlessly aggregate Striatum artifacts, personal memory, git history, and markdown without special casing.

### Operator/developer experience improvements
- **Entity Review Workbench:** A local UI explicitly for merging/splitting entity aliases, attaching external IDs, and inspecting the evidence distribution behind entities.
- **Privacy/Sensitivity Dashboard:** A read-only UI answering questions like "What Tier 2 material is visible?", "What was withheld and why?", and "Which sources have extraction capabilities enabled?".
- **Data Quality Dashboard:** Visibility into un-embedded segments, extraction failures, and contradictions by age.

### Reliability, security, observability, or workflow improvements
- **Backup and Key Management:** A codified mechanism for encrypted local backups, restoring, and "Tier 5" destruction (dead-man switch capabilities).
- **Source Auditing for Failures:** Currently, audits only trigger on successful ingestion transactions. The system needs to append durable audit rows for failed reads, parse errors, and aborted transactions.
- **Event-Sourced Snapshots:** Implement `memory_events` to properly invalidate and refresh materialized views (`current_beliefs`) so serving layers don't serve stale beliefs.

---

## 8. Suggested execution roadmap

### Near-term
**Clear First Step:** Complete "Step 5" from the current roadmap by authoring the gold set (25-50 entries). Immediately follow this by shipping the minimal personal `context_for` read-only compiler so these gold-set queries can be processed and empirically evaluated.
- Fix documentation drift: add PyYAML to `pyproject.toml` and regenerate schema docs.
- Unify the retrieval result contract (`MemoryHit`) across all data types.

### Medium-term
- Implement the executable No-Egress wrapper (`engram no-egress run`).
- Introduce the centralized Policy Engine module to sanitize all outputs based on `privacy_tier`.
- Break up monolithic modules (`cli.py`, `extractor.py`, `memory.py`) into bounded packages (`engram.derive`, `engram.retrieve`, etc.).
- Introduce the `memory_events` and context snapshot invalidation cycle.

### Long-term
- Draft an RFC for, and implement, the generic **Evidence Vault and Reference Index**, transitioning away from disparate source-specific raw tables.
- Introduce local encrypted content-addressed blob storage for handling large bodies of text, images, or future multimodal sources.
- Build the formal Backup, Key Management, and Tier 5 destruction mechanisms.
- Build the Entity Identity Service to govern lifetime identity deduplication.