# V1 Review — Claude Opus 4.7

Reviewer: Claude Opus 4.7 (1M context)
Date: 2026-04-28
Inputs: HUMAN_REQUIREMENTS.md, V1_ARCHITECTURE_DRAFT.md, SECURITY.md,
CONSENSUS_REVIEW.md, DECISION_LOG.md, ROADMAP.md, REVIEW_claude-opus-4-7.md
(round-1).

The principles change the review on three axes round-1 didn't load-bear:
the corpus/network wall, the contract with downstream models, and what
"deferred but schema-ready" means for adversarial review. Most of V1
survives. A handful of small omissions — none of them headline — would
break a principle if shipped as-is.

---

## 1. Per-principle assessment

The seven principles, in HUMAN_REQUIREMENTS order. P1 is the temporal
spine; P2–P3 are local-first and corpus/network separation; P4 is raw
sacred; P5 is eval; P6 is adversarial review; P7 is refusal of false
precision.

### P1 — Time-indexed biography (every fact carries a validity interval)

**Honors, with one silence.**

Beliefs carry `valid_from`, `valid_to`, `observed_at`, `recorded_at`,
`superseded_by`. Close-and-insert on contradiction. `current_beliefs`
view defaults to `valid_to IS NULL`. This is the principle's load-bearing
core and V1 has it.

The silence: **`captures` and `notes` have no validity interval of their
own.** A capture asserts content; the assertion has a timestamp but not
a `valid_from`/`valid_to`. The current pipeline punts validity to the
belief stage. That is fine *if and only if* every captured fact passes
through extraction. For things the user types directly as ground truth
("I lived at 123 Main from 2018-04 to 2022-09"), forcing them through
LLM extraction adds a hallucination surface where none was needed.

**Delta:** allow `captures` to carry an optional explicit
`(valid_from, valid_to)` payload. When present, claim extraction lifts
those windows directly into the belief instead of re-deriving them from
prose. This is a column on `captures` (`asserted_validity JSONB NULL`),
not a new table.

A second silence worth naming: meta-requirement "gaps as data." A day
with nothing logged should be a recorded gap, not silence. V1 has no
sparse-day primitive. Recommended for the schema-additions list below
rather than as a principle violation — the principle is the temporal
spine, and a missing day's gap-marker is a domain-coverage issue more
than a temporal-spine issue.

### P2 — Local-first is load-bearing

**Honors structurally; silent on the binding constraints.**

V1 runs Postgres + pgvector + local Ollama / ik-llama. No cloud calls in
the pipeline. That part is right.

Three things the principle pins that V1 does not name:

1. **Encryption at rest with a key not derivable from OS login alone.**
   V1 says nothing. SECURITY.md flags it TBD. V1 should at minimum say
   *which posture it's targeting* before any health/financial data is
   ingested — the principle treats this as the one constraint that, if
   relaxed, makes the project a liability.
2. **No telemetry.** V1 is presumably silent because there isn't any,
   but "presumably" is exactly what the principle says is unacceptable.
   A line in V1 stating "the engram process initiates no outbound
   network traffic of any kind" is one sentence and forecloses the
   future drift that the principle is trying to prevent.
3. **Posthumous policy hooks.** V1 schema has no `settings` /
   `successors` / `dead_mans_switch_config` placeholder. The principle
   commits the design to an encrypted dead-man's-switch. V1 can defer
   the *mechanism* to v2 without violation, but a `settings` table with
   a typed `posthumous_config` slot is a free schema addition that
   prevents a v2 migration over already-encrypted data.

**Delta:** add a single sentence in V1_ARCHITECTURE_DRAFT under "Sources"
or a new "Local-first commitments" subsection: "engram makes no outbound
network requests under any code path." Add a `settings` table to the
schema primitives. Defer the encryption posture choice to SECURITY but
make V1 pass-through-aware: don't ingest Tier-1-default categories
(health, finances) until the encryption decision lands.

### P3 — Corpus access and network egress are kept separate

**Honors at the design layer; silent at the enforcement layer.**

V1 has `context_for` as a pure read producing text — structurally on the
right side of the wall. The downstream model that *uses* the package
runs in its own process. This is the principle's structural fix.

What V1 does not say: the wall is ideally enforced at the OS level —
sandbox, network namespace, deny-by-default firewall — not by hoping the
code never imports `requests`. The build order has no step for
network-isolating the engram process. The MCP server's bind interface
isn't specified (must be 127.0.0.1; must not bind 0.0.0.0).

**Delta:** add as build-order step 0:
"Configure a network-disconnected runtime for the engram-reading process
(Linux network namespace, macOS sandbox, or equivalent). MCP server
binds to 127.0.0.1 only." Add to V1 non-goals: "engram never makes
outbound network requests; freshness is not a v1 feature." That last
clause heads off the natural drift toward "let the local model do a web
search." The principle says no.

### P4 — Raw data is sacred (model portability)

**Honors strongly, with one belief-review-queue ambiguity.**

V1 has all the structural pieces: immutable raw, three-tier separation,
`evidence_ids NOT NULL` on accepted, `prompt_version` /
`model_version`, non-destructive resumable pipeline, SHA256-keyed
embedding cache, `superseded_by` on beliefs.

The ambiguity is the **belief review queue's "correct" action**. The
principle is explicit: *"User corrections are raw, not metadata. When
the user tells engram 'that fact is wrong, the truth is X,' that input
lands as a new `capture` row in the raw store, not as a flag on the bad
belief."* V1 says the review queue supports "accept / reject / correct /
promote to pinned." If "correct" mutates the belief in place, or
attaches a correction to it as metadata, that violates P4. If "correct"
writes a new capture and lets the supersession pipeline run, it's
correct.

This is ambiguous in V1_ARCHITECTURE_DRAFT.md as written. It needs a
sentence.

**Delta:** in the HITL section, add:
"`reject` and `correct` write new `captures` rows (the user is a
first-class evidence source). They do not mutate beliefs in place. The
new capture is processed by the same extraction pipeline as any other
evidence; the resulting new belief supersedes the bad one via
`superseded_by`."

A second small item: the principle says **multiple coexisting versions
of every derivation must be representable**. V1 covers this for
embeddings (multiple `embedding_model_version` per segment via the
content-addressed cache) and for beliefs (via `superseded_by`). It is
silent on whether *segments* can have multiple versions (re-segmentation
under a new heuristic). The build order says re-segmentation is
non-destructive, but the schema should make this explicit:
`segments.segmenter_version` and a `superseded_by` on segments. This is
already implied by D005 + the non-destructive invariant; it just needs
to be a column.

### P5 — Eval is the only objective oracle

**Honors in spirit; the gate sizing is the interim question, addressed
in §6 below.**

The build-order gate (eval pass before full-corpus consolidation), the
gold set as canonical specification, and `context_feedback` as
gold-set-extension-in-production are all in V1. Three points of
observation:

- The principle says gold-set authoring "cannot be delegated." V1's
  build order has no enforcement that the gold set is authored *before*
  the eval gate fires. The gate could pass on a gold set the user
  hasn't actually engaged with. ROADMAP step 4 puts this on the human,
  but a `consolidation_progress` flag costs nothing and makes the
  enforcement structural.
- "**Eval before full-corpus**" is in V1. The size of the gating subset
  is the open question (§6).
- The principle elevates `context_feedback` to "evolving ground truth."
  V1 captures `useful / wrong / stale / irrelevant` with belief and
  segment ids. Recommend one more field: a free-text `correction_note`,
  optional. Without it, `wrong` is a binary signal; with it, the user
  can say *what* the right answer should have been, and that becomes a
  new `capture`. Cheap, structural.

**Delta:** add a `correction_note TEXT NULL` column to
`context_feedback`. Add a `consolidation_progress` checkpoint
`gold_set_authored: bool` that the full-corpus gate consults.

### P6 — Adversarial review is a permanent feature

**Violates — by omission of one schema primitive.**

The principle is explicit about what V1 owes here: *"Adversarial sweeps
are deferred for v1, but the schema must accommodate them now.
`contradictions`, `belief_audit`, and the immutable raw store are
exactly the infrastructure adversarial sweeps need — all already in V1."*

V1's minimal schema primitives list (V1_ARCHITECTURE_DRAFT.md §Minimal
Schema Primitives) does **not** include `contradictions`. CONSENSUS_REVIEW
mentions it under hard-to-reverse decisions and the open-contradictions
candidate lane references it, but the schema-primitives list omits it.
The principle expects it to be there. Schema omission is exactly the
"deferred" mistake the principle warns against — the table costs nothing
to define now and is a migration headache later when adversarial sweeps
arrive and need to write somewhere.

**Delta:** add `contradictions` to the V1 minimal schema primitives.
Minimum columns: `id`, `belief_a_id`, `belief_b_id`, `discovered_by`
(`user | review_queue | adversarial_sweep`), `discovered_at`,
`resolution` (`open | resolved_supersede_a | resolved_supersede_b |
resolved_both_valid_different_windows | dismissed`), `resolved_at`,
`resolved_by`. The "open contradictions" candidate lane already
references this table; it's a missing primitive, not a new design.

A second item: the principle says "at least two models in production
over time — primary extractor and adversarial reviewer." V1 silent.
Acceptable for v1 to defer the second model, but
`belief_audit.model_version` should already track *which* model
extracted each belief so cross-model adversarial diffs are possible
when the second model lands. D010 already implies this; just confirm
it lands as a column.

### P7 — Refusal of false precision is a contract

**Honors partially — confidence is a field, but not a propagated signal,
and gaps are not represented.**

V1 has `confidence` on beliefs and `stability_class` for lifespan-aware
ranking. The `context_for` shape includes an "Uncertain / Conflicting"
section. Good as far as it goes.

What it doesn't do:

1. **Propagate confidence into the rendered context.** The context_for
   sections render belief content with a token budget; nothing in the
   draft says confidence and provenance are *in the rendered text*. The
   principle: *"`context_for` outputs surface provenance and confidence
   alongside content so consumers can weight accordingly."* If the
   consuming model sees "user lives at 123 Main" without "(confidence:
   0.62, source: capture from 2024-03)", the contract is broken at the
   serving layer.
2. **Represent gaps as a first-class output.** When a query asks about
   a topic engram has no data on, the right answer is "no data on this,"
   not a thinly-populated section. V1 has no gaps lane, no "no data"
   path. A thin section reads, to a downstream model, like silence
   rather than refusal — and that is exactly what the principle says
   poisons the consumer.

**Deltas:**

- Specify in V1_ARCHITECTURE_DRAFT (under "Context_For Shape") that
  every rendered belief carries an inline `(conf=0.NN, src=…)` tag, and
  that the section composer is responsible for emitting these.
- Add a `Gaps / No Data` section to the `context_for` shape with a
  small token budget (~150 tokens). A gap entry fires when a candidate
  lane was queried for a topic and produced nothing above scoring
  threshold. This must be a positive emit ("no data on X"), not absence.
  Per-section budgets for `Uncertain / Conflicting` and `Gaps / No
  Data` should both default to "fire only when topic-relevant," but
  they are *different sections*: conflict means contradicting evidence
  was found, gap means none was found.

---

## 2. Schema and build-order additions

Concrete items, all small:

| Surface | Addition | Principle | Cost |
|---------|----------|-----------|------|
| `contradictions` | new table; `id`, `belief_a_id`, `belief_b_id`, `discovered_by`, `discovered_at`, `resolution`, `resolved_at`, `resolved_by` | P6 | one migration |
| `settings` | new table; placeholder for `posthumous_config`, `encryption_posture`, future global state | P2 | one migration |
| `captures.asserted_validity` | nullable JSONB; lets the user pass through explicit validity windows without LLM re-derivation | P1 | one column |
| `segments.segmenter_version` + `segments.superseded_by` | match the belief versioning pattern; make re-segmentation explicit | P4 | two columns |
| `context_feedback.correction_note` | nullable free-text; gives `wrong` a payload that becomes a new `capture` | P5 | one column |
| `consolidation_progress.gold_set_authored` | boolean checkpoint the full-corpus gate consults | P5 | one column |
| `context_for` shape | add `Gaps / No Data` section (~150 tokens); specify confidence/provenance inline rendering for every belief | P7 | spec change |
| Build order step 0 | network-disconnected runtime for engram-reading process; MCP binds 127.0.0.1; no engress permitted | P3 | ops setup |
| Build order step 14 (Eval) | reframe per §5 — smoke at ≈200 gates V1-corpus consolidation (ChatGPT+Claude+Gemini, ≈5k conv); gold-set validation runs against the consolidated V1 corpus, not as the gate itself | P5 | sequencing |
| Non-goals | "engram makes no outbound network requests under any code path" | P2/P3 | one line |
| HITL section | "`reject` and `correct` actions write new `captures`; never mutate beliefs in place" | P4 | one line |

None of these expand V1 scope. They tighten existing decisions to what
the principles already require.

---

## 3. Security implications (items for SECURITY.md)

SECURITY.md is a skeleton with TBDs. The principles imply specific
constraints worth elevating from "open" to "decided":

1. **MCP server bind interface.** Must be 127.0.0.1 (or a Unix domain
   socket). Never 0.0.0.0. This is a one-line decision that closes the
   most obvious accidental egress path. Currently absent from
   SECURITY.md.
2. **No outbound network from the engram-reading process — full stop,
   not "default-deny."** P3's existing language in HUMAN_REQUIREMENTS
   is stronger than SECURITY.md's draft. The reading process gets a
   network namespace with no interface, not an egress proxy. Egress
   proxy is for the *action-taking* process. SECURITY.md currently
   blurs this.
3. **Belief-review-queue corrections are raw inputs.** A
   privilege-escalation review note: any UI that lets the user "edit
   beliefs" must be wired to *write captures*, not UPDATE beliefs. Code
   path that UPDATEs accepted beliefs is a P4 violation and a corpus
   integrity risk; flag it as a security-relevant invariant.
4. **Adversarial-sweep model isolation.** When the second model arrives
   (deferred but schema-ready per P6), it reads the same corpus the
   primary extractor reads. It must run in the same network-isolated
   posture as the engram-reading process. SECURITY.md should pre-empt
   this with: "any process that reads the corpus inherits the no-egress
   constraint; this includes future adversarial sweep processes."
5. **`captures.asserted_validity` is privileged input.** If the user
   can write captures with structured payloads, the capture writer
   becomes a high-trust path. The action-taking model must not be able
   to call the capture writer; only direct user input (CLI, MCP tool
   the user invokes) may. Flag as a tier boundary.
6. **`context_for` tier filtering — a P-derived constraint not yet in
   SECURITY.md.** The principle "every fact carries provenance and
   confidence in the rendered context" implies the renderer must apply
   tier filtering *before* ranking, not after. Otherwise, a Tier-1
   belief can be ranked, scored, and *then* dropped — leaking its
   existence via timing or by influencing the cut. This is a small
   architectural detail with security weight.

The five-tier privacy model in SECURITY is correctly listed as
TBD-coupled-to-posthumous; nothing principle-derived adds urgency
beyond what's already there.

---

## 4. Position changes from round-1

My round-1 review (REVIEW_claude-opus-4-7.md) prioritized bitemporal
modeling, lifespan tagging, three-layer context composition, provenance
discipline, and topic-segmented chunking. With the principles now
explicit, three positions shift:

1. **Layer-3 entity expansion: from "cut for v1" to "keep but
   conditional."** Round-1 said cut Layer-3 entity expansion until
   retrieval shows gaps. CONSENSUS_REVIEW resolved this as "keep schema,
   gate live activation on eval." The principles tilt me toward the
   consensus position rather than my round-1 cut, for two reasons:
   (a) gold-set categories like person-recall and ambiguous-reference
   resolution structurally need entity neighborhood, and authoring
   those entries against a schema that *cannot* answer them produces
   self-fulfilling poor evals; (b) `entity_edges` is one of the
   schema-now-or-pay-later tables. I withdraw the round-1 "cut Layer-3"
   recommendation. Conditional activation behind eval gates is correct.

2. **`stability_class`: from "I had three buckets" to "the seven-class
   enum is right."** Round-1 proposed `permanent / slow-changing /
   transient`. CONSENSUS_REVIEW chose Codex's seven-class enum
   (`identity / preference / project_status / goal / task / mood /
   relationship`). With P7 in mind, the seven-class enum is the better
   call — `currentness` and `stale_penalty` need the finer-grained
   signal to honor the contract that confidence and currency don't
   collapse. Three buckets would force the ranker to flatten distinctions
   the principle says it must preserve. Position changed.

3. **Adversarial review: from "interesting research probe" to
   "schema-mandatory in v1, sweeps deferred."** Round-1 mentioned
   adversarial re-extraction as a circuit breaker. CONSENSUS_REVIEW put
   it in the research/experimental bucket. The principle moves the
   *infrastructure* (not the sweeps themselves) to v1-mandatory: the
   `contradictions` table is the missing primitive. This is the most
   concrete schema-level violation in V1 and the one I'd most insist on
   fixing before the first migration.

Two round-1 positions hold up unchanged: cut hypotheses/causal-links/
patterns from v1 (P3 affirms — synthesis-of-synthesis is a
hallucination amplifier without grounding), and topic segments as the
canonical chunk (P4 affirms — coherent chunks are what give the LLM
enough context to attach an honest evidence chain).

---

## 5. Strongest residual concern

**The current V1 language conflates two different checks under one
"eval gate," and the conflation is the thing that breaks P5 in
practice.**

A terminology note for this section: "full corpus" in V1 means the V1
AI-conversation ingestion set (ChatGPT + Claude + Gemini, ≈5k
conversations) plus Obsidian and capture. It does *not* mean the
long-arc biographical corpus (health, finances, locations,
relationships, recipes, decades of capture) — that accrues over years
and is out of scope for V1. The gold set authored for V1 is sized to
what the V1 corpus can answer; future domain coverage will produce new
gold-set entries that V1 cannot ground.

CONSENSUS_REVIEW reads as "the 25–50 prompt gold set runs against a
≈100-conversation subset and the result gates full-corpus
consolidation." That sentence runs two different validations together:
*does the pipeline work* (plumbing), and *does retrieval produce useful
context against real V1-corpus state* (correctness). They want
different inputs.

A random 100-conversation subset is appropriate for the first and
structurally unable to do the second. Gold-set entries reference
specific people, projects, and years; a random sample of 100 from the
≈5k V1 corpus will contain none of the entities most entries reference.
The eval would fail not because the architecture is wrong but because
the evidence the gold set asks for isn't there. The user is then
forced into one of: (a) lower the bar — defeating the gate;
(b) consolidate the V1 corpus to make entries passable — defeating the
gate; (c) lose confidence in the eval methodology — defeating P5.

A stratified middle tier (subset chosen to match gold-set targets) is
also wrong, for a different reason: stratification on "conversations
mentioning Sarah" requires entity extraction to have already run, which
is exactly what the gate is supposed to be gating. The stratifier needs
its own pre-pipeline; that pre-pipeline needs its own validation; the
regress doesn't terminate.

The right resolution — owner's call, validated against the underlying
constraints — is to **split the two validations and order them**:

- **Smoke gate (≈200 conv, random) — gates V1-corpus consolidation.**
  Plumbing only. Does ingestion populate raw tables, do segments embed,
  do claims extract, do beliefs land with `evidence_ids`, do
  contradictions get flagged, does the build resume after interruption.
  Pass/fail is schema-level, not retrieval-quality-level. Cheap to run;
  cheap to iterate the pipeline against.
- **V1-corpus consolidation (≈5k AI conversations + Obsidian +
  capture) — runs after smoke passes, not behind a quality gate.**
  Estimated 2–3 weeks of local-LLM compute. The local-research-lab
  posture absorbs this cost; the alternative (a stratified middle tier)
  introduces complexity that itself needs validating. This is "full
  V1 corpus," not "full biographical corpus" — the latter is the
  long-arc target, not a V1 deliverable.
- **Gold-set validation — runs against the consolidated V1 corpus.**
  This is the P5-binding eval. Failures here are real failures —
  retrieval is wrong, ranking is wrong, beliefs are wrong — and the
  remediation is prompt-version / model-version re-extraction against
  the same immutable raw store (which P4 makes cheap). The V1 gold set
  is sized to what AI conversations + Obsidian + capture can ground;
  domain categories beyond that scope (health, finances, etc.) produce
  v2-or-later gold-set entries.

Two implications for V1 as written:

1. V1_ARCHITECTURE_DRAFT.md's "Eval set runs on a small ChatGPT subset
   (≈100 conversations) before full-corpus consolidation. Full-corpus
   consolidation is gated on eval results." reads as "gold-set gates
   consolidation." That language should be replaced with: "Smoke eval
   on a ~200-conversation subset gates V1-corpus consolidation
   (plumbing only). Gold-set validation runs against the consolidated
   V1 corpus and drives prompt/model re-extraction cycles, not the
   initial consolidation."
2. The non-destructive, resumable pipeline (per P4) is what makes this
   posture viable. Re-extracting against the immutable raw store after
   a gold-set failure is cheap; that's the whole point of the
   three-tier separation. Without P4, this resolution would be reckless;
   with it, it's the right call.

This narrows the "gate" concept to where it actually has teeth (does
the pipeline run end-to-end without dropping data) and lets retrieval
correctness be measured where it can actually be measured (against the
production store). My round-1 framing wanted three tiers; the right
answer is two, with the middle correctly cut.

---

*End of review.*
