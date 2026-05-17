# Striatum Architecture Remediation Plan

This step-by-step plan outlines the process for correcting the findings and executing the recommendations detailed in the `STRIATUM_ARCHITECTURE_REVIEW_2026-05-16.md`.

## Phase 1: Eradicate Legacy State Fallbacks (Immediate)
**Goal:** Ensure PostgreSQL is the sole authoritative state substrate, eliminating state-split risks and masking of daemon failures.
1. **Identify SQLite Fallbacks:** Audit the codebase for any remaining SQLite fallback logic (particularly around workflow verbs and RPC failures).
2. **Remove Fallback Paths:** Delete the identified production SQLite fallback pathways.
3. **Enforce Hard Failures:** Modify the CLI/RPC client to fail predictably and transparently if the daemon RPC is unreachable or if a PostgreSQL connection cannot be established.
4. **Update Tests:** Ensure test matrices covering state operations assert against the PostgreSQL paths and do not implicitly rely on SQLite structures (unless explicitly for migration testing).

## Phase 2: Resolve Daemon Core Strategy (Near-Term)
**Goal:** Eliminate the split-brain scenario between Python (`daemon_pg/`) and Go (`go/pkg/`) daemon implementations.
1. **Architectural Decision:** Formalize the decision (via an RFC or Decision Log entry) to adopt Go as the unified daemon substrate going forward, halting new feature development in the Python daemon.
2. **Define RPC Contract:** Create a single, authoritative RPC contract definition (e.g., Protobuf/gRPC if feasible, or a strictly versioned JSON-RPC matrix) to bind the CLI to the daemon.
3. **Port Handlers:** Systematically port remaining workflow handlers from the Python `daemon_pg` implementation to the Go implementation.
4. **Deprecate Python Daemon:** Once parity is achieved, cleanly remove the Python daemon codebase.

## Phase 3: Enforce Reviewer Diversity (Near-Term)
**Goal:** Prevent "co-blindness" loops caused by identical models performing both implementation and review.
1. **Validation Logic:** Add a workflow validation rule that checks the model/agent assignments for the `implement` and `review` lanes.
2. **Refuse Identical Pairings:** Hard-fail or warn if the same model is assigned to both lanes.
3. **Override Flag:** Introduce an `--allow-same-model-pairing` flag to permit identical pairings when explicitly desired by the operator.

## Phase 4: Upgrade Process Supervision (Medium-Term)
**Goal:** Improve process robustness by switching from standard Unix FIFOs to native PTY allocation, preventing agent stalls in non-interactive environments.
1. **Research PTY Libraries:** Evaluate libraries such as `creack/pty` in Go for the process adapter.
2. **Refactor Process Supervisor:** Modify the wrapper that manages agent lifecycles to allocate true PTYs instead of standard piped stdin/stdout.
3. **Implement Auto-Finalize (RFC 0051):** Enhance the supervisor to auto-finalize jobs if the agent process crashes but a valid, schema-compliant artifact has been written to disk.

## Phase 5: Rearchitect Web Service (Medium-Term)
**Goal:** Enforce a single-source-of-truth paradigm by routing all state queries through the daemon.
1. **Audit Dashboard Queries:** Identify all direct database queries made by the local web dashboard.
2. **Expose Daemon Endpoints:** Implement necessary read-only endpoints in the daemon RPC contract to serve the dashboard's needs.
3. **Refactor Web UI:** Update the web dashboard to communicate exclusively via the daemon RPC, removing its direct database connection pool.

## Phase 6: Documentation & Consistency Cleanup (Immediate to Near-Term)
**Goal:** Align documentation with the current and future architectural reality.
1. **Update `README.md` and `GETTING_STARTED.md`:** Remove references to `.striatum/state.sqlite3` as the authoritative state.
2. **Document PostgreSQL Requirement:** Clearly document the daemon-managed PostgreSQL instance as the system of record (resolving GH #15).
3. **Publish Strategy:** Update architecture docs (e.g., `AGENTS.md`, `ARCHITECTURE.md`) to reflect the unified Go daemon strategy and PTY process supervision models.

---
**Prepared By:** Gemini CLI
