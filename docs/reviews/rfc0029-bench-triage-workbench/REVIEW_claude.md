# RFC 0029 Bench Triage Workbench Review — claude

author: reviewer-claude-opus-001

Status: review
Date: 2026-05-09
RFC refs: RFC-0029
Decision refs: D020, D074, D082
Phase refs: PHASE-0003-FOLLOWON, PHASE-0004

## Findings

### F001 — Privacy-tier ceiling escape clause regresses from RFC 0027 posture
Severity: major
Source: docs/rfcs/0029-bench-triage-workbench.md § "Routes" and § "Privacy and Security"

RFC 0029 says "The default ceiling is Tier 1. A higher ceiling requires an
explicit CLI flag and is never implied by opening an existing scratch artifact."
RFC 0027 v1 hard-coded the Tier 1 ceiling at the route layer with **no escape
clause** in v1; the env var name was reserved but not implemented, with
higher-tier rendering deferred to v1.1. The bench workbench inherits the same
loopback / single-operator threat model and the same browser-tab risk surface,
so the same posture should apply. A CLI flag that lifts the ceiling is more
permissive than RFC 0027 in a context where the artifacts under review
(benchmark slices on private corpus) are at least as sensitive as the gold-set
interview surface. The RFC should either (a) hard-code Tier 1 in v1 with the
higher-tier env var reserved-but-unimplemented, mirroring RFC 0027, or
(b) justify in writing why the bench surface needs a divergent escape clause
the gold-set surface explicitly refused. Option (a) is the safer default.

### F002 — Same-origin/CSRF posture is named but not specified
Severity: major
Source: docs/rfcs/0029-bench-triage-workbench.md § "Privacy and Security"

The RFC says "same-origin checks reject unsafe cross-origin POSTs" in a single
bullet. RFC 0027's resolution to the same browser-tab threat (any tab on the
local machine can drive forms at `127.0.0.1:<port>`) was concrete: an `Origin`
header allowlist over `http://127.0.0.1:<port>` and `http://localhost:<port>`
plus `Sec-Fetch-Site: same-origin` enforcement on every mutating route, with
403 on mismatch and a v1 enforcement test. RFC 0029 should adopt the same
language verbatim and enumerate which routes are mutating
(`POST /segments/{segment_id}/decision`, `POST /export`). The mutating route
list is small enough to bind by name, and inheriting RFC 0027's exact spec is
both safer and reduces drift between two near-identical local web surfaces.

### F003 — `POST /export` web route writes outside scratch
Severity: major
Source: docs/rfcs/0029-bench-triage-workbench.md § "Routes" and § "CLI commands"

`POST /export` writes a redacted Markdown summary "to a user-provided path
under `docs/reviews/`" and "refuses paths outside `docs/reviews/` unless
`--allow-outside-reviews` is passed" (the `--allow-outside-reviews` line is
under the CLI subcommand, but the route table also lists `POST /export` and
implies the same capability). A web route that writes into the tracked working
tree from a browser form — even with a path allowlist — is a category of
surface that did not exist in RFC 0027 (its export is CLI-only in v1, by
design). Two recommendations:

1. Drop `POST /export` from v1 routes. Make export CLI-only, mirroring
   RFC 0027's posture. The CLI already has `engram phase3 bench-review export`
   per § CLI commands; the web surface does not need a parallel write path
   that crosses the scratch boundary.
2. If a UI affordance for export is required, the web button should issue a
   GET that returns the redacted markdown body for the operator to save
   manually, leaving every tracked-tree write to an explicit CLI invocation.

This keeps the scratch ↔ tracked-tree boundary mechanical: scratch state is
written by the running workbench; tracked exports are written only by an
explicit operator CLI command.

### F004 — `--allow-outside-reviews` widens the export blast radius without need
Severity: minor
Source: docs/rfcs/0029-bench-triage-workbench.md § "CLI commands"

`bench-review export` "refus[es] paths outside `docs/reviews/` unless
`--allow-outside-reviews` is passed." The RFC offers no use case for an
out-of-tree export. If the operator has a private destination, they can pipe
the markdown through their own command. Removing the flag in v1 keeps the
export contract single-purpose: the only legitimate destination is a tracked
review file under `docs/reviews/`, which is precisely the boundary the rest of
the document defends. Add the flag back in a follow-on RFC if a real use case
materializes.

### F005 — Tracked-export contract should explicitly forbid notes by default
Severity: minor
Source: docs/rfcs/0029-bench-triage-workbench.md § "Review state" and § "CLI commands"

The RFC says notes "must not be copied into tracked exports unless the export
command is explicitly run with `--include-notes`" and that exports include
"redacted notes only if `--include-notes` is passed." Two reinforcements
worth folding into the contract before implementation:

1. Notes are free-text; an operator can paste private corpus text into them.
   The default redacted export should drop the notes column entirely (not
   merely truncate or scrub), and `--include-notes` should print a startup
   warning and prompt for confirmation when the destination is under
   `docs/reviews/`. This matches the project pattern of making the privacy
   action mechanical, not procedural.
2. `--include-notes` should also be a tracked decision: the export header
   should record whether notes were included, so a future reader can tell
   whether the file is "redacted by default" or "operator opted into note
   inclusion."

### F006 — Scratch SQLite is the right v1 boundary; reaffirm the no-derivation rule
Severity: nit
Source: docs/rfcs/0029-bench-triage-workbench.md § "Review state" / Open Question 1

SQLite-under-`.scratch/` is the right answer for v1: production-DB write paths
must protect raw evidence (immutability, evidence-id chains, prompt/model
versions), and the workbench's review labels are operator scratch, not raw
evidence and not derivations of it. The RFC already says so. One small
addition: state explicitly that benchmark-review decisions never feed
production derivations — they are not consumed by extraction, consolidation,
or interview pipelines, even read-only — so the RFC's promise that the
workbench leaves canonical tables untouched holds at the read side as well as
the write side. This pre-empts the future temptation in Open Question 1 to
promote the SQLite table into an append-only Postgres table that beliefs or
claims pipelines might learn to read; the right move there is to keep
derivations rooted in raw evidence per the project's "raw is sacred" stance,
not in operator triage labels.

### F007 — Static assets path should match RFC 0027's vendoring spec
Severity: nit
Source: docs/rfcs/0029-bench-triage-workbench.md § "Shape" and § "Relationship to RFC 0027"

The RFC says "Static assets are package-local and served by the app; no
network asset fetch is allowed." RFC 0027 is more concrete: htmx is vendored
at `src/engram/interview/static/htmx.min.js`, served from the wheel, with no
CDN reference reachable from any rendered page. RFC 0029 should pin the
analogous path (`src/engram/bench_review/static/htmx.min.js`) and the wheel
packaging requirement, so the no-CDN constraint is mechanical at packaging
time, not at code-review time. While here, mention `[tool.setuptools.package-data]`
parity with RFC 0027 so the static asset is guaranteed to ship inside the
wheel rather than relying on the source checkout.

### F008 — Loopback bind refusal needs an explicit `exit` code
Severity: nit
Source: docs/rfcs/0029-bench-triage-workbench.md § "Privacy and Security"

RFC 0027 specifies "any non-loopback `--host` is refused at startup with exit
8 and there is no `--allow-non-loopback` flag." RFC 0029 says only "non-loopback
bind is refused in v1." Adopt the same exit code (or a new one if 8 collides)
and the same explicit "no escape flag" wording. This is small but the kind of
detail that tends to drift between two parallel local web surfaces during
implementation; pinning it in the RFC saves a downstream review cycle.

### F009 — Acceptance criteria omit a CDN-egress test
Severity: nit
Source: docs/rfcs/0029-bench-triage-workbench.md § "Tests and Acceptance Criteria"

The acceptance list covers loaders, classifiers, storage, FastAPI routes,
exports, and CLI; it does not name a test that asserts every rendered page's
HTML references no `https://`-scheme asset and that the served `htmx.min.js`
is read from the package, not fetched. RFC 0027 made the no-CDN posture a
test (the htmx-served-from-static check). Add the analogous test here so the
RFC's "no CDN" promise is enforced rather than aspirational.

### F010 — Implementation plan should specify shared-helper extraction discipline
Severity: nit
Source: docs/rfcs/0029-bench-triage-workbench.md § "Relationship to RFC 0027"

The RFC says "Shared web helpers may move to a small common module only if
implementation shows real duplication in loopback checks, template setup, or
htmx static serving. That extraction should be narrow and tested." This is
the right instinct, but in practice the candidates are knowable from RFC 0027
today: loopback-bind validation, the `Origin` allowlist + `Sec-Fetch-Site`
check, the htmx static handler, and the privacy-tier-ceiling decorator. The
RFC could call those four out by name as the candidate shared module
(`src/engram/web/`), so the implementation does not re-derive the answer or
quietly diverge two implementations of the same loopback check. This is also
the cleanest place to host the route-level Origin allowlist test once and
reuse it from both surfaces.

## Open questions

- Should the RFC explicitly state that the workbench's read-side connection
  to Postgres uses a role with no write privileges to claims, beliefs, raw
  evidence, audits, or projection tables? RFC 0027 inherits write capability
  from `engram.interview.{agent, storage}`; RFC 0029 has no business writing
  to canonical tables at all, so a read-only role would make the boundary a
  database-level invariant rather than an application-level one.
- Should the export contract pin a "no segment IDs from any privacy_tier > 1
  segment" filter for default tracked exports? Segment IDs alone are not
  corpus text, but in a small slice they can identify a specific private
  conversation by external reference. v1 may be willing to live with that;
  the RFC should at least name it.
- Is a per-run "promotion verdict" worth a small explicit field in
  `review_sessions`? Open Question 4 in the RFC asks this. From a
  privacy-and-immutability standpoint either answer works; from an "easy to
  audit later" standpoint a single explicit run-level verdict is cheaper
  than reconstructing it from per-segment decisions.

verdict: accept_with_findings
