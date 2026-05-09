# RFC 0030 Public-Dataset Entity Grounding Adversarial Privacy Review

author: privacy-adversary-claude-opus-001

Status: review
Date: 2026-05-09
RFC refs: RFC-0030
Decision refs: D020, D044, D068, D076, D080
Phase refs: PHASE-0003, PHASE-0004

Lens: adversarial privacy and network-boundary review. Assume the RFC will
be implemented as written; find any path by which corpus content, agent
metadata, or operator activity could leak across the local-first boundary.

## Threat model summary

The RFC's privacy posture rests on five non-negotiable constraints. The two
most load-bearing — "no live web at extraction time" and "personal evidence
does not leave the machine" — are stated as policy, not enforced by code
shape. The grant model and snapshot discipline are well-named but
underspecified at integrity, audit, and process boundaries. There is no
explicit defense against poisoned or swapped snapshots, no mention of
supply-chain integrity at fetch time, and no commitment to a chokepoint
that makes "no live web at extraction time" grep-checkable.

This review treats each of these as exploitable until the RFC commits to
specific defenses.

## Findings

### P001 - Dataset acquisition leaks operator IP and dataset selection to a third-party host
Severity: minor
Source: § Non-negotiable constraints item 2; § D-A; § D-E

Attack model: passive observer. The operator runs `engram grounding
snapshot --dataset wikidata`; the fetcher resolves a hostname (Wikidata
download mirror, GeoNames host) and downloads ~10 GB. The mirror operator
sees: operator IP, user-agent, dataset id, snapshot date, and download
volume. None of this is corpus content; all of it is correlatable
identifying metadata about the operator's grounding posture.

Rationale: the RFC says corpus content does not leave the machine, which
is true. But it implicitly extends "local-first" to a stronger claim
("nothing identifying leaves the machine") that the dataset-fetch path
violates. Engram's prior position (D020 LLM-local-only, no telemetry) sets
a higher bar than the RFC currently meets.

Suggested fix: name explicitly that dataset acquisition is a sanctioned
network-boundary crossing and that the network footprint is exactly
"public dataset metadata + IP", nothing more. This is a documentation fix,
not an architectural one. Without it, future readers will misread the
constraint and weaken it inadvertently.

### P002 - Snapshot integrity not pinned; "swap" attack is silent
Severity: blocking
Source: § D-E snapshot discipline; § Non-negotiable constraints item 5

Attack model: local attacker (or accidental file-system corruption). The
snapshot directory at `~/.engram/grounding/<dataset>/<snapshot_id>/` is
identified by an opaque label (e.g., `wikidata@2026-04-15`) but the RFC
does not commit to a content hash recorded with the label. Two failure
modes follow:

1. A malicious or compromised mirror serves a tampered snapshot.
   Subsequent extractions ground claims against poisoned data; the
   provenance row records the label honestly, but the world it points
   at is not the world the operator intended.
2. A user accidentally edits a file in the snapshot dir (or restores
   from a partial backup). All future grounded extractions under that
   label silently produce different results; reproducibility — the RFC's
   fifth non-negotiable — is broken.

Rationale: "snapshot reproducibility" requires that `dataset@snapshot`
identifies a *world*, not a *directory name*. Without an integrity
guarantee, the label is a wish, not a fact.

Suggested fix: D-E must commit to (a) recording a content hash (e.g.,
SHA-256 of a Merkle-rooted index over the snapshot files) at registration
time, (b) verifying that hash on every load, and (c) refusing to load —
loud failure, not silent — when verification fails. The hash becomes part
of the snapshot id: `wikidata@2026-04-15@sha256:abcd...` or a separate
stored record.

This is the single change that turns "snapshot reproducibility" from
documentation into an invariant.

### P003 - "No live web at extraction time" is policy, not a chokepoint
Severity: blocking
Source: § Non-negotiable constraints item 1; § Promotion path step 4b

Attack model: future drift. The RFC commits to no live web at extraction
time but does not name where this is enforced. The current
`src/engram/extractor.py` happens to have no HTTP client, but nothing in
the RFC prevents a future commit (perhaps reasonable on its face — "let's
add a live Wikidata fallback for entities not in the snapshot, just for
this one case") from quietly weakening the constraint.

Rationale: the constraint is the RFC's strongest privacy claim. It needs
to be grep-checkable: a reviewer should be able to scan
`src/engram/grounding/` and `src/engram/extractor.py` for any HTTP-client
import (`urllib`, `requests`, `httpx`, `aiohttp`) and assert *none*.

Suggested fix: § Non-negotiable constraints should add a "Code-side
enforcement" subsection that:
- names the modules where HTTP clients are forbidden;
- commits to a unit test that asserts the module list is HTTP-client-free
  via `ast` walk;
- excludes the dataset-acquisition module (`engram grounding snapshot`)
  from this assertion explicitly, with the rationale documented in code.

### P004 - Poisoned dataset content can exfiltrate via prompt-time hint propagation
Severity: major
Source: § D-B option 3 hybrid; § D-G extraction prompt impact

Attack model: malicious dataset publisher. The hybrid resolver placement
puts a "candidates, not facts" hint block into the extraction prompt. A
malicious or compromised public dataset could include records whose
description fields contain prompt-injection payloads designed to trigger
the local LLM to:
- emit specific surface-form claims that encode attacker-chosen
  predicates;
- paste back portions of the segment under attacker-controlled labels;
- extend output beyond the schema in ways the JSON parser tolerates.

Rationale: the local LLM (D020) does not call out to a network — but it
*does* receive operator-corpus content as input alongside the candidate
hints. If the LLM's output is logged, persisted, or subsequently sent
anywhere (interview UI rendering, benchmark artifacts), prompt-injected
output containing reflected corpus snippets is a leak vector even though
no network call is made.

Suggested fix:
- Treat dataset content as untrusted input. Apply the same content
  sanitization the RFC applies to corpus segments before insertion into
  the prompt.
- Pin specific dataset description fields (Wikidata `schema:description`,
  GeoNames `description`) and reject control characters, prompt-shape
  patterns, and inflated lengths.
- Document this in D-B as "candidate descriptions are sanitized; the LLM
  cannot be given dataset text in a way that lets the dataset author
  shape extraction output."

### P005 - Grant audit log location and retention unspecified; potential cross-machine leakage
Severity: major
Source: § D-F grant model; § Why this fits the principles (auditability)

Attack model: dotfile-sync exfiltration. The RFC commits to a grant audit
log but does not name the storage. Plausible homes:
- Production PostgreSQL (drags grant-exercise volume into a schema
  reachable by anyone with DB read access; reveals corpus shape).
- Scratch SQLite at `~/.engram/grants/audit.sqlite3` (better, but
  vulnerable to dotfile sync via `chezmoi`, `mackup`, or Dropbox-mounted
  home directory; logs replicate cross-machine without operator intent).
- Plain JSONL append log (worst — easily indexed by file-search tools).

Rationale: the audit log must be local-machine-bound, not just
local-host-bound. The RFC currently does not state which.

Suggested fix: D-F must:
- name the storage (recommended: scratch SQLite under
  `~/.engram/grants/` with a `.engram-no-sync` marker file);
- name a retention policy (recommended: 90 days of access, then
  truncate);
- name an explicit non-sync stance: the grant log is per-machine, never
  syncs.

### P006 - Snapshot-file paths can be observed by other processes; no mode-bit guidance
Severity: minor
Source: § D-E; § Privacy and provenance

Attack model: shared-machine observer. Snapshot directories at
`~/.engram/grounding/<dataset>/<snapshot_id>/` are listable by any user on
the same machine unless mode bits are tightened. Other users (or other
processes running as the same operator under different roles) can
enumerate which datasets the operator has snapshotted, when, and at what
size.

Rationale: not corpus exfil, but a fingerprint of operator interest. On
a single-user laptop this is moot; on a dev box, server, or container
host, it is a nontrivial signal.

Suggested fix: name expected file mode bits in D-E (snapshot dirs at
0700, manifest files at 0600). State that engram refuses to use a
snapshot dir with looser permissions — loud failure, not silent.

### P007 - "Grounding" boundary not protected against future redefinition
Severity: major
Source: § Non-negotiable constraints; § What this RFC does not propose

Attack model: future RFC drift. The RFC says "no live web calls from the
extraction loop" and "no remote LLM calls" and "no grounding for
private/personal entities". These are stated as scope boundaries, not as
invariants. A future RFC could legitimately redefine "grounding" to
include a "lightweight live verification call" or "a remote disambiguator
service" — softening the boundary while still using the word "grounding"
on operators who built mental models around the original promise.

Rationale: privacy constraints are most fragile when the words protecting
them can be redefined. The RFC's strength is precisely in its stated
non-negotiables; that strength should be locked.

Suggested fix:
- promote the five non-negotiables to a new D### entry in the decision
  log (recommend acceptance criterion at promotion time);
- state that any future change to those five requires a new D### that
  names its predecessor and explicitly supersedes;
- restate this protection in the RFC's "Promotion path" section.

### P008 - Resolver output may surface in benchmark logs and interview UI rendering
Severity: minor
Source: § D-H eval oracle; § D-C output shape

Attack model: data-flow leakage. The resolver attaches candidate sets to
claims; D-H proposes measuring grounded-extraction quality via
operator-false-rate, which implies the interview UI surfaces the
resolution choices alongside corpus segments. If the workflow's tracked
review artifacts (per RFC 0029's bench-triage workbench, or any future
review export) include resolution prose, that prose may inadvertently
include resolved entity descriptions that reveal which Wikidata QIDs the
operator is engaging with.

Rationale: this is one redaction-policy step away from a leak surface.
RFC 0029's redaction policy is well-thought-out for raw segment text; it
does not yet contemplate grounded-resolution prose.

Suggested fix: extend D-C with a redaction rule: tracked exports may
record candidate QIDs / dataset-ids and confidence scores, but not the
descriptive prose attached to those candidates. Resolved-entity
descriptions stay in scratch state.

### P009 - First-run posture: silent downgrade rewards inattention
Severity: minor
Source: § Open questions Q7; § D-F default posture

Attack model: privacy-by-accident-erosion. The RFC's recommended seed for
Q7 is silent downgrade with a one-line warning when grants are missing.
This means an operator who installs engram, never grants a dataset, and
runs extraction gets ungrounded results — fine — but also an operator
who *had* grants, revoked them, and forgets gets the same output without
salient feedback. Privacy posture is strongest when the system says
loudly "you turned this off" rather than quietly continuing.

Rationale: silent downgrade is the user-friendly default but it makes
privacy posture invisible. Engram's local-first stance says invisibility
is a smell.

Suggested fix: prefer "silent downgrade with a header line in the
benchmark/extraction summary that names the active grants." A summary
header is not loud-fail, but is observable. Q7's recommended seed should
be re-stated this way.

## Threat model summary

The RFC's privacy posture is *defensible* but not yet *defended*. The
strongest fixes are:

- P002 (snapshot integrity hash): without this, "reproducibility" is a wish.
- P003 (chokepoint enforcement of "no live web"): without this, the
  central privacy claim is convention.
- P007 (lock the non-negotiables in the decision log): without this,
  future drift can soften the promise.

P004 and P005 are major; the rest are tightening fixes.

verdict: needs_revision
