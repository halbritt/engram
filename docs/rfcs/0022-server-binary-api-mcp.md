<a id="rfc-0022"></a>
# RFC 0022: Server Binary with HTTP API and MCP Interface

| Field | Value |
|-------|-------|
| RFC | 0022 |
| Title | Server Binary with HTTP API and MCP Interface |
| Status | proposal |
| Implementation | none |
| Date | 2026-05-07 |
| Context | RFC 0021 (gold-set interview surface — drives the immediate need for a non-CLI consumer); BUILD_PHASES Phase 5 (`context_for` + serving path, MCP exposure planned); `docs/design/V1_ARCHITECTURE_DRAFT.md` § Hot State / Serving (MCP snapshot-first); `docs/design/V1_SYNTHESIS_DELTAS.md` § Process Isolation; D018 (process isolation), D020 (local-only inference / 127.0.0.1 binding), D025 (snapshot-first hot state); `src/engram/cli.py:45` (`main`); `src/engram/cli.py:49`–`:147` (existing subcommand surface) |

Decision refs:
  - D018
  - D020
  - D025

Review refs:
  - none

Phase refs:
  - PHASE-0005

This RFC proposes an Engram **server binary** (`engramd`) that mounts both an
HTTP/JSON API and an MCP interface over a shared handler layer, binds only to
`127.0.0.1`, and becomes the substrate for: the gold-set interview web UI
(RFC 0021), eventual Phase 5 `context_for` serving, and external MCP clients
(Claude, ChatGPT, Gemini, Cursor, etc., per `V1_ARCHITECTURE_DRAFT.md`
§ Hot State). The CLI in `src/engram/cli.py` continues to exist; read-shaped
subcommands gain the option to call the server, while pipeline-driving
subcommands stay direct-to-Postgres for now.

This is an idea-capture RFC, not an accepted architecture decision. It does
not yet authorize a Phase 5 implementation, does not change schemas, does not
change Phase 2/3 pipeline ownership, and does not introduce any cloud or
external service. It brings forward and generalizes the MCP serving slot
already planned for Phase 5 so that an earlier consumer (RFC 0021's web UI)
has a stable backend without a parallel one-off shim.

## Background

Today Engram is exclusively CLI-driven. `src/engram/cli.py` exposes
`migrate`, `ingest-{chatgpt,claude,gemini}`, `segment`, `embed`, `extract`,
`re-extract`, `consolidate`, `pipeline`, and `pipeline-3`. Each subcommand
opens its own Postgres connection and drives a phase worker directly. There
is no long-lived process beyond the per-command process.

The design docs already commit Engram to a server-shaped serving path:

- `BUILD_PHASES.md` § Phase 5 commits to a 127.0.0.1-bound MCP server with
  `context_feedback` capture and snapshot read paths.
- `V1_ARCHITECTURE_DRAFT.md` § Hot State frames "external frontier-model
  consumers (Claude, ChatGPT, Gemini, Cursor, or any MCP client)" as the
  intended consumer of `context_for` snapshots.
- `V1_SYNTHESIS_DELTAS.md` § Process Isolation makes the local-binding and
  no-egress requirement explicit at the OS level for the serving process.

RFC 0021 introduces the first non-CLI consumer with a live UX requirement
(the interview web UI). Without a server, RFC 0021's web surface needs an
ad-hoc backend; building one outside the planned Phase 5 server creates a
parallel surface that has to be retired or merged later.

The current CLI surface also splits cleanly along an axis that maps well
onto the API/CLI boundary:

| Subcommand | Shape | API-eligible? |
|---|---|---|
| `migrate` | privileged DDL, single-shot | no — admin/CLI |
| `ingest-{chatgpt,claude,gemini}` | local FS read, privileged write | maybe — admin/CLI in v1 |
| `segment`, `embed`, `extract`, `re-extract`, `consolidate` | long-running pipeline workers, supervisor-coordinated | no — CLI / supervisor |
| `pipeline`, `pipeline-3` | long-running orchestration | no — CLI / supervisor |
| (read paths) — claim/belief lookup, segment search, evidence resolution | short-lived reads | yes |
| RFC 0021 interview sampler + `gold_labels` write | short-lived turn loop | yes |
| Phase 5 `context_for(...)` | short-lived read with optional snapshot warm path | yes (and is the eventual MCP tool surface) |

The split is not arbitrary: pipeline commands have batch state, retry
semantics, supervisor visibility, and operator-grade output that does not
belong over an RPC boundary. Read and curation surfaces are pure
request/response.

## Problem

How do we expose Engram to non-CLI consumers (web UI, MCP clients,
`context_for` callers) while:

- preserving D020 (local-only inference) and the Phase 5 §
  "binds 127.0.0.1 only" rule;
- preserving D018 process isolation — the serving process must not have
  network egress;
- not duplicating handler logic across CLI / HTTP / MCP;
- not flattening the operational distinction between "pipeline workers"
  (long-running, supervisor-owned) and "serving paths"
  (short-lived, read-shaped);
- not pre-committing Phase 5's `context_for` final shape, which still has
  open ranking/snapshot work.

## Proposal

### Shape

A single Python binary, **`engramd`**, hosting:

- a **handler layer** (`src/engram/api/handlers.py`) that owns the request/
  response contracts for read endpoints and the RFC 0021 interview surface;
- an **HTTP transport** (`src/engram/api/http.py`, FastAPI / Starlette over
  uvicorn, bound to `127.0.0.1`);
- an **MCP transport** (`src/engram/api/mcp.py`, registering the same
  handlers as MCP tools);
- shared **schemas** (`src/engram/api/schemas.py`, Pydantic) used by both
  transports and re-exported for CLI consumption.

The CLI is unchanged in v1 except for one new subcommand:

- `engram serve [--http-port 8765] [--mcp-stdio | --mcp-port <n>] [--bind 127.0.0.1]`

The CLI's existing read paths (e.g. a hypothetical `engram show belief
<id>`) can later switch to "call the server if running, else direct DB" but
that migration is out of scope here.

### Process boundary

One binary, two transports:

- **HTTP/JSON** for the web UI and any local programmatic client.
- **MCP** for external frontier-model consumers, exposed both as
  stdio-launched (the canonical MCP transport) and optionally
  TCP-over-loopback for editor integrations that prefer it.

A single binary keeps the lifecycle (config, secrets, connection pool, log
sink, signal handling) in one place. MCP and HTTP do not share a port; they
share a handler dispatch table. MCP's tool set is a curated subset of the
HTTP API (the model-facing surface), not 1:1.

### Surface scope (v1)

**Read endpoints** (HTTP only; MCP-eligible subset noted):

- `GET /healthz` — liveness; HTTP only.
- `GET /readyz` — DB ping + migration version; HTTP only.
- `GET /v1/version` — server version, schema version, prompt versions
  (extraction, consolidation), model versions; HTTP only.
- `GET /v1/claims/{id}` — full claim row + evidence summary; **MCP**.
- `GET /v1/beliefs/{id}` — full belief row + audit trail; **MCP**.
- `GET /v1/beliefs?subject=…&predicate=…&status=…` — filtered list; **MCP**.
- `POST /v1/search/segments` — pgvector + FTS over segments; **MCP**.
- `POST /v1/search/beliefs` — pgvector over belief embeddings; **MCP**.
- `GET /v1/evidence/{message_id}` — privacy-tier-respecting evidence
  resolver; HTTP only (privacy-sensitive surface — hold MCP exposure until
  the snapshot-renderer in Phase 5 owns redaction).

**Interview endpoints** (RFC 0021; HTTP only in v1):

- `POST /v1/interview/sessions` → start a session, returns `session_id` +
  the first sampled question.
- `GET /v1/interview/sessions/{id}/next` → next sampled question or
  session-complete.
- `POST /v1/interview/sessions/{id}/answer` → record a verdict.
- `GET /v1/interview/labels?target=…` → label history for a target.
- `POST /v1/interview/export` → JSONL export (privacy-tier-bounded).

**Phase 5 placeholder** (HTTP + **MCP**, locked to a stub until Phase 5
ships):

- `POST /v1/context_for` → returns `not_implemented` with a structured
  envelope. Reserves the URL and the MCP tool name (`engram.context_for`)
  so the eventual Phase 5 work changes only the implementation, not the
  surface. Avoids consumers binding to a transient endpoint.

**Out of scope for v1:**

- Pipeline-driving endpoints (`segment`, `embed`, `extract`, `re-extract`,
  `consolidate`, `pipeline*`). These remain CLI-only and supervisor-owned.
- Ingestion endpoints. CLI / FS only.
- `migrate`. Admin / CLI only.
- Write endpoints over MCP. v1 MCP is read-only + (later) `context_for`.

### Authentication & binding

- **Bind.** Default `127.0.0.1`. Any non-loopback bind must be explicit
  via `--bind` and emits a startup warning. D020 / Phase 5 §
  "binds 127.0.0.1 only" stays the contract.
- **Auth, v1.** None. Loopback is the trust boundary. The CLI and any
  local browser tab are inside that boundary.
- **Auth, future.** A pre-shared token in a header for trusted-network
  binds; deferred until a real non-loopback need exists. Out of scope here.
- **CORS.** Allowed origins default to `http://127.0.0.1:*` and
  `http://localhost:*`. No third-party origin.
- **Process isolation.** The server process inherits Phase 5's no-egress
  rule. Operationally enforced via systemd/launchd-level egress block (or
  a Linux netns / macOS sandbox profile) per `V1_SYNTHESIS_DELTAS.md`
  § Process Isolation. The RFC notes this; the platform-specific
  enforcement is a follow-on spec.

### Versioning

- HTTP API path-prefixed `/v1/...`. Breaking changes go to `/v2/...`.
- MCP tool names are namespaced `engram.*`. Tool-version stamps live in
  the tool's `description` field.
- Response envelopes carry the same version-stamp triples already used on
  derived data (`extraction_prompt_version`, `consolidation_prompt_version`,
  `request_profile_version`) when the response includes derived rows. This
  matches RFC 0017 versioning discipline.

### Schema sharing

Pydantic models are the single source of truth:

- `src/engram/api/schemas.py` defines request/response types.
- The HTTP transport mounts them via FastAPI directly.
- The MCP transport derives JSON Schemas for tool definitions from the
  same Pydantic models.
- Pydantic models also serialize → CLI JSON output for a future
  `--format json` flag on read-shaped CLI subcommands.

No SQLAlchemy ORM. The schemas describe the API contract, not the DB
shape; the existing `psycopg`-driven query layer in `src/engram/*` stays
the only path to Postgres.

### Connection pooling and lifecycle

- A `psycopg_pool.ConnectionPool` per process; existing one-off
  `connect()` callsites in CLI scripts continue to work unchanged.
- Read endpoints get a connection from the pool, run the query, return
  the connection. No session affinity. No transactions held across
  request boundaries.
- Graceful shutdown drains in-flight requests on SIGTERM, then closes
  the pool. SIGINT is loud-and-fast for development.
- Hot reload via uvicorn `--reload` only in `--dev` mode; never default.

### Observability

- Structured JSON logs to stdout (compatible with the existing
  `consolidation_progress` event style for visual continuity).
- A `/v1/metrics` Prometheus-style endpoint, gated on `ENGRAMD_METRICS=1`.
  Default off; no metric collection unless explicitly enabled. Avoids
  any "the daemon is silently telemetering me" failure mode.
- No outbound log shipper. Logs are local; redirection is the operator's
  responsibility.

### Operational model

- **Daemon, not a script.** `engramd` is intended to run under the
  user's session manager (systemd user service, launchd plist, or a
  direct `engramd serve` for a developer tab). Not a fork-and-detach
  shell hack.
- **Striatum integration.** `engramd` registers its presence and port
  in Striatum SQLite (D074 — Striatum is the authoritative gate state),
  so CLI tools and the supervisor can discover the running server
  without a config file. If no `engramd` is registered, CLI commands
  continue running direct-to-DB.
- **Single instance.** First-process-wins on the registered port; a
  second `engramd serve` exits with a clear error pointing at the
  running PID.
- **Config file.** `~/.engram/engramd.toml` (or `$ENGRAMD_CONFIG`)
  for non-default port, bind, log level. No env-only configuration —
  but every config key is overridable via `ENGRAMD_*` env vars
  (matches the `ENGRAM_*` pattern in `AGENTS.md` § Python Coding
  Standard).

## Worked example

Browser → `engramd` → Postgres for the RFC 0021 interview loop.

```
# user runs once, persistent
$ engramd serve
engramd 0.0.0  schema=migration/008  http=127.0.0.1:8765
                mcp=stdio (use `engramd mcp-stdio` to attach a client)

# web tab issues:
POST /v1/interview/sessions
  body: {"n": 5, "seed": 4, "strata": null}
→ 200 {"session_id": "gl-sess-...","question": {...}}

# answer cycle:
POST /v1/interview/sessions/gl-sess-.../answer
  body: {"verdict": "stale", "rationale": "switched to helix Apr 2026"}
→ 200 {"committed": true, "next": {...}}
```

Same backend, MCP transport, external Claude tool call:

```
tool: engram.search_beliefs
args: {"subject": "user", "predicate": "uses_editor", "status": "accepted"}
→ {"beliefs": [{"id":"...", "object_text":"helix",
                "valid_from":"2026-04-...", "confidence":0.71, ...}]}
```

Same handlers in both flows; transports differ only in framing.

## Privacy and provenance

- **No outbound network.** The serving process is sandboxed off egress.
  D020 stands; Phase 5 § "no network egress" stands.
- **Privacy-tier carry.** Every response that contains derived rows
  carries the row's `privacy_tier`. A request can include a
  `privacy_tier_max` ceiling; the server filters below the ceiling
  rather than redacting in-place. Responses never silently drop fields;
  withheld rows are reported by id only.
- **Evidence redaction.** `/v1/evidence/{message_id}` is HTTP-only in
  v1. MCP exposure waits for the Phase 5 snapshot renderer to own
  redaction policy. This RFC does not redefine that policy.
- **Auth = trust boundary, not access control.** Loopback is the
  authorization model in v1. Multi-user does not exist for Engram and
  is not introduced here.
- **No analytics.** The metrics endpoint is opt-in and local-only. There
  is no usage-pinging, no error reporting, no remote diagnostics.

## Relationship to other artifacts

- **RFC 0021** — directly enables the gold-set interview web UI without
  a parallel backend. The interview endpoints listed above are the
  HTTP-shaped equivalent of the CLI surface RFC 0021 specifies for v1.
- **RFC 0017** — version-stamp triples in API responses match the
  re-extraction discipline. Clients can pin to a version stamp and
  detect drift without hitting the DB.
- **RFC 0018** — claim and belief response objects can include any
  attached `claim_audits` / `belief_audit` rows as a sibling field
  (advisory, not a gate, per D069).
- **Phase 5 / `context_for`** — this RFC reserves the URL and the MCP
  tool name; the implementation is Phase 5's deliverable. Treating the
  server binary as "the Phase 5 server, started early" rather than "a
  new server we'll merge later" avoids a doomed parallel-track problem.
- **D025** — snapshot-first hot state is preserved. The first `context_for`
  implementation can serve from `context_snapshots` exactly as Phase 5
  describes; nothing in this RFC changes that path.
- **D018 / V1_SYNTHESIS_DELTAS § Process Isolation** — the no-egress
  requirement transfers from "the eventual MCP server" to "this server
  binary, starting now." The platform-specific enforcement spec is a
  follow-on.
- **D074 / Striatum** — Striatum SQLite stays the authoritative gate
  state. `engramd` registers there; it does not become a parallel state
  authority.
- **CLI (`src/engram/cli.py`)** — unchanged in v1 except for the new
  `engram serve` subcommand. Pipeline subcommands continue to drive
  Postgres directly. A future migration of read-shaped CLI subcommands
  to call `engramd` is desirable (one connection pool, fewer cold
  starts) but explicitly out of scope here.

## What this RFC does **not** propose

- **Does not** expose pipeline operations over the API. Segmentation,
  embedding, extraction, re-extraction, and consolidation remain
  CLI/supervisor surfaces in v1.
- **Does not** introduce a cross-machine deployment model. Loopback is
  the only supported bind by default.
- **Does not** redefine `context_for` semantics. Phase 5 still owns the
  ranking, snapshot, and `context_feedback` design.
- **Does not** introduce write-over-MCP. The interview write surface is
  HTTP-only; MCP write tools are deferred until there is a justified
  consumer.
- **Does not** make `engramd` a hard dependency. CLI continues to work
  with no server running.
- **Does not** prescribe a web UI framework, build tool, or styling
  system. Web UI lives in its own RFC.

## Open questions

1. **HTTP framework.** FastAPI is the obvious default (ecosystem,
   Pydantic-native, OpenAPI for free). Starlette-direct is leaner. The
   tax of FastAPI is small for this surface. Decision is non-binding
   until implementation.
2. **MCP transport priority.** Stdio is the canonical MCP transport and
   matches how Claude/Cursor/etc. attach today. TCP-over-loopback is
   useful for editor integrations that pre-launch a daemon. Worth
   shipping both? v1 likely stdio + an optional loopback MCP listener.
3. **Server-side rendering vs. JSON-only API.** Lean JSON-only; the web
   UI is a separate process even if it ends up bundled in the same
   distribution.
4. **CLI ↔ server cutover for read commands.** When (and how) do
   `engram show ...` style read CLIs prefer the running server over
   direct DB? Touches connection-pool sharing semantics. Defer.
5. **Streaming responses.** Search and `context_for` may eventually
   stream. v1: synchronous responses only; SSE/WebSocket deferred until
   an actual consumer needs it.
6. **Snapshot freshness signaling.** When `context_for` lands in Phase 5,
   does the API expose snapshot age / dirty-bit? Belongs to Phase 5
   spec, not this RFC.
7. **Auth roadmap.** What is the trigger for adding token auth? Likely
   "first justified non-loopback bind." Captured here so the bar is
   clear.
8. **Process isolation enforcement.** Linux netns vs. systemd
   `RestrictNetwork=` vs. macOS sandbox profile vs. nothing-and-trust
   the bind. Belongs in a follow-on operational spec.
9. **Static assets / web UI hosting.** Does `engramd` serve the web
   UI's static bundle, or does the web UI run from a separate dev
   server? Lean toward `engramd` serving static assets in production
   so a single process is the user-facing thing; that's a separate
   web-UI RFC decision.

## Promotion path

1. Discuss / amend in review.
2. If accepted, add a BUILD_PHASES entry between Phase 4 and Phase 5
   covering `engramd` v1 (reads + interview), or fold into a Phase 5
   prelude. Mark this RFC `accepted`.
3. Land `src/engram/api/` skeleton: handlers, schemas, HTTP transport,
   MCP transport. Keep `engramd` strictly read + interview in the first
   commit; do not touch pipeline workers.
4. Wire `engram serve` into the CLI as a thin entrypoint.
5. Wire RFC 0021's interview CLI to call `engramd` when present, else
   direct DB.
6. Reserve `POST /v1/context_for` and `engram.context_for` MCP tool as
   stubs returning `not_implemented`.
7. Phase 5 implementation (separate work) replaces the stub.
8. Defer web UI, auth, non-loopback bind, and pipeline-over-API to
   their own RFCs as needs arise.
