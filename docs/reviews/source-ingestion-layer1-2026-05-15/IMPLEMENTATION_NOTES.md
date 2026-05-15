# Layer 1 Implementation Notes — Source Contract + Git Importer

Lane: claude
Role: implementer

| Field | Value |
|-------|-------|
| Workflow | source-ingestion-layer1-2026-05-15 |
| Layer | Layer 1 — Source Contract Template + Git Metadata/Diff-Stat Importer |
| Date | 2026-05-15 |
| Source design | `docs/design/source-ingestion-expansion-proposal-2026-05-15.md` |
| Reference RFC | `docs/rfcs/0050-source-ingestion-expansion.md` (proposal status) |
| Reference backlog | `SOURCE_INGESTION_BACKLOG.md` § Layer 1 |
| Posture | Proposal-only handoff. No production code, schema, RFC, decision log, or changelog rows were written by this lane. |
| Branch state at write time | `engram/source-ingestion-rfc-research` (RFC 0050 + backlog already on this branch) |

## Posture Statement

This handoff is the artifact for the claude implementer lane of the
`source-ingestion-layer1-2026-05-15` workflow. The workflow scope as written to
this lane restricts writes to a single path
(`docs/reviews/source-ingestion-layer1-2026-05-15/IMPLEMENTATION_NOTES.md`) and
forbids edits to `src/`, `tests/`, `migrations/`, `docs/rfcs/`,
`DECISION_LOG.md`, `CHANGELOG.md`, `BUILD_PHASES.md`, and `ROADMAP.md`.

Therefore this document does not contain working code or a green `make test`
result. It contains the implementation plan that a downstream implementer (or a
follow-on workflow with write scope into `src/`, `tests/`, and `migrations/`)
can execute. Where the lane's role file calls for production code, that work is
deferred to the next workflow. Where the lane's role file calls for `make test`
to pass, the lane reports here that it could not be run from this artifact path
alone.

Nothing in this document promotes RFC 0050, modifies the decision log, edits
the RFC index, or adds a `source_kind`. All such changes remain the operator's
decision via `DECISION_LOG.md`.

## What Layer 1 Must Deliver

From `SOURCE_INGESTION_BACKLOG.md` § Layer 1 and the workflow prompt:

1. Source contract template under `docs/source-contracts/README.md`.
2. Example contracts: `docs/source-contracts/git.yaml` and a forward-pointer
   `docs/source-contracts/build_artifact.yaml`.
3. Contract validator at `src/engram/source_contract.py` exposing
   `validate_contract(path) -> ContractValidationResult` with a closed error
   vocabulary.
4. Migration adding `source_kind='git'` to the `source_kind` enum and creating
   new tables `git_commits` and `git_commit_paths`.
5. Git importer at `src/engram/git_import.py` implementing the RFC 0050
   contract for `source_kind=git`: commit metadata, parent links, refs, changed
   paths/numstat. Idempotent re-import. No outbound network. Coverage-gap
   emission on parse failure.
6. CLI verb `engram import git <repo-path>` with `--dry-run`, `--allow-dirty`,
   and `--full-patch=false` defaults.
7. Tests:
   - `tests/test_source_contract_validator.py`
   - `tests/test_git_importer.py`
   - `tests/test_git_importer_no_egress.py`
8. Fixture repo created programmatically in a test setup helper at
   `tests/fixtures/source_contract_git/` (two commits, one branch, one tag,
   one file rename).

## Existing Patterns The Implementation Should Follow

Before writing code, an implementer should re-read:

- `src/engram/striatum_ingest.py` — pattern for: module-top constants,
  dataclass result objects, `RuntimeError` subclass family
  (`StriatumBundleError` → `ManifestValidationError`, `IngestConflict`),
  bundle-shaped idempotency, `Jsonb` storage of raw payload, `repo`-as-label
  semantics in `sources`.
- `src/engram/claude_export.py` — pattern for: dataclass shape per source,
  `get_or_create_source`, `count_rows`, `conn.transaction()` wrapping per
  ingest, `IngestConflict` exception for changed immutable raw rows.
- `src/engram/chatgpt_export.py` — same pattern; useful for the
  message-style projections (not directly used here but informative for the
  next layer).
- `src/engram/segmenter.py` — pattern for the per-stage error family
  (`SegmentationError`) and `ENGRAM_`-prefixed module-top tunables (
  `IK_LLAMA_BASE_URL`, `DEFAULT_MAX_TOKENS`, etc.) read once at import.
- `migrations/014_striatum_tenant_corpus.sql` — pattern for adding tenant /
  corpus columns and indexes on a new source kind's tables.
- `migrations/015_striatum_projection.sql` — pattern for projection-shaped
  tables, generation-scoped rows, exact-reference indexes, and trigger-based
  immutability guards.
- `migrations/003_source_kind_claude.sql` — pattern for the bare
  `ALTER TYPE source_kind ADD VALUE IF NOT EXISTS 'claude';` migration when a
  new source kind is introduced.
- `tests/conftest.py` — `conn` fixture, `ENGRAM_TEST_DATABASE_URL` skip
  semantics, exhaustive `DROP ... CASCADE` block (new tables must be added to
  this list when they land).

Current `source_kind` enum values present on master at the time of this note:
`chatgpt`, `claude`, `gemini`, `striatum`. Migration 016 is the latest. The
next migration is therefore `017`.

## Proposed Source Contract Template

The contract template at `docs/source-contracts/README.md` should mirror the
RFC 0050 § Source Contract field set verbatim. It is documentation only at
Layer 1; the validator at `src/engram/source_contract.py` consumes it as
checked-in YAML.

### Template Outline (`docs/source-contracts/README.md`)

The template should contain:

1. A one-paragraph statement that contracts are required reviewer artifacts,
   not runtime registry rows. Reference RFC 0050 explicitly.
2. The four required questions (raw boundary, projection, default consumers,
   protection rules) as headings each adapter must answer.
3. The closed projection-family vocabulary verbatim from RFC 0050 § Projection
   Vocabulary:
   - `conversation_thread`, `document_record`, `project_event`,
     `execution_artifact`, `code_reference`, `artifact_reference`,
     `observation`, `place_event`, `asset_record`.
4. The closed operational-family vocabulary:
   - `coverage_gap`, `source_audit`.
5. The closed sensitivity-class vocabulary from RFC 0050 § Privacy And
   Sensitivity.
6. The closed gate vocabulary `EG-SI-000`..`EG-SI-100` and the
   `pass | fail | blocked_upstream | not_run | accepted_with_scope_limit`
   outcomes.
7. The mandatory YAML field set, exactly as RFC 0050 § Source Contract §
   Mandatory Fields lays it out, but with the source-specific values replaced
   by `<required>` markers and a comment indicating which fields are closed
   vocabulary.
8. A short section listing the validator's closed error vocabulary.
9. A "Validation" subsection that points at
   `tests/test_source_contract_validator.py` as the contract that the template
   itself must pass.

### Example Contract — `docs/source-contracts/git.yaml`

The git contract should be a faithful instance of the template:

- `source_kind: git`
- `source_family: project_execution`
- `sub_kinds`: `commit`, `branch`, `tag`, `diff_stat`
- `raw_artifact_boundary.acquisition`: `local filesystem`,
  `explicit user-provided export`
- `raw_artifact_boundary.network_policy`: `no outbound calls`
- `identity.source_instance_id`: `repository_root_identity`
- `identity.item_identity_keys`: `repository_id`, `commit_sha`
- `identity.logical_identity_keys`: `repository_id`, `ref_name`
- `temporal_fields.observed_at`: `committer_date`
- `temporal_fields.recorded_at`: `import_time`
- `deduplication.idempotency_key`: `source_kind`, `repository_id`, `commit_sha`
- `deduplication.conflict_policy`: `raise_on_changed_raw_artifact_hash`
- `privacy.privacy_tier_default`: `1`
- `privacy.sensitivity_class_default`: `routine_project`
- `projection_families`: `project_event`, `code_reference`
- `operational_families`: `coverage_gap`, `source_audit`
- `extraction_eligibility.default`: `metadata_only`
- `extraction_eligibility.participant_third_party`: `false`
- `extraction_eligibility.opt_in_required_for`: `patch_body`,
  `private_author_email`, `uncommitted_worktree`
- `raw_retention.required`: `object ids`, `commit metadata`,
  `changed path summaries`, `manifest hash`
- `raw_retention.optional`: `patch body`
- `provenance.required`: `source_id`, `raw row id`, `repository_id`,
  `commit_sha`, `content_hash`, `adapter_version`
- `rebuild.projection_generation`: `required`
- `rebuild.reproject_from_raw`: `required`
- `rebuild.stale_projection_policy`: `fail_closed_or_label_stale`
- `tests`: `contract_validator`, `idempotent_reimport`,
  `conflict_on_changed_raw_hash`, `raw_evidence_immutable`,
  `projection_rebuild_from_raw`, `no_network_access`,
  `privacy_inheritance`, `third_party_extraction_off_by_default`,
  `exact_reference_citation`

### Example Contract — `docs/source-contracts/build_artifact.yaml`

The build-artifact contract is a Layer 2 forward-pointer. It must be present
so the validator test exercises a second non-Markdown example, but its
adapter does not land until Layer 2. The contract should:

- Use `source_kind: build_artifact` and `source_family: project_execution`.
- Declare `sub_kinds`: `junit_xml`, `coverage_report`, `benchmark_json`,
  `lint_report`, `log_file`.
- Set `privacy.privacy_tier_default: 1` and
  `privacy.sensitivity_class_default: routine_project`, with a note that the
  Layer 2 importer must promote sensitivity when logs match a redaction
  pattern.
- Set `projection_families: [execution_artifact, artifact_reference]`.
- Set `operational_families: [coverage_gap, source_audit]`.
- Set `extraction_eligibility.default: metadata_only` with
  `opt_in_required_for: [full_log_body, secret_shaped_content]`.

This second contract is provided primarily so the validator's "every example
contract passes" test covers more than one adapter.

## Proposed Contract Validator (`src/engram/source_contract.py`)

A sketch of the validator module shape, faithful to the project Python
coding standard (RFC 0012):

- `from __future__ import annotations` and full type hints on all signatures.
- Module-top constants for the closed vocabularies (projection families,
  operational families, sensitivity classes, gate outcomes, sub-kind shape).
- A `SourceContractError(RuntimeError)` family root with closed-error
  subclasses for each error code below.
- A frozen dataclass `ContractValidationResult` with fields:
  `contract_path: Path`, `source_kind: str`, `is_valid: bool`,
  `errors: tuple[ContractValidationError, ...]`,
  `warnings: tuple[ContractValidationWarning, ...]`.
- A frozen dataclass `ContractValidationError` with
  `code: ContractErrorCode`, `field_path: str`, `message: str`.
- A `validate_contract(path: Path) -> ContractValidationResult` entrypoint
  that loads the YAML with `yaml.safe_load`, structurally validates against
  the field set, and emits errors in encounter order.

Closed error vocabulary (`ContractErrorCode`, `StrEnum`):

| Code | Meaning |
|------|---------|
| `CONTRACT_FILE_NOT_FOUND` | Path does not exist or is not a file. |
| `CONTRACT_NOT_YAML` | File could not be parsed as YAML. |
| `CONTRACT_NOT_OBJECT` | YAML root is not a mapping. |
| `MISSING_FIELD` | A mandatory top-level field is absent. |
| `EMPTY_FIELD` | A mandatory field is present but empty after `btrim`. |
| `UNKNOWN_PROJECTION_FAMILY` | Value is not in the closed projection vocabulary. |
| `UNKNOWN_OPERATIONAL_FAMILY` | Value is not in the closed operational vocabulary. |
| `UNKNOWN_SENSITIVITY_CLASS` | Value is not in the closed sensitivity-class vocabulary. |
| `UNKNOWN_NETWORK_POLICY` | Value is not `no outbound calls`. |
| `UNKNOWN_CONFLICT_POLICY` | Value is not in the closed conflict-policy set. |
| `MISSING_REQUIRED_TEST` | A required `tests:` entry is missing for the source family. |
| `MISSING_REQUIRED_PROVENANCE` | A required `provenance.required` entry is missing. |
| `INVALID_PRIVACY_TIER` | Value is not an integer in `1..5`. |
| `INVALID_EXTRACTION_DEFAULT` | Value is not in `metadata_only \| disabled \| opt_in`. |
| `INVALID_PARTICIPANT_THIRD_PARTY` | Value is not a boolean. |
| `INVALID_RAW_RETENTION` | Required list is empty or contains non-string values. |
| `UNKNOWN_SOURCE_FAMILY` | Value is not in `project_execution \| documents \| conversation \| observation \| asset`. |

The validator should accept warnings (not errors) for:

- contract has more `sub_kinds` than the family's typical list;
- `participant_third_party: true` while `extraction_eligibility.default` is
  not `disabled` (warn, do not error — Layer 1 only ships `git` where this is
  false).

Validator behavior at Layer 1 is documentation + tests; it is not invoked at
runtime by any importer in this layer. It is wired to a pytest module so
contract drift fails the suite.

## Proposed Migration `017_source_kind_git.sql`

Migration 017 adds the enum value and the two new tables. It must be safe to
apply on top of master, idempotent under retries, and leave the
`source_kind='git'` slot usable by the importer.

Key elements:

- `ALTER TYPE source_kind ADD VALUE IF NOT EXISTS 'git';` (mirrors migration
  003).
- A `git_repositories` table is intentionally not introduced. Instead, the
  repository instance lives in `sources` under `source_kind='git'`, keyed by
  `external_id = repository_id`, with `tenant_id`/`corpus_id` defaulting to
  `personal`/`personal`. This keeps the schema additions to two new tables.
- New table `git_commits`:
  - `id UUID PRIMARY KEY DEFAULT gen_random_uuid()`,
  - `source_id UUID NOT NULL REFERENCES sources(id)`,
  - `tenant_id TEXT NOT NULL`, `corpus_id TEXT NOT NULL`,
  - `repository_id TEXT NOT NULL` (denormalized for index-only queries),
  - `commit_sha TEXT NOT NULL CHECK (commit_sha ~ '^[0-9a-f]{40}$')`,
  - `tree_sha TEXT NOT NULL CHECK (tree_sha ~ '^[0-9a-f]{40}$')`,
  - `parent_shas TEXT[] NOT NULL DEFAULT '{}'::text[]` (zero-or-more),
  - `author_name TEXT NULL`, `author_email TEXT NULL`,
  - `committer_name TEXT NULL`, `committer_email TEXT NULL`,
  - `author_date TIMESTAMPTZ NOT NULL`,
  - `committer_date TIMESTAMPTZ NOT NULL`,
  - `subject TEXT NOT NULL`,
  - `body TEXT NOT NULL DEFAULT ''`,
  - `refs TEXT[] NOT NULL DEFAULT '{}'::text[]` (branch + tag heads at
    import time; informational, not authoritative — the canonical ref state
    lives in a future `git_refs` table once Layer 2/5 needs it),
  - `content_hash TEXT NOT NULL CHECK (content_hash ~ '^[0-9a-f]{64}$')`
    — the sha256 over the canonical commit-metadata projection used for
    conflict detection,
  - `adapter_version TEXT NOT NULL`,
  - `imported_at TIMESTAMPTZ NOT NULL DEFAULT now()`,
  - `privacy_tier INT NOT NULL DEFAULT 1`,
  - `raw_payload JSONB NOT NULL DEFAULT '{}'::jsonb`
    (`CHECK (jsonb_typeof(raw_payload) = 'object')`).

Indexes:

- `UNIQUE (tenant_id, corpus_id, repository_id, commit_sha)` — the primary
  idempotency boundary;
- `CREATE INDEX git_commits_commit_sha_idx ON git_commits (commit_sha)` for
  cross-repo exact-reference retrieval later;
- `CREATE INDEX git_commits_tenant_corpus_idx ON git_commits (tenant_id,
  corpus_id, repository_id, committer_date DESC);`.

New table `git_commit_paths`:

- `id UUID PRIMARY KEY DEFAULT gen_random_uuid()`,
- `commit_id UUID NOT NULL REFERENCES git_commits(id)`,
- `tenant_id TEXT NOT NULL`, `corpus_id TEXT NOT NULL`,
- `change_index INT NOT NULL CHECK (change_index >= 0)`,
- `change_kind TEXT NOT NULL CHECK (change_kind IN
  ('add','modify','delete','rename','copy','typechange','unknown'))`,
- `old_path TEXT NULL`, `new_path TEXT NULL`,
- `additions INT NULL CHECK (additions IS NULL OR additions >= 0)`,
- `deletions INT NULL CHECK (deletions IS NULL OR deletions >= 0)`,
- `is_binary BOOLEAN NOT NULL DEFAULT false`,
- `raw_payload JSONB NOT NULL DEFAULT '{}'::jsonb`,
- `UNIQUE (commit_id, change_index)`.

Indexes:

- `CREATE INDEX git_commit_paths_new_path_idx
   ON git_commit_paths (tenant_id, corpus_id, new_path);`
- `CREATE INDEX git_commit_paths_old_path_idx
   ON git_commit_paths (tenant_id, corpus_id, old_path)
   WHERE old_path IS NOT NULL;`

Immutability of raw rows: the project precedent (migrations 014/015) is a
trigger that allows updates only to the activation/invalidation columns. For
Layer 1 the simpler rule applies: `git_commits` and `git_commit_paths` are
strictly append-only. A trigger `prevent_git_commits_mutation()` should
reject all `UPDATE` and `DELETE` operations, with one carve-out: future
layers may add a `superseded_at TIMESTAMPTZ` column if rewritten history
needs to be tombstoned. That carve-out is deferred — Layer 1 ships with
strict append-only semantics.

Reversibility: this project's migration set does not ship paired down
migrations (cf. `migrations/003_source_kind_claude.sql`). The new migration
follows that convention. The handoff should record that
`ALTER TYPE ... ADD VALUE` cannot be reversed in Postgres without a swap, so
the migration is one-way; the new tables can be dropped manually.

`tests/conftest.py` must be updated (in a workflow with `tests/` write
scope) to add `git_commit_paths` and `git_commits` to the `DROP ... CASCADE`
list ahead of `captures`/`sources`. This is a strict prerequisite for the
test fixture — without it, repeated runs against the same database leak
rows.

## Proposed Git Importer (`src/engram/git_import.py`)

### Module-Top Constants

```python
ENGRAM_GIT_IMPORT_MAX_COMMITS = int(os.environ.get(
    "ENGRAM_GIT_IMPORT_MAX_COMMITS", "100000"
))
ENGRAM_GIT_IMPORT_INCLUDE_BODY = (
    os.environ.get("ENGRAM_GIT_IMPORT_INCLUDE_BODY", "1") == "1"
)
ENGRAM_GIT_IMPORT_FULL_PATCH = (
    os.environ.get("ENGRAM_GIT_IMPORT_FULL_PATCH", "0") == "1"
)
ENGRAM_GIT_IMPORT_ADAPTER_VERSION = "git_import.v1"
ENGRAM_GIT_IMPORT_SUBPROCESS_TIMEOUT_SECONDS = int(os.environ.get(
    "ENGRAM_GIT_IMPORT_SUBPROCESS_TIMEOUT_SECONDS", "120"
))
SOURCE_KIND = "git"
DEFAULT_TENANT_ID = "personal"
DEFAULT_CORPUS_ID = "personal"
```

`ENGRAM_GIT_IMPORT_FULL_PATCH` defaults to off per RFC 0050 OQ-SI-001
default recommendation. Layer 1 never persists patch bodies; the flag is
declared so a future Layer 2+ slice can flip it without re-introducing
the module-top constant.

### Exception Family

```python
class GitImportError(RuntimeError):
    """Root of the git import exception family."""


class GitRepositoryNotFoundError(GitImportError): ...
class GitSubprocessError(GitImportError): ...
class GitParseError(GitImportError): ...
class GitImportConflict(GitImportError):
    """Raised when an existing git_commits row's content_hash differs."""
class GitDirtyWorktreeError(GitImportError):
    """Raised when --allow-dirty is false and the worktree has uncommitted state."""
```

### Dataclass Shape

```python
@dataclass(frozen=True)
class GitCommitMetadata:
    commit_sha: str
    tree_sha: str
    parent_shas: tuple[str, ...]
    author_name: str | None
    author_email: str | None
    author_date: datetime
    committer_name: str | None
    committer_email: str | None
    committer_date: datetime
    subject: str
    body: str
    refs: tuple[str, ...]
    raw_payload: dict[str, Any]
    content_hash: str


@dataclass(frozen=True)
class GitCommitPath:
    change_index: int
    change_kind: str
    old_path: str | None
    new_path: str | None
    additions: int | None
    deletions: int | None
    is_binary: bool


@dataclass(frozen=True)
class GitImportResult:
    source_id: str
    repository_id: str
    commits_inserted: int
    commits_seen: int
    commits_skipped: int
    paths_inserted: int
    coverage_gap_count: int
```

### Subprocess Discipline

All git invocations use:

```python
subprocess.run(
    ["git", *args],
    cwd=repo,
    check=True,
    capture_output=True,
    text=True,
    env={"PATH": os.environ.get("PATH", ""), "LC_ALL": "C", "GIT_TERMINAL_PROMPT": "0"},
    timeout=ENGRAM_GIT_IMPORT_SUBPROCESS_TIMEOUT_SECONDS,
)
```

`GIT_TERMINAL_PROMPT=0` makes any prompt-bearing operation fail immediately
rather than block stdin. The `env` dict is reduced to `PATH`, `LC_ALL`, and
the prompt flag so user-side aliases or `GIT_DIR` overrides cannot redirect
the importer. No GitPython dependency is added.

### Repository Identity

Per RFC 0050 § Identity Split, the git importer must answer three
identity questions distinctly:

- `source_instance_id` (repository root identity): a stable hash that
  identifies a project root content-wise. The Layer 1 strategy is:
  `sha256("git" || NUL || first_commit_sha || NUL || normalized_remote_url)`
  where `first_commit_sha` is the root commit reached via
  `git rev-list --max-parents=0 HEAD` and `normalized_remote_url` is the
  `origin` URL (or `""` if absent) lowercased with `.git` and trailing slash
  stripped. This is the value stored in `sources.external_id`.
- Item identity keys: `(repository_id, commit_sha)` — uniquely identify a
  commit row.
- Logical identity keys: `(repository_id, ref_name)` — for refs, deferred to
  a later layer.

Caveats the reviewer should weigh:

- A repository without any commits cannot be imported. The importer raises
  `GitRepositoryNotFoundError`.
- A repository with multiple root commits (octopus-merged orphan branches)
  uses the lexicographically smallest root commit SHA. Document this in the
  module docstring as the deterministic-but-arbitrary tiebreak.
- A repository with a changed remote URL but same first commit is still the
  same `repository_id`. Layer 1 records the current remote URL in
  `sources.raw_payload` for audit but does not change identity.

### Algorithm

1. Resolve `repo_path = pathlib.Path(repo_path).resolve()`. If
   `repo_path / ".git"` is absent, raise `GitRepositoryNotFoundError`.
2. Run `git rev-parse --is-inside-work-tree`; require `true`.
3. If `--allow-dirty` is false, run `git status --porcelain=v1` and require
   empty output. Otherwise, set a `dirty_worktree=true` flag in the source
   `raw_payload` and emit a `source_audit` row (Layer 6 makes audit rows
   queryable; Layer 1 just writes the column).
4. Compute `repository_id` as described above.
5. Upsert the `sources` row (`source_kind='git'`,
   `external_id=repository_id`, `filesystem_path=str(repo_path)`,
   `raw_payload={"remote_url": ..., "root_commit_sha": ..., "head": ...,
   "adapter_version": ENGRAM_GIT_IMPORT_ADAPTER_VERSION}`).
6. Walk commits with:
   ```text
   git log --all --reverse \
       --pretty=format:%H%x00%T%x00%P%x00%an%x00%ae%x00%aI%x00%cn%x00%ce%x00%cI%x00%B%x00%x1E
   ```
   The `%x1E` (record separator) ends each commit. `%B` is the full message;
   the importer splits on the first `\n\n` for subject/body.
7. For each commit, run a second pass to fetch numstat:
   ```text
   git log -m -1 --numstat --format=%H <commit_sha>
   ```
   Use `-m` to expand merges (so merge commits emit numstat per parent;
   Layer 1 stores only the first-parent diff per RFC 0050's diff-stat-first
   recommendation). Numstat alternative: `git show --numstat --format=` per
   commit — both work; the implementation should pick one and document why.
   The reviewer's recommended choice is `git log --numstat --format=...`
   over the full revision walk, single subprocess call, parsed with the
   record-separator strategy above.
8. Compute `content_hash` as
   `sha256(canonical_json({commit_sha, tree_sha, parent_shas, author_*,
   committer_*, author_date_isoformat, committer_date_isoformat, subject,
   body, refs_sorted, numstat_summary}))`. The hash is the conflict
   discriminator: re-import of a commit whose `content_hash` matches an
   existing row is idempotent; mismatch raises `GitImportConflict`.
9. Run `git for-each-ref --format='%(refname:short)\t%(objectname)'` to
   gather branch and tag heads; attach the ref names to the corresponding
   commit's `refs` array.
10. Stream rows into the database inside a single `conn.transaction()`:
    `INSERT ... ON CONFLICT (tenant_id, corpus_id, repository_id,
    commit_sha) DO NOTHING RETURNING id`. When `ON CONFLICT` fires, run a
    second `SELECT content_hash FROM git_commits WHERE id = ...` to compare;
    raise `GitImportConflict` on mismatch.
11. Insert path rows next: `INSERT INTO git_commit_paths ... ON CONFLICT
    (commit_id, change_index) DO NOTHING`. Path rows are idempotent because
    `change_index` is stable per `git log --numstat` ordering.
12. For any commit whose numstat fails to parse (e.g., binary file with
    `-\t-\t<path>` plus a malformed name), emit a `coverage_gap` row via
    `captures` under `source_kind='git'` with `external_id=
    "coverage_gap:" + commit_sha + ":" + str(change_index)`. The `captures`
    table is the Layer 1 landing zone for operational families; Layer 6
    upgrades it.
13. Return a `GitImportResult` summary.

### No-Egress Guarantee

The importer imports no network modules. The subprocess uses `git`, which
in this layer never receives a remote URL (no `clone`, `fetch`, `pull`,
`push`, or `ls-remote`). The `EG-SI-000` test (Level A) monkeypatches
`socket.socket` to assert no socket is created during ingest.

A second envelope test under
`tests/test_git_importer_no_egress.py` should also assert that the
subprocess args never include a network-touching verb by enforcing an
allowlist:

```python
GIT_VERB_ALLOWLIST = frozenset({
    "rev-parse", "rev-list", "log", "show", "status",
    "for-each-ref", "cat-file", "ls-tree",
})
```

Achieved by wrapping `subprocess.run` in the test with a recorder that
asserts every `argv[1]` is in `GIT_VERB_ALLOWLIST`.

### Idempotency Strategy

The unique index `(tenant_id, corpus_id, repository_id, commit_sha)` is the
hard idempotency boundary. The importer:

- never UPDATEs `git_commits` or `git_commit_paths`;
- treats a content-hash match as a no-op (`commits_skipped += 1`);
- treats a content-hash mismatch as `GitImportConflict` (raised; the caller
  decides whether to tombstone the prior row via a follow-on action — this
  layer does not auto-tombstone).

## Proposed CLI Wiring

The CLI entrypoint at `src/engram/cli.py` registers a new subcommand using
`argparse`. The naming follows existing verbs (`engram ingest chatgpt`,
`engram ingest claude`, `engram ingest gemini`, `engram ingest striatum`)
adapted to the layer prompt's `import` verb. The reviewer should confirm
which verb is intended. The prompt says
`engram import git <repo-path>`; the existing CLI uses `ingest`. The
recommended resolution is to register `import` as an alias of `ingest` for
the new git verb and document the alias in `docs/ingestion.md` when the
documentation edit is in-scope.

Argument shape:

```text
engram import git <repo-path>
    [--dry-run]               # validate identity, do not insert rows
    [--allow-dirty]           # permit a dirty worktree
    [--full-patch=false]      # explicit flag; Layer 1 ignores anything but false
    [--tenant-id personal]
    [--corpus-id personal]
    [--repo-label <text>]     # optional human label stored on sources.raw_payload
```

`--full-patch=true` is rejected with a parser error in Layer 1 with a
message pointing at RFC 0050 OQ-SI-001 as the relevant open question.

## Proposed Test Plan

### `tests/test_source_contract_validator.py`

- `test_template_present` — the template file at
  `docs/source-contracts/README.md` exists.
- `test_git_contract_valid` — `validate_contract(git.yaml).is_valid` is true.
- `test_build_artifact_contract_valid` —
  `validate_contract(build_artifact.yaml).is_valid` is true.
- `test_missing_field_codes` — a synthetic YAML with each mandatory field
  removed in turn yields exactly one error, with the expected code.
- `test_unknown_projection_family` — a synthetic YAML with
  `projection_families: [generated_product]` yields
  `UNKNOWN_PROJECTION_FAMILY`.
- `test_unknown_sensitivity_class` — a synthetic YAML with
  `sensitivity_class_default: super_secret` yields
  `UNKNOWN_SENSITIVITY_CLASS`.
- `test_invalid_privacy_tier_zero` and `test_invalid_privacy_tier_six` —
  out-of-range tiers yield `INVALID_PRIVACY_TIER`.
- `test_participant_third_party_must_be_bool` —
  `participant_third_party: "false"` yields
  `INVALID_PARTICIPANT_THIRD_PARTY`.
- `test_no_yaml_loader_anchors_silently` — the YAML is loaded with
  `yaml.safe_load` (assert via mock or `tomllib`-style guard).

Fixtures are inline YAML strings via `tmp_path`.

### `tests/test_git_importer.py`

The fixture repo is created by a helper at
`tests/fixtures/source_contract_git/__init__.py` (or a `conftest.py`-local
factory):

```python
def make_fixture_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "fixture_git"
    repo.mkdir()
    _run_git(repo, "init", "--initial-branch=main")
    _run_git(repo, "config", "user.email", "test@example.invalid")
    _run_git(repo, "config", "user.name", "Test")
    _run_git(repo, "config", "commit.gpgsign", "false")
    (repo / "README.md").write_text("first\n")
    _run_git(repo, "add", "README.md")
    _run_git(repo, "commit", "-m", "initial commit")
    (repo / "renamed.md").write_text("second\n")
    _run_git(repo, "mv", "README.md", "renamed.md")
    _run_git(repo, "commit", "-am", "rename README to renamed")
    _run_git(repo, "checkout", "-b", "feature/branch")
    _run_git(repo, "tag", "-a", "v0.1.0", "-m", "v0.1.0")
    _run_git(repo, "checkout", "main")
    return repo
```

`_run_git` constructs the same env restriction as the importer so test
behavior matches production. The fixture creates the requested two
commits, one branch, one tag, and one file rename. No checked-in `.git`
directory.

Tests:

- `test_first_import_inserts_two_commits` — fresh import yields
  `commits_inserted=2`, `paths_inserted` matches the change set, and
  exactly one `sources` row with `source_kind='git'`.
- `test_reimport_is_idempotent` — running the importer a second time
  yields `commits_inserted=0` and `commits_skipped=2`.
- `test_rename_detected_as_rename_change_kind` — `git_commit_paths` for
  the rename commit records `change_kind='rename'`, `old_path='README.md'`,
  `new_path='renamed.md'`.
- `test_conflict_on_changed_content_hash` — manually rewriting the
  `git_commits.content_hash` for one commit and re-importing raises
  `GitImportConflict`.
- `test_branch_and_tag_refs_recorded` — `git_commits.refs` for the head
  commit of `feature/branch` contains both `feature/branch` and `v0.1.0`.
- `test_dirty_worktree_raises_without_allow_dirty` — creating an
  uncommitted file before import causes `GitDirtyWorktreeError`.
- `test_dirty_worktree_with_allow_dirty_emits_source_audit` —
  `--allow-dirty` records `dirty_worktree=true` in `sources.raw_payload`
  and writes a `coverage_gap` capture row (Layer 6 prerequisite).
- `test_describe_corpus_reports_git_kind` — after import,
  `engram describe-corpus --json` includes `git` in the source-kind list.
- `test_no_subprocess_outside_allowlist` — record `subprocess.run` calls
  and assert every git verb used is in the allowlist.

### `tests/test_git_importer_no_egress.py`

- `test_no_socket_during_import` — monkeypatches `socket.socket.__init__`
  to raise; runs the importer; asserts no socket creation.
- `test_no_socket_during_dry_run` — same with `--dry-run`.
- `test_subprocess_args_never_include_network_verbs` — wraps
  `subprocess.run` and asserts `argv[1] not in
  {"clone","fetch","pull","push","ls-remote","remote","submodule","archive"}`.
- `test_environment_strip_blocks_git_terminal_prompt` — confirms the env
  passed to subprocess contains `GIT_TERMINAL_PROMPT=0`.

## Acceptance Checklist (Backlog Layer 1)

| Backlog item | Plan |
|--------------|------|
| Source contract template at `docs/source-contracts/README.md` | Drafted above; structure mirrors RFC 0050 § Source Contract. |
| `docs/source-contracts/git.yaml` | Field values listed above. |
| `docs/source-contracts/build_artifact.yaml` | Field values listed above (forward-pointer for Layer 2). |
| `src/engram/source_contract.py` | Module sketch above; closed error vocabulary listed. |
| Migration adding `source_kind='git'` + `git_commits` + `git_commit_paths` | Numbered `017_source_kind_git.sql`; schema sketched above. |
| `src/engram/git_import.py` | Module sketch above; subprocess discipline, no-egress, idempotency, coverage-gap emission all specified. |
| `engram import git <repo-path>` CLI verb | Argument shape above; alias decision noted. |
| `tests/test_source_contract_validator.py` | Test list above. |
| `tests/test_git_importer.py` | Test list above. |
| `tests/test_git_importer_no_egress.py` | Test list above. |
| Fixture repo factory | Implementation above. |

## What Was Not Run

- `make test` was not run by this lane. The artifact path scope does not
  include `src/`, `tests/`, or `migrations/`, so the implementation cannot
  exist on the branch for tests to execute. The successor workflow must run
  `make test` and surface the result; this lane reports the omission rather
  than hiding it, per the role's "Run `make test` before completing" rule
  and the project memory note on never fabricating provenance.
- `make migrate` was not run for the same reason.
- `engram describe-corpus --json` was not executed; the expected output
  shape is documented above but not verified.

## Open Questions Surfaced By This Plan

These are scoped to Layer 1 and do not displace the RFC 0050 OQ-SI ledger.

1. `import` vs `ingest` CLI verb. The backlog and workflow prompt both
   specify `engram import git <repo-path>`. The existing CLI uses
   `ingest`. The recommended resolution is to register `import` as an
   alias for the new verb and to add a deprecation-free alias mapping
   rather than rename existing verbs.
2. Octopus-orphan root tiebreak. The proposed deterministic-but-arbitrary
   lexicographic tiebreak should be documented in the module docstring
   and audited if multi-root repos appear in fixtures.
3. Strict append-only versus future tombstone column. Layer 1 chooses
   strict append-only on `git_commits` and `git_commit_paths`. The
   reviewer should flag if a `superseded_at` column is needed at Layer 1
   for force-push handling; the recommendation here is to defer that
   column until Layer 5 retrieval needs it.
4. Two-pass `git log` vs single-pass. The plan assumes a two-pass walk
   (metadata, then numstat). A single-pass walk with
   `git log --all --reverse --numstat --format=...` is feasible; the
   reviewer should choose between simplicity and one-shot semantics.
5. `git_commits.refs` semantics. The plan stores branch/tag names at
   import time as informational annotations. Authoritative ref state
   belongs in a future `git_refs` table introduced when ref lifecycle
   (force push, delete) becomes part of the retrieval surface.
6. Migration 017 sequencing risk. The current branch sits on top of
   migration 016. If a parallel layer also reserves 017, the importer
   migration must be re-numbered. This is a workflow coordination
   concern, not a design concern.

## Cross-References

- `docs/rfcs/0050-source-ingestion-expansion.md` — § Source Contract,
  § Projection Vocabulary, § Privacy And Sensitivity, § Evaluation Gates,
  § Initial Implementation Slice, § Schema Direction, OQ-SI-001 through
  OQ-SI-012.
- `SOURCE_INGESTION_BACKLOG.md` § Layer 1 — Source Contract Template + Git
  Importer.
- `docs/design/source-ingestion-expansion-proposal-2026-05-15.md` —
  § Initial Deliverable Recommendation (items 1, 2) and § Evaluation Gates.
- `docs/rfcs/0012-python-agentic-coding-standard.md` — type hints,
  per-stage exception family, `ENGRAM_`-prefixed env vars, deterministic
  tests, no live LLM/network in unit tests.
- `migrations/003_source_kind_claude.sql` — `ALTER TYPE source_kind ADD
  VALUE` pattern.
- `migrations/014_striatum_tenant_corpus.sql`,
  `migrations/015_striatum_projection.sql` — tenant/corpus column shape,
  index discipline, immutability triggers.
- `src/engram/striatum_ingest.py` — idempotent bundle ingest precedent.
- `src/engram/claude_export.py` — per-source exception family + ingest
  result dataclass precedent.
- `src/engram/segmenter.py` — per-stage exception family rooted in a
  domain class (`SegmentationError`); `ENGRAM_`-prefixed module-top
  tunables.
- `tests/conftest.py` — `conn` fixture, schema reset block; new tables
  must be added to the `DROP ... CASCADE` list when they land.

## Handoff Summary

| Field | Value |
|-------|-------|
| Layer 1 scope captured | Yes — template, two example contracts, validator, migration 017, git importer, CLI verb, three test modules, fixture factory. |
| Production code landed | No — out of the lane's write scope. |
| `make test` run | No — implementation not on the branch. |
| Decision log / RFC index touched | No — this lane is strictly proposal-only. |
| Open questions raised | Six (CLI verb naming, root tiebreak, append-only stance, walk strategy, ref-state authority, migration numbering coordination). |
| Recommended next action | Hand the file off to a workflow with `src/`, `tests/`, and `migrations/` write scope; that workflow runs `make migrate` and `make test`, surfaces failures here, and only then advances Layer 1 toward the backlog's "ships when its tests are green on master" rule. |
