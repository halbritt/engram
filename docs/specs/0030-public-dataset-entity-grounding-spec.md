<a id="spec-0030"></a>
# Spec 0030: Public-Dataset Entity Grounding Implementation Contract

| Field | Value |
|-------|-------|
| Spec | 0030 |
| Title | Public-Dataset Entity Grounding for Claim Extraction |
| Status | accepted |
| Source RFC | [RFC 0030](../rfcs/0030-public-dataset-entity-grounding.md) |
| Source review | [RFC 0030 final design review](../reviews/rfc0030-grounding-claim-extraction/FINAL_REVIEW.md) |
| Date | 2026-05-09 |
| Decision refs | D020 (LLM-local), D044 (gold-set advisory), D068 (artifact-id), D076 (32k context budget), D080 (RFC 0027 promotion) |
| Phase refs | PHASE-0003 (extraction), PHASE-0004 (entity consolidation) |

## Purpose

Claim extraction (`src/engram/extractor.py::extract_claims_from_segment`)
gains entity grounding against locally-held public datasets (Wikidata,
GeoNames). This spec is the implementation contract derived from the
revised RFC 0030 and the design-review synthesis. Implementation lands
in four commits behind a 600-segment three-arm bench gate.

## Non-negotiable invariants (preserved verbatim from RFC § Non-negotiable)

1. **No live web access from the extraction path.**
2. **Personal evidence does not leave the machine.**
3. **Per-agent dataset grants are explicit and recorded.**
4. **Raw evidence stays sacred.**
5. **Reproducibility is preserved.**

These five are the privacy posture. Each is enforced by a named code
chokepoint in this spec; § Code-side enforcement names the modules
and the AST-walk test.

## Out of scope

Same as RFC 0030 § Scope (Out of scope). Additionally for spec-time:

- No live Wikidata / GeoNames HTTP API client at any layer.
- No telemetry, usage analytics, or remote-call instrumentation.
- No automatic dataset refresh; snapshot lifecycle is operator-driven.

## Architecture

### Module layout

```
src/engram/grounding/
    __init__.py             # public exports
    snapshot.py             # ONLY module permitted to make outbound network calls
    resolver.py             # surface-form → candidate set; HTTP-client-forbidden
    attachment.py           # post-extraction writer of entity_external_references
    grants.py               # GrantStore (single-accessor chokepoint)
    private_aliases.py      # operator override table; resolver consults first
    schema.py               # snapshot manifest dataclasses, Candidate, etc.
    bench.py                # three-arm bench mechanics for `engram phase3 grounding-bench`

src/engram/extractor.py     # gains candidate-block assembly (HTTP-client-forbidden)
src/engram/cli.py           # gains `engram grants` and `engram grounding` subparsers
```

### Code-side enforcement

The five non-negotiables are enforced by:

- **Forbidden HTTP-client imports** in `resolver.py`, `attachment.py`,
  `extractor.py`, `grants.py`, `private_aliases.py`, `bench.py`. Test:
  `tests/test_grounding.py::test_no_http_clients_in_forbidden_modules`
  walks the AST of these modules and asserts no `urllib`, `requests`,
  `httpx`, `aiohttp`, `socket` imports.
- **Sanctioned-network module:** `snapshot.py` is the *only* module
  permitted to make outbound calls. Its surface area is bounded:
  `fetch(dataset_id, version) -> SnapshotManifest`,
  `verify(manifest) -> bool`. The function takes only public dataset
  identifiers; tests assert it cannot accept corpus content as a
  parameter.
- **Single-accessor grant chokepoint:** every read of an active grant
  goes through `grants.GrantStore.read_active(role: str, dataset: str)
  -> Optional[Grant]`. Test:
  `tests/test_grounding.py::test_grants_single_accessor` greps the
  `src/engram/` tree (excluding `grants.py`) for any direct SQLite
  access to the `grants` table; asserts none.

### DECISION_LOG lock

On spec acceptance, a new `D###` entry is added to `DECISION_LOG.md`
whose body is the verbatim five-bullet list of non-negotiables from
RFC 0030. Future supersession requires a new `D###` naming the
predecessor. The spec carries this obligation; the operator applies
the entry.

## Schema

### Production PostgreSQL (new tables)

```sql
-- Migration: migrations/013_grounding_external_refs.sql

CREATE TABLE entity_external_references (
    eer_id          TEXT PRIMARY KEY,         -- D068 prefix: eer_*
    entity_id       TEXT NOT NULL REFERENCES entities(entity_id),
    dataset         TEXT NOT NULL,
    external_id     TEXT NOT NULL,
    snapshot_id     TEXT NOT NULL,            -- snapshot_id format below
    confidence      NUMERIC NOT NULL,
    superseded_by   TEXT REFERENCES entity_external_references(eer_id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (entity_id, dataset, external_id, snapshot_id)
);
CREATE INDEX CONCURRENTLY idx_eer_dataset_external_id
    ON entity_external_references (dataset, external_id);
CREATE INDEX CONCURRENTLY idx_eer_entity_id
    ON entity_external_references (entity_id) WHERE superseded_by IS NULL;

-- Append-only enforcement
CREATE TRIGGER trg_eer_no_update_delete
    BEFORE UPDATE OR DELETE ON entity_external_references
    FOR EACH ROW EXECUTE FUNCTION raise_append_only_violation();

CREATE TABLE grounding_resolution_set (
    grs_id          TEXT PRIMARY KEY,         -- D068 prefix: grs_*
    claim_id        TEXT NOT NULL REFERENCES claims(claim_id),
    run_id          TEXT NOT NULL,            -- extraction run id
    snapshot_pins   JSONB NOT NULL,           -- list of {dataset, snapshot_id}
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (claim_id, run_id)
);
CREATE INDEX CONCURRENTLY idx_grs_run_id
    ON grounding_resolution_set (run_id);

CREATE TABLE private_aliases (
    pal_id              TEXT PRIMARY KEY,     -- D068 prefix: pal_*
    surface_form        TEXT NOT NULL,
    scope               TEXT NOT NULL CHECK (scope IN ('segment','corpus')),
    segment_id          TEXT REFERENCES segments(segment_id),
    suppressed_dataset  TEXT NOT NULL,
    suppressed_external_id TEXT NOT NULL,
    reason              TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX CONCURRENTLY idx_pal_surface_form
    ON private_aliases (surface_form);

-- Snapshot manifest (production-side record of registered snapshots)
CREATE TABLE grounding_snapshots (
    snapshot_id     TEXT PRIMARY KEY,         -- format: <dataset>@<date>@sha256:<hash>
    dataset         TEXT NOT NULL,
    snapshot_date   DATE NOT NULL,
    content_hash    TEXT NOT NULL,
    manifest_path   TEXT NOT NULL,            -- ~/.engram/grounding/<dataset>/<id>/MANIFEST.json
    storage_bytes   BIGINT NOT NULL,
    indexed_at      TIMESTAMPTZ,
    rolled_back_at  TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (dataset, snapshot_date, content_hash)
);
```

The migration is idempotent: re-running is a no-op via `CREATE TABLE
IF NOT EXISTS` and conditional index creation.

### Scratch SQLite (grants live outside production PG)

`~/.engram/grants/grants.sqlite3`:

```sql
CREATE TABLE IF NOT EXISTS grants (
    role         TEXT NOT NULL,
    dataset      TEXT NOT NULL,
    granted_at   TIMESTAMP NOT NULL,
    granted_by   TEXT NOT NULL,
    revoked_at   TIMESTAMP,
    PRIMARY KEY (role, dataset)
);

CREATE TABLE IF NOT EXISTS grants_audit (
    audit_id     TEXT PRIMARY KEY,            -- D068 prefix: gae_* (grant audit event)
    role         TEXT NOT NULL,
    dataset      TEXT NOT NULL,
    action       TEXT NOT NULL,               -- granted|revoked|read
    occurred_at  TIMESTAMP NOT NULL,
    process_pid  INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_grants_audit_occurred_at
    ON grants_audit (occurred_at);
```

A marker file at `~/.engram/grants/.engram-no-sync` documents the
non-sync stance. Audit rows older than 90 days are truncated by
`grants.GrantStore.maintenance()`, called on every CLI invocation.

### Snapshot storage layout

```
~/.engram/grounding/<dataset>/<snapshot_id>/    (mode 0700)
    MANIFEST.json                               (mode 0600)
    data/                                       (raw dataset files)
    index/                                      (resolver lookup index, e.g. SQLite)
```

`engram` refuses to use a snapshot directory whose mode bits are
looser than 0700/0600.

## Resolver contract

### Input/output dataclasses (`src/engram/grounding/schema.py`)

```python
from dataclasses import dataclass
from typing import Optional

@dataclass(frozen=True)
class SurfaceFormSpan:
    text: str
    start: int      # char offset in segment
    end: int

@dataclass(frozen=True)
class Candidate:
    dataset: str            # e.g. "wikidata", "geonames"
    external_id: str        # e.g. "Q42", "geoname:5391959"
    snapshot_id: str        # full snapshot_id including hash
    label: str              # canonical label (sanitized; <=200 chars)
    confidence: float       # in [0.0, 1.0]
    description: Optional[str]  # sanitized; None if rejected by sanitizer

@dataclass(frozen=True)
class SnapshotPin:
    dataset: str
    snapshot_id: str
```

### Surface-form normalization (pinned)

```python
def normalize_surface_form(s: str) -> str:
    return unicodedata.normalize("NFKC", s).lower().strip().split()
    # Returns space-collapsed normalized string. Pinned for index compatibility.
```

Trade-off: precision over recall. Tests pin both directions.

### Resolver determinism contract

```python
class Resolver:
    def resolve(
        self,
        surface_form: str,
        kind_hint: Optional[EntityKind],
        snapshot_pin: SnapshotPin,
    ) -> tuple[Candidate, ...]:
        """Deterministic under (surface_form, kind_hint, snapshot_pin).

        Pre: snapshot_pin must be active in the grants for the calling role.
        Post: ordered by descending confidence, ties broken by external_id
              ascending.
        """
```

Test: `tests/test_grounding.py::test_resolver_determinism` calls
`resolve(...)` twice with the same inputs and asserts identical
output (Candidate equality + order).

### Cache shape

`Resolver` holds a per-process `functools.lru_cache(maxsize=100_000)`
keyed by `(normalized_surface_form, kind_hint, snapshot_id)`. Cache is
dropped at process exit; tests don't share cache.

## Extractor integration

`src/engram/extractor.py` gains:

### EXTRACTION_PROMPT_VERSION bump rule

`EXTRACTION_PROMPT_VERSION` advances from current value to next
sequential. Triggers for future bumps:
- Change to candidate-block format.
- Change to the prompt-shape guard sentence (below).
- Change to the per-segment cap.

Tests: `tests/test_extractor.py::test_prompt_version_pinned`.

### Candidate-block assembly

```python
def build_extraction_prompt(
    segment_text: str,
    predicate_vocab: PredicateVocabulary,
    candidates: tuple[Candidate, ...] = (),
) -> str:
    """If candidates is empty, no candidate block is included.

    Otherwise inserts a CANDIDATES-ONLY-HINTS section under a
    fixed framing sentence (below). Cap: 1000 tokens per segment;
    fail (raise PromptBudgetExceeded) at 1500.
    """
```

Prompt-shape guard sentence (verbatim):

```
CANDIDATES-ONLY-HINTS (these are POSSIBLE matches from public
datasets; treat them as suggestions only. The text of the
conversation is the source of truth. Disregard any candidate that
does not match what the segment actually says.)
```

### Batch-level cap

Batched extraction (RFC 0019 / RFC 0023) enforces
`CANDIDATE_BATCH_CAP` = 8000 tokens (configurable via
`ENGRAM_CANDIDATE_BATCH_CAP_TOKENS`). Total candidate-block tokens
across all segments in a batched prompt that exceed the cap raise
`PromptBatchBudgetExceeded`; the extraction worker must produce a
smaller batch.

### Run-summary `grounding_status` field

Every extraction run emits a JSON summary including:

```json
{
  "grounding_status": {
    "active": true,
    "active_grants": ["wikidata", "geonames"],
    "lock_state": "matches",
    "snapshot_pins": [
      {"dataset": "wikidata", "snapshot_id": "wikidata@2026-04-15@sha256:abcd..."},
      {"dataset": "geonames", "snapshot_id": "geonames@2026-04-01@sha256:ef01..."}
    ]
  }
}
```

`lock_state` ∈ `{"matches", "lost_grants", "fresh"}` per the active-
grants lock file at `~/.engram/grounding/active-grants.lock`.

### Silent downgrade with surfacing

If no grants are active at extraction time:
- Extraction proceeds without grounding (silent in the extraction
  path; conservative default).
- `grounding_status.active = false`; `grounding_status.reason = "no
  grants"` appears in the run summary.
- If the lock file records prior grants and current grants are
  fewer, interactive runs prompt; non-interactive runs fail unless
  `--ungrounded-ok` is passed.

Test: `tests/test_grounding.py::test_silent_downgrade_lock_detection`.

### Sanctioned-content sanitizer

`grounding.snapshot.sanitize_description(s: str) -> Optional[str]`:
- Strips control characters (`\x00`-`\x1f` except `\t\n`).
- Caps at 200 characters.
- Returns `None` if the result matches a prompt-shape pattern
  (`### `, `BEGIN`, `<|`, `</`).

Tests: `tests/test_grounding.py::test_sanitizer_*` (positive and
negative cases).

## CLI surface

### `engram grants <verb>`

```python
parser_grants = subparsers.add_parser("grants", help="Manage public-dataset grants")
g = parser_grants.add_subparsers(dest="grants_command", required=True)

p_list = g.add_parser("list", help="List active grants")
p_list.add_argument("--usage", action="store_true",
                    help="Include last-accessed and access-count per grant")
p_list.add_argument("--json", action="store_true")
# Exit codes: 0 ok; 8 invalid args.

p_grant = g.add_parser("grant", help="Grant a role access to a dataset")
p_grant.add_argument("role")
p_grant.add_argument("dataset")
p_grant.add_argument("--json", action="store_true")
# Exit codes: 0 granted; 4 already granted; 6 unknown dataset; 8 invalid args.

p_revoke = g.add_parser("revoke", help="Revoke a role's access to a dataset")
p_revoke.add_argument("role")
p_revoke.add_argument("dataset")
p_revoke.add_argument("--json", action="store_true")
# Exit codes: 0 revoked; 4 not granted; 8 invalid args.

p_template = g.add_parser("apply-template",
                          help="Apply a grant template to a role")
p_template.add_argument("template",
                        choices=["places-only", "places-and-companies",
                                 "everything-public"])
p_template.add_argument("role")
p_template.add_argument("--json", action="store_true")
# Exit codes: 0 applied; 8 invalid args.
```

### `engram grounding <verb>`

```python
parser_grounding = subparsers.add_parser("grounding",
                                          help="Manage public-dataset snapshots")
gr = parser_grounding.add_subparsers(dest="grounding_command", required=True)

p_snapshot = gr.add_parser("snapshot",
                           help="Fetch and index a dataset snapshot")
p_snapshot.add_argument("--dataset", required=True,
                        choices=["wikidata", "geonames", "places",
                                 "companies", "public-figures"])
p_snapshot.add_argument("--version", help="upstream version (default: latest)")
p_snapshot.add_argument("--json", action="store_true")
# Progress shown on TTY; periodic JSON status lines on non-TTY.
# Exit codes: 0 ok; 4 already exists at this version; 5 budget exceeded;
#             6 download/verify failed; 8 invalid args.

p_rollback = gr.add_parser("rollback",
                           help="Roll back to a prior snapshot (tombstones EER rows)")
p_rollback.add_argument("--snapshot-id", required=True)
p_rollback.add_argument("--json", action="store_true")
# Exit codes: 0 ok; 4 not found; 8 invalid args.

p_detach = gr.add_parser("detach",
                         help="Detach grounded resolutions from claims (cheap rollback)")
g2 = p_detach.add_mutually_exclusive_group(required=True)
g2.add_argument("--segment")
g2.add_argument("--all-since")  # ISO date
p_detach.add_argument("--json", action="store_true")
# Exit codes: 0 ok; 8 invalid args.

p_versions = gr.add_parser("versions",
                           help="Show active snapshots and upstream-current versions")
p_versions.add_argument("--json", action="store_true")
# This is the ONLY operator-driven command that may reach the dataset
# upstream (to query latest version); it does so at command-invocation
# time, never during extraction.

p_onboarding = gr.add_parser("onboarding",
                             help="Walk through grounding setup interactively")
# Step-by-step: pick datasets → snapshot → index → grant → confirm → done.
```

### `engram phase3 grounding-bench`

```python
p_bench = phase3_subparsers.add_parser("grounding-bench",
                                       help="Run three-arm grounding bench")
p_bench.add_argument("--slice", required=True,
                     choices=["sanity-100", "promotion-600"])
p_bench.add_argument("--baseline-version", default="v8",
                     help="Arm A baseline prompt version")
p_bench.add_argument("--candidate-version", default="v9",
                     help="Arm B/C candidate prompt version")
p_bench.add_argument("--json", action="store_true")
# Reports false-rate AND coverage per arm; pre-registered decision rule
# evaluates accept/reject.
```

## Bench mechanics

Three arms (per RFC § D-H):

- **Arm A — v8 baseline** (existing prompt, no grounding). Cached
  artifacts; content-hash-pinned. If unavailable, bench preflight
  fails closed.
- **Arm B — v9 negative control** (new prompt with candidate-block
  format, grounding *disabled*).
- **Arm C — v9 grounded** (new prompt + grounding enabled).

Paired metric (per arm):

- `false_rate` = entity-mismatch false claims ÷ total claims with
  entity references in the slice.
- `coverage` = surface-form-spans-receiving-attachment ÷
  total-surface-form-spans-in-slice.

Pre-registered decision rule (Arm C vs Arm B):

- `false_rate_reduction = (B.false_rate - C.false_rate) / B.false_rate
  >= 0.30`.
- `coverage_drop = (B.coverage - C.coverage) / B.coverage <= 0.05`.
- Both must hold. The `--json` output includes `verdict ∈ {"promote",
  "hold"}`.

Sample sizes: 100 (sanity); 600 (promotion gate). The 600-sample slice
is stratified random over the corpus.

Independent secondary signal: a 100-segment held-out gold set with
operator-curated `(surface_form, expected_dataset, expected_external_id)`
triples. Bench reports precision/recall/F1 of resolver top-1 vs gold.

Baseline reproducibility: bench preflight verifies Arm A artifacts
match a stored content hash; refuses to run on mismatch.

## Operator onboarding

`engram grounding onboarding` flow:

1. **Pick datasets** — interactive prompt; default suggestion is
   `places-only` template.
2. **Snapshot** — runs `engram grounding snapshot --dataset <id>` for
   each picked; shows progress; verifies hash on completion.
3. **Index** — performed automatically as part of snapshot (per RFC
   § D-E "indexing happens at fetch time").
4. **Grant** — runs `engram grants apply-template <picked> <role>`.
5. **Confirm** — shows the resulting `engram grants list` output.
6. **Done** — prints a one-paragraph summary including the run-summary
   field operators should look for after their next extraction.

## Test matrix

`tests/test_grounding.py` covers:

| Test name | Asserts |
|---|---|
| `test_no_http_clients_in_forbidden_modules` | AST walk on resolver/attachment/extractor/etc shows no HTTP-client imports |
| `test_grants_single_accessor` | only `grants.py` accesses the `grants` table |
| `test_resolver_determinism` | `resolve(...)` is deterministic under fixed inputs |
| `test_normalize_surface_form_pinned` | NFKC + lowercase + collapse whitespace; recall trade-off documented |
| `test_snapshot_integrity_hash_loaded` | loader verifies hash on every read |
| `test_snapshot_integrity_mismatch_refuses` | tampered snapshot raises `SnapshotIntegrityError` |
| `test_snapshot_mode_bits_required` | snapshot dir mode 0700 / manifest 0600 enforced |
| `test_eer_append_only` | UPDATE/DELETE on `entity_external_references` raises |
| `test_tombstone_supersession` | new EER row with `superseded_by` linking prior row |
| `test_cascade_audit_visits_eer` | RFC 0018 cascade walk includes grounding |
| `test_grant_revocation_forward_only` | existing EER rows persist; live queries filter |
| `test_silent_downgrade_lock_detection` | lost-grants state surfaces in run summary |
| `test_sanitizer_strips_control_chars` | dataset description sanitizer |
| `test_sanitizer_rejects_prompt_shape_patterns` | sanitizer returns None on `###`/`BEGIN`/`<|` |
| `test_prompt_per_segment_cap` | 1000 token soft cap; fail at 1500 |
| `test_prompt_batch_cap` | `CANDIDATE_BATCH_CAP` enforced; `PromptBatchBudgetExceeded` |
| `test_private_aliases_consulted_first` | resolver returns no candidates when alias matches |
| `test_grounding_bench_three_arms` | `engram phase3 grounding-bench` produces three arms |
| `test_grounding_bench_decision_rule` | paired-metric thresholds applied correctly |
| `test_grounding_bench_baseline_pin` | preflight refuses on baseline content-hash mismatch |
| `test_storage_budget_enforcement` | `--dataset` snapshot refused when budget exceeded |
| `test_resolution_latency_skip_on_overflow` | per-segment >100ms warns and skips |

## Test fixture strategy

- A synthetic snapshot at `tests/fixtures/grounding/synthetic_dataset_v1/`
  (~10MB; content-hash-pinned in `tests/fixtures/grounding/MANIFEST.json`).
  Committed to repo.
- Integration tests opt-in via `ENGRAM_GROUNDING_INTEGRATION=1` to
  download a real subset (Wikidata-places ~500MB). CI does not run these.

## Migration plan

Single migration: `migrations/013_grounding_external_refs.sql`. Steps:
1. `CREATE TABLE` for the four new tables (idempotent via IF NOT EXISTS).
2. `CREATE INDEX CONCURRENTLY` for the seven indexes.
3. `CREATE TRIGGER` for the append-only enforcement on
   `entity_external_references`.

Re-running the migration is a no-op. The migration is reversible only
via a new dedicated rollback migration (not shipped in v1).

## Promotion path

1. **Spec authoring** (this document) — the multi-agent review run
   gates this spec.
2. **Implementation in four commits** (RFC § Promotion path step 4):
   - `migrations/013_grounding_external_refs.sql` + production DDL.
   - `src/engram/grounding/` module (every file listed above) + CLI
     surface in `src/engram/cli.py` + `tests/test_grounding.py`.
   - Extractor integration: `EXTRACTION_PROMPT_VERSION` bump,
     candidate-block assembly, run-summary `grounding_status` field +
     `tests/test_extractor.py` updates.
   - Consolidator integration: PHASE-0004 consumes external refs;
     `projection_audits` integrates grounding tombstones +
     `tests/test_consolidator.py` updates.
3. **Bench gate (Arm B vs Arm C on 600-segment slice)** — must satisfy
   the pre-registered decision rule. Iteration cost: 6-12 operator-
   hours + 2-6 wall-clock compute hours per cycle.
4. **Operator promotion** — after bench passes, operator runs
   grounded re-extraction; results land alongside ungrounded under
   the bumped `EXTRACTION_PROMPT_VERSION`.

## Acceptance criteria

The implementation satisfies this spec when:

- All migrations are idempotent and apply cleanly to a fresh and an
  existing database.
- Every test in the test matrix passes.
- `make test` and `make lint` are green.
- The three CLI subparser groups (`engram grants`, `engram grounding`,
  `engram phase3 grounding-bench`) produce help output matching the
  argparse definitions in this spec.
- A 100-segment sanity bench (Arm B vs Arm C) shows the predicted
  direction (false-rate down, coverage stable) before any 600-segment
  bench is run.
- The five non-negotiable invariants are enforced by their named
  chokepoints; every chokepoint test passes.
