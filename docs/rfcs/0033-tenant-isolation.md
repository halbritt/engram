<a id="rfc-0033"></a>
# RFC 0033: Tenant Isolation for Co-Located Engram Instances

| Field | Value |
|-------|-------|
| RFC | 0033 |
| Title | Tenant Isolation for Co-Located Engram Instances |
| Status | proposal |
| Implementation | none |
| Date | 2026-05-12 |
| Owner | heath |
| Context | `src/engram/db.py` (`ENGRAM_DATABASE_URL`, single `connect()`); `src/engram/migrations.py` (`schema_migrations` checksum-stamped runner in `public`); `migrations/001_raw_evidence.sql` and downstream migrations (all `CREATE TABLE ... ;` without an explicit schema, so they land in `public`); `Makefile` `migrate`, `phase1-*`, `phase2-*`, `phase3-*`, `phase4-*` targets (all pass a single `ENGRAM_DATABASE_URL`); engram principles: local-first, raw-is-sacred, derived tables rebuildable |

Decision refs:
  - none yet (proposal)

Review refs:
  - none

Phase refs:
  - PHASE-0001 (raw evidence — schema layout affects every raw table)
  - PHASE-0001-5 (cleanup + multi-source ingest — ingesters write across
    every raw table)
  - PHASE-0002 (segmenter / embedder — derived tables follow the same
    isolation rule as raw)
  - PHASE-0003 / PHASE-0004 (claims, beliefs, entities — same)
  - PHASE-0005 (`context_for` serving path — must scope retrieval to the
    tenant whose context is being built)

## Summary

Allow multiple engram instances to share one host **and** one Postgres
cluster while keeping their evidence, derived tables, and retrieval
surfaces from contaminating each other. The motivation is resource
sharing (one cluster, one pgvector install, one local-model runtime,
one disk volume) without the operational cost of running parallel
Postgres servers per tenant.

The proposal is **schema-per-tenant within a single Postgres database**,
with a small shared `engram_common` schema for reference data and the
existing checksum-stamped migration runner extended to apply migrations
per tenant. Connection scoping via `search_path` makes accidental
cross-tenant reads or writes structurally impossible at the SQL layer
without changing application code.

## Motivation

Today there is implicitly one engram instance per host. `src/engram/db.py`
reads a single `ENGRAM_DATABASE_URL` and connects without setting a
schema, so every table lands in `public`. The Makefile's phase
targets do the same.

The operator wants to run several engram instances on one box — e.g.
a personal corpus and a work corpus, or a primary and an experimental
re-extraction tenant — without either of these properties:

1. Two Postgres servers running side by side (wasted RAM, two
   `shared_buffers` caches, two WAL streams, two upgrade paths).
2. Two engram repo checkouts trying to coordinate which schema
   each migration lands in.

Co-tenancy is also valuable for the multi-agent review patterns under
`docs/process/multi-agent-review-loop.md`: running a review tenant
against a frozen snapshot of the primary tenant's raw evidence is
much cheaper if both live in the same cluster.

## Threat model

Stated up front so the design is sized correctly:

- **All tenants share root authority.** The operator owns every
  tenant. There is no hostile cross-tenant adversary. Postgres
  superuser access, the engram repo, the local model runtime, and
  the disk volume are all the same trust boundary.
- **The risk is accidental cross-tenant contamination, not malicious
  escape.** A query path that forgets to scope to a tenant must
  fail closed (return nothing, or error), not silently union two
  tenants' beliefs into one answer. A raw-evidence write must land
  in exactly one tenant's append-only log.
- **The risk is also operator confusion.** When two tenants have the
  same `source_kind = 'chatgpt'` and the same kind of `beliefs`
  table, an interactive `psql` session, a notebook, or a stray
  script needs to make it obvious which tenant is in scope.

That threat model rules out a defense posture aimed at hostile
multi-tenancy (per-tenant Postgres roles, row-level security
policies enforced against an untrusted application, per-tenant
connection pools brokered by an authentication proxy). It rules in a
defense posture aimed at hygiene (schema-scoped names, search_path
scoping, per-tenant migration ledger, per-tenant data directories).

## Non-goals

- Hostile multi-tenancy. This RFC does not propose Postgres role
  separation, row-level security, network segmentation between
  tenants, or per-tenant secret stores.
- Cross-tenant aggregation as a primary feature. A read-only union
  across tenants is allowed as an explicit operator action, not as
  an everyday query path.
- Cloud-managed Postgres or multi-host clustering. Tenancy here is
  purely co-location on a single local Postgres cluster.
- Per-tenant model weights or per-tenant local model runtime. The
  local LLM and embedder are stateless and shared.
- Renaming or re-homing existing data. The current single-tenant
  install becomes the first tenant in place; no dump/restore.

## Design space considered

Three real options, in order of isolation strength and operational
cost.

### A. Database-per-tenant (one cluster, N databases)

Each tenant gets its own database within the shared cluster
(`engram_home`, `engram_work`, ...). Connection strings are
tenant-scoped. Postgres makes cross-database joins impossible
without `postgres_fdw` or `dblink`. Migrations run unchanged per
database.

Pros: strongest isolation short of separate clusters; zero risk
of search_path mistakes; minimal application-code change.

Cons: no shared reference tables (predicate vocabulary, audit
reason vocabulary, embedding model registry) — each tenant
re-seeds. Per-database connection cost. Cluster-level resources
(shared_buffers, the pgvector extension state) are still shared,
which is the actual resource-sharing goal, so this option does
satisfy the motivation — but at the cost of duplicating every
reference table per tenant.

### B. Schema-per-tenant within one database (recommended)

One database, N tenant schemas (`engram_home`, `engram_work`, ...)
plus a small shared `engram_common` schema for vocabularies and
registries that are genuinely identical across tenants. Each
connection sets `search_path = engram_<tenant>, engram_common`,
so every existing unqualified table reference (`sources`,
`messages`, `segments`, `beliefs`, ...) resolves into the tenant
schema without code changes.

Pros: structural isolation at the SQL layer (an unqualified
`SELECT * FROM beliefs` cannot see another tenant); cheap shared
reference data; one connection pool can serve many tenants by
swapping `search_path`; migrations still run per tenant, but the
SQL files themselves are unchanged.

Cons: schema-qualified ad-hoc SQL (`SELECT * FROM
engram_home.beliefs UNION ...`) is possible. For same-trust
tenants that is a feature, not a leak; for any other threat
model it would be a hole. Migration runner needs a per-tenant
`schema_migrations` ledger (or the same ledger keyed by tenant).

### C. Row-level tenancy (one schema, `tenant_id` column on every table)

Add `tenant_id` to every raw and derived table, enforce scoping
in application code (and optionally via RLS policies). One
physical schema; one set of indexes; analytics-friendly.

Pros: maximum sharing, including pgvector HNSW indexes that span
all tenants and are amortized across them; trivial cross-tenant
analytics.

Cons: every query path must explicitly scope by `tenant_id`, and
"forget the WHERE clause" is the exact failure mode this RFC
exists to prevent. The engram principle that raw evidence is
immutable and append-only is preserved structurally today by
"the row exists or it doesn't" — adding `tenant_id` to that
contract means a missing scope can silently merge two tenants'
evidence into one query result. RLS policies fix this in
principle but only if every connection assumes a known role and
the role-to-tenant binding is trusted, which contradicts the
"same root authority everywhere" property.

## Recommendation

Adopt **Option B (schema-per-tenant in one database)**. It matches the
operator's mental model ("instance A vs instance B"), preserves the
raw-is-sacred invariant via SQL-level structural scoping, allows the
genuinely shared reference tables to live in one place, and reuses
the existing checksum-stamped migration runner with a narrow
extension. Option A is the fallback if search_path discipline ever
proves too easy to violate in practice. Option C is rejected as
overweight for the stated threat model and underweight for any
stronger one.

## Schema layout

Two kinds of schema:

- `engram_<tenant>` — one per tenant. Contains every table currently
  defined under `public/` by the migrations: `sources`,
  `conversations`, `messages`, `notes`, `captures`, `segments`,
  `segment_embeddings`, `segment_generations`, `embedding_cache`,
  `claims`, `beliefs`, `claim_audits`, `belief_audit`, `entities`,
  `entity_resolution_events`, `entity_edges`, `belief_review_actions`,
  `pinned_beliefs`, `consolidation_progress`, `schema_migrations`,
  plus the per-tenant enums (`source_kind`, `capture_type`,
  `consolidation_status`).
- `engram_common` — one, shared. Reference data and registries that
  are identical across tenants and that no tenant should mutate
  independently:
  - `audit_reason_vocabulary` (currently in `migrations/007_claim_audits.sql`)
  - `predicate_vocabulary` (whichever migration owns it, when
    promoted from RFC 0028)
  - any future "embedding model registry" / "extraction prompt
    registry" tables that should be globally versioned

Existing migrations relocate via a one-time relocation step (see
below); they do not need to be rewritten because all current
`CREATE TABLE` statements are schema-unqualified and will land in
whatever schema `search_path` puts first.

Postgres enums are schema-scoped. The existing `source_kind`,
`capture_type`, `consolidation_status` enums therefore become
per-tenant. That is correct: a tenant should be free to extend
its own `source_kind` (e.g. RFC 0032's `claude_code`) without
forcing every other tenant to carry the value.

Vector indexes (`segment_embeddings_nomic_768_hnsw_idx` and
friends) become per-tenant. This is the right cost trade for the
isolation property; pgvector index sharing across tenants is
explicitly out of scope (it would force Option C).

## Connection scoping

`src/engram/db.py` is extended:

```python
def database_url(env_var: str = "ENGRAM_DATABASE_URL") -> str: ...

def tenant(env_var: str = "ENGRAM_TENANT") -> str:
    return os.environ.get(env_var, "default")

def tenant_schema(tenant_name: str | None = None) -> str:
    return f"engram_{tenant_name or tenant()}"

def connect(url: str | None = None,
            tenant_name: str | None = None) -> psycopg.Connection:
    conn = psycopg.connect(url or database_url())
    schema = tenant_schema(tenant_name)
    conn.execute(
        "SET search_path = %s, engram_common",
        (schema,),
    )
    return conn
```

Every code path that calls `connect()` (which is every code path
that touches Postgres in engram today) becomes tenant-scoped with
no further change. Unqualified table names resolve into the
tenant schema first, the shared schema second, and never into
`public`. Code that needs to reach another tenant must do so by
explicit schema qualification and is therefore reviewable.

The migration in-place rule from RFC 0007 (raw is sacred,
schema-stamped IDs, etc.) is unaffected.

## Migration runner changes

`src/engram/migrations.py` currently keeps `schema_migrations` in
`public` and applies SQL files in `migrations/` against it.
Required changes:

1. Move `schema_migrations` into each tenant schema. The runner
   takes a `tenant_name` argument, sets `search_path` for the
   connection, and reads/writes `schema_migrations` from
   `engram_<tenant>`.
2. Apply each migration with the tenant `search_path` already set,
   so every unqualified `CREATE TABLE` lands in the tenant schema.
3. Bootstrap step: if `engram_<tenant>` does not exist, create it
   before running migration 001. If `engram_common` does not
   exist, create it once and apply any common-only migrations
   there.
4. Split or annotate the migrations that touch `engram_common`
   tables (currently the audit-reason vocabulary seed). One
   approach: keep the SQL files as they are and ship a small
   `migrations/common/` subdirectory that the runner applies
   exactly once against `engram_common`. Predicate-vocabulary
   seeds and audit-reason seeds belong here.
5. Migration checksum invariants stay intact per tenant.

The migration relocation for an existing install is a one-time
operation:

```sql
CREATE SCHEMA engram_default;
ALTER SCHEMA public RENAME TO public_legacy;  -- optional, for safety
ALTER TABLE public_legacy.sources SET SCHEMA engram_default;
-- … repeat for every table, enum, sequence, index
CREATE SCHEMA engram_common;
ALTER TABLE engram_default.audit_reason_vocabulary
    SET SCHEMA engram_common;
```

A `scripts/relocate_default_tenant.py` (or a one-shot migration
gated on "is the current install single-tenant?") handles this so
the operator does not run it by hand.

## CLI and Makefile changes

- `engram` CLI gains a `--tenant <name>` global flag, defaulting
  to `$ENGRAM_TENANT` and then `"default"`.
- Every `Makefile` target that exports `ENGRAM_DATABASE_URL` also
  exports `ENGRAM_TENANT`:

  ```make
  migrate: install
  	ENGRAM_DATABASE_URL="$(DATABASE_URL)" \
  	ENGRAM_TENANT="$(TENANT)" \
  	$(PYTHON) -m engram.cli migrate
  ```

  with `TENANT ?= default` near the top of the Makefile.
- `make migrate TENANT=work` applies all migrations into
  `engram_work` (creating the schema first if needed).
- `make pipeline TENANT=home` runs the full segment / embed /
  extract / consolidate loop against the `home` tenant only.

The phase 5 serving surface (`context_for`, and the RFC 0027
interview web UI) must accept and surface the tenant explicitly.
Two engram web servers should bind different loopback ports
(`ENGRAM_INTERVIEW_PORT` per tenant), and every served page
should display the tenant name so the operator cannot accidentally
review one tenant's claims while believing they are looking at
another's.

## Filesystem and operational layout

Resources that live outside Postgres also need per-tenant homes
so co-tenancy is not just a Postgres property:

- **Striatum state.** `.striatum/state.sqlite3` becomes
  `.striatum/<tenant>/state.sqlite3`, picked up via an
  `ENGRAM_STRIATUM_DIR` override or an analogous variable in
  the striatum skill stack. The Phase 4 workflows under
  `striatum/phase-4-spec-review/` are checked into the repo and
  shared, but their per-run state must be tenant-scoped.
- **Operational artifact home (RFC 0014 / D074).**
  `docs/operations/<area>/<loop>/reports/` is repo-tracked and
  remains shared; **run-specific** outputs that contain raw
  evidence land under a tenant-scoped path
  (`docs/operations/<area>/<loop>/runs/<tenant>/...`) and are
  gitignored unless explicitly published.
- **Local export blobs.** ChatGPT, Claude desktop, Gemini, and
  Claude Code (RFC 0032) source archives land under a
  tenant-scoped directory (`/var/lib/engram/<tenant>/`) so the
  proximal-side mirror cannot get mixed.
- **Environment files.** A per-tenant `.env.<tenant>` is the
  intended shape; the Makefile sources it when `TENANT=<name>`
  is passed. The single-tenant install continues to work with no
  `.env.default` required.

## Open questions

- **Embedding cache sharing.** `embedding_cache` from migration 004
  is content-addressed and dedupes embedding work across identical
  inputs. There is a case for moving it to `engram_common` so two
  tenants that embed the same public-domain snippet pay the cost
  once. Counter-argument: it leaks an existence signal across
  tenants ("the other tenant has already embedded this exact
  string"). For same-trust tenants this is fine; flagging for
  explicit decision before implementation.
- **Cross-tenant retrieval as a first-class operator move.** Should
  there be `engram --tenant home,work query "..."` that
  schema-qualifies both tenants and unions the results? Useful for
  "what do I think about X across home and work?" Defaulting to
  no; revisit when the serving path (PHASE-0005) lands.
- **Per-tenant or shared predicate / extraction prompt versioning.**
  RFC 0017 made extraction prompts versioned. The version registry
  itself is shared (`engram_common`), but two tenants may want to
  pin to different versions for reproducibility windows. The
  pinning record is per-tenant; the registry is shared.
- **Vector index sharing.** Decided: per-tenant in this RFC.
  Reconsidered only if disk pressure from N × HNSW indexes
  becomes material.
- **Postgres role separation.** This RFC says one Postgres role
  connects to all tenants because the threat model is same-trust.
  Operators who want belt-and-suspenders may still create per-tenant
  roles with `USAGE` on only one tenant schema; the application is
  not required to do so but should not break if they do.
- **Backups.** A `pg_dump --schema=engram_<tenant>` is a clean
  per-tenant snapshot. `pg_dump` of the whole database covers all
  tenants in one file. Both work; no engram-side change needed,
  but document the recommended pattern.

## Acceptance criteria

A minimum implementation lands when:

1. A migration (or relocation script) introduces
   `engram_<default>` and `engram_common` and moves existing
   tables, enums, sequences, and indexes accordingly without
   data loss. The current single-tenant install upgrades cleanly.
2. `src/engram/db.py::connect()` sets `search_path` to the
   tenant schema and `engram_common` on every connection.
3. `src/engram/migrations.py` applies migrations against a named
   tenant, tracks per-tenant `schema_migrations`, and creates a
   new tenant schema on first migration.
4. CLI accepts `--tenant`; Makefile accepts `TENANT=`; both
   default to `default`.
5. Tests under `tests/` cover: a fresh tenant bootstrap, two
   tenants coexisting in one test database without cross-reads
   (e.g., a row inserted into tenant A's `messages` does not
   appear in a tenant B `SELECT * FROM messages`), and a
   migration-checksum drift test that operates per tenant.
6. Operational paths outside Postgres (Striatum SQLite, export
   blob storage, per-tenant ports for the web UI) are documented
   in `docs/process/` and gated on `ENGRAM_TENANT`.
7. `CHANGELOG.md` and `DECISION_LOG.md` updated per AGENTS.md.

## Risks

- **Search_path mistake in an ad-hoc script.** An operator running
  `psql` without setting `search_path` first will land in
  `public`, which after relocation is either empty or holds only
  legacy artifacts. Mitigation: ship a small psql snippet
  (`\set tenant home` → `SET search_path = engram_:tenant,
  engram_common;`) and document it; consider an alias in
  `~/.psqlrc`.
- **Cross-tenant query as a foot-gun.** Same-trust tenants can
  schema-qualify across schemas. Mitigation: code review and the
  open-question above about an explicit `--tenant a,b` path that
  makes intent legible.
- **Migration drift between tenants.** Tenants on different
  migration heads can produce different table shapes. Mitigation:
  a `make migrate-all` target that iterates over a configured
  tenant list and applies missing migrations to each; a
  `engram status --all-tenants` that reports each tenant's head.
- **One-time relocation bug corrupts existing install.** The
  relocation is one-way and touches every table. Mitigation:
  run inside a single transaction; require a `pg_dump` before
  the relocation runs; gate the relocation behind an explicit
  CLI flag; cover with tests that build a single-tenant
  reference database and verify it relocates byte-equivalent.
- **Operational artifact bleed.** A reviewer runs a Striatum
  workflow against tenant B but writes review notes into tenant
  A's report directory by habit. Mitigation: tenant-scoped run
  directories with the tenant name baked into the path; web UI
  always shows the active tenant.

## Next step

A short pre-implementation experiment: spin up an empty Postgres
database, apply the existing `migrations/` against
`engram_test_default`, then apply them a second time against
`engram_test_work`, and prove with `psql` that
`SET search_path = engram_test_work, engram_common` and
`SET search_path = engram_test_default, engram_common` resolve
the same unqualified queries to disjoint data. That validates the
core search_path-scoping property before the migration runner
changes land in code.
