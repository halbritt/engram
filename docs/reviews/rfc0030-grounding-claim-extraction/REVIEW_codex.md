# RFC 0030 Public-Dataset Entity Grounding Review - codex

author: reviewer-codex-gpt-5.5-001

Status: review
Date: 2026-05-09
RFC refs: RFC-0030
Decision refs: D020, D044, D068, D076, D080
Phase refs: PHASE-0003, PHASE-0004

Lens: implementation feasibility, integration with existing extractor and
consolidator code, prompt-budget impact, resolver placement (D-B).

## Findings

### F001 - Resolver placement (D-B) needs explicit module boundaries before spec
Severity: major
Source: § D-B Resolver placement; § Promotion path step 4b

The hybrid placement (option 3) requires three distinct components that
the RFC bundles together:
1. A surface-form extractor that scans segment text for entity-shaped phrases.
2. A candidate resolver that maps surface forms to dataset candidates.
3. A post-extraction attachment pass that writes
   `entity_external_references` rows.

Each is a separate testable unit with its own contract. The RFC describes
the data flow but not the seam. For an implementation reviewer to bound
the work, the spec needs:
- Whether (1) is per-segment or per-claim; whether the extractor reuses
  the existing predicate-vocabulary tokenizer or introduces a new one.
- The resolver's input/output shape: `(surface_form: str, hint:
  Optional[EntityKind]) -> tuple[Candidate, ...]`.
- Whether (3) is a synchronous post-pass or a separate worker following
  the `(input_id, version) -> idempotent commit` contract from RFC 0001.

Suggested fix: D-B option 3 should add a "Module split" subsection that
names these three units and their interfaces.

### F002 - Prompt-shape impact under-specified for batched extraction
Severity: major
Source: § D-G extraction prompt impact; references to RFC 0023

D-G states the candidate block caps at ~1000 tokens per segment and
flags D076's 32k context budget. RFC 0023 (concurrent extraction
pipeline) and RFC 0019 (extraction batching server) push multiple
segments per request — by 16 or more segments per batch in concurrent
mode. At 1000 tokens × 16 = 16k tokens of candidate block alone,
leaving only the predicate vocabulary, the schema preamble, and the
segments themselves to fit in 16k more.

Suggested fix:
- State whether the cap is per-segment-in-batch or per-batch.
- If per-segment, add a batched-prompt assembly check that fail-closes
  when the total candidate-block tokens exceed `CANDIDATE_BATCH_CAP`
  (recommend 8000 by default).
- Add an `EXTRACTION_PROMPT_VERSION` bump rule: any change to the
  candidate-block format triggers a version bump.

### F003 - `extract_claims_from_segment` integration path missing
Severity: major
Source: § Architecture (implicit); § Promotion path step 4c; references
to `src/engram/extractor.py`

The current `extract_claims_from_segment` has a single signature with
implicit prompt construction. Grounding adds:
- A pre-call resolver invocation.
- A candidate-block in the prompt.
- A post-call attachment pass.

The RFC mentions "extractor / consolidator integration" as a single
commit (4c) but does not state how the resolver is injected — singleton,
dependency injection, module-level cache. Singleton-with-grant-check is
probably right, but say so.

Suggested fix: name the injection pattern, the cache shape (per-process
LRU? per-request? snapshot-pinned?), and the lifecycle (init at first
extraction, dropped at process exit).

### F004 - Migration shape (4a) under-specified; row counts and locking discipline missing
Severity: major
Source: § Promotion path step 4a

Step 4a says "new tables for grants, snapshots, and external references;
append-only triggers consistent with the existing pattern." The
implementer needs:
- Estimated table sizes at v1 (probably small for grants, larger for
  external_references depending on backfill scope).
- Whether the migration backfills any existing rows (probably no — old
  claims stay ungrounded under their existing prompt_version).
- Locking behavior: PostgreSQL `CREATE TABLE` is fine; `CREATE INDEX`
  on a populated table needs `CONCURRENTLY`. Specify which indexes
  exist at migration time.
- Idempotency: re-running the migration must be a no-op (engram's
  migrations have generally been idempotent; confirm).

Suggested fix: D-D and the promotion path should commit to a migration
sketch that names exact table DDL (column types, FK constraints, index
list) and labels each as `CREATE`, `CREATE INDEX CONCURRENTLY`, or
trigger.

### F005 - Test coverage matrix not committed
Severity: minor
Source: § Promotion path step 4c

"Update `tests/test_extractor.py` and add `tests/test_grounding.py`
covering grant enforcement" is too coarse. The implementer needs:
- Test for grant enforcement: granted role can read; ungranted role
  raises specific exception; revocation takes effect immediately on
  next read.
- Test for snapshot integrity (assuming the snapshot-hash fix from the
  privacy review lands).
- Test for resolver placement: hybrid placement actually places
  candidates in prompt and post-extraction attaches them.
- Test for `EXTRACTION_PROMPT_VERSION` bump on candidate-block format
  change.
- Test for downgrade: with no grants, extraction proceeds without
  grounding and produces ungrounded claim rows that are valid under
  the existing schema.

Suggested fix: spec should ship with a test matrix.

### F006 - Resolver input is "surface form" but no canonical normalization specified
Severity: minor
Source: § D-B; § Architecture

"Surface form" in the RFC is undefined. Is it the raw substring as it
appears in segment text? A normalized form (lowercase, whitespace-
collapsed, NFKC)? A lemma? Different choices make different lookup
indexes feasible.

Suggested fix: spec should pin a normalization rule and document the
trade-off (recall vs precision).

### F007 - Idempotency contract for the resolver's output
Severity: minor
Source: § D-B option 3; RFC 0001 contract

If the resolver is called twice on the same surface form during a single
extraction (or across re-extraction), it must return the same candidate
set under the same snapshot pin. The RFC implies this but does not state
it as a contract. Tests should pin it.

Suggested fix: spec should commit "resolver invocations are deterministic
under (surface_form, dataset@snapshot)".

### F008 - `engram grants` and `engram grounding` CLI shapes under-specified
Severity: minor
Source: § Promotion path step 4b

The CLI commands are named (`engram grants list/grant/revoke`,
`engram grounding snapshot/index`) but not shape-specified. Implementer
needs:
- Exit codes for each (grant exists vs not, dataset known vs unknown).
- JSON output for scripting (per the engram convention of `--json`
  flags elsewhere).
- Whether `engram phase3 extract` accepts a `--grounding-snapshot`
  override or always uses the active config.

Suggested fix: spec should ship the CLI surface as exact `argparse`
subparser definitions.

## Open questions

- What's the resolver's storage shape? Inline SQLite under the snapshot
  dir? An indexer module that translates the dataset dump into a
  searchable form? RFC defers; spec must answer.
- Is there a per-dataset adapter contract (Wikidata vs GeoNames have
  very different shapes), or one universal Candidate type with
  dataset-specific extraction?
- How does the resolver participate in RFC 0023 concurrent extraction?
  Each worker gets its own resolver instance, or shared cache?

verdict: accept_with_findings
