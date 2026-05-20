# Roadmap (Owner Actions)

> What I need to do, in order. Update this when status changes.
> Default to working through these in sequence — convergence happens by
> finishing the prior step, not by parallelizing.

## Right now

**Step 5A: Build the synthetic context-eval e2e harness.** Real owner chat
history has too many ambiguous proper nouns to be the first reliable eval
substrate. Use synthetic evidence, expected facts, and local public-entity
grounding rows to prove `context_for`, citation, gap, and
`engram.ground_entity` behavior end to end. Done when `make e2e-context-synthetic`
passes.

**Step 5B: Author the owner gold set.** 25–50 entries via GOLD_SET_TEMPLATE,
against the now-extant claims and beliefs, after the synthetic harness is
stable. *Trap to watch:* `expected_facts` come from my real-life answer, not
from what extraction produced. Reference evidence by content, not by id. Use
local grounding evidence for ambiguous proper nouns instead of making the model
guess whether a name is a person, product, place, or organization.

**Architecture follow-up track:** execute
`ARCHITECTURE_RECOMMENDATION_EXECUTION_PLAN_2026-05-16.md` as the active
roadmap supplement. Do not expand RFC 0050 Stage 3+ source families until the
thin, cited, no-egress `context_for` path has been exercised against the
owner-authored gold set. A0-A9 now have working code for the narrow serving
path, generic evidence/reference projection, and local-only grounding
substrate. Generated products, default-on or extraction-affecting network
grounding, high-risk source families, and A10/A11 implementation remain
separately gated.

## Already done

- Step 1: principle review → HUMAN_REQUIREMENTS.
- Step 2: ingestion-blocking open questions → privacy_tier defaults Tier 1 (D019); posthumous policy in HUMAN_REQUIREMENTS.
- Step 3: V1 re-pass against principles → V1_SYNTHESIS_DELTAS, DECISION_LOG D016–D022.
- Step 4A: D026 pre-Phase-2 adversarial round → Gemini + Opus reviews,
  synthesis, DECISION_LOG D027-D033.
- Step 4B: Full Phase 2 AI-conversation segmentation + embedding run.
  7916/7916 conversations have active segment generations across ChatGPT
  (3437), Claude (78), and Gemini (4401); 11266 active segments are
  embedded (last activation 2026-05-08).
- Step 4C: Phase 3 claim extraction + belief consolidation, primary run.
  11169/11340 expected extractions succeeded (149 active segments without
  an extraction remain, plus 22 failed extractions to revisit). 43812
  claims, 42558 beliefs (last extraction 2026-05-07). The residual
  149-segment gap and the 22 failed extractions are minor cleanup; they
  do not block gold-set authoring.
- Architecture follow-up A0-A9 (2026-05-17): baseline/freeze, drift repair,
  unified retrieval hit contract, non-capture `fetch_reference`, executable
  no-egress probe/run wrapper, minimal personal `context_for`, fixture context
  eval runner, and context event/snapshot/feedback foundation with warm
  snapshot lookup, Phase 4 review-action memory events, MCP `context_for`,
  packet-policy integration, generic evidence/reference indexing for current
  sources, and local-only MCP entity grounding.

## Up next, in order

### Architecture follow-up queue (2026-05-16)

These items come from
`ARCHITECTURE_RECOMMENDATION_EXECUTION_PLAN_2026-05-16.md`. Work them in
order; keep changes small and test-backed.

**A0: Freeze and baseline — done.** Record the baseline commit/test status, make
Stage 3+ source-family expansion explicitly out of scope, and separate any
pre-existing failures from new work.

**A1: Repair operational drift — done.** Add the direct `PyYAML` dependency,
regenerate schema docs, align RFC 0046-0052 header/index status where needed,
reconcile stale backlog/report text, and add a lightweight authority-lint
checklist or script.

**A2: Unify the retrieval result contract — done.** Define one `MemoryHit` /
`ReferenceHit` shape across Striatum, git, build-artifact, and Markdown exact
refs; make packet building, citations, audits, and reference fetching consume
that shape.

**A3: Make no-egress executable — done.** Add `engram no-egress probe`,
`engram no-egress run -- <command>`, `make no-egress-smoke`, and honest
`unsupported` reporting when OS enforcement is unavailable.

**A4: Build minimal personal `context_for` — done.** Ship the smallest useful
read-only compiler over pinned/current beliefs, recent signals, exact refs,
citations, policy withholding, and explicit gaps. No live LLM and no network
egress. The MCP stdio surface now also exposes guarded `engram.context_for`
after explicit `memory.read_personal` authorization.

**A5: Build the first gold-set eval loop — synthetic e2e harness in progress;
real run waits on Step 5B.** Add `engram eval context` over
human-authored expected facts, stale suppressions, required gaps, citation
coverage, and token-waste metrics. The public synthetic e2e dataset lives at
`tests/fixtures/context_eval/synthetic_e2e/`; it seeds beliefs, captures, and
local public-entity grounding rows, then runs the real CLI/compiler path and
`engram.ground_entity` local lookup. Real evals stay local/private. D087 accepts
the current eval item schema; the real private dataset lives outside the repo
and is discovered via `--dataset-path` or `ENGRAM_EVAL_DATASET_PATH`.

**A6: Add events, snapshots, and feedback — serving slice done.** Add `memory_events`,
`context_snapshots`, and `context_feedback`; make context serving refreshable,
auditable, and compatible with eval versioning. Implemented: append-only
tables, memory events, cold snapshot persistence, warm snapshot lookup,
`context_snapshot_refreshed` events, feedback insertion helper, and sanitized
Phase 4 review-action `belief_changed` events. Still to do later: source
import, projection, entity-resolution, and broad invalidation policy coverage.

**A7: Centralize policy — narrow serving/review slice done.** Move privacy/sensitivity decisions into one policy
module used by packets, `context_for`, review surfaces, and future exports;
persist meaningful withhold/omit reasons. Implemented for `context_for`,
`MemoryService.build_packet`, the shared interview/bench-review web tier guard,
and the Phase 3 interview export tier filter. Broader future exports and
sensitivity dashboards remain later work.

**A8: Generalize evidence and reference indexing — narrow substrate done.**
D094 authorizes the RFC 0051 implementation slice: migration 022 adds
`evidence_items` / `evidence_refs`, `src/engram/evidence.py` rebuilds the
projection for current supported sources, `engram evidence refresh-index` /
`make evidence-refresh` expose the rebuild, and exact-reference search reads
the generic index before source-specific fallback. Generated products still
need a downstream spec from RFC 0051 before they become retrieval-visible
(D089).

**A9: Build entity identity review — local grounding substrate done.** D094
authorizes the RFC 0052 implementation slice: migration 023 adds append-only
`entity_grounding_evidence` and `entity_identity_review_actions`, and MCP stdio
now exposes authorized local-only `engram.ground_entity`. Remote grounding fetch
runtime behavior and review UI remain separately gated. RFC 0053 now captures the
proposal-level network/process boundary between corpus-reading claim extraction
and any grounding broker, grounding LLM, or future network-capable broker/fetch
adapter. The 2026-05-18 Striatum review kept RFC 0053 proposal-only and made
the pre-runtime blockers explicit: exact entity-surface network queries from
extractor-originated requests, persisted grant verification, separate broker
credentials, append-only request/response/grant/link audit, and a dedicated
claim-grounding synthetic e2e gate before grounding may affect extraction.
The starter gate now exists as `make e2e-claim-grounding-synthetic`; it is
separate from `make e2e-context-synthetic` and exercises request, minimized
network dispatch, response, denial, ambiguity, fake granted-broker, poisoned
public-evidence, and no-live-network paths.
The runtime scaffold now also exists: migration 024 adds append-only
claim-grounding request/grant/dispatch/response/link sidecars,
`src/engram/claim_grounding_runtime.py` records them with append-only grant
lifecycle verification, `src/engram/claim_grounding_broker.py` provides a local
broker with optional sidecar persistence and injected-adapter-only network
behavior, `src/engram/claim_grounding_network.py` adds disabled configured
generic HTTP and Tavily search-adapter scaffolds, and local-only CLI/MCP
surfaces are available. Tavily is opt-in via
`ENGRAM_CLAIM_GROUNDING_SEARCH_PROVIDER=tavily` and
`ENGRAM_CLAIM_GROUNDING_TAVILY_API_KEY`; the adapter is fixed to Tavily's HTTPS
Search API and broker invocation requires persisted sidecars plus a
latest-approved persisted grant before any network call. The CLI product
surface can list exact draft grants and append approve, deny, and revoke rows.
`src/engram/claim_grounding_integration.py` adds disabled extraction-adjacent
sidecar emission. `make e2e-claim-grounding-runtime` is the current gate. The
RFC 0054/0055 operator command names and gate inclusion are wired as
`engram entity-grounding draft`, `engram entity-grounding process-approved`, and
`make e2e-entity-grounding`; the RFC 0054 batch worker and RFC 0055
materializer are implemented and covered by the runtime gate. The 2026-05-19
Striatum hardening pass added byte-exact entity-surface query validation,
materializer-side public URL filtering, query privacy-tier preservation on
evidence-attachment review actions, and
`ENGRAM_ENTITY_GROUNDING_BROKER_DATABASE_URL` for broker-authority
materializer runs. The local provisioning surface now exists as
`make provision-grounding-broker` / `make check-grounding-broker` with the
runbook at `docs/runbooks/grounding-broker-role.md`. The local long-running
broker workflow is scaffolded as `engram entity-grounding broker-daemon` plus
`make grounding-broker-daemon`, documented in
`docs/runbooks/grounding-broker-daemon.md`; it requires the broker DSN, uses a
per-iteration advisory lock, and avoids re-processing grants that already have a
dispatch audit row. The matching Striatum workflow scaffold is
`striatum/entity-grounding-broker-daemon-2026-05-19/workflow.json`; run
`run_ecf126b2e6234ae3b54958d8471e5e56` completed with final review
`accept_with_findings`. The residual follow-up scaffold is
`striatum/entity-grounding-broker-daemon-followups-2026-05-19/workflow.json`;
it splits durable dispatch/concurrency, retry/cooldown policy, production
daemon packaging, CLI typecheck debt, and review/claim-use gate work into
parallel lanes before docs, verification, synthesis, and final review. Still
gated until that follow-up work or later decisions land: richer review UI,
production deployment packaging for the broker process, bounded retry/cooldown
behavior, durable crash-safe dispatch claiming, and evidence that grounding
improves extraction/eval quality enough to affect claim content.

**A10: Design backup, keys, and Tier 5 destruction — proposal drafted.** Accept
a local encrypted backup/restore/key hierarchy and Tier 5 destruction design
before durable high-risk source expansion. D091 says this is not a hard blocker
for A8/A9 narrow substrate work or other low-risk eval-driven work. Draft proposal:
`docs/specs/local-backup-key-tier5-design-v1.md`.

**A11: Add blob vault for large and sensitive bodies — exploration spec drafted.**
D092 splits this from A10 and defers exact implementation pending local
S3-compatible storage exploration. “S3-compatible” means a local endpoint, not
AWS/cloud S3. Draft exploration spec:
`docs/specs/blob-vault-local-s3-exploration-v1.md`.

**A12: Refactor along active boundaries.** Put new retrieval, policy, context,
and runtime work in bounded packages; split old large modules only when active
behavior changes justify it.

**First implementation packets:** P-ARCH-001 dependency/schema/RFC/backlog
drift repair; P-ARCH-002 unified hit contract and project-source packet tests;
P-ARCH-003 generic non-capture `fetch_reference`; P-ARCH-004 no-egress probe
and wrapper; P-ARCH-005/P-ARCH-006 minimal `context_for`; P-ARCH-007 context
eval runner; P-ARCH-008 generic evidence/reference projection; P-ARCH-009
local entity grounding MCP substrate.

### Existing V1 sequence

**Step 6: Adversarial round** on V1 + principles + gold set + claim/belief
inventory.
This is the post-claims/beliefs round and does not replace the narrower D026
pre-Phase-2 round.

**Step 7: Synthesize.** Update DECISION_LOG and V1_ARCHITECTURE_DRAFT as needed.

**Step 8: Full V1-corpus stabilization.** Re-run non-destructive extraction /
consolidation cycles as needed after synthesis. Multi-week local compute is
acceptable, but it is not a prerequisite for authoring the first gold set.

**Step 9: Gold set against consolidated V1 corpus.** Drives prompt/model re-extraction cycles via the non-destructive pipeline. Done when pass-rate stabilizes.

## Standing items I own forever

- **Update this file when status changes.** Attention artifact, not a one-shot.
- **Resist per-decision review.** Multi-model convergence beats my intuition on technical calls; anxiety to weigh in is background noise.
- **Reauthor gold-set entries** as new categories of question come up.
- **Run adversarial sweeps** on the live store after launch (P6).

## Promoted into V1

- Async context precompute / hot state — promoted by D025. Implement only
  as minimal Phase 5 `context_snapshots` + `memory_events`; distributed
  multi-GPU serving remains later-stage.

## Explicitly deferred (so anxiety doesn't pull me back)

### Engram features (v2-or-later)

- Wiki output layer (replaced by belief review queue for v1)
- RFC 0050 Stage 3+ source-family expansion until real context-eval failures
  identify the missing evidence class (D093)
- Generated memory products until the downstream generated-product spec
  required by D089 is accepted
- Goal / failure / hypothesis / pattern inference
- Causal-link mining
- Apache AGE / graph backend
- Bulk Evernote → Obsidian migration (Claude + Gemini brought into V1 per D024)
- LLM cross-encoder reranker in live path
- Bidirectional Obsidian sync

### External tooling

- **Dev-workflow orchestrator** (e.g., [ai-auto-work](https://github.com/chaohong-ai/ai-auto-work)) — skipped. Working pattern is single coding agent + multi-model adversarial review at decision boundaries. Revisit only if that breaks down.

## When in doubt

- **Outcome:** *Biography of one human life, queryable at any point in time, owned by me.*
- **Process:** *Articulate principles. Articulate desired outcome. Articulate the eval. Get out of the way.*
- **My job:** Steps 1, 2, 5. Refuse to do Steps 6, 7, 9 until 5 is done. Steps 3, 4, 8 are engineering / model-driven.
