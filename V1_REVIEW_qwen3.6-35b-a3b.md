# V1 Review: Qwen3.6-35B-A3B (Claw)

Date: 2026-04-27
Inputs: HUMAN_REQUIREMENTS.md, V1_ARCHITECTURE_DRAFT.md,
CONSENSUS_REVIEW.md, DECISION_LOG.md, claw-review.md (prior)

---

## 1. Per-Principle Assessment

### P1: Why local-first is load-bearing

**Honors.** V1 is fully local: PostgreSQL + pgvector on local machine,
`nomic-embed-text` via local ollama, `qwen3.6-35b-a3b` via local ik-llama.
No cloud APIs in the data pipeline. The MCP server is local-only.

The principle goes further than "no cloud" — it demands:
- Encrypted-at-rest backups with user-held keys
- No telemetry
- Full-disk encryption assumption
- Encrypted dead-man's-switch for posthumous handoff
- Database encrypted with key not derivable from OS login

**V1 does not address:** encryption at rest, dead-man's-switch, or database-level
encryption. The principle says this is the one constraint that, if relaxed,
makes the project a liability. V1's schema has no `encrypted` flag, no key
management, no tier-based access control.

**Proposed delta:** Add a `settings` table (already in SPEC.md) with keys:
`db_encryption_key_source` (user-held / password-manager / HSM),
`dead_mans_switch_config` (heartbeat cadence, grace window, successor list).
Add a privacy tier column to `captures` and `beliefs`: `privacy_tier` (1–5,
default 1). This is v1 schema cost that V2+ features depend on.

---

### P2: Why corpus access and network egress are kept separate

**Honors.** The V1 architecture enforces this structurally:
- The engram-reading process (ingestion pipeline + MCP `context_for`) has no
  network egress — it reads from local Postgres and emits text.
- The network-using process (the AI that consumes `context_for` output) has
  no direct corpus access — it receives a curated package via stdin/IPC.
- `context_for(conversation)` is a pure read that produces text for a
  calling process.

The principle requires OS-level enforcement (sandbox, network namespace,
deny-by-default firewall), not just code discipline. V1 doesn't specify this.

**Proposed delta:** Document in V1_ARCHITECTURE_DRAFT.md that the engram
process should run in a network-disconnected container or namespace. This
is an operational constraint, not a schema change. The build order should
add "set up network-disconnected runtime for engram process" as step 0
(before PostgreSQL baseline).

---

### P3: Why raw data is sacred (model portability)

**Honors.** V1 explicitly encodes this:
- Episodes/messages/notes/captures are immutable (stated in V1 draft and
  CONSENSUS_REVIEW.md "Hard-To-Reverse Decisions" point 7)
- Three-tier separation: raw evidence → claims → beliefs (D002)
- `evidence_ids NOT NULL` on accepted beliefs (D003)
- `prompt_version` and `model_version` on every belief
- Non-destructive, resumable pipeline via `consolidation_progress`
- Re-derivation triggers: new embedding model, new prompt version, new
  segmentation heuristic, targeted slice upgrade

**The one tension:** V1 doesn't explicitly state that the pipeline must
support multiple coexisting versions of every derivation. The `superseded_by`
back-pointer on beliefs handles belief-level versioning. The SHA256-keyed
embedding cache handles embedding versioning (same input → same key → same
embedding, but different model versions can coexist). But there's no explicit
schema for tracking multiple `embedding_model_version` values simultaneously,
or for tracking that a belief was produced by model A with prompt B and
later re-extracted by model C with prompt D.

**Proposed delta:** On the `beliefs` table, add `original_prompt_version` and
`original_model_version` alongside the current `prompt_version` and
`model_version`. The current fields track the most recent extraction; the
original fields track the first one. The `belief_audit` table already records
every state transition — it should also record the model and prompt used
for each extraction run. This is already partially covered by D010 (belief
audit log) but the V1 schema doesn't spell it out.

---

### P4: Why eval is the only objective oracle

**Honors.** V1 explicitly gates full-corpus consolidation on eval pass
(step 15), lands a 25–50 prompt gold set (step 14), and tracks precision,
recall, stale fact rate, unsupported belief rate, contradiction rate, token
waste, and human usefulness rating.

**`context_feedback`** (step 13) feeds into the evolving gold set — the
principle says "treat the feedback table as evolving ground truth." V1
captures `useful / wrong / stale / irrelevant` annotations with belief ids
and segment ids. This is correct.

**The gap:** The principle says "gold-set authoring is the single most
irreplaceable human contribution." V1 doesn't encode this as a constraint —
there's no schema field or process that forces the user to author the gold
set before full consolidation. The build order has the eval harness as
step 14, but nothing prevents skipping it.

**Proposed delta:** Add a `consolidation_progress` checkpoint state:
`eval_gold_set_authoring_complete: boolean`. Step 15 (full-corpus gate)
checks this flag. This is a one-column addition to the existing
`consolidation_progress` table. It enforces the principle at the build
order level.

---

### P5: Why adversarial review is a permanent feature

**Silent.** V1 does not name adversarial review as a permanent feature.
The CONSENSUS_REVIEW.md lists "adversarial re-extraction sweeps" as a
research/experimental architecture item:

> "Take high-confidence accepted beliefs and run a falsification prompt:
> 'what evidence would contradict this — search episodes for it.' Surface
> conflicts as new contradictions."

This is deferred to research-only, not v1 product. The V1 build order has
no step for adversarial sweeps. The schema has `belief_audit` and `contradictions`
(via the CONSENSUS_REVIEW.md "Hard-To-Reverse Decisions" point 4, though
the V1 architecture draft doesn't explicitly include a `contradictions`
table in its minimal schema primitives).

**V1 should name this:** The principle says adversarial sweeps substitute
for engagement signals in a single-user system. V1's belief review queue
provides a HITL correction loop, but it's reactive (catches errors after
promotion) rather than proactive (searches for contradictions before they
matter). The principle says the system must manufacture its own engagement
signal.

**Proposed delta:** Add a `contradictions` table to the V1 schema primitives:
```
id
belief_a_id (FK → beliefs)
belief_b_id (FK → beliefs)
resolution   (resolved | unresolved | user_decided)
resolved_at
resolved_by  (user | adversarial_sweep)
```

This table is needed by both the belief review queue (user resolves) and
adversarial sweeps (model proposes). The principle says "at least two models
in production over time" — the schema must accommodate this. The
`belief_audit` table already records the model that produced each belief,
making cross-model comparison possible.

---

### P6: Why refusal of false precision is a contract

**Honors (partially).** V1 includes:
- `confidence` as a first-class field on beliefs
- `stability_class` for lifespan-aware ranking (identity beliefs get
  near-flat decay, transient beliefs decay fast)
- Historical beliefs surface only with explicit historical labeling
- `context_for` sections have explicit token budgets (prevents bloat)

**Does NOT address:**
- The principle says "when engram doesn't know something, it has to say so."
  V1 has no "no data" signal. The `context_for` shape has an "Uncertain /
  Conflicting" section (only when topic-relevant), but there's no mechanism
  to explicitly say "no data available for this question."
- The principle says "gaps are explicit — not silence, not a confident-sounding
  inference." V1's ranking formula has no gap-detection step. If all candidate
  lanes return low-scoring results, the `context_for` output may simply be
  thin rather than explicitly "no data."

**Proposed delta:** Add a "gaps" lane to `context_for` candidate generation:
```
gaps                           (~200 tokens — explicit "no data" statements
                                 for high-confidence queries that returned
                                 zero or low-scoring results)
```

This lane fires when the query asks about a topic that the candidate lanes
search but return nothing above the scoring threshold. It's not a belief —
it's a meta-statement about what the system doesn't know. The `context_for`
compiler checks: "for this query topic, did any lane produce results above
threshold? If not, emit 'no data'."

---

### P7: Domain coverage (not a "Why" principle, but a structural constraint)

**Honors (with reservations).** V1's schema primitives accommodate the
domain categories through the generic belief shape:
```
subject_entity_id
predicate
object_entity_id | value_text | value_json
valid_from
valid_to
```

The `value_json` column is the escape hatch — it can hold any structured
data. The `stability_class` enum (identity, preference, project_status,
goal, task, mood, relationship) maps to some domain categories.

**Does NOT address:**
- Privacy tiers. HUMAN_REQUIREMENTS.md specifies Tier 1–5 access control.
  V1 has no tier column on beliefs or captures.
- Posthumous handling. No encryption, no dead-man's-switch, no successor
  filtering.
- Multi-perspective. The principle says "store both my account and others'
  accounts for the same event." V1 has no mechanism for this.
- Gaps as data. "A day with nothing logged should be marked 'no log'
  rather than absent." V1 has no sparse-day tracking.
- Forgetting. "Some episodes should consolidate into summary and the raw
  fall away." V1 keeps raw evidence forever (correct per P3), but has no
  mechanism to drop raw episodes after consolidation — it just stores them
  indefinitely.

**Proposed delta:** Add `privacy_tier` (int, default 1) to `captures` and
`beliefs`. Add `gap_flag` (bool) to segments for days with no activity.
Add `multi_perspective` (JSONB) to captures for storing alternative accounts.
These are low-cost schema additions that V2+ features depend on.

---

## 2. Schema or Build-Order Additions

### Required schema additions

| Table | Column | Type | Purpose | Principle |
|-------|--------|------|---------|-----------|
| beliefs | original_prompt_version | text | Track first extraction prompt | P3 |
| beliefs | original_model_version | text | Track first extraction model | P3 |
| beliefs | privacy_tier | int | Tier 1–5 access control | P7 |
| captures | privacy_tier | int | Tier 1–5 access control | P7 |
| captures | multi_perspective | JSONB | Alternative accounts | P7 |
| segments | gap_flag | bool | Mark sparse days | P7 |
| contradictions | id | PK | Track belief conflicts | P5 |
| contradictions | belief_a_id | FK | Reference belief A | P5 |
| contradictions | belief_b_id | FK | Reference belief B | P5 |
| contradictions | resolution | text | resolved/unresolved/user_decided | P5 |
| contradictions | resolved_by | text | user/adversarial_sweep | P5 |
| consolidation_progress | eval_gold_set_authoring_complete | bool | Gate enforcement | P4 |

### Build-order additions

```
0.  Set up network-disconnected runtime for engram process (P2)
1.  PostgreSQL + pgvector baseline (add new tables above)
2.  ... (unchanged)
...
14. Eval harness: 25–50 prompt gold set (enforce eval_gold_set_authoring_complete flag)
15. Gate: full-corpus consolidation only after eval pass AND eval_gold_set_authoring_complete
```

The `contradictions` table is needed before step 5 (claim extraction) so that
adversarial sweeps can write conflicts. The `original_prompt_version` and
`original_model_version` columns are needed before step 6 (belief consolidation)
so that re-extraction records both the original and current extraction metadata.

---

## 3. Security Implications

### 3.1: Database encryption at rest (from P1)

HUMAN_REQUIREMENTS.md says "the database itself should be encrypted with a
key not derivable from the OS login alone." V1 uses PostgreSQL, which supports
pgcrypto for column-level encryption or full-disk encryption via LUKS. V1
should document which approach is used and how the key is managed.

**Constraint:** Postgres data directory encrypted via LUKS. Key held by user
at login (not auto-unlocked by systemd). This is infrastructure, not schema.

### 3.2: Privacy tier enforcement (from P7)

If `privacy_tier` is added to `captures` and `beliefs`, the `context_for`
compiler must enforce tier filtering. Tier 1 data is only visible in the
raw store and in the user's own review queue. Tier 2 data is surfaceable
to the AI for context. Tiers 3–5 are posthumous or restricted.

**Constraint:** `context_for` must apply tier filtering before ranking.
Tier-1 beliefs should never appear in the context package unless the user
explicitly promotes them.

### 3.3: Network egress enforcement (from P2)

The principle says the engram-reading process should have no network egress.
V1's MCP server exposes `context_for` — if the MCP server binds to a network
interface, it becomes a vector for exfiltration.

**Constraint:** MCP server binds to 127.0.0.1 only. The engram process runs
in a network-disconnected container or namespace. Document this as an
operational constraint in V1_ARCHITECTURE_DRAFT.md.

### 3.4: Adversarial sweep safety (from P5)

Adversarial sweeps run a second model against the live store to find
contradictions. This model reads the same corpus as the primary extractor.
If the adversarial model is compromised or hallucinates, it could create
false contradictions that pollute the `contradictions` table.

**Constraint:** Adversarial sweeps write to `contradictions` with
`resolution = unresolved`. They do NOT auto-reject beliefs. Only the user
or a separate adjudication process resolves contradictions. This preserves
the principle that "the user is not the only adversarial reviewer" while
preventing adversarial model errors from becoming action.

### 3.5: Posthumous handoff (from P1/P7)

HUMAN_REQUIREMENTS.md specifies an encrypted dead-man's-switch. V1 doesn't
address this, but the schema should accommodate it:
- `dead_mans_switch_config` in `settings` table
- Per-successor view filtering (future, not v1)
- Tier-5 destruction prior to release (future, not v1)

**Constraint:** These are deferred to v2, but the schema should have a
`settings` table with a `posthumous_config` key (nullable for v1).

---

## 4. Position Changes

### 4.1: P1 (local-first) — from "honors" to "honors with delta needed"

My prior review (claw-review.md) said local-first is honored. The principle
goes further than "no cloud" — it demands encryption at rest, dead-man's-switch,
and database-level encryption. V1 doesn't address these. I now classify V1 as
"honors the spirit but violates the letter" of P1, requiring the `privacy_tier`
and `settings` additions above.

### 4.2: P5 (adversarial review) — from "deferred" to "schema needed in v1"

My prior review deferred adversarial sweeps entirely. The principle says this
is not a research probe — it's "the thing that keeps the system honest with
itself." V1's schema must accommodate contradictions from adversarial sweeps.
I now recommend adding the `contradictions` table in v1, even if the sweeps
themselves are deferred. The table is the infrastructure the principle needs.

### 4.3: P6 (refusal of false precision) — from "honors" to "honors partially"

My prior review said V1 honors this via `confidence` and `stability_class`.
The principle is stronger: "when engram doesn't know something, it has to
say so." V1 has no "no data" signal. The `context_for` compiler may simply
be thin rather than explicitly "no data available." I now recommend adding
a gaps lane to `context_for`.

### 4.4: P3 (raw data sacred) — confirmed, with one addition

My prior review correctly identified `evidence_ids NOT NULL`,
`prompt_version`/`model_version`, and non-destructive pipeline as honoring
P3. I now recommend adding `original_prompt_version` and
`original_model_version` to distinguish the first extraction from current
re-extraction. This is needed for the principle's "the trail of what the
system thought it knew, with which model, at which time" requirement.

---

## 5. Strongest Residual Concern

The single most important issue: **the V1 schema has no way to represent
"the system doesn't know" as a first-class answer.** The principle of
refusal of false precision (P6) says gaps must be explicit, but V1's
`context_for` compiler has no gaps lane. If all candidate lanes return
zero or low-scoring results for a query topic, the output is a thin or
missing section — not an explicit "no data available for this question."
This is worse than a false precision problem because it's structurally
invisible: the downstream model sees a thin context package and may infer
silence rather than explicit uncertainty, poisoning its reasoning just as
badly as a confident-but-wrong fact would. The fix is simple (add a gaps
lane), but it's absent from the current draft and has no precedent in the
schema. Without it, engram's contract with downstream models — the most
distinctive property of the system — is broken at the serving layer.
