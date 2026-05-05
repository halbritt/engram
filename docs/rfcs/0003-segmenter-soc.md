# RFC: Decoupling Micro-Architecture in the Segmentation Pipeline

Status: proposal
**Date:** 2026-05-02

## 1. Context
Engram's macro-architecture demonstrates a rigorous application of the Principle of Separation of Concerns (SoC). Core invariants—such as epistemological separation (D002), treating corrections as append-only captures (D017), and OS-level execution isolation (D020)—successfully isolate distinct conceptual domains. The data ontology effectively prevents hallucination cascading and ensures provenance.

## 2. Problem Statement
The micro-architecture within Phase 2, specifically `src/engram/segmenter.py`, violates the project's SoC standards. The module operates as a procedural monolith, conflating four distinct operational domains:

* **Data Access Coupling:** Raw `psycopg` connections and inline SQL statements (e.g., `UPDATE segment_generations...`) are tightly coupled to the algorithmic control flow.
* **Telemetry Coupling:** Progress tracking (`upsert_progress`) and metadata logging are hardcoded into the chunking loops, preventing the logic from being executed or tested in isolation.
* **Transport Conflation:** The `IkLlamaSegmenterClient` manages HTTP transport mechanics alongside domain-specific prompt generation and schema enforcement.
* **State Mutation:** Pure mathematical operations (context boundary calculus, token estimation) are intermingled with functions that mutate database state or initiate network IO.

This coupling degrades testability, makes the chunking algorithms brittle to schema changes, and contradicts the architectural rigor established in Phase 1.

## 3. Proposed Architecture
Decompose `segmenter.py` into isolated operational layers.

### 3.1 Data Access Layer (Repository Pattern)
* Extract all `psycopg` imports, raw SQL queries, and telemetry/progress writes into a dedicated repository boundary (e.g., `segmenter_repo.py`).
* Core algorithms must consume immutable data structures (`Conversation`, `MessageWindow`) and return domain objects (`SegmentationResult`), completely abstracted from the Postgres persistence layer.

### 3.2 Pure Domain Logic
* Extract the context boundary calculus (`context_safe_window_char_budget`, `assert_context_budget`), token estimation, and windowing math into pure functions.
* These modules must accept primitives (integers, strings, lists) and return primitives, containing zero database, disk, or network dependencies.

### 3.3 Transport and Orchestration Isolation
* **LLM Client:** Reduce the client to pure transport and protocol enforcement (executing the payload, handling timeouts, parsing the JSON schema).
* **Orchestrator:** Implement a distinct coordinator function that manages the high-level pipeline: pulling from the repository, passing data to the pure domain logic, routing prompts to the LLM client, and handing the outputs back to the repository.

## 4. Consequences
* **Testability:** Algorithmic math and prompt construction can be exhaustively unit-tested without requiring a live Postgres instance, network mocks, or a running `ik_llama` server.
* **Maintainability:** Future changes to the `segment_generations` or `consolidation_progress` schemas will be isolated to the repository layer, leaving the core segmentation logic untouched.
* **Reversibility:** High. This is a structural refactor of existing Python logic. It requires zero changes to the underlying database schema, the bitemporal invariants, or the LLM request contract defined in D034.
