# REVIEW — Source Ingestion RFC Candidate Package (privacy boundary lens)

| Field | Value |
|-------|-------|
| Workflow | `source-ingestion-rfc-research-2026-05-15` |
| Lane | claude |
| Role | reviewer |
| Date | 2026-05-15 |
| Inputs reviewed | `DRAFT_claude.md`, `DRAFT_codex.md`, `DRAFT_gemini.md`, `PRIOR_ART_DOSSIER.md` |
| Source design | `docs/design/source-ingestion-expansion-proposal-2026-05-15.md` |
| Verdict | **accept_with_findings** |
| Scope of verdict | The three drafts plus the dossier are a viable candidate package for synthesis. They do not, in themselves, promote any RFC. The synthesizer must resolve the findings below before producing the final RFC 0050 body. |

> This is a review artifact only. It does not edit the drafts, the dossier, the
> source design document, `DECISION_LOG.md`, the RFC index, code, tests, or
> migrations. It does not promote any draft.

## 1. Method

I read the three drafts, the prior-art dossier, the source design document, and
the project canon named in the task prompt (`AGENTS.md`, `HUMAN_REQUIREMENTS.md`,
`SPEC.md`, `BUILD_PHASES.md`, `ROADMAP.md`, `docs/schema/README.md`,
`STRIATUM_MEMORY_E2E_BACKLOG.md`, and `docs/AGENT_CONTEXT_NOTES.md`), plus the
adjacent RFC index (`docs/rfcs/README.md`, RFC 0033-RFC 0036, RFC 0045-RFC 0049).
I did not run any importer code, schema migration, or evaluation gate. I treat
the candidate package as a paper artifact under review against the six task-prompt
checks: scope, privacy/no-egress, contract coherence, rollout order, evaluation
gates, and open questions.

All findings carry a stable handle (`R-NNN`), the affected drafts, and a concrete
suggested edit for the synthesizer. Findings ordered by load-bearing weight, not
by section.

## 2. Verdict And Headline Findings

**Verdict: `accept_with_findings`.**

The three drafts converge well on the load-bearing shape: a four-question source
contract, a closed projection-family vocabulary, per-family privacy defaults, a
sequenced rollout that starts with project sources and defers life/observation
sources, an RFC 0049-shaped minimum gate set, and an honest "scope kept out"
section. The dossier is independent and reliable; it explicitly flags itself as
research artifact rather than promotion.

None of the divergences is fatal. They are policy choices the synthesizer must
pick before the final RFC body lands. The five headline issues, ordered by
review weight, are:

1. **R-001 (HUMAN_REQUIREMENTS tier-vocabulary reconciliation).** The drafts
   use a "lower tier = less restrictive" interpretation of `privacy_tier` that
   does not literally match HUMAN_REQUIREMENTS § Privacy & access tiers, where
   Tier 1 = "only me, only on this machine" and Tier 2 = "surfaceable to my AI
   assistants for context." The candidate package must reconcile the two
   meanings explicitly before any new source family inherits a numeric default.
2. **R-002 (projection-family vocabulary divergence).** The claude draft
   declares six families, the codex draft eleven, and the gemini draft does not
   close the list. Synthesizer must pick one closed initial vocabulary and
   commit to it as the load-bearing structure for retrieval, privacy, and
   evaluation gates.
3. **R-003 (`(source_kind, external_id)` uniqueness boundary).** Codex names
   the constraint that `sources` is unique on `(source_kind, external_id)`
   while `tenant_id`/`corpus_id` were added later. Claude and gemini are
   silent. The constraint will start to bind as soon as the first multi-repo
   or multi-account adapter lands. The synthesizer must include this as an
   open question or a contract field.
4. **R-004 (evaluation-gate ID namespace).** Claude uses `EG-S00..EG-S31`,
   codex uses `EG-SI-000..EG-SI-100`, gemini uses `EG-101..EG-104`. The names
   collide with RFC 0049's existing Striatum gate IDs unless namespaced.
   Synthesizer must pick exactly one prefix and update the final RFC body
   uniformly.
5. **R-005 (Tier 4+ extension beyond HUMAN_REQUIREMENTS).** Codex proposes
   "Tier 4+ by default" for biometrics, exact coordinates, face data, health,
   finance, and contacts. HUMAN_REQUIREMENTS defines Tier 4 as posthumous-only
   release and Tier 5 as redact-on-death. Reusing those tier numbers for
   "highest sensitivity default" repurposes audience/lifecycle slots and will
   collide with the posthumous-handoff policy. Synthesizer must either map
   biometrics into the existing 1-5 audience scale or introduce a separately
   named sensitivity scale (and call out the new scale explicitly in HR).

Each headline issue is restated below with the affected drafts and a concrete
suggested edit. Additional findings (R-006 onward) cover the smaller divergences
that synthesis must touch.

## 3. Scope (task-prompt check 1)

The package does not overshoot the design document. All three drafts are
process-and-direction RFCs that explicitly defer importer implementation to
follow-up RFCs (claude § 1, § 12; codex Summary, Initial Implementation Slice;
gemini § Rollout Strategy). None proposes a schema migration in the first slice.
None proposes a runtime registry in the first slice.

The package does not conflict materially with adjacent RFCs:

- RFC 0033 / RFC 0034 / RFC 0035 / RFC 0036 are explicitly named as the design
  references for Step 4 in all three drafts and are not re-litigated.
- RFC 0044 / RFC 0045 are cited as the existing Striatum-side source-contract
  precedent; the package generalizes the shape without overwriting Striatum's
  own contract.
- RFC 0046 is cited as the projection-precedent reference; the package does
  not replace it and does not propose folding `striatum_references` into a
  generic projection table.
- RFC 0047 / RFC 0048 / RFC 0049 are inherited as the retrieval, context, and
  gates substrate; the package adds source families that those RFCs must
  respect, but it does not change their text.

The `STRIATUM_MEMORY_E2E_BACKLOG.md` 2026-05-15 pivot is honored: none of the
drafts proposes promoting RFC 0045-RFC 0049 as part of this RFC, and all three
keep Striatum hardening unblocked.

The scope-kept-out sections in the three drafts are honest. Claude § 8 lists
eight explicit deferrals (media bodies, cloud APIs, derived products,
personal-memory paste-through, live capture, cross-tenant projection coupling,
`source_kind` enum replacement, bidirectional sync). Codex Non-Goals lists ten
deferrals at slightly different granularity. Gemini § Scope Kept Out is shorter
and more general but does name the four most load-bearing deferrals.

Findings under scope:

- **R-006 (Scope; affects: claude, codex).** The two long drafts use different
  granularity for the deferrals list. Codex's "no replacement of the current
  `source_kind` enum in the first implementation slice unless enum churn becomes
  a measured migration burden" is more precise than claude's "Replacing the
  closed `source_kind` enum" deferral. *Suggested edit:* synthesizer should
  merge to codex's wording but keep claude's structural placement (a dedicated
  "Scope Kept Out" section with the deferrals enumerated rather than buried in
  Non-Goals).
- **R-007 (Scope; affects: gemini).** Gemini Scope-Kept-Out does not name the
  `source_kind` enum, the cross-tenant projection rule, or bidirectional sync.
  *Suggested edit:* synthesizer should expand the gemini deferrals to match
  the claude/codex baseline; otherwise an under-specified scope-kept-out
  section will be read as permissive.

## 4. Privacy And No-Egress (task-prompt check 2)

This is the section the lane was asked to weight. It deserves the longest
treatment.

### 4.1 No-egress invariant

All three drafts inherit Engram's no-egress invariant and apply it to every
corpus-reading process introduced by a new source family. Coverage:

- **Claude** § 5.1 names importer, projection worker, retrieval worker, packet
  builder, and MCP server. Calls it the D020 / HUMAN_REQUIREMENTS rule.
- **Codex** § Privacy Defaults names importer, validator, projection worker,
  embedding stages, retrieval services, packet builders, and evaluators.
  Codex also adds the structural rule "a process with network tools must not
  have direct Engram corpus access" — the strongest restatement of the
  HUMAN_REQUIREMENTS § Why corpus access and network egress are kept separate
  principle in any of the three drafts.
- **Gemini** § Privacy Defaults and Egress restates the rule succinctly with
  four bullets including the no-derived-product-leak rule.

The dossier confirms that the existing code base has loopback URL checks
(`segmenter.py`, `embedder.py`) but not OS-level no-egress sandbox proof, and
that RFC 0049 distinguishes the two. None of the three drafts conflates them.
All three either implicitly or explicitly defer OS-level proof to the
per-importer evaluation gate.

No draft proposes a path that could exfiltrate user data by default. No draft
proposes a hosted importer, a cloud-API importer, a remote embedding service,
a remote LLM, a remote OCR/vision API, or remote face recognition. All three
explicitly exclude these in their Non-Goals / Scope-Kept-Out sections.

Findings under no-egress:

- **R-008 (No-egress scope coverage; affects: claude, gemini).** Codex's
  process enumeration is the most complete (validator + embedding stage +
  evaluator are present in codex and missing from claude/gemini). *Suggested
  edit:* synthesizer should adopt codex's enumeration as the canonical list of
  corpus-reading processes for the no-egress invariant.
- **R-009 (No-network gate evidence; affects: all three).** All three drafts
  rely on a per-adapter `no_network_access` test. The dossier flags an
  evidence gap: loopback URL checks (e.g., `segmenter.py:1880-1923`) are
  weaker than OS-level no-egress sandbox proof per RFC 0049. *Suggested edit:*
  synthesizer should explicitly name the gate as `EG-Sxx no-egress (level 1:
  monkeypatched-socket; level 2: sandboxed-process-egress)` and require both
  for any adapter promoted to default-on extraction.

### 4.2 Privacy-tier vocabulary reconciliation

This is the load-bearing finding for the privacy lens.

HUMAN_REQUIREMENTS defines five tiers by *audience and lifecycle*, not by
*sensitivity*:

```
Tier 1: only me, only on this machine
Tier 2: surfaceable to my AI assistants for context
Tier 3: shareable with my partner / chosen heirs
Tier 4: posthumous-only release
Tier 5: redact-on-death
```

The drafts use `privacy_tier` as a *sensitivity scale* where lower = more
permissive default and higher = more restrictive. Examples:

- Claude § 5 sets git repos and project docs to Tier 1 with "default-on
  segmentation" and "default-on extraction for project docs." But Tier 1 in
  HUMAN_REQUIREMENTS literally means "only me, only on this machine," which
  is plausibly read as "no AI assistants either." If extraction is default-on
  at Tier 1, the operational meaning of Tier 1 is no longer "only me." The
  draft does not reconcile this.
- Codex § Privacy Defaults explicitly writes "Higher tiers are more
  restrictive" and uses Tier 4+ for biometrics, exact coordinates, face data,
  health, finance, and contacts. HUMAN_REQUIREMENTS Tier 4 is posthumous-only
  release; using the same integer for "biometrics default" double-books the
  tier number.
- Gemini § Privacy Defaults uses "Tier 1-5" but inherits the same sensitivity
  ordering as the other two drafts.

The dossier already flags this ("That is an unresolved policy mismatch, not an
implementation detail" — PRIOR_ART_DOSSIER, § Privacy Prior Art And Concerns).
The candidate package does not resolve it.

This is the most consequential coherence problem in the package. It is not a
naming nit. The interpretation determines whether default-on AI-assistant
extraction over project docs is consistent with HUMAN_REQUIREMENTS or in
tension with it.

Findings under tier vocabulary:

- **R-001 (Tier vocabulary; affects: all three).** *Suggested edit:* the
  synthesizer should add a § Tier vocabulary reconciliation subsection (or a
  cross-reference to a separately RFC'd reconciliation) before the per-family
  defaults table. Two acceptable shapes:
  1. Re-anchor `privacy_tier` to the HUMAN_REQUIREMENTS audience-and-lifecycle
     scale, then either rename project-docs-default to Tier 2 ("AI assistants
     OK") instead of Tier 1, or explicitly amend HUMAN_REQUIREMENTS to broaden
     Tier 1 to include "AI assistants on this machine, never off-machine."
  2. Introduce a distinct `sensitivity_class` field on the source contract for
     the per-source-family scale (1..n, sensitivity-ordered) and reserve
     `privacy_tier` for the HUMAN_REQUIREMENTS audience scale.

  Either is acceptable; both require an explicit reconciliation and an
  operator decision. Neither is appropriate for the synthesizer to silently
  pick.
- **R-005 (Tier 4+ extension; affects: codex).** *Suggested edit:* the
  synthesizer must either drop "Tier 4+" / "Tier 5+" from codex's defaults and
  re-anchor those source families inside the HUMAN_REQUIREMENTS 1-5 scale, or
  explicitly add a new sensitivity scale per R-001 option 2. Reusing the
  integer "4" for "biometrics default" while HUMAN_REQUIREMENTS reserves it
  for "posthumous-only release" will create a posthumous-handoff bug the day
  someone wires the dead-man's-switch policy.

### 4.3 Per-family privacy defaults

The three drafts agree at the family level (git Tier 1, build artifacts Tier 1,
project docs Tier 1, personal notes Tier 2+, exported email Tier 2+, exported
team chat Tier 2+, personal messaging Tier 3, browser/shell Tier 3, location
Tier 3+, health/finance/contacts highest). Per § 4.2 the integer values are
not the load-bearing part; the *ordering* between source families is.

Specific divergences worth noting:

- **R-010 (AI-conversation default; affects: codex, gemini).** Codex says
  "current source default unless promoted; proposed Tier 1 or Tier 2 by user
  setting" for AI conversation exports. Claude says Tier 1, gemini says Tier
  1 implicitly. The current code base sets Tier 1 by default
  (`migrations/001_raw_evidence.sql`). *Suggested edit:* synthesizer should
  pin to "Tier 1 (current behavior, unchanged)" for ChatGPT/Claude/Gemini
  and queue the operator-setting variant as Open Question.
- **R-011 (Meeting transcripts; affects: claude only).** Claude § 5 splits
  meeting transcripts as Tier 2 / Tier 3 by speaker count ("Depends on whether
  the operator was the only speaker"). Codex and gemini do not split.
  *Suggested edit:* synthesizer should adopt claude's split as a contract
  field (`participant_third_party: true/false`) so the speaker-count rule is
  machine-checkable, not a per-import judgment call.
- **R-012 (Calendar; affects: claude, codex).** Claude says Tier 2 default,
  codex says "Tier 3 by default." Calendars contain other people's emails,
  phone numbers, and locations; codex's stricter default is closer to the
  HUMAN_REQUIREMENTS posture for third-party data. *Suggested edit:*
  synthesizer should pin to Tier 3 default for calendar with an explicit
  per-calendar opt-down to Tier 2 (e.g., for a calendar owned exclusively by
  the operator).

### 4.4 Third-party-data extraction gate

All three drafts agree that human-communication extraction must be off by
default. Coverage:

- Claude § 5.3 defines the extraction gate as a contract field
  (`extraction_eligibility.default != default-on`) plus a CLI flag
  (`--enable-extraction`) plus a documented third-party-data acknowledgment
  visible in `engram describe-corpus`.
- Codex § Privacy Defaults says claim extraction is disabled unless the source
  contract and user approval enable it, and Open Question OQ-SI-007 names the
  third-party-privacy-policy precondition explicitly.
- Gemini § Privacy Defaults and Egress § 4 ("Third-Party Data") states the
  rule but does not name the contract field, the CLI flag, or the
  describe-corpus surfacing.

This is convergent enough for synthesis. The remaining decision is whether the
gate is purely per-source-family or is also conditioned on a separate
third-party-privacy policy document landing first.

Findings under third-party-data:

- **R-013 (Third-party extraction policy; affects: all three).** *Suggested
  edit:* synthesizer should adopt claude's contract field plus CLI flag plus
  describe-corpus surfacing as the *mechanism*, and keep codex's "yes" answer
  to OQ-SI-007 (separate third-party privacy policy must exist before Step 3
  lands) as the *policy*. Both belong in the final RFC body; they are not
  alternatives.

### 4.5 No-derived-product-leak invariant

All three drafts converge that derived products do not become raw evidence and
do not leave the machine by default. Claude § 5.2 formalizes this as the
"No-derived-product-leak invariant" with an explicit AL-D004 pre-requirement.
Codex § Privacy Defaults names the rule and ties it to a separately accepted
generated-product privacy / citation / audit / gate contract. Gemini § 3
restates it briefly.

This is the cleanest area of convergence in the package.

Findings under derived products:

- **R-014 (No-derived-product-leak; affects: all three).** *Suggested edit:*
  synthesizer should adopt claude's invariant name and explicit AL-D004
  reference (which gives the synthesizer a stable handle pointing at
  `STRIATUM_MEMORY_E2E_BACKLOG.md`). Keep codex's longer list of derived
  product types (summaries, packet text, daily biographies, OCR outputs,
  captions, source-specific summaries) inside that invariant.

### 4.6 Privacy summary

No draft introduces a path that exfiltrates user data by default. No draft
proposes a hosted importer. The no-egress invariant is preserved across all
three drafts and the dossier. The dominant privacy finding is the tier-
vocabulary reconciliation (R-001 / R-005), not a missing rule or a forbidden
surface. The other privacy findings (R-008..R-014) are convergent enough that
synthesis can proceed.

## 5. Source-Contract Coherence (task-prompt check 3)

The drafts agree on the four required questions (raw boundary, projection,
default consumers, protection rules) and on the high-level fields a contract
must declare (source_kind, sub_kinds, raw_artifact_boundary, identity keys,
temporal mapping, privacy default, projection families, extraction eligibility,
no outbound calls). They diverge on field granularity and on the closed
projection-family list. Three load-bearing divergences require synthesizer
action.

### 5.1 Projection-family vocabulary

The biggest contract-coherence divergence:

| Family (claude § 4) | Family (codex § Projection Families) | Family (gemini § Evidence Lanes) |
|---|---|---|
| `conversation_event` | `conversation_thread` | "Conversations, messages, participant edges" (open list) |
| `document_chunk` | `document_record` | "Documents, chunks, headings, frontmatter, path-based links" (open list) |
| `project_event` | `project_event` | "Project events" (open list) |
| `code_reference` | `code_reference` | (implicit) |
| `artifact_reference` | `artifact_reference` | (implicit) |
| `observation_metadata` | `observation` | "Observations" (RFC 0033) |
| (none) | `execution_artifact` | (implicit) |
| (none) | `place_event` | (RFC 0035) |
| (none) | `asset_record` | (RFC 0034) |
| (none) | `coverage_gap` | (implicit) |
| (none) | `source_audit` | (implicit) |
| (deferred) | (split) | (deferred) |

Claude declares 6 families and explicitly excludes `generated_product` and
`belief_projection`. Codex declares 11 families, including `coverage_gap` and
`source_audit` which are operational rather than evidence-shape lanes. Gemini
does not close the list at all.

The vocabulary is load-bearing because retrieval, privacy, and evaluation gates
all key off it. Adding `coverage_gap` and `source_audit` as projection families
is plausible (the daily biography RFC 0036 needs gap data, and audit
reconstruction is a real gate). Splitting `execution_artifact` from
`artifact_reference` is also plausible (build runs vs. arbitrary file refs).
But the synthesizer must commit; an "open list" finalizes nothing.

Findings under projection-family vocabulary:

- **R-002 (Projection-family closed list; affects: all three).** *Suggested
  edit:* synthesizer should pick exactly one closed initial vocabulary.
  Recommended baseline (from this reviewer): adopt claude's six families
  (conversation_event, document_chunk, project_event, code_reference,
  artifact_reference, observation_metadata) and add codex's two operational
  families (coverage_gap, source_audit) as a separately-named *operational*
  family band rather than mixing them with evidence-shape families. Drop
  `execution_artifact` for v1 (fold into `artifact_reference`); revisit only
  if a Step 1 build-artifact importer cannot fit the simpler shape.
- **R-015 (Generated-product family exclusion; affects: codex, gemini).**
  Claude § 4 explicitly excludes `generated_product` from the v1 vocabulary
  pending AL-D004. Codex implies the same exclusion in its no-derived-product-
  leak rule but does not name it as a "deliberately out of scope" family.
  Gemini does not name it. *Suggested edit:* synthesizer should adopt
  claude's explicit "deliberately out of scope" subsection so that a later
  proposal cannot quietly add `generated_product` without revisiting this
  RFC.

### 5.2 Source-contract field granularity

Codex's contract template is the most detailed. Claude's is mid-weight.
Gemini's is the highest-level summary. Notable codex-only fields that the
synthesizer should consider keeping:

- `identity.source_instance_id` vs. `identity.item_identity_keys` vs.
  `identity.logical_identity_keys`. This three-way split addresses the
  `(source_kind, external_id)` uniqueness problem (R-003) by separating
  *instance* identity (one repo at one path), *item* identity (one commit
  inside that repo), and *logical* identity (one ref name that moves over
  time). Claude's `identity_keys` and gemini's `identity_keys` are flat lists
  that paper over this.
- `lifecycle.states` enumeration (content / tombstone / redaction /
  withheld_marker). Claude and gemini do not enumerate lifecycle states.
- `extraction_eligibility.opt_in_required_for` as a closed sub-vocabulary
  rather than a single boolean.
- `provenance.required` as an explicit field list (source_id, raw row id,
  repository_id, commit_sha, content_hash, adapter_version). Claude and
  gemini imply this but do not list it.
- `rebuild.projection_generation` / `rebuild.reproject_from_raw` /
  `rebuild.stale_projection_policy`. Claude implies these in § 3.3 but does
  not codify them as contract fields.

Findings under contract field granularity:

- **R-016 (Source-contract template granularity; affects: claude, gemini).**
  *Suggested edit:* synthesizer should adopt codex's longer template as the
  baseline contract shape, and adopt claude's `tests:` enumeration (the six
  named test cases) as the contract-test rider. Gemini's shorter template is
  acceptable as a summary table at the top of the RFC body, but should not
  be the load-bearing contract spec.
- **R-003 (`(source_kind, external_id)` boundary; affects: claude, gemini).**
  *Suggested edit:* synthesizer should adopt codex's three-part identity
  split (source_instance_id, item_identity_keys, logical_identity_keys) and
  add an Open Question on whether the `sources` table's unique constraint
  needs to be expanded to `(tenant_id, corpus_id, source_kind, external_id)`
  before the first multi-repo or multi-account importer lands. This is a
  schema decision; the design doc punts it; the candidate package should
  not.

### 5.3 Contract enforcement mechanism

All three drafts agree that enforcement is by importer tests in the first
slice, with a runtime registry deferred. They use slightly different test
naming conventions:

- Claude § 3.3 names six tests (`idempotent_reimport`, `hash_conflict_raises`,
  `projection_rebuild_from_raw`, `no_network_access`,
  `privacy_tier_inheritance`,
  `extraction_off_by_default_for_third_party_data`).
- Codex § Source Contract Template's `tests:` block names eight
  (`contract_validator`, `idempotent_reimport`,
  `conflict_on_changed_raw_hash`, `raw_evidence_immutable`,
  `projection_rebuild_from_raw`, `no_network_access`, `privacy_inheritance`,
  `exact_reference_citation`).
- Gemini § Importer Verification names four
  (idempotency, conflict detection, immutability, no egress).

Convergent enough. The synthesizer should adopt the union (claude's six plus
codex's `contract_validator`, `raw_evidence_immutable`, and
`exact_reference_citation`).

Findings under enforcement:

- **R-017 (Contract test enumeration; affects: all three).** *Suggested edit:*
  synthesizer should adopt the eight-test union: contract_validator,
  idempotent_reimport, conflict_on_changed_raw_hash, raw_evidence_immutable,
  projection_rebuild_from_raw, no_network_access, privacy_tier_inheritance,
  extraction_off_by_default_for_third_party_data, exact_reference_citation.
  Each test must have a per-source-family fixture under
  `tests/test_<source_kind>_contract.py` (claude's filename convention).

## 6. Rollout Order (task-prompt check 4)

All three drafts converge on the same five-step rollout:

```
Step 0: Source contract + projection-family vocabulary (this RFC)
Step 1: Project sources (git + build_artifact)
Step 2: Project notes + Markdown trees
Step 3: Exported communication logs (email + team chat)
Step 4: Life and observation sources (defer to RFC 0033-0036)
Step 5: Live capture
```

This is defensible by the highest-signal, lowest-egress-risk principle:

- Step 1 has the lowest third-party-data risk (project-selected repos are
  first-party authored; build artifacts are project outputs).
- Step 2 adds documents (still mostly first-party, but personal vaults need
  the per-vault privacy gate).
- Step 3 introduces third-party data (other people's messages) but uses local
  exports rather than live account access.
- Step 4 introduces the most-sensitive categories (biometrics, exact location,
  health, finance) and is deferred to RFC 0033-0036 for design.
- Step 5 introduces live capture, which is the highest surveillance-risk
  surface and is gated on Steps 1-4 being boring.

Findings under rollout order:

- **R-018 (Rollout order convergence; affects: all three).** No edit required.
  The order is defensible. The synthesizer should keep it.
- **R-019 (Step-1 sub-order; affects: codex, gemini).** Claude § 6 Step 1
  orders git before build_artifact and gives an explicit reason ("project
  events ground build artifacts"). Codex Stage 1 lists git, build, and
  Striatum alignment without a sub-order. Gemini Stage 1 lists git and
  build_artifact without a sub-order. *Suggested edit:* synthesizer should
  adopt claude's explicit sub-order (git first, then build_artifact, then
  Striatum source-contract alignment) so the importer RFCs that follow have
  a single sequence to target.
- **R-020 (Step-3 first non-AI chat adapter; affects: all three).** All
  three drafts leave the choice of first non-AI chat adapter open. The
  dossier names mbox, Maildir, Slack JSON, Discord JSON, and Matrix JSON as
  candidates. Claude OQ recommends mbox; codex OQ-SI-005 recommends "the
  simplest local file export with good fixtures and clear third-party privacy
  handling"; gemini does not recommend. *Suggested edit:* synthesizer should
  keep this as a named Open Question for operator decision and not collapse
  it into a recommendation, because the choice has implications for the
  third-party-data extraction gate evidence.

## 7. Evaluation Gates (task-prompt check 5)

All three drafts borrow shape from RFC 0049 (Striatum evaluation gates) and
specialize to source-family invariants. The minimum gate set is convergent:

- No-egress / no outbound calls.
- Idempotent re-import.
- Hash conflict on changed raw artifact.
- Raw evidence immutability.
- Projection rebuild from raw.
- Privacy tier inheritance.
- Extraction opt-in for third-party data.
- Packet citation back to raw evidence.

Claude § 7 adds per-family specializations for git (commit-event dedup,
rewritten-history representation, patch-body-not-in-packet-by-default) and
build_artifact (build-to-commit linkage, long-log-not-in-packet-by-default).
Codex § Evaluation Gates adds level promotion (Level 0/1/2/3), outcome
vocabulary (pass / fail / blocked_upstream / not_run /
accepted_with_scope_limit), and ten gates with per-source-family extra cases
(git, build, markdown/docs, human communication, media/location/life, live
capture). Gemini § Evaluation Gates lists four gates only.

The gate set is enough to keep the pipeline honest under regression, with two
caveats:

- The gates do not yet enforce R-009 (level-1 monkeypatched-socket vs. level-2
  sandboxed-process-egress evidence). The drafts assume the test harness is
  enough; the dossier shows that the current loopback checks are weaker than
  RFC 0049 expects.
- The gates do not enforce R-001 (HUMAN_REQUIREMENTS tier reconciliation). A
  `privacy_tier_inheritance` test only confirms that derived rows carry the
  parent tier; it does not confirm that the chosen integer is consistent with
  HUMAN_REQUIREMENTS' audience scale.

Findings under evaluation gates:

- **R-004 (Gate-ID namespace; affects: all three).** Claude uses
  `EG-S00..EG-S31`. Codex uses `EG-SI-000..EG-SI-100`. Gemini uses
  `EG-101..EG-104`. The RFC 0049 gate-ID space already uses `EG-000` and
  similar prefixes. *Suggested edit:* synthesizer should pick exactly one
  prefix. Recommended: `EG-SI-NNN` (codex's three-digit scheme), because
  three digits leave room for per-family specializations without crowding
  RFC 0049's gate space. Update the entire candidate package to that prefix
  uniformly in the final RFC body.
- **R-021 (Gate-level promotion ladder; affects: claude, gemini).** Codex's
  Level 0 / Level 1 / Level 2 / Level 3 promotion ladder is the most useful
  operational addition. Claude does not have it; gemini does not have it.
  *Suggested edit:* synthesizer should adopt codex's promotion ladder
  explicitly. Tie level promotion to per-gate evidence so that a source
  family cannot reach Level 3 ("routine/default enablement") until all of
  its required gates pass.
- **R-022 (Outcome vocabulary; affects: claude, gemini).** Codex's
  `accepted_with_scope_limit` outcome is the most useful operational
  addition. Without it, a partial pass on one gate (e.g., commit dedup works
  but rewritten-history representation is incomplete) has nowhere to land.
  *Suggested edit:* synthesizer should adopt codex's outcome vocabulary
  uniformly.
- **R-023 (Coverage-gap gate; affects: claude, gemini).** Codex EG-SI-080
  ("Coverage, Gaps, And Lifecycle") makes coverage-gap representation a
  gate. Claude and gemini do not. The HUMAN_REQUIREMENTS § Gaps as data
  rule and RFC 0036 § day-packet gap representation both depend on this.
  *Suggested edit:* synthesizer should adopt codex's coverage-gap gate; if
  R-002 keeps `coverage_gap` as an operational family rather than a
  projection family, the gate still applies via the operational band.

## 8. Open Questions (task-prompt check 6)

The three drafts list overlapping but non-identical open questions:

- Claude § 9 names six (patch body retention, build-log retention,
  `source_kind` enum-vs-registry timing, third-party extraction policy, first
  non-AI chat adapter, source-contract-registry timing).
- Codex § Open Questions names seven (OQ-SI-001 patch bodies; OQ-SI-002 build
  log storage; OQ-SI-003 privacy tier defaults; OQ-SI-004 enum-vs-registry;
  OQ-SI-005 first non-AI chat adapter; OQ-SI-006 contract storage shape;
  OQ-SI-007 human-communication extraction gate).
- Gemini § Open Questions names three (patch retention, third-party privacy
  threshold, source registry timing).

Three open questions are convergent across all three drafts and must survive
synthesis: patch body retention, `source_kind` enum-vs-registry timing, and
the first non-AI chat adapter choice. Two are present in two drafts and worth
keeping: build-log retention (claude, codex), and the third-party-extraction
policy (claude, codex, partial gemini).

Missing open questions that this reviewer believes *should* block synthesis
unless added:

- **R-024 (Missing OQ — tier vocabulary reconciliation; affects: all three).**
  The HUMAN_REQUIREMENTS § Privacy & access tiers reconciliation (R-001) is
  not a present open question in any draft. It must be added.
  *Suggested edit:* add OQ-SI-008 "Tier vocabulary reconciliation. Should
  `privacy_tier` be re-anchored to HUMAN_REQUIREMENTS' audience-and-lifecycle
  scale, or should the source contract introduce a separate
  `sensitivity_class` field?" Operator decision required.
- **R-025 (Missing OQ — `(source_kind, external_id)` uniqueness; affects:
  claude, gemini).** Codex flags this in prose but not as an Open Question.
  *Suggested edit:* add OQ-SI-009 "Source unique-constraint expansion.
  Should the `sources` unique constraint expand to `(tenant_id, corpus_id,
  source_kind, external_id)` before the first multi-repo or multi-account
  importer lands?" Operator decision required.
- **R-026 (Missing OQ — operational vs evidence projection families;
  affects: all three).** R-002's recommended baseline keeps `coverage_gap`
  and `source_audit` separate from the evidence-shape vocabulary. The
  package does not yet have an Open Question on whether that separation is
  the right shape. *Suggested edit:* add OQ-SI-010 "Operational vs
  evidence-shape projection families. Should `coverage_gap` and
  `source_audit` live alongside `conversation_event` /
  `document_chunk` etc., or in a separately named operational band?"
  Operator decision required.
- **R-027 (Missing OQ — no-egress evidence level; affects: all three).**
  R-009's two-level no-egress evidence model is implicit in the dossier but
  not in any draft's Open Questions. *Suggested edit:* add OQ-SI-011 "No-
  egress evidence level. Should the no-egress gate require monkeypatched-
  socket evidence only (cheaper), sandboxed-process-egress evidence only
  (more expensive but stronger), or both before a source family is
  promoted to default-on?" Operator decision required.

The remaining open questions (patch bodies, build logs, enum-vs-registry,
first non-AI chat adapter, third-party extraction policy, contract storage
shape) are convergent and should be carried into the final RFC body verbatim
from the longer drafts.

Findings summary under open questions:

- **R-028 (Open-question carry forward; affects: all three).** *Suggested
  edit:* synthesizer should carry forward all six convergent open questions
  plus the four added in R-024..R-027, for a final RFC body of ten Open
  Questions. Where claude's recommendation differs from codex's
  recommendation (e.g., on first non-AI chat adapter — claude says mbox,
  codex says "simplest with good fixtures"), include both recommendations
  and let the operator pick.

## 9. Coherence With Project Canon

The candidate package is coherent with most of the project canon. Specific
checks:

- **AGENTS.md (no cloud, raw evidence immutable, derived tables rebuildable,
  preserve provenance and confidence, prefer boring local infra).** All
  three drafts honor every clause.
- **HUMAN_REQUIREMENTS.md (long-arc biography, temporal validity on every
  fact, provenance on every fact, privacy tiers, gaps as data, multi-
  perspective, forgetting, posthumous handling).** All three drafts honor
  the long-arc, temporal, and provenance clauses. The privacy-tier clause
  is the source of R-001 / R-005. The gaps-as-data clause is the source of
  R-023.
- **SPEC.md (all data stays on-device, no outbound network for corpus-
  reading processes).** All three drafts honor this.
- **BUILD_PHASES.md (local-only execution, no outbound network as cross-
  cutting criteria).** All three drafts honor this.
- **ROADMAP.md (next milestones).** All three drafts position the package
  as a Step-0 RFC that does not block any near-term milestone.
- **`docs/schema/README.md` (raw tables, privacy_tier, tenant/corpus).**
  Codex explicitly cites the `(source_kind, external_id)` uniqueness
  constraint. Claude and gemini do not. R-003 covers this.
- **`STRIATUM_MEMORY_E2E_BACKLOG.md` (2026-05-15 pivot, RFC 0044
  hardening, no paper promotion as blocker).** All three drafts honor
  the pivot. Claude and codex explicitly cite the backlog; gemini does
  not.
- **`docs/AGENT_CONTEXT_NOTES.md` (operator discipline, generated schema
  docs may lag).** Codex flags the schema-docs-lag note; claude and
  gemini do not. The candidate package as a whole respects the lag.

## 10. Per-Draft Summary

For the synthesizer's convenience, a one-paragraph summary of each draft:

- **claude (≈42 KB, RFC 0050 frame).** The most structurally complete draft.
  Strong on the four-question contract template, the closed projection-family
  vocabulary (six families), the per-family privacy defaults table, the
  rollout order with explicit success criteria, the minimum gate set with
  per-source-family specializations, and the deferrals list. Weak on
  `(source_kind, external_id)` uniqueness (silent) and on operational
  projection families (excludes them). Recommended as the load-bearing
  structural skeleton for the final RFC body.
- **codex (≈32 KB, RFC 0050 frame).** The most detailed draft on contract
  field granularity, identity split, lifecycle states, gate promotion
  ladders, and outcome vocabulary. Best coverage of the
  `(source_kind, external_id)` constraint. Strongest no-egress process
  enumeration. Weakest on tier vocabulary (introduces Tier 4+ without
  reconciling with HUMAN_REQUIREMENTS). Recommended as the field-level
  contract spec and as the gate-promotion model.
- **gemini (≈9 KB, RFC 0050 frame).** The shortest draft. Coherent and
  consistent with the other two on the high-level shape, but missing the
  detail required to be a load-bearing third vote. Recommended as the
  executive-summary section of the final RFC body (the kind of top-of-RFC
  table that orients a reader), not as the technical baseline.

The dossier (codex lane, researcher role) is independent of the three drafts
and is reliable as research artifact. It does not promote anything. It
correctly flags the `(source_kind, external_id)` constraint, the tier
vocabulary mismatch, and the no-egress evidence gap. The synthesizer should
cite the dossier explicitly in the final RFC body where the dossier
identifies prior-art constraints.

## 11. Verdict And Synthesis Path

**Verdict: `accept_with_findings`.** The candidate package is viable for
synthesis. None of the findings is fatal. The synthesizer must, before
producing the final RFC 0050 body, resolve the following in order:

1. R-001 / R-005 (tier vocabulary reconciliation). Add the reconciliation
   subsection or the new `sensitivity_class` field per § 4.2.
2. R-002 (projection-family closed list). Pick one closed initial
   vocabulary and commit to it.
3. R-003 (`(source_kind, external_id)` boundary). Adopt codex's three-part
   identity split and add the corresponding Open Question.
4. R-004 (gate-ID namespace). Pick exactly one prefix uniformly.
5. R-016 (contract template granularity). Adopt codex's template with
   claude's test rider.
6. R-017 (contract test enumeration). Adopt the eight-test union.
7. R-018..R-023 (rollout order, gate ladder, outcome vocabulary, coverage-
   gap gate). Adopt codex's operational additions.
8. R-024..R-027 (missing open questions). Add the four new Open Questions.
9. R-006..R-015 (minor convergent edits). Apply the suggested edits per
   finding.

The synthesizer's output should be a single RFC 0050 body, not a merge of
three drafts. The body should cite the three drafts and the dossier in a
provenance table at the top, follow the structural skeleton of the claude
draft, take the contract-spec detail from the codex draft, take the
executive-summary table shape from the gemini draft, and leave the open
questions per R-028 visible to the operator.

This review does not promote any draft. It does not edit `DECISION_LOG.md`
or the RFC index. It does not authorize implementation. It is a verdict on
synthesis-readiness only.

---

## Appendix A: Finding Index

| Handle | Topic | Affected drafts | Severity |
|---|---|---|---|
| R-001 | HUMAN_REQUIREMENTS tier-vocabulary reconciliation | claude, codex, gemini | high |
| R-002 | Projection-family closed list divergence | claude, codex, gemini | high |
| R-003 | `(source_kind, external_id)` uniqueness boundary | claude, gemini | high |
| R-004 | Gate-ID namespace collision | claude, codex, gemini | high |
| R-005 | Tier 4+ extension beyond HUMAN_REQUIREMENTS | codex | high |
| R-006 | `source_kind` enum-replacement deferral wording | claude, codex | low |
| R-007 | Gemini scope-kept-out missing items | gemini | medium |
| R-008 | No-egress process enumeration completeness | claude, gemini | medium |
| R-009 | No-egress evidence levels | all three | medium |
| R-010 | AI-conversation default tier pinning | codex, gemini | low |
| R-011 | Meeting-transcript split rule | claude only | low |
| R-012 | Calendar default tier | claude, codex | medium |
| R-013 | Third-party extraction policy split | all three | medium |
| R-014 | No-derived-product-leak invariant naming | all three | low |
| R-015 | Generated-product family exclusion explicit | codex, gemini | low |
| R-016 | Contract-template field granularity | claude, gemini | medium |
| R-017 | Contract-test enumeration union | all three | low |
| R-018 | Rollout order convergence | all three | none (no-op) |
| R-019 | Step-1 sub-order (git before build_artifact) | codex, gemini | low |
| R-020 | First non-AI chat adapter remains OQ | all three | low |
| R-021 | Gate-level promotion ladder adoption | claude, gemini | medium |
| R-022 | Gate-outcome vocabulary adoption | claude, gemini | medium |
| R-023 | Coverage-gap gate adoption | claude, gemini | medium |
| R-024 | Missing OQ — tier vocabulary reconciliation | all three | high |
| R-025 | Missing OQ — `(source_kind, external_id)` expansion | claude, gemini | high |
| R-026 | Missing OQ — operational vs evidence families | all three | medium |
| R-027 | Missing OQ — no-egress evidence level | all three | medium |
| R-028 | Open-question carry-forward summary | all three | low |

## Appendix B: Provenance

This review was authored by the **claude** lane of the
`source-ingestion-rfc-research-2026-05-15` multi-agent research workflow,
acting in the **reviewer** role per
`striatum/source-ingestion-rfc-research-2026-05-15/roles/reviewer.md` and the
prompt at `striatum/source-ingestion-rfc-research-2026-05-15/prompts/review.md`.

The review is a proposal-text artifact. It does not edit any source document,
draft, dossier, code, test, migration, RFC index, or decision log. It does not
promote any draft. It does not authorize implementation. The verdict
(`accept_with_findings`) applies to the candidate package's
synthesis-readiness, not to any individual draft and not to RFC 0050 as a
whole.

No network access was used in producing this review. No telemetry was emitted.
All inputs were read from local files on the operator's machine.
