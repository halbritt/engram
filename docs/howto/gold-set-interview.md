# Gold-Set Interview — How-To

Audience: human operator running `engram phase3 interview` against a local
Engram database.

This guide covers what the interview surface does today (RFC 0021 v1), how
to use it, and what is intentionally not wired yet. For the design rationale
read [`docs/rfcs/0021-gold-set-interview-curation.md`](../rfcs/0021-gold-set-interview-curation.md).
For the schema read [`migrations/010_gold_labels.sql`](../../migrations/010_gold_labels.sql).

## What it is

`engram phase3 interview` is the local-only, append-only authoring surface
for **gold labels** — your verdicts on individual claims and beliefs the
system has extracted. Labels become advisory inputs to the Step 9 eval
loop. They never auto-flip belief status (D044) and never gate extraction
or consolidation (D069).

Two tables hold the data:

- `gold_label_sessions` — one row per interview session you open.
- `gold_labels` — one row per verdict. Append-only; the table refuses
  `UPDATE` and `DELETE` at the schema layer.

A `current_gold_label` view returns the latest verdict per
`(target_kind, target_id, version_triple)` with a verdict-rank tiebreak.

## What is wired today

V1 is a smoke-test surface for the schema, sampler, and storage contracts.

| Subcommand | Status |
|------------|--------|
| `start` | Opens a session, samples N targets, stamps the candidate-pool snapshot, prints a summary. **Does not interactively prompt for verdicts.** |
| `resume` | Looks up a session by id and prints whether it is open. |
| `history` | Prints the recorded verdicts for a `--target <uuid>`. |
| `export` | JSONL dump of `gold_labels` filtered by `--privacy-tier-max` (default 1). |
| `list-sessions` | Lists sessions, optionally filtered by `--state open|completed`. |
| `coverage` | Counts rows by `stability_class`. |
| `enable-active-learning` | Records the operator-visible at-scale signal version. |

The interactive question-by-question loop is **not** built yet. To capture
verdicts in v1 you wire a small Python script around
`engram.interview.InterviewAgent.record_verdict()`; see the worked example
below. A future RFC will land an interactive REPL or a web surface.

## Prerequisites

```sh
make install           # local venv
make migrate           # or make migrate-docker — applies migration 010
```

You also need a populated Phase 3 belief set. If `current_beliefs` is empty,
`start` returns zero sampled targets and exits cleanly.

## Your first session

```sh
engram phase3 interview start --n 5 --seed 4
# → phase3 interview start: session=<uuid> seed=4 sampler=stratified@stratified.v1.d079.initial sampled=5

engram phase3 interview list-sessions --state open
# → lists the open session you just created

engram phase3 interview history --target <belief-or-claim-uuid>
# → no rows yet (you have not recorded a verdict)
```

`start` opens a session and pre-stamps the candidate pool. It does not
write any `gold_labels` rows by itself; verdict capture is a separate step.

## Capturing verdicts (v1 Python harness)

While the interactive CLI loop is deferred, `InterviewAgent` exposes the
record path directly:

```python
from engram.db import connect
from engram.interview import GoldLabelSampler, InterviewAgent
from engram.interview.storage import insert_session

with connect() as conn:
    session_id = insert_session(
        conn,
        seed=4,
        sampler_id="stratified",
        sampler_version="stratified.v1.d079.initial",
        strata_weights={},
    )
    sampler = GoldLabelSampler(conn, seed=4)
    agent = InterviewAgent(conn)

    for target in sampler.sample(5):
        question = agent.render_question(target)
        print(question)
        verdict = input("verdict [true/false/stale/unsupported/unsure/skip]> ").strip()
        rationale = input("rationale (Enter to skip)> ").strip() or None
        agent.record_verdict(session_id, target, verdict, rationale=rationale)
    conn.commit()
```

That harness uses the real schema, the real append-only triggers, and the
real cooldown rules. It is a stopgap, not the long-term UX.

## Verdict glossary

The six accepted verdicts and what they mean to a human operator:

| Verdict | Use when |
|---------|----------|
| `true` | The claim or belief is correct about the world right now (or, for claims, was correct at the time of the cited evidence). |
| `false` | Wrong about the world. The claim mis-paraphrases or the belief never held. |
| `stale` | Was true at evidence time, no longer true. (Example: "user works at Acme" after a job change.) |
| `unsupported` | The cited evidence does not actually establish the claim, even if the claim happens to be true. Distinct from `false` — this rules on provenance, not world-truth. |
| `unsure` | You cannot rule. Counts toward cooldown. |
| `skip` | Defer this target. **Cooldown-free** — the next session can re-surface it immediately. |

`true | false | stale | unsupported` outrank `unsure | skip` in the
`current_gold_label` view's tiebreak: a verdict that ruled on something
beats a verdict that didn't.

## Privacy tiers and export

Labels carry the `privacy_tier` of their parent claim or belief, set by a
`BEFORE INSERT` trigger. Mismatched operator-supplied tiers are rejected.

`export` defaults to a **fail-closed Tier 1 ceiling**:

```sh
engram phase3 interview export                  # Tier 1 only (the default)
engram phase3 interview export --privacy-tier-max 2 --output gold.jsonl
```

No flag combination relaxes the ceiling below the default — `--ignore-cooldown`
does not affect `--privacy-tier-max`. Widen `--privacy-tier-max` only when
you have a specific reason and the export destination is local.

`evidence_excerpt` fields are stored separately from `prompt_text` so the
export path can redact them when the row's tier exceeds the requested
ceiling. (V1 export is JSONL of the bare row set; redaction policy lives
above the SQL — extend the export driver in `src/engram/cli.py` if you
need stricter behavior.)

## Cooldown defaults

Per-stability-class cooldowns prevent burning interviews on the same
target. The v1 defaults (in days, per `(target, any verdict)` other than
`skip`):

| Stability class | Default | Env var |
|-----------------|---------|---------|
| `goal` | 14 | `ENGRAM_GOLD_COOLDOWN_GOAL_DAYS` |
| `task` | 7 | `ENGRAM_GOLD_COOLDOWN_TASK_DAYS` |
| `mood` | 3 | `ENGRAM_GOLD_COOLDOWN_MOOD_DAYS` |
| `preference` | 30 | `ENGRAM_GOLD_COOLDOWN_PREFERENCE_DAYS` |
| `relationship` | 60 | `ENGRAM_GOLD_COOLDOWN_RELATIONSHIP_DAYS` |
| `identity` | 90 | `ENGRAM_GOLD_COOLDOWN_IDENTITY_DAYS` |
| `project_status` | 30 | `ENGRAM_GOLD_COOLDOWN_PROJECT_STATUS_DAYS` |

Per-verdict cooldown is half of the per-target value. `skip` is exempt —
skipped targets re-surface immediately on the next session.

Override per-run by env-var or with `--ignore-cooldown` (does not relax
the privacy ceiling).

## Resume, save-and-quit, list-sessions

A session stays open until you mark it complete. Running `start --n 5`
again opens a *new* session; it does not resume.

```sh
engram phase3 interview list-sessions --state open
engram phase3 interview resume --session-id <uuid>
```

To mark a session complete from your harness script:

```python
from engram.interview.storage import mark_session_completed
mark_session_completed(conn, session_id)
conn.commit()
```

## Coverage

```sh
engram phase3 interview coverage --strata stability_class
```

V1 prints row counts per `stability_class`. Use it to spot-check whether
your label set over-represents a few strata. Richer slicing (conf_band ×
recency_band, per-session deltas) is a v1.1 expansion.

## Active-learning bias

Off by default. The bias does not run silently — you must call
`enable-active-learning --signal-version <v>` to record the operator-visible
at-scale signal version, and even then v1 stamps the version on emitted rows
without re-ranking. Re-ranking lands when RFC 0018 reviewer output reaches
the threshold (default 500 audit rows; tunable via
`ENGRAM_GOLD_ACTIVE_LEARNING_THRESHOLD`).

The signal version is a small but real decision: if you flip the bias on
mid-corpus, re-running the same `(seed, sampler_version)` no longer reproduces
the prior question sequence. Treat enabling as a project decision per RFC
0021 § Open Q 4.

## Templates and versioning

Two templates ship in `prompts/interview/`:

- `prompts/interview/claim_v1.md` — claim-mode question. Version
  `interview.claim.v1.d079.initial`.
- `prompts/interview/belief_v1.md` — belief-mode. Version
  `interview.belief.v1.d079.initial`.

Templates follow RFC 0017 versioning: the file path is the join key, and
the version string is stamped onto every emitted `gold_labels` row. A new
prompt revision lands as `*_v2.md` with a new version string; old labels
remain attached to the version they were authored against.

## What labels do (and don't)

- **Do** become inputs to Step 9 eval cycles for prompt and model
  re-extraction (RFC 0021 § Relationship to other artifacts).
- **Do** join onto `claims.id` and `beliefs.id` via the typed version
  triple stored in `gold_labels`.
- **Don't** flip `beliefs.status`. A `false` verdict is signal, not a
  state transition (D044).
- **Don't** gate Phase 2 segmentation, Phase 3 extraction, or Phase 3
  consolidation (D069).
- **Don't** auto-promote into `GOLD_SET_TEMPLATE` entries — that path is
  open question 1 in the RFC.

## Troubleshooting

- **`gold_labels target_id … not found in claims`** — the polymorphic
  `BEFORE INSERT` trigger refused a dangling reference. Re-run the
  sampler; the candidate pool may include rows from a generation that
  has been superseded.
- **`gold_labels.privacy_tier (X) does not match parent tier (Y)`** —
  the carry trigger refused an operator-supplied tier. Drop the
  argument and let the trigger copy the parent's tier.
- **`gold_labels is append-only`** — you tried to `UPDATE` or `DELETE`.
  Re-asks insert new rows; that's the contract.
- **`current_beliefs` is empty** — Phase 3 has not produced beliefs yet,
  or `current_beliefs` needs a refresh. Run `engram phase4
  refresh-current-beliefs` if Phase 4 schema is in place; otherwise
  `start` legitimately samples zero rows.

## Where to read next

- [`docs/rfcs/0021-gold-set-interview-curation.md`](../rfcs/0021-gold-set-interview-curation.md) — design contract.
- [`migrations/010_gold_labels.sql`](../../migrations/010_gold_labels.sql) — schema, triggers, and view.
- [`src/engram/interview/`](../../src/engram/interview/) — `errors.py`, `storage.py`, `sampler.py`, `agent.py`.
- [`docs/rfcs/0017-extraction-prompt-versioning.md`](../rfcs/0017-extraction-prompt-versioning.md) — prompt-template versioning convention.
- [DECISION_LOG.md](../../DECISION_LOG.md) — D044, D069, D079.
