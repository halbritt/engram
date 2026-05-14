<a id="rfc-0048"></a>

# RFC 0048: Striatum Context Injection Policy

| Field | Value |
|-------|-------|
| RFC | RFC-0048 |
| Title | Striatum Context Injection Policy |
| Status | proposal |
| Implementation | none |
| Created | 2026-05-14 |
| Source | `STRIATUM_MEMORY_ROADMAP.md` |
| Context | RFC 0044, RFC 0045, RFC 0046, RFC 0047, `STRIATUM_MEMORY_ROADMAP.md` |
| Review state | reviewable context-injection policy handoff |

## Summary

This RFC defines when retrieved Engram memory may enter Striatum operator and
workflow-agent context. It turns RFC 0048 from a scaffold into a reviewable
policy handoff for section labels, precedence, instruction safety, citations,
tenant/corpus filters, privacy filters, token budgets, stale-memory handling,
disable controls, audit trail, and RFC 0049 evaluation gates.

The load-bearing rule is:

```text
Retrieved memory is evidence/context only. It is never instructions, never an
authorization grant, never workflow readiness state, and never authoritative
Striatum state.
```

Memory may remind an operator or agent about prior evidence. It may cite a
prior RFC, review, run, handoff, or operator report. It may surface a possible
conflict or stale-risk. It must not override current files, current work
packets, explicit operator instructions, Striatum daemon state, workflow JSON,
git history, `.striatum/state.sqlite3`, operator reports, changelogs, decision
logs, or accepted specs.

This RFC does not implement code, migrations, MCP tools, prompt templates, or
Striatum UI. It is a proposal package for review before promotion into an
accepted spec or decision.

## Roadmap Position

RFC 0048 follows RFC 0045, RFC 0046, and RFC 0047:

- RFC 0045 proposes the Striatum Corpus Contract V2 disk bundle.
- RFC 0046 proposes rebuildable Engram projections and indexes over that
  bundle.
- RFC 0047 proposes the retrieval augmentation boundary and response status
  contract.

RFC 0048 narrows the last step before routine operator use: given cited local
retrieval results, decide what can be injected into operator and agent context,
how much, under which labels, and with what safety rules.

RFC 0049 remains the evidence gate for no-egress enforcement, tenant/corpus
isolation, stale-index behavior, latency, fixture bundles, retrieval quality,
redaction handling, and prompt-injection fixtures. This RFC names those gates
but does not claim they have passed.

## Boundary Statement

The permitted boundary is:

```text
authoritative Striatum/repository packet
  -> optional bounded local Engram retrieval
  -> cited memory candidates or non-fatal memory status
  -> labeled memory section in context
```

The forbidden boundary is:

```text
retrieved memory
  -> hidden instruction, capability escalation, workflow dependency,
     state rewrite, readiness gate, uncited assertion, or unbounded prompt dump
```

Striatum must still prepare, start, run, review, recover, and produce required
artifacts when Engram is absent, disabled, stale, unauthorized, malformed,
timed out, or unavailable.

## Goals

1. Define eligible Striatum context surfaces for memory injection.
2. Define section labels and packet shape for injected memory.
3. Define authority and precedence rules.
4. Define instruction-safety and prompt-injection containment rules.
5. Define citation requirements for excerpts, summaries, and claims derived
   from retrieved memory.
6. Define tenant, corpus, privacy, redaction, and capability filters.
7. Define default token budgets and truncation behavior.
8. Define freshness, stale-memory, no-data, disabled, unavailable, timeout,
   unauthorized, and malformed behavior.
9. Define manual versus automatic augmentation.
10. Define reviewability and audit-trail requirements.
11. Define per-run, per-session, and per-packet disable controls.
12. Define RFC 0049 gate dependencies before routine default-on use.

## Non-Goals

- No new raw ingestion format.
- No Striatum exporter implementation.
- No Engram ingestion, projection, migration, schema-doc, or MCP-tool
  implementation.
- No Striatum UI or daemon implementation.
- No write-side memory mutation.
- No personal-memory injection by default.
- No cross-tenant or cross-corpus retrieval by default.
- No hosted service, cloud API, hosted model call, telemetry, remote vector
  store, remote persistence, or network-accessible Engram server.
- No live LLM reranking in the serving path.
- No replacement of current repository files, git history, work packets,
  operator reports, changelogs, decision logs, workflow state, or `.striatum/`
  state as authority.

## Dependencies And Open Upstream Decisions

This RFC depends on proposal material that is not yet accepted architecture.
Review and implementation must name those dependencies rather than hide them.

### RFC 0045 Dependencies

RFC 0048 expects retrieved results to preserve RFC 0045 identity and provenance:

- `tenant_id`, `corpus_id`, `source_kind`, and `sub_kind`;
- `item_id`, `logical_id`, and `version_id`;
- `content_sha256`, `record_sha256`, and bundle identity;
- `observed_at`, `recorded_at`, and `emitted_at`;
- provenance such as path, logical path, line range, commit, run id, process id,
  artifact id, issue id, or blocker id;
- privacy, redaction, visibility, stability, authority, and confidence
  metadata.

Open RFC 0045 decisions that can change RFC 0048 review outcomes:

1. exact per-instance `corpus_id` grammar;
2. stable sources for `instance_id` and `repository_id`;
3. zero-row required files versus manifest-declared omissions;
4. full diff and stdout/stderr export depth;
5. final redaction-state vocabulary;
6. V1 compatibility adapter ownership;
7. fixture bundle selection for RFC 0049.

### RFC 0046 Dependencies

RFC 0048 expects RFC 0046 or its accepted successor to provide retrieval
metadata such as:

- projection generation id and active/superseded state;
- `source_capture_id`, `source_item_id`, `source_logical_id`, and
  `source_version_id`;
- `authority_class`, `stability_class`, `confidence`, `privacy_tier`,
  `redaction_state`, and chunk boundaries;
- exact-reference, structured, lexical, and local pgvector retrieval lanes;
- stale-index and invalidated-active-row health checks.

Open RFC 0046 decisions that can change RFC 0048 review outcomes:

1. generic versus Striatum-specific projection generation table;
2. composite FK versus trigger/service guards for tenant/corpus boundaries;
3. PostgreSQL lexical index strategy;
4. per-corpus pgvector partial indexes;
5. git identity and local-path privacy handling;
6. projection audit shape;
7. semantic or inferred link ownership.

### RFC 0047 Dependencies

RFC 0048 consumes RFC 0047 statuses and timeouts:

```text
ok
no_data
disabled
unavailable
unauthorized
timeout
stale
malformed
error
```

RFC 0048 must not weaken RFC 0047's rules: retrieval is optional, read-only,
local, no-egress, non-authoritative, tenant/corpus scoped, citation-required,
and bounded by timeout.

### RFC 0044 Review Dependencies

The RFC 0044 final synthesis and findings ledger require RFC 0048 to preserve:

- explicit primary-pair semantics;
- `memory.read_cross_corpus` for visible non-primary corpora;
- `memory.read_cross_tenant` for non-primary tenants;
- default personal-memory isolation;
- `fetch_reference` reauthorization;
- visibility as discoverability, not read authority;
- no overclaim of OS-level no-egress evidence before a sandbox probe exists.

## Terms

| Term | Meaning |
|------|---------|
| Injection | Placing a retrieved memory excerpt, summary, status, or citation into Striatum operator or agent context. |
| Automatic augmentation | Retrieval and injection performed by policy during packet assembly after gates and enablement checks. |
| Manual augmentation | Operator-initiated search or fetch whose results enter context only by explicit operator or packet-builder selection. |
| Memory section | A labeled context section containing only retrieved memory and memory status. |
| Primary pair | The Engram-local default `tenant_id` and `corpus_id` pair in the caller token. |
| Current authority | Current repository files, current work packet, explicit operator instructions, Striatum state, and accepted project decisions. |
| Memory candidate | A cited retrieval result that has passed tenant/corpus, privacy, freshness, and citation eligibility checks. |
| Stale memory | Memory whose source or projection is older than known current state, whose index health is stale, or whose freshness metadata exceeds the request policy. |

## Eligible Context Surfaces

Automatic augmentation is policy-based, not blanket prompt enrichment. The only
reviewed purposes are inherited from RFC 0047.

| Purpose | Automatic injection after gates | Manual use | Default memory role |
|---------|----------------------------------|------------|---------------------|
| `operator_startup` | yes, if enabled | yes | Recent relevant state, open risks, prior decisions, and known gaps. |
| `workflow_scaffold` | yes, if enabled | yes | Related RFCs, accepted specs, phase constraints, prior blockers. |
| `packet_prepare` | yes, if enabled | yes | Narrow implementation or author packet context with exact citations. |
| `review_prepare` | yes, if enabled | yes | Prior findings, accepted syntheses, unresolved questions, similar review failures. |
| `blocker_recovery` | yes, if enabled | yes | Prior failed attempts, known friction, recovery notes, logs, and handoffs. |
| `ui_search` | no | yes | Interactive result list. Results are not agent context until selected. |
| `manual_search` | no | yes | Operator-directed recall with richer diagnostics. |

Before accepted RFC 0045-RFC 0048 successors and passing RFC 0049 gates,
automatic injection should remain explicit experimental opt-in. Routine
default-on augmentation is only a target after the upstream contracts are
accepted or promoted and the RFC 0049 Level 3 gates pass for the covered
surfaces. The target default is then automatic augmentation for the primary
Striatum pair on the five non-search purposes above, subject to per-run,
per-session, per-packet, purpose, and operator disable controls.

## Context Eligibility Rules

A retrieval result may enter context only if all of these checks pass:

1. Retrieval is enabled for the run, session, and packet.
2. The purpose is one of the reviewed purposes above.
3. The request names an explicit `(tenant_id, corpus_id)` pair, or uses only
   the sanctioned `striatum/striatum` default.
4. The pair is authorized by Engram-local capabilities through the actual
   serving path, not only helper-level checks.
5. The response echoes the requested authorized pair.
6. The status is `ok`, or `stale` with the request policy allowing stale memory.
7. Every selected result has a citation sufficient for `fetch_reference`.
8. Every selected result has source identity: `sub_kind`, `item_id`,
   `logical_id`, and `version_id`, or a reviewed compatibility-adapter
   equivalent.
9. The result is within the caller's allowed privacy tier and redaction policy.
10. The result is not known-invalidated, not from an inactive projection, and
    not from a stale lower-tier derived row.
11. The result fits the surface budget after citation overhead.
12. Current authority does not contradict the result, or the result is shown
    only as an explicit stale/conflict warning.

Ineligible results must be omitted with a policy reason code in the audit trail.
They must not be silently rewritten into uncited summary prose. The canonical
shape of an omission audit entry, the closed reason vocabulary, and the
extension rule are defined in
[Omission Audit Event Shape](#omission-audit-event-shape) below. RFC 0047
omitted entries on the retrieval wire and RFC 0049 audit reconstruction gates
both reference that definition.

Every projection `raw_payload` value inherits the parent item's
`privacy.privacy_tier`, `privacy.redaction_state`, `privacy.withheld_fields`,
and `visibility` (`visibility.default_visible_to` and
`visibility.requires_capabilities`) as exported by RFC 0045 and projected by
RFC 0046. Context injection must not include excerpts, summaries, citations,
or display fields derived from `raw_payload` that would exceed the caller's
authorized privacy tier, redaction state, or visibility. `raw_payload`-derived
content is injectable only when the upstream RFC 0045/RFC 0046 contract
whitelists the specific field for retrieval exposure and the field's
inherited constraints are within caller authorization; otherwise the result
is ineligible and is omitted with the same policy reason codes used for
above-tier or redacted material. RFC 0049 EG-060 carries the matching gate
fixture.

## Omission Audit Event Shape

This section is the canonical definition for omission entries used by RFC 0047
response `omitted[]` arrays, RFC 0048 packet audit records, and RFC 0049 audit
reconstruction gates (EG-080, EG-110). Other RFCs in this package reference
this section rather than redefining the shape.

Every omitted candidate is recorded as a privacy-safe local audit event. The
event must let a later reviewer reconstruct which candidate was considered,
which retrieval lane and projection generation produced it, how it scored, and
why it was omitted, without leaking source identity above the reviewing
caller's privacy tier.

### Entry Fields

Each omission entry must carry:

```text
candidate_id              opaque request-local id; stable for this request only
selected                  false for omitted entries; true for selected
reason                    omission reason code from the closed vocabulary below
reason_detail             optional short string; must not leak hidden identity
lineage:
  retrieval_lane          exact_reference | structured | lexical | vector
  projection_family       e.g., striatum_items, striatum_chunks
  projection_generation_id
  projection_row_id       when visible to the reviewing tier
  item_projection_id      when visible to the reviewing tier
  chunk_id                when visible to the reviewing tier
  chunk_sha256            when visible to the reviewing tier
  chunk_bounds            line/char/token bounds when visible
  bundle_id               opaque bundle id when visible
  source_kind             when visible to the reviewing tier
  reference_id            when visible to the reviewing tier
  item_id                 RFC 0045 item identity when visible to the reviewing tier
  logical_id              when visible to the reviewing tier
  version_id              when visible to the reviewing tier
ranking:
  rank                    1-based pre-omission rank within the retrieval lane
  score                   raw retrieval score for the lane
  score_breakdown         optional per-input scores
  ranking_profile         identifier for the ranking inputs used
labels:
  freshness               fresh | stale | unknown | current_state_conflict | index_stale
  privacy_tier            integer tier of the candidate
  redaction_state         none | redacted | withheld | synthetic_summary
  authority_class         when visible to the reviewing tier
  stability_class         when visible to the reviewing tier
  confidence              when visible to the reviewing tier
conflict_with:            optional, present for current_state_conflict and
                          stale_rejected with a conflict
  current_authority_kind  packet | repository_path | accepted_decision |
                          striatum_state | operator_instruction
  current_authority_id    `logical_id`, accepted decision id, packet id,
                          repository path, or `null` when not visible to the
                          reviewing tier
```

`candidate_id` is request-local and opaque. It must not be a hash of, or
otherwise derived from, fields the reviewing caller is not authorized to read.
Selected candidates use the same shape with `selected=true` and an empty
`reason`.

### Privacy-Safe Local Audit

Omission audit events are local-only state. They must not be exported to
hosted services, telemetry endpoints, remote caches, or any non-loopback
network destination. Engram-side audit storage and Striatum-side packet
provenance copies both stay inside the same no-egress boundary required of
corpus-reading processes.

Audit entries inherit the maximum privacy tier and redaction constraints of
the candidates they identify. A lower-tier reviewer must receive only the
opaque, redacted, or scrubbed projection of an entry whose underlying
candidate sits above that reviewer's allowed tier. In particular:

- omit or null `reference_id`, `item_id`, `logical_id`, `version_id`,
  `projection_row_id`, `item_projection_id`, `chunk_id`, `chunk_sha256`,
  `bundle_id`, `chunk_bounds`, and any path-shaped detail in `reason_detail`
  when the underlying candidate is above the reviewing tier, unauthorized,
  pair-mismatched, or hidden by redaction;
- omit or null `authority_class`, `stability_class`, `confidence`, source
  time bounds, freshness watermarks, hidden corpus labels, and row counts
  for those entries;
- keep the `candidate_id`, `selected` flag, `reason`, retrieval lane,
  projection family, projection generation id, rank, score, freshness
  label, privacy tier, and redaction state visible so reconstruction can
  still explain that an entry existed and why it was omitted.

Conflict warnings rendered into a packet must use only fields the rendering
caller is authorized to read. The audit entry may still carry the full
`conflict_with` block for higher-tier reconstruction, but lower-tier renders
must redact `current_authority_id` when it would leak a hidden path,
operator-private label, or higher-tier identity.

### Closed Omission Reason Vocabulary

The minimum closed vocabulary used by RFC 0047 omitted entries, RFC 0048
audit trails, and RFC 0049 gate coverage is:

```text
disabled
unavailable
unauthorized
timeout
malformed
pair_mismatch
privacy_tier_exceeded
redaction_withheld
missing_citation
identity_leak
citation_leak
stale_rejected
current_state_conflict
low_score
over_budget
duplicate
unsupported_surface
generated_product_blocked
```

This vocabulary is closed in the sense that implementations must use one of
these codes for every omission in the covered surfaces and may not emit
ad-hoc free-text reasons in the `reason` field. Until RFC 0049 produces
passing gate evidence (EG-060, EG-080, EG-090, EG-110) for each code under
the surfaces it gates, this list is a proposal subject to RFC 0049 review;
codes that gate evidence does not exercise remain proposal-only.

Code semantics:

- `disabled`: retrieval was disabled at run/session/packet/purpose scope.
- `unavailable`: Engram was missing, unhealthy, or could not be reached.
- `unauthorized`: the candidate's pair was not authorized for the caller.
- `timeout`: the candidate arrived after the request timeout.
- `malformed`: the candidate failed schema or invariant validation.
- `pair_mismatch`: the candidate's stored pair did not match the request pair.
- `privacy_tier_exceeded`: the candidate's privacy tier is above the caller.
- `redaction_withheld`: the candidate is `withheld`; only a notice may appear.
- `missing_citation`: the candidate lacks citation fields sufficient for
  `fetch_reference`.
- `identity_leak`: an identity field, instance/repository label, or
  path-shaped field would reveal data above the caller's tier.
- `citation_leak`: a citation, reference payload, line hint, or display
  identifier would reveal an absolute path, operator-private label, hidden
  corpus identity, or higher-tier source identity.
- `stale_rejected`: the candidate exceeded the request freshness policy.
- `current_state_conflict`: the candidate disagrees with current authority.
- `low_score`: the candidate fell below the lane's quality threshold.
- `over_budget`: the candidate did not fit the surface token or result cap.
- `duplicate`: the candidate duplicates a higher-precedence entry.
- `unsupported_surface`: the candidate's surface is not eligible for the
  requested purpose.
- `generated_product_blocked`: the candidate is a generated memory product
  ineligible for Level 2 or Level 3 injection until the separate accepted
  generated-product contract exists.

### Extension Rule

The vocabulary may be extended only through this RFC or an accepted
successor. New codes must:

1. land in this section with a defined semantic;
2. be added to the closed list, not appended ad-hoc by implementations;
3. ship with matching gate coverage in RFC 0049 (or an accepted successor)
   under the surfaces they gate, before the new code is allowed in audit
   reconstruction for those surfaces;
4. preserve the privacy-safe local audit posture above.

Until an extension is accepted, implementations encountering an omission
that does not fit any existing code must use the closest defensible code
plus `reason_detail` (subject to the lower-tier redaction rules above) and
file a follow-up to extend the vocabulary.

## Section Labels And Packet Shape

Injected memory must be visually and semantically separate from instructions.
The default section label is:

```text
Retrieved Local Memory (optional, cited, may be stale)
```

Every memory section starts with a compact status header:

```text
memory: available | disabled | unavailable | unauthorized | timeout | stale | no_data
scope: tenant=<tenant_id> corpus=<corpus_id> purpose=<purpose>
policy: striatum.context_injection_policy.v1
```

If selected memory exists, use this order:

1. `Selected Memory`
2. `Stale Or Conflict Warnings`
3. `Omitted Memory`
4. `No Usable Memory`

If no selected memory exists, include only the status header plus a concise
reason where the surface normally displays memory status. Automatic packet
augmentation should avoid noisy diagnostics; manual search may show richer
diagnostics.

### Memory Item Shape

Each injected item must keep citation and confidence metadata adjacent to the
excerpt or summary:

```text
- <short excerpt or summary>
  citation: tenant=striatum corpus=striatum sub_kind=<kind>
  logical_id=<logical-id> version_id=<version-id> ref=<reference-id>
  path=<logical-path> lines=<start-end-or-null> bundle=<bundle-or-null>
  authority=<authority_class> stability=<stability_class>
  confidence=<value-or-null>
  freshness=<fresh|stale|unknown|current_state_conflict|index_stale|dirty_working_tree>
  dirty_working_tree=<true|false>
```

The `dirty_working_tree` field mirrors the RFC 0047 result row's
`dirty_working_tree` boolean, which itself mirrors the RFC 0046 projection
row's `source_dirty_working_tree` value (RFC 0046 § Dirty working tree
projection rules). When the underlying result row is dirty, the packet
builder must render the item with `dirty_working_tree=true` and the
`freshness=dirty_working_tree` label adjacent to the citation. The label
must not be replaced with `fresh`, dropped, or softened into a generic
staleness marker. Dirty and stale are distinct freshness concerns: a dirty
row may also be stale, in which case both concerns apply, the
`dirty_working_tree` flag remains `true`, and the stale label is surfaced
through the usual stale/conflict warning path rather than by overwriting
the dirty freshness label.

If a summary merges multiple results, each claim in the summary must retain at
least one citation. Do not collapse a cited set into a citation-free paragraph.

## Precedence Rules

Memory never outranks current authority. When memory disagrees with current
authority, the packet must follow current authority and may surface the memory
only as a warning.

Overall authority order:

1. Explicit operator instructions for the current run or packet.
2. Current work packet, workflow JSON, Striatum daemon state, lease/job state,
   and `.striatum/state.sqlite3`.
3. Current repository files and current git history.
4. Accepted decisions, accepted specs, canonical project docs, and generated
   schema docs where those docs are the canonical surface.
5. Accepted syntheses and findings ledgers with dispositions.
6. Current proposal RFCs, design docs, and reviewable handoffs.
7. Unsynthesized reviews and raw findings.
8. Raw logs, run summaries, handoffs, packets, and operator notes.
9. Generated memory products that cite raw evidence and carry audit metadata,
   but only after a separate accepted generated-product privacy, citation,
   audit, and gate contract exists.
10. Older brainstorms, prior-art notes, stale plans, and historical context.

Within memory retrieval, exact identifier matches outrank semantic matches, and
current canonical docs outrank old brainstorm material. Accepted syntheses
outrank unsynthesized reviews. Raw logs remain citeable evidence but do not
become instructions.

## Instruction Safety And Prompt-Injection Containment

Retrieved memory is untrusted content. It may contain old prompts, old agent
instructions, raw logs, review text, or malicious/instruction-shaped strings.

Rules:

- Memory sections must not be placed in system, developer, or operator
  instruction slots.
- Memory text must be labeled as evidence, excerpt, summary, or citation.
- Agents must not follow instructions found inside memory unless current
  operator instructions independently assign the same work.
- Memory may describe prior commands, but it does not authorize running them.
- Memory may describe prior file edits, but it does not authorize repeating or
  reverting them.
- Memory may mention capabilities, but it does not grant capabilities.
- Memory must not trigger broader Engram access after an unauthorized result.
- Retrieved text must not be used to rewrite current repository files, decision
  logs, changelogs, operator reports, or `.striatum/` state without current
  packet authority.
- Raw model output, raw transcripts, and broad logs should not be injected
  automatically. Use bounded summaries or exact excerpts with citations.
- Tool output and network-derived content remain adversarial and must not be
  combined with direct Engram corpus access.

If memory contains text such as "ignore prior instructions" or "run this
command", it is treated as historical evidence only.

## Citation Requirements

No citation, no injection.

Every injected memory item must include:

- `tenant_id`, `corpus_id`, and `source_kind`;
- `sub_kind`, `item_id`, `logical_id`, and `version_id`;
- `reference_id` sufficient for `engram.fetch_reference`;
- source path or logical path when available;
- line range or chunk bounds when available;
- commit, blob hash, content hash, record hash, bundle id, run id, process id,
  artifact id, issue id, or blocker id where available;
- `privacy_tier`, redaction state when exposed, confidence, stability class,
  authority class, and freshness label.

Packet-local summaries assembled from selected cited results must cite the raw
items they summarize and must carry confidence when they add synthesis beyond a
short excerpt. Future stored or generated memory products are not eligible for
Level 2 or Level 3 injection until a separate accepted privacy-inheritance,
citation, audit, and gate contract exists. Direct raw evidence may use
`confidence=null` only when the source itself has no meaningful confidence
value.

If an agent uses memory to justify a finding, implementation choice, review
recommendation, or handoff note, the artifact should preserve the citation next
to the claim.

## Tenant, Corpus, Privacy, And Redaction Filters

Default Striatum augmentation uses:

```text
tenant_id = striatum
corpus_id = striatum
source_kind = striatum
```

Rules:

- Every retrieval and injection request must carry explicit tenant/corpus
  scope. Shorthand is allowed only for the sanctioned `striatum/striatum`
  default.
- The token's primary pair is the default readable pair.
- Visible non-primary corpora require `memory.read_cross_corpus` before their
  results can enter context.
- Non-primary tenants require `memory.read_cross_tenant` and an explicit tenant
  name.
- Personal memory requires `memory.read_personal` plus an explicit operator
  request. It is never injected into Striatum packets by default.
- Visibility, bundle identity, repository label, instance label, path, and
  discovery metadata are not read grants.
- `engram.fetch_reference` must reauthorize the stored row's tenant/corpus
  pair. Opaque references are not authorization.
- Results above the caller's allowed privacy tier are omitted.
- Withheld content may appear only as a deterministic redaction notice when the
  notice itself is allowed by policy. The hidden content must not be implied,
  summarized, or guessed.
- Redacted content must keep its `redaction_state` label.
- Unauthorized and not-found diagnostics should avoid leaking hidden personal
  corpus names, counts, paths, or freshness metadata.
- Every projection `raw_payload` value inherits the parent item's
  `privacy.privacy_tier`, `privacy.redaction_state`, `privacy.withheld_fields`,
  and `visibility` (`visibility.default_visible_to` and
  `visibility.requires_capabilities`) as exported by RFC 0045 and projected
  by RFC 0046. Excerpts, summaries, citations, or display fields derived
  from `raw_payload` that would exceed the caller's authorized privacy tier,
  redaction state, or visibility are forbidden in injected context and are
  omitted with the same policy reason codes used for above-tier or redacted
  material. RFC 0049 EG-060 carries the matching gate fixture.

Manual and automatic augmentation use the same authorization rules.

## Token Budgets And Truncation

Token budgets include headings, status, warnings, excerpts, summaries, and
citations. Implementations may estimate tokens with a local tokenizer or a
conservative character heuristic, but must count citation overhead.

Automatic augmentation hard cap:

```text
min(surface_cap, 25 percent of assembled packet budget)
```

If that cap is below 300 estimated tokens, automatic injection should omit
selected memory and emit only memory status. No automatic memory section may
exceed 2400 estimated tokens without an explicit per-packet operator override.

Default surface caps:

| Purpose | Memory token cap | Result cap | Per-result excerpt cap |
|---------|------------------|------------|------------------------|
| `operator_startup` | 700 | 4 | 250 tokens |
| `workflow_scaffold` | 1000 | 6 | 250 tokens |
| `packet_prepare` | 1400 | 8 | 300 tokens |
| `review_prepare` | 1800 | 10 | 300 tokens |
| `blocker_recovery` | 2200 | 12 | 350 tokens |
| `ui_search` | no packet injection | 20 listed | fetch on demand |
| `manual_search` | no automatic injection | 20 listed | fetch on demand |

Truncation rules:

1. Keep citations attached; never truncate away citation metadata for retained
   text.
2. Deduplicate by `logical_id`, then by near-duplicate excerpt text.
3. Prefer exact identifier matches, current canonical docs, accepted decisions,
   accepted syntheses, and higher-authority classes.
4. Prefer fresh results over stale results when authority is otherwise equal.
5. Preserve at least one conflict/stale warning if memory was omitted because
   current state disagreed.
6. If still over budget, omit lower-precedence items with `over_budget`.

Whole transcripts, raw logs, raw model output, and whole-corpus dumps are never
valid automatic injection. Fetching a full reference is manual or explicit
packet-builder behavior and still obeys privacy and citation rules.

## Freshness And Stale-Memory Handling

Freshness is not naive age decay. Old accepted decisions may remain true, and
fresh logs may be wrong. Freshness policy compares memory metadata with current
authority and projection health.

Freshness inputs:

- RFC 0045 `observed_at`, `recorded_at`, `emitted_at`;
- bundle source time bounds and watermarks;
- RFC 0046 projection generation status and activation time;
- invalidation status and stale-index health checks;
- RFC 0046 `source_dirty_working_tree` state on the projection row, surfaced
  through the RFC 0047 result row's `dirty_working_tree` boolean;
- current repository file state, current git history, and current packet
  content;
- authority class and stability class.

Default behavior:

- Fresh memory can be injected if all eligibility checks pass.
- Stale memory may be injected only with a stale label and only when the request
  policy accepts stale results.
- Stale memory that conflicts with current authority is omitted from selected
  memory and may be shown only as a conflict warning.
- Unknown freshness is allowed only for manual search or for low-risk context
  where the item is explicitly labeled `freshness=unknown`.
- Dirty working-tree evidence must be labeled `freshness=dirty_working_tree`
  with `dirty_working_tree=true`, never relabeled as `fresh`, and never
  collapsed into the generic `stale` label. Dirty status is independent of
  staleness: a dirty row may also be stale, in which case both concerns
  apply, the `dirty_working_tree` flag remains `true`, and stale handling
  follows the usual stale/conflict path without overwriting the dirty
  freshness label.
- V1 raw-only bundles must not be treated as projection-ready for RFC 0046
  surfaces unless a reviewed compatibility adapter supplies the required
  metadata.
- `no_data` is a valid result and must not be converted into a confident
  assertion that no evidence exists outside the requested scope.

Suggested stale labels:

```text
freshness=fresh
freshness=stale
freshness=unknown
freshness=current_state_conflict
freshness=index_stale
freshness=dirty_working_tree
```

## Disabled, Unavailable, Timeout, And Error Behavior

All memory failure modes are non-fatal. The baseline Striatum packet continues.

| Status | Injection behavior |
|--------|--------------------|
| `disabled` | Do not call Engram. Emit status only where memory status is normally shown. |
| `unavailable` | Continue baseline packet. Do not install, fetch, or phone home. |
| `unauthorized` | Omit memory. Do not retry with broader capabilities. |
| `timeout` | Omit late results and continue. Stay within RFC 0047 timeout budgets. |
| `no_data` | Emit explicit no-data status when memory was requested or normally shown. |
| `stale` | Include only if stale is allowed; otherwise treat as no usable memory. |
| `malformed` | Discard the response or affected result. Do not inject partial content. |
| `error` | Continue baseline packet. Do not expose stack traces, raw SQL errors, or secret paths. |

RFC 0047 timeout ceilings remain the default:

- health check: 500 ms;
- search: 2 seconds;
- fetch: 5 seconds;
- total automatic augmentation per packet: 10 seconds.

Automatic retries default to zero. One retry is allowed only for local transient
process startup failure and must stay inside the same total packet budget.

## Manual Versus Automatic Augmentation

Manual augmentation:

- is initiated by the operator or by an explicit packet-builder command;
- may show richer diagnostics and more results;
- still obeys tenant/corpus, privacy, redaction, no-egress, and citation rules;
- does not become agent context until selected or summarized into a memory
  section with citations.

Manual paste-through into Striatum operator or agent packets is still memory
injection. Personal memory, non-primary corpora, non-primary tenants, and
withheld or redacted results may enter a packet only with explicit per-packet
operator or packet-builder selection, current authorization, citation
eligibility, privacy/redaction checks, and audit metadata. Pasted memory remains
evidence only; it does not become an instruction, capability grant, or workflow
readiness signal.

Automatic augmentation:

- runs only for eligible purposes and enabled scopes;
- uses bounded task-focused queries, not entire packets or transcripts as
  retrieval input;
- emits a visible memory status;
- injects only cited, bounded, policy-selected memory;
- stores audit metadata for what was shown and what was omitted;
- must be disableable per run, per session, and per packet.

Disable controls:

```text
run: disable all automatic memory for this Striatum run
session: disable automatic memory for this operator/agent session
packet: disable or override memory for one packet
purpose: disable memory for a purpose such as review_prepare
manual: allow manual search while automatic injection stays disabled
```

Disable state must be explicit in packet metadata or memory status. Silent
disablement makes later review ambiguous.

Session-scope disablement is transient to the current operator or agent session
and prevents automatic Engram calls for that session. It does not survive a
daemon restart unless an implementation explicitly promotes it to run scope or
operator configuration and records that promotion. Disabled automatic memory
must not degrade into hidden manual search, hidden retries, or broader
capability requests.

## Reviewability And Audit Trail

Every automatic memory section should be reconstructable after the fact without
making memory authoritative Striatum state.

Record at least:

- policy version, packet type, purpose, and timestamp;
- Striatum `run_id`, `workflow_job_id`, `job_id`, `session_id`, and `lease_id`
  when available;
- enabled/disabled state and override source;
- request id, query text, filters, tenant/corpus pair, limits, freshness policy,
  timeout, and citation requirement;
- response status and warnings;
- Engram schema/retrieval profile version;
- bundle ids or projection generation ids;
- selected `reference_id`, `item_id`, `logical_id`, `version_id`, and
  projection/chunk ids where available;
- candidate-level selected and omitted entries using the canonical shape from
  [Omission Audit Event Shape](#omission-audit-event-shape) above, including
  request-local `candidate_id`, retrieval lane, projection family, projection
  generation, rank, score, freshness label, privacy tier, redaction state,
  and (for omitted entries) the closed-vocabulary `reason`;
- the `dirty_working_tree` boolean for every selected candidate and for
  every visible omitted candidate, mirrored from the RFC 0046 projection
  row's `source_dirty_working_tree` value and the RFC 0047 result row's
  `dirty_working_tree` field, so audit reconstruction can show which
  injected or omitted items derived from dirty working-tree evidence and
  which derived only from committed Git objects; the boolean inherits the
  parent item's privacy tier and is omitted only when the candidate itself
  is opaque to the reviewing tier under the
  [Omission Audit Event Shape](#omission-audit-event-shape) rules;
- token budget, estimated token use, result counts, and truncation decisions;
- stale/conflict labels and `conflict_with` blocks for conflict-driven
  omissions;
- privacy/redaction labels.

Audit records inherit the maximum privacy tier and redaction constraints of the
selected or omitted candidates they identify, per
[Omission Audit Event Shape](#omission-audit-event-shape). Lower-tier audit
views must use opaque request-local candidate ids for unauthorized,
pair-mismatched, higher-tier, redacted, or otherwise hidden omitted candidates
rather than leaking item ids, logical ids, paths, labels, bundle ids,
source-time bounds, counts, freshness metadata, or corpus inventory.
Reconstruction for a lower-tier caller receives only the redacted or opaque
omission evidence that caller is authorized to see.

Audit records and any audit storage are subject to the same local-only,
no-egress, and tenant/corpus-isolation rules as retrieval projections.
Audit-storage backends must remain on-host and must not introduce a hosted
service, cloud API, remote persistence, telemetry sink, or any other
network-accessible dependency that would transmit audit content off the
machine. The loopback-to-local-runtime exception that RFC 0047 and RFC 0049
EG-020 permit on corpus-reading paths does not authorize remote audit egress;
loopback access is allowed only for local-runtime audit consumers that
themselves carry paired no-egress evidence. This restates the audit-storage
constraint that RFC 0049 EG-110 enforces at gate level so it is not lost
when an implementer reads only this policy.

Striatum may preserve a per-run copy of the injected section as provenance for
what an operator or agent saw. That copy is not readiness state, not a future
retrieval cache authority, and not a substitute for current repository reads.

## RFC 0049 Gate Dependencies

Routine default-on automatic injection is blocked until RFC 0045, RFC 0046, RFC
0047, and RFC 0048, or accepted successors, are accepted or promoted and RFC
0049 provides or requires passing evidence for:

1. no-egress sandbox probe for corpus-reading paths;
2. tenant/corpus isolation through actual service and MCP paths;
3. primary-pair, cross-corpus, cross-tenant, and personal-memory negative tests;
4. `fetch_reference` reauthorization and unauthorized/not-found collapse;
5. stale-index detection and invalidated-active-row checks;
6. latency gates for operator startup and packet augmentation;
7. deterministic V2 fixture bundle and multi-corpus fixture;
8. golden retrieval queries with expected references;
9. malformed, uncited, pair-mismatched, and redacted-result fixtures;
10. prompt-injection fixtures proving memory text is not treated as
    instructions;
11. audit-trail reconstruction test for at least one automatic packet;
12. disable-control tests for run, session, and packet scopes.

Manual search can be available earlier as explicit operator action if it remains
local, read-only, cited, and scope-limited. Manual search of source evidence
does not authorize generated memory products, automatic packet insertion, or
manual paste-through that bypasses the injection, privacy, citation, and audit
rules above.

## Review Requirements

Use the multi-agent review loop before promotion. The review packet should
include this RFC, RFC 0045, RFC 0046, RFC 0047, the RFC 0044 final synthesis,
the RFC 0044 findings ledger, and this RFC's handoff artifact under
`docs/reviews/rfc0048-striatum-context-injection-policy/`.

Required review lanes:

- operator ergonomics and context-quality review;
- provenance and truthfulness review;
- prompt-injection and instruction-safety review;
- tenant/corpus and privacy-boundary review;
- Striatum runtime-independence review;
- packet-budget and truncation review;
- RFC 0049 gate-readiness review.

Reviewers should treat as blockers any rule gap that would allow uncited memory,
personal memory by default, hidden capability escalation, current-state
override, workflow dependency on Engram, stale low-tier retrieval, unbounded
prompt dumps, or instruction-shaped retrieved text becoming active
instructions.

## Acceptance Criteria

- The RFC states that retrieved memory is evidence/context only, never
  instructions or authoritative Striatum state.
- Eligible context surfaces and manual versus automatic augmentation are
  defined.
- Manual paste-through is treated as explicit cited memory injection, not a
  bypass around packet policy.
- Section labels, memory item shape, status labels, and the canonical
  omission audit event shape (including the closed reason vocabulary, the
  extension rule, lineage fields, ranks/scores, and privacy-safe local audit
  posture) are defined and referenced by RFC 0047 and RFC 0049.
- Current authority outranks retrieved memory, and current canonical docs
  outrank stale brainstorms.
- Accepted syntheses outrank unsynthesized reviews.
- Instruction-safety and prompt-injection containment rules are explicit.
- Every injected item must carry citations sufficient for `fetch_reference`.
- Tenant/corpus, primary-pair, cross-corpus, cross-tenant, personal-memory,
  privacy-tier, redaction, and visibility rules are explicit.
- Token budgets and truncation behavior are bounded per surface.
- Freshness and stale-memory behavior are explicit.
- Disabled, unavailable, unauthorized, timeout, stale, malformed, no-data, and
  error behavior are non-fatal and visible.
- Audit-trail fields are named.
- Audit-trail privacy inheritance and lower-tier opaque omission behavior are
  named.
- Per-run, per-session, and per-packet disable controls are required.
- Session-disable persistence semantics are stated.
- RFC 0049 gates and accepted/promoted upstream RFC successors are required
  before routine default-on automatic injection.
- Generated memory products remain blocked from Level 2 and Level 3 injection
  until a separate accepted privacy-inheritance, citation, audit, and gate
  contract exists.
- Upstream dependencies and open decisions from RFC 0045, RFC 0046, and RFC
  0047 are named rather than assumed accepted.

## Deferred Questions

1. Exact accepted `corpus_id` grammar and display label rules depend on RFC
   0045.
2. Exact projection generation and chunk identifiers depend on RFC 0046.
3. Exact Striatum CLI/UI names for disable controls belong to Striatum
   implementation planning.
4. Whether routine automatic injection is default-on for all five non-search
   purposes or only selected workflows should be validated by RFC 0049 latency
   and operator-ergonomics evidence.
5. Whether stale memory should be automatically included for
   `operator_startup` or only for `review_prepare` and `blocker_recovery`
   needs ergonomics review.
6. Which separate accepted privacy-inheritance, citation, audit, and gate
   contract will permit generated memory products to enter future injection
   remains deferred; until then they cannot enter Level 2 or Level 3 injection.
7. Whether memory-section citations should be inline text only or also a
   structured sidecar depends on the future packet format.
