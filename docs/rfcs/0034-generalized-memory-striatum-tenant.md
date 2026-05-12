<a id="rfc-0034"></a>
# RFC 0034: Generalized Memory Scope — Striatum as First Dogfood Tenant

| Field | Value |
|-------|-------|
| RFC | 0034 |
| Title | Generalized Memory Scope — Striatum as First Dogfood Tenant |
| Status | proposal |
| Implementation | none |
| Date | 2026-05-12 |
| Owner | heath |
| Context | `HUMAN_REQUIREMENTS.md` (personal-biography mission, V1-as-validation framing); `BUILD_PHASES.md` (PHASE-0005 serving path); `ROADMAP.md`; `docs/process/multi-agent-review-loop.md`; RFC 0017 (extraction prompt versioning); RFC 0030 (public-dataset entity grounding); RFC 0032 (Claude Code session ingest); RFC 0033 (tenant isolation); `striatum/` workflows and `.striatum/state.sqlite3` gate state |

Decision refs:
  - none yet (proposal)

Review refs:
  - none

Phase refs:
  - PHASE-0001-5 (multi-source ingestion — the Striatum tenant adds new
    sources of the same shape)
  - PHASE-0002 (segmentation + embeddings — same pipeline, different
    chunking taste for source code and structured logs)
  - PHASE-0003 / PHASE-0004 (claims, beliefs, entities — narrower
    vocabulary, mostly derivable from primary sources)
  - PHASE-0005 (`context_for` and serving — accelerated by a workload
    whose ground truth is cheap)

## Summary

Hold the personal-biography mission as the load-bearing scope, and at
the same time treat engram as a **general memory architecture** that
can serve more than one use case. Adopt **Striatum** — the operator's
local multi-agent orchestration and gate-state system — as the
**first dogfood tenant** alongside the personal corpus, running under
the tenant isolation proposed in RFC 0033.

Software-development memory has a much narrower fact band than human
biography: facts are grounded in commits, decision logs, RFCs, code,
CI runs, and Striatum workflow state, which means **claims and
beliefs can largely be derived rather than asserted** and **verified
mechanically rather than adjudicated by hand**. That property makes
it a fast path to a real serving surface — letting us iterate on
latency, context utility, retrieval quality, and the
extraction/consolidation contract on a workload where ground truth
costs cents, before the personal corpus has accumulated the years of
data its own validation will eventually require.

This RFC proposes the scope change. It does not propose a new
architecture. The implementation surface is the union of existing
RFCs (0017 prompt versioning, 0030 entity grounding, 0032 Claude
Code ingest, 0033 tenant isolation) plus a small number of
Striatum-specific ingesters and a Striatum-tenant predicate
vocabulary.

## Mission, restated

`HUMAN_REQUIREMENTS.md` is unambiguous: engram exists to produce **a
complete time-indexed biography of one human life**, queryable at
any point in time, never leaving the operator's machine. That
mission is **unchanged** by this RFC.

What this RFC adds is a framing shift:

- engram-the-architecture (raw evidence → segmentation → embeddings
  → claims → beliefs → entities → serving, all local-first, all
  tenant-scoped) is **general**.
- engram-the-instance, today, is the personal-biography tenant.
- An additional instance — the Striatum tenant — is a **specific
  use case** of the same architecture, scoped to one operator's
  software-development life. It is **part of** that operator's
  biography (every commit they make is part of "what did I work
  on in 2026"); it is simultaneously a **validation vehicle** for
  the architecture as a whole.

This is consistent with the existing "V1 is a validation phase, not
an end state" framing in `HUMAN_REQUIREMENTS.md`. The Striatum
tenant is, in that vocabulary, a **second validation surface**:
narrower domain, faster ground truth, earlier serving path.

What this RFC explicitly does **not** do:

- Repackage engram as a generic SaaS memory product.
- Make engram a "coding agent memory" product at the expense of the
  biography mission.
- Relax local-first by even a query. Striatum runs on the same host,
  in the same Postgres cluster, in its own RFC-0033 tenant. No
  network egress changes.

## Why Striatum is the right first additional tenant

Four properties, in order of weight:

1. **Cheap, verifiable ground truth.** A claim like *"commit
   `4074bc5` introduced `docs/rfcs/0032-claude-code-session-ingest.md`"*
   is checkable in milliseconds against git. *"RFC 0029 was
   promoted to a spec via D080"* is checkable against
   `DECISION_LOG.md`. *"The Phase 4 spec-review workflow gate G
   reached verdict V on date D"* is checkable against
   `.striatum/state.sqlite3`. A meaningful share of the
   Striatum-tenant claim graph is **derivable**, not extracted —
   i.e. produced by a deterministic transform from a primary
   source — and therefore not subject to LLM extraction error.
   The remaining LLM-extracted share (e.g. "this PR fixed
   regression R" inferred from PR prose) sits next to a strong
   verifier corpus, which makes the extraction prompts much
   easier to evaluate.

2. **Forces the serving path early.** Today the agent reading this
   RFC has no in-process recall of *"what did the operator decide
   about predicate vocabulary three weeks ago, and which RFC
   superseded it?"* — it greps `DECISION_LOG.md` line by line.
   A Striatum tenant whose serving path resolves *"what's the
   current state of RFC 0029?"* in a small budget of milliseconds
   is the first PHASE-0005 (`context_for`) consumer that runs
   continuously and complains loudly when latency regresses. The
   personal corpus, by contrast, is queried interactively by a
   human who tolerates seconds; it does not pressure latency.

3. **Stress-tests tenant isolation (RFC 0033) under load.** Two
   tenants sharing one cluster is a hypothesis until two tenants
   actually share it. Running the personal-biography tenant and
   the Striatum tenant side by side validates `search_path`
   scoping, per-tenant migration ledgers, and the operational
   layout described in RFC 0033 against a real workload, not a
   test fixture.

4. **Half the ingest is already proposed.** RFC 0032 (Claude Code
   session history ingest) already covers a major Striatum
   source — the operator's CLI conversations with the agents that
   produced the work. Git ingest, decision-log ingest, and
   Striatum SQLite ingest are small additional ingesters of the
   same shape, slotting onto the existing
   `sources`/`conversations`/`messages` triad under
   `source_kind` extensions.

The shared corollary across all four: **iterating on latency, on
the utility of the served context, and on the extraction /
consolidation contract is cheaper here.** Wins from that
iteration carry back into the personal-biography tenant for free,
because the architecture is the same.

## Striatum-tenant scope

The Striatum tenant is one engram tenant (per RFC 0033) whose
corpus is the operator's software-development life as it
intersects this repository and adjacent agent work.

### Sources

| Source | Source kind | Ingester | Notes |
|--------|-------------|----------|-------|
| Git commits + tree | `git_repo` (new) | new | One row per commit; raw payload = full commit metadata. Per-commit file diffs as derived rows or as JSONB. |
| RFCs, decision log, build phases, process docs (`docs/**/*.md`) | reuse `obsidian` or new `repo_markdown` | new | Per-file ingester with stable `external_id` keyed on git blob hash so re-ingest is idempotent. |
| Pull requests, issues, review comments | `github` (new) | new | GitHub MCP-mediated; out-of-band cache so engram pulls from a local mirror, never live. Local-first preserved. |
| CI / test run outputs | `ci_run` (new) | new | One row per run; raw payload = the JSON the CI emits; content_text = a short human summary. |
| Claude Code session transcripts | `claude_code` (RFC 0032) | RFC 0032 ingester | Already proposed. The Striatum tenant inherits this ingester. |
| Striatum SQLite gate state | `striatum_state` (new) | new | Workflow runs, gate verdicts, agent-lane evidence. Striatum is the system of record; engram is the system of record for *what it means*. |

`source_kind` enum extensions follow the established pattern from
migrations 003 and 004.

### Stability classes

Many Striatum-tenant facts are structurally immutable once
recorded — *the commit happened, the CI run finished, the gate
reached a verdict*. The existing `stability_class` on beliefs
already supports this; the Striatum tenant's belief population
will skew far more `stable` and far less `evolving` than the
personal-biography tenant, which is itself useful data about how
the consolidator behaves under different stability mixes.

### Predicate vocabulary

Striatum-tenant predicates are a **mostly disjoint, much
smaller** vocabulary tuned to software development:

- `introduces(commit, artifact)`, `modifies(commit, artifact)`,
  `removes(commit, artifact)`
- `references_rfc(artifact, rfc_id)`,
  `supersedes(rfc_id, rfc_id)`, `promotes_to(rfc_id, spec_id)`
- `decided_in(decision_id, artifact)`,
  `applies_to(decision_id, phase_id | rfc_id)`
- `passes_gate(workflow_run, gate_id, verdict)`,
  `signed_off_by(artifact, identity)`
- `tests(test_name, symbol)`, `defined_in(symbol, file:line)`
- `caused_by(incident, commit)`,
  `closes_issue(commit | pr, issue_id)`

The exact list is the work of a follow-on RFC; what matters here
is that it is **small, concrete, and largely directly derivable
from primary sources**. The Striatum-tenant extraction prompt is
therefore much shorter, much easier to version (RFC 0017), and
much easier to evaluate (cheap ground truth) than the
personal-biography prompt.

### Entity gazetteer

The Striatum tenant's entities are mostly **the repo's own
artifacts**: files, RFC IDs, decision IDs, phase IDs, workflow
IDs, contributor identities, PR / issue numbers. This is a tiny
private gazetteer compared to RFC 0030's Wikidata / GeoNames
proposal. It can be **built and maintained inside the tenant
itself** without RFC 0030's snapshot-pinned-public-dataset
machinery — though if RFC 0030 ships, the Striatum tenant can
opt into a code-aware public dataset (e.g. a software ecosystem
gazetteer) under the same grant model.

## What this changes (after acceptance)

Only the framing and the work order, not the architecture.

- `HUMAN_REQUIREMENTS.md` gains a short paragraph at the bottom of
  "V1 vs the long arc" noting that the validation strategy now
  includes a **second tenant** (Striatum) chosen because its
  ground truth is cheap. The personal-biography mission and the
  local-first constraints stay verbatim.
- `ROADMAP.md` and `BUILD_PHASES.md` get a cross-cutting note
  that the Striatum tenant runs in parallel to PHASE-0001..0005
  on the personal tenant, **sharing the same phase machinery**
  rather than forking it. The Striatum tenant does not skip
  phases; it traverses them on a different (faster, narrower)
  workload.
- The next concrete RFCs flow from this: a Striatum-tenant
  predicate-vocabulary RFC, a `git_repo` ingester RFC, a
  `striatum_state` ingester RFC, and a serving-path latency RFC
  for `context_for`.

## What this does not change

- **Local-first.** Striatum runs on the operator's machine. Its
  data, its embeddings, its retrieval, and its served context
  stay local. No telemetry, no third-party backups, no
  inference-time network egress. Every constraint in
  `HUMAN_REQUIREMENTS.md` § "Why local-first is load-bearing"
  applies unchanged.
- **The personal mission.** The personal-biography tenant remains
  the project's reason to exist. The Striatum tenant exists
  because it accelerates that mission, not because it
  replaces it.
- **Architecture.** Raw is sacred. Derived is rebuildable. Phase
  ordering holds. No new pipelines.
- **PHASE numbering and gates.** The Striatum tenant runs through
  the same PHASE-0001..0005 sequence, scored on its own gold
  set.

## Phasing

**Phase A — tenant exists.** Land RFC 0033 (tenant isolation) and
spin up an empty `engram_striatum` tenant alongside
`engram_default`. Verifies `search_path` scoping under real
load.

**Phase B — derived-first ingesters.** Land the ingesters whose
output is mechanically verifiable: `git_repo`, `repo_markdown`,
`striatum_state`. Claude Code session ingest (RFC 0032)
plugs in here. **No LLM extraction yet.** At end of Phase B,
the tenant has a fully populated raw-evidence layer queryable
via SQL.

**Phase C — Striatum-tenant predicate vocabulary.** Author the
small predicate set above as a follow-on RFC. Wire it through
the existing extraction / consolidation path with RFC 0017
versioning. Because the vocabulary is small and the ground
truth is cheap, the gold set for Phase C is authored in days,
not weeks.

**Phase D — serving.** First real `context_for` consumer: an
agent (potentially a Claude Code session itself) asks the
Striatum tenant *"what's the current state of RFC X?"* or
*"what changed in `src/engram/db.py` between commit A and
commit B, and why?"* and gets back a citation-bundled context
within a measured latency budget. **This is where latency,
context utility, and reranker work all become real for the
first time.**

**Phase E — evaluation harness.** Lift the Striatum-tenant gold
set and retrieval-quality harness into a reusable shape so the
personal-biography tenant can be evaluated with the same
machinery once its corpus matures. This is the dogfooding
payoff.

## Open questions

- **Does Striatum SQLite become a `source_kind`, or does engram
  consume Striatum as a sidecar?** Proposed: a `source_kind`.
  Striatum is the system of record for *workflow state* (which
  agent ran when, which gate verdict landed); engram is the
  system of record for *what those events mean over time*.
  Treating Striatum state as raw evidence preserves the
  raw-is-sacred contract and lets the consolidator project
  workflow-state facts into beliefs ("RFC 0029 was promoted
  via D080 at time T").
- **One embedder, or a code-aware embedder for the Striatum
  tenant?** Default: same `nomic-embed-text:latest` for both
  tenants. Revisit only if code-symbol retrieval quality
  plateaus and a code-tuned local embedder is genuinely
  better. The embedder must remain local.
- **Chunking strategy for source code.** RFC 0032 proposes
  conversational-turn windows for Claude Code sessions. Source
  code wants symbol-boundary windows (function / class / RFC
  section). Both are window strategies in the existing
  `segments.window_strategy` column; the choice is per-source
  rather than per-tenant.
- **Cross-tenant retrieval.** Should an agent be able to ask
  *"what did I decide in any tenant about predicate
  vocabulary?"* and get a unioned answer? Defaulting to no per
  RFC 0033's "isolation is the default" stance; revisit when
  there is a concrete need.
- **What is the kill criterion for the Striatum tenant?** See
  next section. Stated explicitly because mission drift is the
  real risk.
- **How does this RFC interact with the suspect-autonomous-work
  audit (RFC 0031)?** The Striatum tenant ingests Striatum
  state including the suspect-work workflow runs. Provenance
  flags from RFC 0031 should propagate into the tenant's
  beliefs as `provenance_status = 'quarantined'` or similar,
  so a served context never silently builds on suspect
  evidence.

## Acceptance criteria

This is a scope RFC, so acceptance is a posture decision rather
than a code delivery. The RFC is accepted when:

1. The mission paragraph addition to `HUMAN_REQUIREMENTS.md`
   lands and is reviewed against the local-first contract.
2. `ROADMAP.md` and `BUILD_PHASES.md` carry the cross-cutting
   note that the Striatum tenant traverses the same phases on a
   parallel workload.
3. RFC 0033 (tenant isolation) is accepted and implemented at
   least to "Phase A — tenant exists."
4. The follow-on RFCs named in **Phasing** (Striatum-tenant
   predicate vocabulary, `git_repo` ingester, `striatum_state`
   ingester) have at least proposal-status drafts.
5. `DECISION_LOG.md` records the scope expansion, including the
   kill criterion below.

## Kill criteria

The Striatum tenant is dropped if any of:

- Dogfooding stops accelerating the personal-biography mission
  (e.g. work on the Striatum tenant displaces personal-corpus
  ingest for more than one quarter without producing
  reusable harness or serving-path improvements).
- The serving-path latency, retrieval-quality, or
  extraction-quality results obtained on Striatum demonstrably
  do **not** transfer to the personal tenant (i.e. the
  validation hypothesis fails).
- Operating two tenants on one cluster proves to require
  hostile-multi-tenancy controls (i.e. RFC 0033's threat model
  is wrong in practice), in which case the architectural fix
  belongs in RFC 0033 first, not in a Striatum-specific patch.

Stating these in the RFC, before any code lands, is the
discipline `docs/process/project-judgment.md` calls for: scope
control by pre-committed off-ramp.

## Risks

- **Mission drift toward "coding agent memory."** Mitigated by the
  explicit kill criteria, the verbatim preservation of the
  biography mission, and treating Striatum as a tenant rather
  than a product.
- **Resource competition with personal ingest.** Mitigated by
  RFC 0033's per-tenant scoping; personal-tenant batch jobs and
  Striatum-tenant serving traffic share one Postgres, one
  embedder, and one disk volume, so capacity planning is now
  load-bearing. Document budgets explicitly when serving lands.
- **Scope creep into "agentic IDE."** Out of scope. The Striatum
  tenant is a memory layer that agents consume; this RFC does
  not authorize building agents, editors, or IDE plugins inside
  engram.
- **Provenance contamination from suspect autonomous work
  (RFC 0031).** Mitigated by propagating provenance status as
  first-class belief metadata in the Striatum tenant. A served
  context that cites quarantined evidence must surface that
  fact, not silently bury it.

## Next step

Accept this RFC (or reject it) before any of the follow-on RFCs
are written. The point of stating the scope change first is to
avoid the situation where ingester RFCs accumulate and the
implicit scope drifts without an explicit decision. After
acceptance, the next concrete artifact is the
Striatum-tenant predicate-vocabulary RFC.
