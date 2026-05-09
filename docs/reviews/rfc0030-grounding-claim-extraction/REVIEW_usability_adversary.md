# RFC 0030 Public-Dataset Entity Grounding Adversarial Usability Review

author: usability-adversary-codex-gpt-5.5-001

Status: review
Date: 2026-05-09
RFC refs: RFC-0030
Decision refs: D020, D044, D068, D076, D080
Phase refs: PHASE-0003, PHASE-0004

Lens: adversarial usability — assume the operator is overloaded and just
wants the extractor to stop misidentifying entities; find places this
proposal will impose ongoing operator burden or invite mistakes.

## Findings

### U001 - Persistent grants with no expiry rot into invisible state
Severity: major
Source: § D-F grant model

The RFC recommends "per agent role, persistent until revoked." Six
months later, an operator has eight grants, can't remember which roles
have access to which datasets, and is afraid to clean up because they
don't know which extractions depend on which grants. This is the
"saved passwords" failure mode.

The RFC mentions an audit log of access; it does not mention any
*reminder* surface. An operator will not run `engram grants list`
unless something prompts them to.

Suggested fix:
- Surface active grants in the daily/weekly run summary (one line:
  "active grants: extractor reads wikidata, geonames").
- Add an optional grant TTL (default off; on by operator request) so
  expiry forces a periodic re-confirmation.
- Make `engram grants list --usage` show "last accessed: 32 days
  ago" so unused grants are visible.

### U002 - Snapshot freshness has no operator-facing dial
Severity: major
Source: § D-E; § Open questions Q5/Q6

The RFC says snapshots are operator-curated. No surface tells the
operator their active snapshot is six months stale. No surface tells
them when the upstream dataset shipped a new version. No surface
tells them what changed between snapshots.

A tired operator who set up grounding once will never refresh the
snapshot. Six months in, they have grounded resolutions against a
world that no longer exists, and their `dataset@2026-04-15` provenance
labels are factually correct but operationally meaningless.

Suggested fix:
- `engram grounding status` command that shows: active snapshot, age,
  upstream's most-recent-known version, optional "since you snapshotted
  N entities were added/changed/removed in your subset" if cheap to
  compute.
- Run-summary header line: "active snapshot is 187 days old (wikidata
  released 2026-09-01)" when applicable.

### U003 - Silent downgrade rewards inattention
Severity: major
Source: § Open questions Q7

"Silent downgrade with a one-line warning per run" means: an operator
who has grants today and revokes them tomorrow gets the same
extraction-runs-fine experience, just without grounding. They may not
notice for weeks. By then the claims under the new prompt-version are
all ungrounded, mixed with prior grounded ones in the same `claims`
table, and the operator has to do `re-extract --version` work to
sort it out.

Suggested fix: stronger middle ground than "silent" or "fail-closed":
- A persistent state file (`~/.engram/grounding/active-grants.lock`)
  that is rewritten only when grants change.
- If extraction starts and the lock file says "grounding was active
  yesterday but no grants now", **prompt** the operator (interactive)
  or **fail with a one-flag override** (non-interactive).
- One-flag override surfaces in run summary so a benchmark observes it.

### U004 - Interview UI candidate disambiguation is operator-disruptive
Severity: major
Source: § D-C; § Open questions Q2/Q4

D-C wants interview to handle disambiguation. The interview is currently
a fast yes/no/unsure surface. Adding "and which of these 5 candidates
is right" doubles or triples the time per interview question. For a
tired operator, this is the difference between getting through 100
claims in an hour and getting through 30.

Suggested fix:
- Default to "show only top-1 candidate above threshold X". Below
  threshold, show "see N candidates" affordance (don't expand by
  default).
- Allow the operator to set per-domain confidence thresholds in
  `engram grounding config` (default conservative).
- Track per-operator interview latency; if grounding is making
  interviews slower, the spec acceptance criteria fails.

### U005 - "Tartine" example reveals an unaddressed naming-collision class
Severity: major
Source: § Motivation; § Open questions Q4

The RFC names "Tartine" as a case where resolver wants bakery, user
means a friend's nickname. The proposal's answer is "interview UI
disambiguates." That is not an answer for nicknames *of friends*,
because the friend is a private entity that won't be in any public
dataset.

The operator has to: see "Tartine → Tartine Bakery" in the interview,
correct it (verdict false?), and then... what? The system doesn't
learn this is a private nickname. The next mention of "Tartine"
re-resolves to bakery.

Suggested fix: spec must include a per-corpus "alias suppression" or
"private entity override" surface. The operator's interview correction
should populate a private alias table that the resolver consults
*first*. Without this, the same false grounding repeats every segment.

### U006 - Reversibility is theoretical, not ergonomic
Severity: minor
Source: § Privacy and provenance (revocability)

The RFC names re-extraction under no-grant configuration as the
operator's tool for rolling back. Re-extraction is a multi-hour,
multi-stage process that requires the operator to:
1. Revoke grants.
2. Bump `EXTRACTION_PROMPT_VERSION`.
3. Run `engram phase3 re-extract --version vN+1`.
4. Re-run interview against the new claims.

That is not "reversible." That is "redoable." For a feature that may
go wrong, redo cost is the operator's risk premium.

Suggested fix: name a faster path. Specifically:
- `engram grounding detach --segment <id>` removes external_reference
  rows for one segment without re-extraction.
- `engram grounding detach --all-since <date>` for bulk detach.
- These leave claim rows intact but unground them.

### U007 - Bench gate hides operator-decision burden
Severity: minor
Source: § Promotion path step 3; § D-H

Step 3 is "Bench v1 on a 100-segment slice ... if the slice shows no
improvement, return to the design loop." The hidden assumption is that
*the operator* runs this and decides. After running grounded
extraction on 100 segments, then re-running interview on those 100,
then comparing to v8 baseline, the operator has spent maybe three
hours of their day to learn whether grounding helped. If it didn't,
they redesign. That is a heavy gate.

Suggested fix: build a `engram phase3 grounding-bench` automation that:
- Runs the grounded slice extraction.
- Runs the v8 baseline slice extraction (if not already cached).
- Surfaces a single number: false-rate-delta on entity-mismatch class.
- Surfaces a recommendation: "promote / reject / inspect manually".
- The operator decision becomes "I trust this; proceed" rather than
  "I personally compared 100 claims".

### U008 - First-run download experience has no progress feedback story
Severity: minor
Source: § D-A; § Promotion path

`engram grounding snapshot --dataset wikidata` will download ~10 GB.
Operators are used to package downloads with progress bars; engram's
existing CLI is generally JSON-first and quiet. A 10 GB silent
download will worry an operator into killing the process and trying
again, multiple times.

Suggested fix: spec must say the download command shows a progress
indicator (TTY-detected: bar; non-TTY: periodic JSON status lines).
Also says how to resume a partial download.

## Open questions

- Does the spec ship a "grounding tour" command that walks operators
  through the six-step onboarding?
- Is the operator's interview verdict on a wrong-grounding case
  feedback, or just a "false" mark on the claim?

verdict: accept_with_findings
