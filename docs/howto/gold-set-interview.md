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

| Subcommand | Status |
|------------|--------|
| `start` | Opens a session, samples N targets, runs an interactive question-by-question loop on a tty, commits each verdict as it's answered, marks the session complete on exhaustion. `--non-interactive` skips the loop for scripts/tests. |
| `resume` | Looks up a session by id and prints whether it is open. |
| `history` | Prints the recorded verdicts for a `--target <uuid>`. |
| `export` | JSONL dump of `gold_labels` filtered by `--privacy-tier-max` (default 1). |
| `list-sessions` | Lists sessions, optionally filtered by `--state open|completed`. |
| `coverage` | Counts rows by `stability_class`. |
| `enable-active-learning` | Records the operator-visible at-scale signal version. |

Press `q` (or Ctrl-C) at any verdict prompt to save-and-quit; the session
stays open and a resume hint is printed. Resume with
`engram phase3 interview resume --session-id <uuid>` (currently a status
check; running `start` with the same `--seed` re-samples the same target
set against the same session if you commit each verdict yourself via the
Python harness shown below).

## Prerequisites

All commands in this guide run from the **engram repo root** (the directory
that contains `Makefile`, `pyproject.toml`, and `src/engram/`). If you are
starting cold:

```sh
git clone https://github.com/halbritt/engram.git
cd engram
make install          # creates .venv, installs the engram package editable
make migrate          # local Postgres; or `make migrate-docker` for the compose Postgres
```

`make install` writes `.venv/.installed` and exposes the CLI as
`.venv/bin/engram`. Either activate the venv (`source .venv/bin/activate`)
or call the binary directly (`.venv/bin/engram phase3 interview …`); the
plain `engram` examples below assume the venv is active.

**If your database already exists** from prior Engram work, you still need
to run `make migrate` after pulling — migration 010 may not have applied
yet. The migration runner is idempotent and only applies missing files.
The symptom of skipping it is `psycopg.errors.UndefinedTable: relation
"gold_label_sessions" does not exist` on the first `start`.

You also need a populated Phase 3 belief set. If `current_beliefs` is empty,
`start` returns zero sampled targets and exits cleanly. To get there from
empty: ingest at least one export (`make phase1-ingest-chatgpt PATH=...`),
then `make phase2-run` and `make phase3-run`. See the README's Operator
Quick Start for the full bootstrap.

## Your first session

On a tty, `start` runs the interactive loop directly:

```sh
engram phase3 interview start --n 5 --seed 4
```

Output (illustrative):

```text
session: <uuid>  seed: 4  sampler: stratified@stratified.v1.d079.initial  sampled: 5
verdicts: t/f/stale/unsupported/unsure/skip   q to save and quit

[1/5] belief 7f3a…  stability=project_status  conf=0.87  conf_band=0.8-1.0  recency=<30d  status=accepted
  user -[works_at]-> Acme Corp
  evidence: 3 row(s), valid 2024-11-12..2025-08-04
  Q: Is this currently true?
verdict [t/f/stale/unsupported/unsure/skip] (q to save and quit) > t
rationale (Enter to skip) > still here, role unchanged

[2/5] ...
```

Each verdict commits as soon as you type it. Closing the terminal mid-loop,
hitting Ctrl-C, or typing `q` all leave the session open with whatever
verdicts you've already given preserved. The runner prints a resume hint
on exit.

```sh
engram phase3 interview list-sessions --state open
# → lists open sessions, including any you've abandoned mid-loop

engram phase3 interview history --target <belief-or-claim-uuid>
# → all verdicts on that target across sessions, newest first
```

## Web UI (alternative to the CLI loop)

`engram phase3 interview serve` runs a local browser UI for the same
interview surface (RFC 0027 / spec 0027). The app binds to
127.0.0.1 by default; non-loopback hosts are refused. There is no
auth and no TLS — same posture as the CLI.

```sh
# install the optional FastAPI / Uvicorn / Jinja2 deps if you haven't yet
pip install -e ".[serve]"

# start the server
engram phase3 interview serve            # http://127.0.0.1:8765
engram phase3 interview serve --port 9000
```

Open `http://127.0.0.1:8765/` in your browser. The index page lists
open sessions and exposes a "New session" form (`n`, `seed`). Click
"Start" and you'll be on a per-question page with the same metadata
the CLI shows: header, predicate gloss, evidence excerpts, and the
six verdict buttons. `true` and `skip` commit on a single click;
`false` / `stale` / `unsupported` / `unsure` reveal a verdict-specific
rationale prompt before committing. Press `?` to see all keyboard
shortcuts; `Esc` closes the help. `q` (or the "Save and quit" button)
leaves the session open and prints a resume command.

The CLI loop continues to work unchanged — sessions started in the
CLI are resumable in the web UI and vice-versa, since both write to
`gold_label_sessions` and `gold_label_session_targets`.

What the web UI does NOT expose in v1 (CLI-only): `export`, `history`,
`coverage` (a small inline strata strip ships in v1; the dashboard is
deferred), `enable-active-learning`, `--include-superseded`,
`--ignore-cooldown`. Drop to the CLI for those.

## Driving the loop from your own code

If you want to script the loop (e.g., feed verdicts from a file, or wrap
the agent in a richer UI), `InterviewAgent` exposes the record path
directly:

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
- **`UndefinedTable: relation "gold_label_sessions" does not exist`** —
  migration 010 hasn't been applied to your database. Run `make migrate`
  (or `make migrate-docker`); the runner is idempotent.

## Where to read next

- [`docs/rfcs/0021-gold-set-interview-curation.md`](../rfcs/0021-gold-set-interview-curation.md) — design contract.
- [`migrations/010_gold_labels.sql`](../../migrations/010_gold_labels.sql) — schema, triggers, and view.
- [`src/engram/interview/`](../../src/engram/interview/) — `errors.py`, `storage.py`, `sampler.py`, `agent.py`.
- [`docs/rfcs/0017-extraction-prompt-versioning.md`](../rfcs/0017-extraction-prompt-versioning.md) — prompt-template versioning convention.
- [DECISION_LOG.md](../../DECISION_LOG.md) — D044, D069, D079.
