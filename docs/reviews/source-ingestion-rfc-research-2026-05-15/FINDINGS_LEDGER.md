# Source Ingestion RFC Research Findings Ledger

Lane: codex
Role: ledger
Workflow: `source-ingestion-rfc-research-2026-05-15`
Date: 2026-05-15
Status: proposal-review ledger only

This ledger normalizes the independent review findings for the source-ingestion
RFC research workflow. It is not RFC body text, does not promote RFC 0050, and
does not edit the source proposal, drafts, prior-art dossier, decision log, RFC
index, code, tests, migrations, or Striatum state.

## Inputs Read

- Role definition:
  `striatum/source-ingestion-rfc-research-2026-05-15/roles/ledger.md`
- Task prompt:
  `striatum/source-ingestion-rfc-research-2026-05-15/prompts/findings_ledger.md`
- Source design:
  `docs/design/source-ingestion-expansion-proposal-2026-05-15.md`
- Reviews:
  `docs/reviews/source-ingestion-rfc-research-2026-05-15/REVIEW_privacy_boundary.md`
  and
  `docs/reviews/source-ingestion-rfc-research-2026-05-15/REVIEW_project_judgment.md`
- Project canon named by the task:
  `AGENTS.md`, `README.md`, `HUMAN_REQUIREMENTS.md`, `SPEC.md`,
  `BUILD_PHASES.md`, `ROADMAP.md`, `docs/schema/README.md`,
  `STRIATUM_MEMORY_E2E_BACKLOG.md`, and `docs/AGENT_CONTEXT_NOTES.md`
- Additional canon read because `AGENTS.md` requires it:
  `DECISION_LOG.md`

## Review Verdicts

| Review | Lane | Role | Normalized Verdict |
|---|---:|---:|---|
| `REVIEW_privacy_boundary.md` | claude | reviewer | `accept_with_findings` |
| `REVIEW_project_judgment.md` | gemini | reviewer | `accept_with_findings` |

Normalized package verdict: **accept_with_findings**.

Verbatim verdict lines recorded from the reviews:

```text
REVIEW_privacy_boundary.md: Verdict | **accept_with_findings**
REVIEW_project_judgment.md: Status | Review complete; verdict: `accept_with_findings`
REVIEW_project_judgment.md: **Verdict:** `accept_with_findings`
```

## Disposition Rules

- Default disposition is **accepted** when a finding appears in only one review
  or the reviews materially agree.
- Disposition is **needs_operator_decision** when the reviews recommend
  conflicting outcomes or when the normalized finding is explicitly a policy
  fork that the synthesizer should not silently decide.
- No findings are marked **declined**.
- No findings are marked **deferred** except where the accepted action is to
  preserve an open question for a later operator decision.

## Normalized Findings

| Ledger ID | Severity | Source Handles | Normalized Finding | Disposition | Follow-Up For Synthesizer |
|---|---:|---|---|---|---|
| SI-L-001 | High | Privacy R-001, R-005, R-024; Judgment R-001 | Privacy tier vocabulary is unresolved. The drafts use `privacy_tier` partly as a sensitivity scale, while `HUMAN_REQUIREMENTS.md` defines tiers by audience and lifecycle. Codex's Tier 4+ language also collides with posthumous-handoff semantics. The judgment review recommends stricter defaults; the privacy review requires an explicit vocabulary reconciliation. | needs_operator_decision | Add a "Tier vocabulary reconciliation" section and an open question. Present the two viable paths: re-anchor `privacy_tier` to the audience/lifecycle scale, or introduce a separate `sensitivity_class`. Do not silently assign health, finance, biometrics, exact coordinates, or contacts to Tier 4+ without resolving the scale. |
| SI-L-002 | High | Privacy R-002, R-026; Judgment R-002 | Projection-family vocabulary diverges. The privacy review recommends Claude's smaller evidence-family set plus a separate operational band for `coverage_gap` and `source_audit`; the judgment review recommends the more granular Codex vocabulary. | needs_operator_decision | Pick one closed initial vocabulary, or present the fork as an operator decision. The final RFC must not leave projection families open-ended. If operational families are split from evidence-shape families, name both bands explicitly. |
| SI-L-003 | High | Privacy R-003, R-025 | The current `(source_kind, external_id)` uniqueness boundary may not survive multi-repo or multi-account importers under tenant/corpus separation. | accepted | Adopt the Codex three-part identity split: `source_instance_id`, item identity keys, and logical identity keys. Add an open question on whether `sources` uniqueness must expand to `(tenant_id, corpus_id, source_kind, external_id)` before multi-repo or multi-account adapters land. |
| SI-L-004 | High | Privacy R-004; Judgment R-004 | Evaluation gate ID namespace collides across drafts and risks confusion with RFC 0049 gate IDs. The reviews disagree on the preferred prefix: privacy recommends `EG-SI-NNN`; judgment recommends `EG-Sxxx`. | needs_operator_decision | Pick one namespace and use it uniformly. The ledger recommendation is to preserve the disagreement visibly for synthesis rather than choosing inside the ledger. |
| SI-L-005 | Low | Privacy R-006 | Scope-kept-out wording around `source_kind` enum replacement is inconsistent. | accepted | Use precise wording: do not replace the current closed enum in the first implementation slice unless enum churn becomes a measured migration burden. Put this in a dedicated Scope Kept Out section. |
| SI-L-006 | Medium | Privacy R-007 | Gemini's scope-kept-out section omits enum timing, cross-tenant projection rules, and bidirectional sync. | accepted | Expand the synthesized deferrals to match the Claude/Codex baseline so omissions are not read as permission. |
| SI-L-007 | Medium | Privacy R-008 | No-egress process coverage is incomplete in the shorter drafts. | accepted | Adopt Codex's complete corpus-reading process list: importer, validator, projection worker, embedding stage, retrieval service, packet builder, evaluator, and any MCP serving path. |
| SI-L-008 | Medium | Privacy R-009, R-027 | No-egress gate evidence needs levels. Loopback checks and monkeypatched sockets are weaker than OS-level no-egress proof. | accepted | Add a no-egress evidence-level open question and gate text covering at least two levels: monkeypatched-socket evidence and sandboxed-process-egress evidence. Require the stronger level before any source family becomes default-on extraction. |
| SI-L-009 | Low | Privacy R-010 | AI-conversation default tier should not drift during this RFC. | accepted | Pin ChatGPT/Claude/Gemini to current behavior, Tier 1 as currently implemented, and leave user-configurable promotion as an open question. |
| SI-L-010 | Low | Privacy R-011 | Meeting transcripts need a machine-checkable split between solo/operator-only and third-party participant content. | accepted | Add a source-contract field such as `participant_third_party: true/false`; use it to control default privacy and extraction eligibility. |
| SI-L-011 | Medium | Privacy R-012 | Calendar defaults differ; calendars often include third-party contact, location, and sensitive schedule data. | accepted | Use a stricter calendar default in the synthesized proposal, with explicit per-calendar opt-down only when the calendar is operator-only and low sensitivity. |
| SI-L-012 | Medium | Privacy R-013 | Human communication extraction must remain off by default and needs both mechanism and policy. | accepted | Combine Claude's mechanism with Codex's policy: contract field, CLI opt-in flag, `describe-corpus` surfacing, and a separate third-party privacy policy before Step 3 extraction. |
| SI-L-013 | Medium | Privacy R-014; Judgment R-003 | Derived products can leak evidence if summaries, packets, OCR/captions, or biographies do not inherit source privacy and citation/audit requirements. | accepted | Include the "no-derived-product-leak" invariant explicitly. Tie it to AL-D004 / generated-product contract work before generated products are treated as memory artifacts. |
| SI-L-014 | Low | Privacy R-015 | `generated_product` should be explicitly excluded from the v1 projection vocabulary until the generated-product contract exists. | accepted | Add a deliberate exclusion subsection for `generated_product` and `belief_projection` style families. |
| SI-L-015 | Medium | Privacy R-016 | Source-contract field granularity should be load-bearing, not only illustrative. | accepted | Use Codex's richer contract template as the baseline, including identity splits, lifecycle states, extraction eligibility, provenance fields, and rebuild policy. Use Gemini's shorter shape only as summary/orientation. |
| SI-L-016 | Low | Privacy R-017 | Contract-test enumeration should be unified. | accepted | Adopt the union test set: contract validator, idempotent re-import, changed-raw-hash conflict, raw immutability, projection rebuild, no network access, privacy inheritance, third-party extraction off by default, and exact-reference citation. |
| SI-L-017 | Info | Privacy R-018 | Rollout order is convergent and defensible. | accepted | Preserve the sequence: contract/taxonomy, project sources, project notes, exported communication logs, life/observation sources, then live capture. |
| SI-L-018 | Low | Privacy R-019 | Step 1 needs a sub-order. | accepted | State the Step 1 order as git first, build artifacts second, Striatum alignment third. |
| SI-L-019 | Low | Privacy R-020; Judgment R-005 | First non-AI chat adapter choice is unresolved. The privacy review says keep it an open question; the judgment review recommends `mbox`. | needs_operator_decision | Carry this as an explicit open question. Include `mbox` as a strong candidate and record the competing criterion: simplest local file export with good fixtures and clear third-party privacy handling. |
| SI-L-020 | Medium | Privacy R-021 | Gate-level promotion ladder is useful and missing from shorter drafts. | accepted | Adopt Level 0/1/2/3 source-family promotion, with Level 3 requiring all required gates to pass before routine/default enablement. |
| SI-L-021 | Medium | Privacy R-022 | Gate outcome vocabulary needs a partial-pass state. | accepted | Adopt Codex's outcome vocabulary, including `accepted_with_scope_limit`, so partial but bounded evidence does not get flattened into pass/fail. |
| SI-L-022 | Medium | Privacy R-023 | Coverage gaps need gate coverage because biography-scale recall must represent missing data explicitly. | accepted | Add a coverage-gap/lifecycle gate. If `coverage_gap` is not an evidence projection family under SI-L-002, make it part of the operational family band. |
| SI-L-023 | Low | Privacy R-028 | Open questions should be carried forward as first-class synthesis output. | accepted | Carry forward the six convergent open questions plus the four added by privacy review: tier vocabulary, unique constraint expansion, operational vs evidence projection families, and no-egress evidence level. |

## Open Questions To Preserve

The synthesized RFC should carry these questions visibly rather than burying
them as prose:

1. Should patch bodies be retained as raw evidence by default, retained only
   by opt-in, or represented as metadata and diff stats only?
2. Should build logs be copied into a managed content-addressed store, or
   referenced by path and content hash?
3. How should the source contract reconcile `privacy_tier` with
   `HUMAN_REQUIREMENTS.md`: re-anchor `privacy_tier`, or add
   `sensitivity_class`?
4. When should the closed `source_kind` enum be supplemented or replaced by a
   source registry?
5. Which local export format should be the first non-AI chat adapter?
6. What third-party privacy policy must exist before human communication
   extraction can be enabled?
7. Should contract storage start as YAML/docs plus tests, a database table, or
   both?
8. Should `sources` uniqueness expand to include `tenant_id` and `corpus_id`
   before multi-repo or multi-account importers land?
9. Should `coverage_gap` and `source_audit` be projection families or a
   separate operational band?
10. What no-egress evidence level is required before a source family can become
    default-on?

## Synthesizer Action Checklist

- Resolve or surface the four operator-decision items: SI-L-001, SI-L-002,
  SI-L-004, and SI-L-019.
- Use the Claude draft as the likely structural skeleton, Codex for detailed
  contract/gate mechanics, and Gemini for concise top-level framing, matching
  the privacy review's synthesis path.
- Keep the RFC proposal-only: do not update `DECISION_LOG.md`, do not update
  the RFC index, and do not authorize implementation from this ledger.
- Preserve Engram's core constraints throughout: local-only acquisition, no
  outbound network from corpus-reading processes, immutable raw evidence,
  rebuildable projections, provenance/citation, privacy inheritance, and
  source-family extraction gates.

## Ledger Provenance

| Field | Value |
|---|---|
| Producing lane | codex |
| Producing role | ledger |
| Artifact path | `docs/reviews/source-ingestion-rfc-research-2026-05-15/FINDINGS_LEDGER.md` |
| Network access | Not used |
| Write scope used | This file only |
