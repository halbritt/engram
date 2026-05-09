# RFC 0030 Public-Dataset Entity Grounding Revision Synthesis

author: synthesizer-claude-opus-001

Status: synthesis
Date: 2026-05-09
RFC refs: RFC-0030
Decision refs: D020, D044, D068, D076, D080
Phase refs: PHASE-0003, PHASE-0004

## Decision

**Accept the RFC's overall thesis and architecture; require substantive
revisions before promotion to spec.** All 30 findings in the ledger
are accepted. The five non-negotiable constraints stand and are
locked. The largest revisions are to D-H (eval oracle methodology) and
to enforcement details that turn the privacy posture from policy into
invariants.

## Accepted findings

All 30. Disposition by severity:

- **Blocking (4):** L001, L002, L003, L004. Each requires a concrete
  RFC text change that turns a stated policy into a code-side
  invariant or pre-registered methodology.
- **Major (12):** L005-L016. Each requires either a new RFC subsection
  or a tightening of an existing § D-A..D-H or Q1..Q7 position.
- **Minor (14):** L017-L030. Each is a single-sentence-to-single-
  paragraph clarification of an existing position.

## Rejected findings

None. The findings are uniformly tightening, expanding, or locking;
none would require softening a non-negotiable or reverting a core
architectural choice.

## Deferred findings

None to spec-time-only. The author's revision pass should land all
30; the spec is then a contract over the revised RFC.

## Position on each design choice

### D-A — Starting dataset set
**Position: Wikidata + GeoNames for v1, with explicit budget enforcement.**
- v1 datasets: Wikidata (filtered to relevant entity classes — places,
  organizations, products, public figures) + GeoNames.
- OpenStreetMap is deferred to v1.x.
- Storage budget: 10GB target, 12GB hard-fail, configurable; warn at
  80%. Enforce at `engram grounding snapshot` time. (L011)
- Ship operator-friendly aliases (`places`, `companies`,
  `public-figures`) that map to dataset-and-filter combinations. (gemini:F006)

### D-B — Resolver placement
**Position: Hybrid (option 3), with three guards.**
- Module split (L009): `surface_form_extractor`, `candidate_resolver`,
  `attachment_writer` — three units, three contracts.
- Surface-form normalization rule pinned (NFKC + lowercase + collapse
  whitespace) with documented recall/precision trade-off. (codex:F006)
- Prompt-shape guard: candidate block appears under a
  `CANDIDATES-ONLY-HINTS` section that the prompt explicitly tells
  the model not to treat as ground truth. Sample prompt sentence
  shipped in the RFC. (L005, claude:F004)
- Dataset description fields are sanitized before insertion (control
  characters stripped, length capped, prompt-shape patterns rejected).
  (L005, privacy_adversary:P004)

### D-C — Output shape
**Position: Full candidate set with confidences (as recommended), with
a redaction rule and a default UI surface.**
- Output: full candidate set with per-candidate confidences attached
  to claim via `entity_external_references` rows.
- Tracked-export redaction: candidate QIDs / dataset-ids and
  confidence scores OK; descriptive prose attached to candidates
  stays in scratch. (L020, privacy_adversary:P008)
- Interview UI default: top-1 candidate above threshold X (default
  0.85, configurable) with "see N more" affordance below. Full set
  not rendered by default. (L005, usability_adversary:U004)

### D-D — Schema home
**Position: `entity_external_references` table (option 2), append-only
with tombstone supersession; cascade integrated with RFC 0018.**
- New table `entity_external_references` with columns: `eer_id`,
  `entity_id`, `dataset`, `external_id`, `snapshot_id`,
  `confidence`, `superseded_by` (NULLable, FK to same table),
  `created_at`. (L007, schema_adversary:S001)
- Append-only: no UPDATEs, no DELETEs. Supersession via inserting a
  tombstone row whose `superseded_by` references the new row;
  current-state view filters `WHERE superseded_by IS NULL AND grant
  active`. (L007)
- RFC 0018 cascade integration: raw evidence → `entities` →
  `entity_external_references` → `claims`. Cascade walks join order
  spelled out in spec. (L007, schema_adversary:S004)
- Live-consumer queries filter by grant-active rows; audit queries
  see all rows. Tests pin both behaviors. (L007, schema_adversary:S008)

### D-E — Snapshot discipline
**Position: Per-dataset content-hashed snapshots with mode-bit
discipline and operator-curated lifecycle.**
- Snapshot id: `<dataset>@<date>@sha256:<hash>`. Hash computed at
  registration time. Loader verifies on every access; refuses on
  mismatch. (L002, privacy_adversary:P002, claude:F003)
- Storage layout: `~/.engram/grounding/<dataset>/<snapshot_id>/`
  with mode 0700 dirs / 0600 manifests. Engram refuses snapshot
  dirs with looser permissions. (L019, privacy_adversary:P006)
- Indexing happens at snapshot-fetch time, not lazily at extraction.
  (L027, cost_adversary:C007)
- Rollback semantics: rolling back snapshot X invalidates all
  `entity_external_references` recorded under X via tombstone
  insertion. Claim rows unaffected. Re-extraction is the path to
  fresh resolutions. (L007, schema_adversary:S002)

### D-F — Grant model
**Position: Per agent role, persistent, scratch-SQLite-stored audit
log with non-sync stance and template management.**
- Storage: `~/.engram/grants/grants.sqlite3`. Schema: `(role,
  dataset, granted_at, granted_by, revoked_at)`. Grant exercises
  log to a separate `grants_audit` table. (L006,
  privacy_adversary:P005, claude:F002)
- Non-sync stance: a `~/.engram/grants/.engram-no-sync` marker
  documents that the dir must not replicate via dotfile sync. (L006)
- Retention: grant exercises kept 90 days, then truncated. (L006)
- Revocation behavior: forward-only. Existing grounded claims keep
  their `entity_external_references` rows (history); live queries
  filter by grant-active. (L030, gemini:F002)
- Default for non-role-typed CLI invocations: inherit operator's
  grants (default-operator-inherits). State explicitly. (claude:F006)
- Grant template surface (L014, cost_adversary:C005): ship default
  templates (`places-only`, `places-and-companies`,
  `everything-public`); operator picks per role.

### D-G — Extraction prompt impact
**Position: Per-segment cap with batch-level fail-fast; explicit
prompt-version bump rule.**
- Per-segment cap: 1000 tokens of candidate block per segment.
- Batch-level cap: total candidate-block tokens across all segments
  in a batched extraction prompt must not exceed
  `CANDIDATE_BATCH_CAP` (default 8000). Fail-fast on overflow with
  loud error. (L008, codex:F002)
- `EXTRACTION_PROMPT_VERSION` bump rule: any change to the
  candidate-block format or framing sentence triggers a version
  bump per RFC 0017. (L008)
- Resolver-output provenance does NOT live on the claim row's
  prompt_version tuple. It lives on a new
  `grounding_resolution_set` table pinning (claim_id, run_id,
  snapshot_pin_set). (L008, schema_adversary:S003)

### D-H — Eval oracle (largest revision)
**Position: Three-arm bench, paired metric, pre-registered decision
rule, held-out gold set as independent secondary.**
- **Three arms:**
  1. v8 (baseline; existing prompt; no grounding).
  2. v9 (new prompt with candidate-block format) with grounding
     **disabled** — the negative control.
  3. v9 with grounding **enabled**.
  Only the (2) vs (3) comparison isolates the grounding effect.
  (L004, eval_adversary:E001)
- **Paired metric** (false-rate AND coverage):
  - Primary: operator-false-rate on entity-mismatch claims (lower
    is better).
  - Required paired: coverage = fraction of entity-shaped surface
    forms that received any resolution at all. (L004,
    eval_adversary:E002)
- **Pre-registered decision rule:** "Promote" requires a relative
  reduction in false-rate of ≥30% with coverage drop ≤5%, comparing
  arm (3) to arm (2). (L004, eval_adversary:E006)
- **Sample size:** 100 segments for sanity (Step 3 fast-fail); 600+
  segments for promotion-grade decision. The 100-segment slice is
  not the gate; it is a precondition for running the 600. (L004,
  eval_adversary:E003)
- **Slice specification:** primary = RFC 0028 failure-class slice (for
  sanity); promotion = stratified random 600-segment selection
  across the corpus. Both reported. (L004, eval_adversary:E004)
- **Independent secondary signal:** a held-out 100-segment gold set
  of pre-resolved entity-grounding pairs (operator-curated under
  RFC 0021's discipline, but built specifically for grounding).
  Reports recall/precision. **PHASE-0004 merge-rate is dropped as
  secondary** (contaminated). (L004, eval_adversary:E005)
- **Baseline reproducibility:** v8 baseline artifacts must be
  content-hash-pinned and verified at bench preflight. (L004,
  eval_adversary:E008)

## Position on each open question

### Q1 — Smallest deliverable that proves the thesis
**Position: 100-segment Wikidata-places-only sanity slice for
fast-fail; 600-segment stratified slice for promotion gate.**
The single-stage 100-segment claim from the RFC is wrong by ~6x in
power. (L004)

### Q2 — Interaction with RFC 0028 subject_kind_hint
**Position: Deepening with type-narrowing.** RFC 0028's `subject_kind_hint`
narrows the resolver's candidate-type filter (e.g., `subject_kind=person`
restricts to person-class candidates). The interview verdict overrides
both. (L025, claude:F007, gemini:F007)

### Q3 — Interaction with PHASE-0004 consolidation
**Position: External refs are a strong de-dup signal; consolidation
consumes them before falling back to text similarity.** Spec specifies
precedence and tie-breakers (matching external refs across two
candidate-merge entities is presumptive merge; conflicting refs
require the operator). PHASE-0004 merge-rate is no longer a grounding
oracle; it is a downstream consumer. (L004 secondary)

### Q4 — Resolver vs operator disagreement
**Position: Per-corpus private alias suppression table.**
- Operator interview verdict on a wrong grounding case populates a
  `private_aliases` table: `(surface_form, segment_or_corpus_scope,
  reason, suppressed_dataset, suppressed_external_id)`.
- Resolver consults `private_aliases` first. If a match exists, no
  candidate is attached.
- Scope: per-segment (precise) or per-corpus (broad); operator
  picks. (L016, usability_adversary:U005)

### Q5 — Storage budget
**Position: 10GB target, 12GB hard-fail, configurable.** Budget
enforced at snapshot-add time; warn at 80%. (L011, cost_adversary:C001)

### Q6 — Resolution latency
**Position: ≤100ms per segment with fail-fast on overflow; ≤2x
extraction time per corpus.**
- Per-segment budget (default 100ms): a segment whose resolution
  exceeds budget skips resolution (one warning per run, machine-
  readable in summary).
- Per-corpus budget: extraction time with grounding ≤ 2x baseline
  extraction time. Bench preflight verifies; refuses bench if
  exceeded.
- Cache discipline: per-process LRU keyed by (surface_form, snapshot)
  with a hard cap (default 100k entries). (L012, cost_adversary:C002)

### Q7 — Failure mode when grants are missing
**Position: Silent downgrade in extraction path; loud surfacing in
run summary; lock-file detection of prior-grants-now-absent.**
- Default: extraction proceeds without grounding. (Conservative
  ergonomics.)
- Run summary JSON includes machine-readable
  `grounding_status: {"active": false, "reason": "no grants",
  "active_grants": []}` — visible to downstream tooling. (L013,
  gemini:F005)
- Lock file at `~/.engram/grounding/active-grants.lock` records
  prior grants. If extraction starts and current grants ≠ lock
  state and the difference is "lost grants", **prompt** in
  interactive mode or **fail with a `--ungrounded-ok` override
  flag** in non-interactive mode. (L013, usability_adversary:U003)

## Required RFC edits

The author must apply the following edits in `apply_findings`. Each
references the section name and the synthesis position to install.

1. **§ Non-negotiable constraints — add subsection "Code-side
   enforcement"** with:
   - Names the modules (`src/engram/grounding/`, `src/engram/extractor.py`)
     where HTTP clients are forbidden.
   - Names a unit test (`tests/test_grounding.py::test_no_http_clients`)
     that walks the AST and asserts.
   - Excludes the dataset-acquisition module
     (`src/engram/grounding/snapshot.py`) explicitly with rationale.
   (L001)

2. **§ Non-negotiable constraints — promote to a locked DECISION_LOG
   entry.** Add a paragraph in the RFC stating that the five
   non-negotiables will be promoted to a new `D###` entry on RFC
   acceptance, and that any future change requires named supersession.
   (L003)

3. **§ D-A — replace recommended seed paragraph** with the L011 +
   gemini:F006 prescription: Wikidata + GeoNames v1 with
   places/organizations/products/public-figures filter; aliases shipped
   for `places`, `companies`, `public-figures`; storage budget
   enforced.

4. **§ D-B — replace option 3 paragraph** with the L009 + L005
   prescription: three-module split, surface-form normalization rule,
   prompt-shape guard sentence, dataset-content sanitization.

5. **§ D-C — replace recommended seed paragraph** with the L020 + L005
   prescription: candidate set + redaction rule + interview UI
   top-1-default.

6. **§ D-D — replace recommended seed paragraph** with the L007 +
   schema_adversary prescription: option 2 with append-only/
   tombstone/cascade discipline.

7. **§ D-E — replace recommended seed paragraph** with the L002 +
   L019 + L027 prescription: content-hashed snapshot id, mode-bit
   discipline, fetch-time indexing, rollback semantics.

8. **§ D-F — replace recommended seed paragraph** with the L006 +
   L014 + L030 prescription: scratch SQLite location, non-sync,
   templates, forward-only revocation, default-operator-inherits.

9. **§ D-G — replace open-question paragraph** with the L008 + L022
   prescription: per-segment + per-batch cap, prompt-version bump
   rule, grounding_resolution_set table.

10. **§ D-H — full rewrite** per L004: three-arm bench, paired metric,
    pre-registered decision rule, sample size, slice spec,
    independent secondary signal, baseline pinning. This is the
    largest single edit.

11. **§ Open questions Q1-Q7 — replace each with the synthesis
    position above.** Each is a one-paragraph replacement.

12. **§ Promotion path — split step 4 into 4a/4b/4c/4d** per L029, and
    add an honest cost statement on the bench-and-iterate loop. (L010,
    cost_adversary:C004)

13. **§ Why this fits the principles — add bullets:**
    - "Refusal-of-false-precision: the candidate-block prompt-shape
      guard prevents premature collapse to a single ID at extraction
      time."
    - "Adversarial-review-friendly: the five non-negotiables are
      grep-checkable, not just stated."

14. **Front-matter table — update Decision refs** to include each Dxxx
    that gets explicitly walked: D020 (LLM-local), D044 (gold-set
    advisory), D068 (artifact-id), D076 (32k context budget), D080
    (RFC 0027 promotion). (L028, claude:F008)

15. **`docs/rfcs/README.md` — update RFC 0030 row** Implementation
    column stays `none`; Topic stays as currently; Status flips to
    `accepted` (synthesis-time) with the same row gaining a parenthetical
    `(see [spec 0030](../specs/0030-...md) once authored)` placeholder
    that the spec-authoring run will replace.

## Required follow-up artifacts

1. **`apply_findings` produces `REVISION_HANDOFF.md`** showing
   per-section: prior text quoted, new text quoted, source finding.

2. **`final_review` produces `FINAL_REVIEW.md`** with the acceptance
   check from the prompt template; verdict gates spec promotion.

3. **(Out of run scope) Spec authoring run** is the natural next
   step IF final_review accepts.

4. **(Out of run scope) DECISION_LOG entry** for the locked
   non-negotiables (L003) is the operator's job; synthesis cannot
   write to DECISION_LOG.

## Decision: ready for spec promotion?

**Conditional.** Ready for spec promotion *if and only if* `apply_findings`
lands the 15 RFC edits above and `final_review` confirms each lands
faithfully. The author should not introduce new design choices not
listed in this synthesis.
