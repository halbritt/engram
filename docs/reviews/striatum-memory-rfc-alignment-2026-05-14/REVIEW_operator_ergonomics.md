author: operator [self-declared: alignment-review-ergonomics]
verdict: needs_revision

## Scope

Recovery operator-ergonomics review for Striatum memory RFC alignment. Scope was
review-only: RFC 0046, RFC 0047, RFC 0048, RFC 0049, the Striatum memory
roadmap, the RFC index, and relevant roadmap/alignment handoffs. No source RFC,
roadmap, index, code, migration, schema doc, Striatum state, publish command,
complete command, or verdict command was edited or run.

The review asks whether operators and implementors can find source evidence,
exact references, omission reasons, disable semantics, proposal/default-off
status, and validation gates without ambiguous interpretation.

## Evidence Reviewed

- `docs/rfcs/0046-striatum-projection-index-schema.md`
- `docs/rfcs/0047-striatum-retrieval-augmentation-boundary.md`
- `docs/rfcs/0048-striatum-context-injection-policy.md`
- `docs/rfcs/0049-striatum-evaluation-gates.md`
- `docs/rfcs/0045-striatum-corpus-contract-v2.md` for upstream omission and
  V2 field assumptions used by RFC 0046-RFC 0049.
- `STRIATUM_MEMORY_ROADMAP.md`
- `docs/rfcs/README.md`
- `docs/reviews/striatum-memory-roadmap-rfcs-2026-05-14/FINAL_SYNTHESIS.md`
- `docs/reviews/striatum-memory-roadmap-rfcs-2026-05-14/FINDINGS_LEDGER.md`
- `docs/reviews/striatum-memory-roadmap-rfcs-2026-05-14/REVIEW_operator_ergonomics.md`
- `docs/reviews/striatum-memory-roadmap-rfcs-2026-05-14/REVIEW_contract_coherence_repair.md`
- `docs/reviews/striatum-memory-roadmap-rfcs-2026-05-14/OPERATOR_DECISION_CONTRACT_REPAIR.md`
- `docs/reviews/striatum-memory-roadmap-rfcs-2026-05-14/OPERATOR_DECISION_ACCEPT_CONTRACT_REPAIR_REVIEW.md`
- Alignment handoffs under
  `docs/reviews/striatum-memory-rfc-alignment-2026-05-14/`, including
  `ALIGN_RFC0046.md`, `ALIGN_RFC0047.md`, `ALIGN_RFC0048.md`,
  `ALIGN_RFC0049.md`, and `ROADMAP_INDEX_CLEANUP.md`.
- Five independent read-only sub-agent ergonomics checks.

## Blockers

- B001: RFC 0046 still leaves projection provenance and authorization fields
  ambiguous for implementors.

  RFC 0046 says every first-class projection table carries common columns unless
  explicitly noted, including `source_capture_id`, `source_item_id`,
  `source_logical_id`, `source_version_id`, and `source_sub_kind`
  (`docs/rfcs/0046-striatum-projection-index-schema.md:147`). It also requires
  future `fetch_reference` implementations to reauthorize the stored projection
  row's `tenant_id`, `corpus_id`, `source_kind`, privacy tier, redaction state,
  and visibility (`docs/rfcs/0046-striatum-projection-index-schema.md:402`).

  The actual table descriptions weaken that contract. `striatum_references`
  may inherit `source_capture_id` through `item_projection_id`
  (`docs/rfcs/0046-striatum-projection-index-schema.md:341`). The embedding and
  embedding-skip tables list retrieval-visible copied fields but omit
  `source_capture_id`, `source_sub_kind`, and any direct `source_kind` column
  (`docs/rfcs/0046-striatum-projection-index-schema.md:683`,
  `docs/rfcs/0046-striatum-projection-index-schema.md:726`). The validation
  expectations then say every projection row cites `source_capture_id`,
  `source_item_id`, `source_logical_id`, hashes, and derivation generation
  (`docs/rfcs/0046-striatum-projection-index-schema.md:1027`).

  From an operator-ergonomics perspective, this is a blocker before promotion or
  implementation handoff. A Striatum agent cannot tell whether source evidence
  and source-kind authorization must be direct columns on every retrieval-visible
  row, inherited through `item_projection_id`, or enforced by mandatory joins.
  The text should choose one rule and make the join/direct-column requirements
  explicit for references, chunks, embeddings, and skip rows.

## Nonblocking Findings

- N001: Proposal/default-off posture is clear enough for workflow execution.
  RFC 0046-RFC 0049 are all `Status | proposal` and `Implementation | none`
  (`docs/rfcs/0046-striatum-projection-index-schema.md:9`,
  `docs/rfcs/0047-striatum-retrieval-augmentation-boundary.md:9`,
  `docs/rfcs/0048-striatum-context-injection-policy.md:9`,
  `docs/rfcs/0049-striatum-evaluation-gates.md:9`). The roadmap says RFC
  0045-RFC 0049 do not authorize implementation, default-on memory, runtime
  changes, or binding architecture without a separate decision
  (`STRIATUM_MEMORY_ROADMAP.md:74`). The RFC index repeats that note
  (`docs/rfcs/README.md:65`).

- N002: RFC 0048 now makes session-disable persistence understandable, but RFC
  0049 does not yet gate the restart/promotion rule. RFC 0048 says session-scope
  disablement is transient to the current operator or agent session and does not
  survive daemon restart unless promoted and recorded
  (`docs/rfcs/0048-striatum-context-injection-policy.md:612`). EG-120 only checks
  that session-scope disable prevents automatic calls for that session and is
  visible in packet metadata or memory status
  (`docs/rfcs/0049-striatum-evaluation-gates.md:861`). Add restart/transient and
  promotion-record cases before treating disable controls as fully validated.

- N003: Status naming needs a small render-contract mapping. RFC 0047 response
  status uses `ok` (`docs/rfcs/0047-striatum-retrieval-augmentation-boundary.md:349`),
  while operator-facing packet labels use `memory: available`
  (`docs/rfcs/0047-striatum-retrieval-augmentation-boundary.md:613`,
  `docs/rfcs/0048-striatum-context-injection-policy.md:307`). Implementors can
  infer `ok -> available`, but the rendering policy should state that mapping.

- N004: Omission reason vocabulary is still partly advisory. RFC 0048 requires
  ineligible results to be omitted with a policy reason code
  (`docs/rfcs/0048-striatum-context-injection-policy.md:261`), but introduces the
  list as "Suggested omission reason codes"
  (`docs/rfcs/0048-striatum-context-injection-policy.md:264`). RFC 0049 expects
  exact omission reasons for malformed, identity-leak, and citation-leak cases
  (`docs/rfcs/0049-striatum-evaluation-gates.md:724`). Before implementation,
  the minimum automatic-injection/audit vocabulary should be closed or have an
  explicit extension mechanism.

- N005: Workflow/job identifiers are exact-reference fields but are
  under-required in citation rendering. RFC 0046 includes `workflow_job_id` and
  `job_id` in `striatum_references`
  (`docs/rfcs/0046-striatum-projection-index-schema.md:364`), and RFC 0049
  requires golden exact-reference coverage for them
  (`docs/rfcs/0049-striatum-evaluation-gates.md:629`). RFC 0047 and RFC 0048
  citation requirements mention run/process/artifact/issue/blocker fields but
  omit workflow/job fields where available
  (`docs/rfcs/0047-striatum-retrieval-augmentation-boundary.md:501`,
  `docs/rfcs/0048-striatum-context-injection-policy.md:408`).

- N006: Roadmap sequencing mostly helps operators, but the phase layout can still
  mislead scaffolding. The roadmap's execution backlog correctly requires RFC
  alignment cleanup, RFC 0044 hardening/EG-000 evidence, and then a separate
  recorded decision before implementation treats RFC 0045-RFC 0049 as binding
  (`STRIATUM_MEMORY_ROADMAP.md:224`). The immediate next step repeats that
  ordering (`STRIATUM_MEMORY_ROADMAP.md:254`). However, the narrative roadmap
  still presents "Phase 7: Add Evaluation Gates" after export, projection,
  retrieval, context integration, and generated products
  (`STRIATUM_MEMORY_ROADMAP.md:211`). Label Phase 7 as gate-spec/evidence before
  routine use, or make the backlog ordering the canonical sequencing hook for
  workflow scaffolds.

- N007: Level 1 manual/raw-only search has a vague quality floor. RFC 0049 allows
  Level 1 to use RFC 0044 raw retrieval while RFC 0045/RFC 0046 remain unaccepted
  (`docs/rfcs/0049-striatum-evaluation-gates.md:248`). The gate matrix says
  EG-070 requires "minimal cited exact/search coverage" for Level 1
  (`docs/rfcs/0049-striatum-evaluation-gates.md:324`), but no concrete Level 1
  checklist is given. This is not a blocker for proposal alignment, but it will
  matter before manual search is scaffolded.

## Deferred Items

- D001: Collapsed `no_data` ergonomics remains an explicit deferred UX choice.
  The earlier operator ergonomics review flagged packet noise from multi-line
  no-data headers
  (`docs/reviews/striatum-memory-roadmap-rfcs-2026-05-14/REVIEW_operator_ergonomics.md:14`),
  and the ledger keeps it deferred
  (`docs/reviews/striatum-memory-roadmap-rfcs-2026-05-14/FINDINGS_LEDGER.md:402`).
  RFC 0048 still requires the status header shape
  (`docs/rfcs/0048-striatum-context-injection-policy.md:304`).

- D002: Stale-memory automatic inclusion remains a policy question, not an
  implementation assumption. RFC 0047's request example sets
  `accept_stale_with_warning: true`
  (`docs/rfcs/0047-striatum-retrieval-augmentation-boundary.md:233`), while stale
  automatic inclusion is deferred in RFC 0047 and RFC 0048
  (`docs/rfcs/0047-striatum-retrieval-augmentation-boundary.md:736`,
  `docs/rfcs/0048-striatum-context-injection-policy.md:750`). Mark examples as
  illustrative if promotion packets reuse them.

- D003: Gate-report artifact location and runnable validation commands are not
  fixed yet. RFC 0049 defines the evidence packet contents
  (`docs/rfcs/0049-striatum-evaluation-gates.md:921`) and defers the durable
  report convention (`docs/rfcs/0049-striatum-evaluation-gates.md:1029`). Roadmap
  Phase 7 names gate categories (`STRIATUM_MEMORY_ROADMAP.md:211`) but not
  commands. This is acceptable for proposal text, but workflow scaffolding will
  need concrete artifact homes and command names.

- D004: Generated memory products remain correctly blocked from Level 2 and
  Level 3 injection until a separate accepted privacy-inheritance, citation, and
  audit contract exists (`docs/rfcs/0049-striatum-evaluation-gates.md:890`,
  `docs/rfcs/0049-striatum-evaluation-gates.md:1001`).

- D005: The roadmap/index cleanup points operators toward RFC 0044 hardening and
  EG-000 evidence, but direct links to the RFC 0044 findings ledger or hardening
  packet would reduce search cost before promotion
  (`STRIATUM_MEMORY_ROADMAP.md:79`, `docs/rfcs/README.md:65`).

## Workflow Friction

- Gemini recovery note: the Gemini ergonomics lane for
  `job_run_169531d5568248ff8f0dfc803d955311_review_operator_ergonomics`
  exhausted model capacity with quota reset in roughly 20h44m and produced no
  artifact. This file is a recovery artifact authored by the operator, not a
  Gemini-authored artifact.

- A pre-existing untracked file was present at the target artifact path when this
  recovery pass started. It was replaced as the requested recovery artifact and
  was not treated as evidence of a successful Gemini lane.

- The first sub-agent launch attempted a full-history fork while also setting an
  explicit explorer role and reasoning effort; the tool rejected that
  combination. The agents were relaunched as non-forked read-only explorers, and
  five independent checks completed without file edits.

- Alignment handoffs recorded path/setup friction that future workflows should
  account for: prompt-named inputs were absent from the prompt-local Striatum run
  path and had to be read from
  `docs/reviews/striatum-memory-roadmap-rfcs-2026-05-14/`
  (`docs/reviews/striatum-memory-rfc-alignment-2026-05-14/ALIGN_RFC0047.md:81`,
  `docs/reviews/striatum-memory-rfc-alignment-2026-05-14/ALIGN_RFC0048.md:81`,
  `docs/reviews/striatum-memory-rfc-alignment-2026-05-14/ALIGN_RFC0049.md:89`).

- Some per-RFC alignment handoffs are stale when read in isolation because
  parallel lanes deferred work that companion lanes later addressed. For example,
  `ALIGN_RFC0049.md` still says RFC 0046 and RFC 0048 alignment remains deferred
  (`docs/reviews/striatum-memory-rfc-alignment-2026-05-14/ALIGN_RFC0049.md:35`),
  while `ALIGN_RFC0046.md` and `ALIGN_RFC0048.md` record those changes as
  addressed
  (`docs/reviews/striatum-memory-rfc-alignment-2026-05-14/ALIGN_RFC0046.md:24`,
  `docs/reviews/striatum-memory-rfc-alignment-2026-05-14/ALIGN_RFC0048.md:29`).
  A final roll-up status would prevent future agents from chasing already-closed
  parallel-lane findings.
