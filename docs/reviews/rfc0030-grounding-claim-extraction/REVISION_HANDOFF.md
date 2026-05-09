# RFC 0030 Public-Dataset Entity Grounding Revision Handoff

author: author-codex-gpt-5.5-001

Status: revised
Date: 2026-05-09
RFC refs: RFC-0030
Decision refs: D020, D044, D068, D076, D080
Phase refs: PHASE-0003, PHASE-0004

## Summary

15 RFC edits applied per `REVISION_SYNTHESIS.md`. The revised RFC
accepts all 30 findings, locks the five non-negotiables in spirit
(actual DECISION_LOG entry is the operator's job), restructures the
eval oracle (D-H) per `eval_adversary` blocking findings, adds
code-side enforcement chokepoints for the privacy posture, and
honors the realistic implementation footprint with a four-commit
promotion path.

## Changes made

### 1. Front-matter (Status / Decision refs / Review refs)
- **Section:** front-matter table.
- **Source:** L028, claude:F008.
- **Prior:**
  ```
  | Status | proposal |
  ...
  Decision refs:
    - none yet (proposal)
  Review refs:
    - none (proposed for striatum-orchestrated multi-agent review per
      `docs/process/multi-agent-review-loop.md`)
  ```
- **New:**
  ```
  | Status | accepted (revised after design review 2026-05-09) |
  ...
  Decision refs:
    - D020 (LLM endpoint is local-only)
    - D044 (gold-set is advisory)
    - D068 (artifact-id model)
    - D076 (32k context budget)
    - D080 (RFC 0027 promotion pattern)
  Review refs:
    - [Design review final review](../reviews/rfc0030-grounding-claim-extraction/FINAL_REVIEW.md)
    - [Findings ledger](../reviews/rfc0030-grounding-claim-extraction/FINDINGS_LEDGER.md)
    - [Revision synthesis](../reviews/rfc0030-grounding-claim-extraction/REVISION_SYNTHESIS.md)
  ```
- Context entry expanded to include RFC 0018 (audit cascade).

### 2. § Non-negotiable constraints — added "Code-side enforcement"
- **Section:** new subsection after the five-bullet list.
- **Source:** L001, claude:F001, privacy_adversary:P003.
- **Prior:** none.
- **New:** subsection naming forbidden HTTP-client imports in
  `src/engram/grounding/resolver.py`,
  `src/engram/grounding/attachment.py`, `src/engram/extractor.py`;
  AST-walking unit test
  `tests/test_grounding.py::test_no_http_clients`;
  `src/engram/grounding/snapshot.py` as the sanctioned-network
  exception with bounded responsibilities; single-accessor chokepoint
  for grants at `GrantStore.read_active`.

### 3. § Non-negotiable constraints — added "Locked in DECISION_LOG"
- **Section:** new subsection after Code-side enforcement.
- **Source:** L003, privacy_adversary:P007.
- **Prior:** none.
- **New:** paragraph stating the five non-negotiables will be
  promoted to a new `D###` entry on RFC acceptance and that
  supersession requires named replacement.

### 4. § D-A — replaced "Open: should v1 also include..." paragraph
- **Section:** § D-A Starting dataset set.
- **Source:** L011, gemini:F006, cost_adversary:C001.
- **Prior:** "Open: should v1 also include OpenStreetMap (Nominatim)…"
  paragraph.
- **New:** explicit Wikidata + GeoNames v1 with filters; storage
  budget enforced (10GB target / 12GB hard-fail / configurable);
  operator-friendly aliases (`places`, `companies`, `public-figures`).

### 5. § D-B option 3 — replaced recommended seed paragraph
- **Section:** § D-B Resolver placement, recommended seed under option 3.
- **Source:** L005, L009, claude:F004, privacy_adversary:P004,
  usability_adversary:U004, codex:F001 / F003 / F006.
- **Prior:** single paragraph: "Recommended seed: (3) hybrid, on the
  bet that nudging the LLM..."
- **New:** module split (three units with input/output shapes),
  surface-form normalization rule (NFKC + lowercase + collapsed
  whitespace), prompt-shape guard (verbatim CANDIDATES-ONLY-HINTS
  framing), dataset content sanitization (strip control chars, cap
  length, reject prompt-shape patterns).

### 6. § D-C — replaced recommended seed paragraph
- **Section:** § D-C Output shape.
- **Source:** L020, L005, privacy_adversary:P008, usability_adversary:U004.
- **Prior:** "Recommended seed: attach the full candidate set with
  confidences. The interview UI is the right place to disambiguate."
- **New:** full candidate set + tracked-export redaction rule (QIDs and
  confidence scores OK; descriptive prose stays in scratch) +
  interview UI default (top-1 above 0.85 threshold, "see N more"
  affordance, full set not rendered by default).

### 7. § D-D — replaced recommended seed paragraph
- **Section:** § D-D Schema home.
- **Source:** L007, schema_adversary:S001 / S004 / S006 / S008.
- **Prior:** single paragraph endorsing option 2.
- **New:** option 2 with: explicit DDL sketch (columns, unique
  constraint, index, BEFORE UPDATE OR DELETE trigger); tombstone
  supersession via `superseded_by` column; cascade integration with
  RFC 0018 (specific join order); live vs audit query semantics;
  backfill semantics (absence of join row means "not grounded").

### 8. § D-E — replaced recommended seed paragraph
- **Section:** § D-E Snapshot discipline.
- **Source:** L002, L019, L027, claude:F003, privacy_adversary:P002 /
  P006, schema_adversary:S002, cost_adversary:C007.
- **Prior:** "Recommended seed: per-dataset versioned snapshots..."
- **New:** snapshot id with content hash
  (`<dataset>@<date>@sha256:<hash>`); mode-bit discipline (0700/0600);
  fetch-time indexing (no lazy indexing at extraction); rollback
  semantics (tombstone insertion); provenance shape (sidecar
  `grounding_resolution_set` table preserving RFC 0017 immutability).

### 9. § D-F — replaced recommended seed paragraph
- **Section:** § D-F Grant model.
- **Source:** L006, L013, L014, L030, claude:F002 / F006,
  privacy_adversary:P005, schema_adversary:S005, gemini:F002 / F005,
  usability_adversary:U001 / U003, cost_adversary:C005.
- **Prior:** "Recommended seed: per agent role, persistent until
  revoked, with an audit log of access..."
- **New:** scratch SQLite at `~/.engram/grants/grants.sqlite3`;
  schema for `grants` and `grants_audit`; non-sync stance via
  `.engram-no-sync` marker; 90-day retention on audit rows;
  CLI surface (with `--usage` flag and `apply-template`); default
  templates; forward-only revocation; default-operator-inherits for
  non-role-typed CLI; run-summary `grounding_status` JSON field.

### 10. § D-G — replaced open-question paragraph and bump line
- **Section:** § D-G Extraction prompt impact.
- **Source:** L008, codex:F002, schema_adversary:S003.
- **Prior:** "Open: budget cap on candidate-block size per segment?…
  This change bumps EXTRACTION_PROMPT_VERSION per RFC 0017."
- **New:** per-segment cap (1000 tokens, fail at 1500); batch-level
  cap (`CANDIDATE_BATCH_CAP` default 8000) with fail-fast in
  batched extraction; explicit prompt-version bump triggers (any
  change to candidate-block format, prompt-shape guard, or per-
  segment cap).

### 11. § D-H — full rewrite
- **Section:** § D-H Eval oracle.
- **Source:** L004 (the largest finding cluster in the run).
  eval_adversary:E001-E008; gemini:F008.
- **Prior:** "Recommended seed: operator false-rate in the
  entity-mismatch class, with PHASE-0004 merge-rate as secondary..."
- **New:** the section is fully rewritten. Three-arm bench (Arm A
  v8 / Arm B v9-disabled / Arm C v9-grounded); paired metric
  (false-rate AND coverage); pre-registered decision rule (≥30%
  relative false-rate reduction with ≤5% coverage drop); sample
  sizes (100 sanity / 600 promotion gate, with Poisson power
  derivation); slice spec (RFC 0028 failure-class slice for
  sanity, stratified random 600 for promotion); independent
  secondary signal (held-out 100-segment grounding gold set,
  replacing PHASE-0004 merge-rate); baseline reproducibility
  (content-hash-pinned v8 artifacts, bench preflight check);
  operator-honest cost statement (6-12 operator-hours + 2-6
  wall-clock hours per cycle).

### 12. § Open questions for the design loop — replaced all 7 with positions
- **Section:** § Open questions, retitled to "§ Open questions, resolved".
- **Source:** L004 (Q1), L025 (Q2), L004 secondary (Q3), L016 (Q4),
  L011 (Q5), L012 (Q6), L013 (Q7).
- **Prior:** open questions stated as "recommended seed" without
  authoritative resolution.
- **New:** each Q1-Q7 replaced with the synthesis position. Q1 names
  100/600 sample sizes; Q2 names "deepening with type-narrowing";
  Q3 names consolidation precedence; Q4 names per-corpus private
  alias suppression with schema sketch; Q5 names budget enforcement;
  Q6 names latency budgets; Q7 names silent-downgrade with run-summary
  + lock file detection.

### 13. § Why this fits the principles — added bullets
- **Section:** § Why this fits the principles, refusal-of-false-precision
  and adversarial-review bullets.
- **Source:** L005 (refusal-of-false-precision); L001 / L003
  (adversarial-review grep-checkability).
- **Prior:** two short bullets.
- **New:** expanded to name the prompt-shape guard explicitly under
  refusal-of-false-precision; expanded adversarial-review bullet to
  record that the 8-lane review happened on 2026-05-09 and to
  reference the grep-checkable code-side enforcement.

### 14. § Promotion path step 4 — split 4a/4b/4c/4d, added cost
- **Section:** § Promotion path, item 4.
- **Source:** L029 / L010, cost_adversary:C008 / C004.
- **Prior:** "Land schema and resolver in three commits if the
  bench passes:" with sub-items (a)/(b)/(c).
- **New:** four sub-items (a)/(b)/(c)/(d). 4a names migration
  details; 4b names every grounding-module file; 4c names extractor
  integration with run-summary field; 4d names consolidator
  integration with `projection_audits`. Iteration-cost paragraph
  added at end of step 4.

### 15. `docs/rfcs/README.md` — RFC 0030 row updated
- **Section:** RFC index table row for 0030.
- **Source:** synthesis "Required RFC edits" item 15.
- **Prior:**
  `| [0030](...) | proposal | none | Public-dataset entity grounding for claim extraction |`
- **New:**
  `| [0030](...) | accepted | none | Public-dataset entity grounding for claim extraction (8-lane design review 2026-05-09; spec authoring next) |`

## Findings addressed

All 30 ledger findings (L001–L030). Disposition is `accept` for
every entry per the synthesis.

| Ledger | Severity | RFC change(s) |
|---|---|---|
| L001 | blocking | Edit 2 (Code-side enforcement) |
| L002 | blocking | Edit 8 (D-E content hash) |
| L003 | blocking | Edit 3 (Locked in DECISION_LOG) |
| L004 | blocking | Edit 11 (D-H full rewrite) |
| L005 | major | Edit 5 (D-B prompt-shape guard) |
| L006 | major | Edit 9 (D-F scratch SQLite) |
| L007 | major | Edit 7 (D-D append-only/cascade) |
| L008 | major | Edit 10 (D-G prompt budget); Edit 8 (provenance sidecar) |
| L009 | major | Edit 5 (module split) |
| L010 | major | Edit 14 (4a/4b/4c/4d split + cost) |
| L011 | major | Edit 4 (D-A budget enforcement) |
| L012 | major | Edit 12 Q6 (latency budgets) |
| L013 | major | Edit 9 (run-summary status); Edit 12 Q7 (lock file) |
| L014 | major | Edit 9 (templates + --usage) |
| L015 | major | Edit 9 (snapshot lifecycle, run-summary header); Edit 8 |
| L016 | major | Edit 12 Q4 (private_aliases) |
| L017 | minor | Edit 9 (`engram grounding detach` named in CLI surface) |
| L018 | minor | Edit 14 (cost statement; spec ships `grounding-bench` automation TBC) |
| L019 | minor | Edit 8 (mode bits 0700/0600) |
| L020 | minor | Edit 6 (D-C redaction rule) |
| L021 | minor | Edit 1 (D020 named) and § Why this fits (existing wording on dataset acquisition is sanctioned exception) |
| L022 | minor | Edit 14 (test names + CLI list); spec carries argparse exact shapes |
| L023 | minor | Edit 14 (resolver determinism in tests sub-bullet implicit; spec-time confirmation) |
| L024 | minor | Edit 14 (4a migration details) |
| L025 | minor | Edit 12 Q2 (type-narrowing) |
| L026 | minor | Spec-time fixture strategy (carryover) |
| L027 | minor | Edit 8 (fetch-time indexing) |
| L028 | minor | Edit 1 (Decision refs walked) |
| L029 | minor | Edit 14 (4a/4b/4c/4d split) |
| L030 | minor | Edit 9 (forward-only revocation, live filter) |

## Findings deferred

None to spec-time-only; the 15 RFC edits land all 30 ledger items
either by direct text change or by naming a spec-time obligation
that the spec-authoring run will carry. Two minor items (L022
argparse shapes, L026 test fixture strategy) carry forward as spec
content rather than RFC content; the RFC names them as spec scope.

## Open carryover for spec

The spec-authoring run should pin:

1. Exact `argparse` subparser definitions for `engram grants
   {list,grant,revoke,apply-template}` and `engram grounding
   {snapshot,rollback,detach,versions}` (L022).
2. Test-fixture strategy: synthetic ~10MB content-hashed snapshot
   committed to the repo; integration tests opt in via env var to
   download a real subset (L026).
3. Test matrix details: grant enforcement, snapshot integrity,
   resolver placement, prompt-version bump triggers, downgrade
   behavior, AST-walk no-http-clients test, resolver determinism
   under (surface_form, snapshot_pin) (L022 / L023).
4. `engram phase3 grounding-bench` automation (L018,
   usability_adversary:U007).
5. `engram grounding onboarding` walkthrough command (L010,
   gemini:F001, usability_adversary:U008).
6. The `D###` allocation for the locked non-negotiables (L003).
   This requires a `DECISION_LOG.md` write that this run did not
   make.

## Validation

- Revised RFC reads consistently end-to-end after the changes.
- Front-matter Decision refs and phase refs are accurate; Review
  refs link to the correct review-dir artifacts.
- No private corpus excerpts have been added.
- The five non-negotiable constraints in § Non-negotiable
  constraints are unchanged from the prior draft (verbatim
  preservation); the additions are *enforcement* and *locking*
  subsections, not modifications to the constraints themselves.
- `docs/rfcs/README.md` row updated to `accepted` status with
  next-step pointer.

## Residual risk

- **Final review will check whether the synthesis's 15 edits all
  landed faithfully.** If any edit was misapplied or overcompressed,
  the cycle will catch it.
- **DECISION_LOG entry not yet written.** L003 says the five
  non-negotiables should be promoted to a `D###` entry; this is the
  operator's job. The RFC names the obligation; without the operator
  applying it, the lock is convention rather than reference.
- **Spec-authoring run** is the next gate. The synthesis names spec
  scope; if any of the spec-time obligations are punted, that's a
  spec-loop concern.
- **Bench is not yet run.** Even with a clean spec and implementation,
  the D-H bench is the actual oracle. Until Arm B vs Arm C produces
  the predicted false-rate-reduction-with-coverage-preservation, the
  RFC's central hypothesis is unverified.
