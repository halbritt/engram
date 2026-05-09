# RFC 0030 Public-Dataset Entity Grounding Review - claude

author: reviewer-claude-opus-001

Status: review
Date: 2026-05-09
RFC refs: RFC-0030
Decision refs: D020, D044, D068, D076, D080
Phase refs: PHASE-0003, PHASE-0004

Lens: privacy posture, local-first constraints, and decision-log compatibility.

## Findings

### F001 - Five non-negotiable constraints stated as policy, not enforced by code shape
Severity: major
Source: § Non-negotiable constraints (lines ~52-86)

The constraints are correctly identified and prominently placed, but the RFC
does not commit to *where* each constraint is enforced in the code path.
"No live web at extraction time" is satisfiable today only because
`src/engram/extractor.py` lacks an HTTP client; nothing prevents a future
edit from adding one. "Personal evidence does not leave the machine" relies
on convention rather than a chokepoint.

The RFC promotes itself as adversarial-review-friendly; it should name the
single accessor through which every grant check runs (so a reviewer can grep
for it), and it should commit to a unit test that asserts the resolver does
not import any HTTP client. Privacy posture is much stronger when the
constraint is grep-checkable than when it is documented.

Suggested edit: add a "Code-side enforcement" subsection to "Non-negotiable
constraints" that names the accessor module, the prohibited imports, and the
test that locks them.

### F002 - Grant-log storage location unspecified; the natural place is scratch SQLite
Severity: major
Source: § Privacy and provenance, § Why this fits the principles, § D-F grant model

The RFC says grants are "operator-driven, enumerable, and revocable" and
mentions an "audit log of access," but does not name the storage. Two
plausible homes are production PostgreSQL and scratch SQLite. The
local-first posture argues for scratch SQLite at `~/.engram/grants/` (or
similar): grants are operator-local state, not shared evidence. Putting
them in production PostgreSQL drags a privacy concern (grant-exercise
volume reveals corpus shape to anyone with DB read access) into the
production schema.

This is also relevant to D068 (artifact-id model). Grants and snapshot
manifests are artifacts; their IDs and lifecycle must fit D068's scheme,
or D068 needs an explicit carve-out.

Suggested edit: name the grant-log location and the artifact-id treatment
in § D-F.

### F003 - Snapshot integrity guarantees not specified; "swap" attack is undefended
Severity: major
Source: § D-E snapshot discipline, § Privacy and provenance

The RFC commits to versioned snapshots stored under
`~/.engram/grounding/<dataset>/<snapshot_id>/` but does not commit to an
integrity guarantee on those directories. Two failure modes follow:
(a) a downloaded snapshot whose tarball is corrupted silently corrupts
all future grounded extractions under that label; (b) a swapped snapshot
(deliberate or accidental) produces grounded claims whose provenance lies
about which world they were resolved against.

The simplest fix is to record a content hash with the snapshot id and
verify on every load. This also makes "snapshot reproducibility" mean
something concrete — same id + same hash = same world.

Suggested edit: D-E should say "snapshot id is `<dataset>@<date>` AND
content hash is recorded; the resolver refuses to load a snapshot whose
hash has changed since registration."

### F004 - Hybrid resolver placement biases extraction without an explicit guard
Severity: major
Source: § D-B Resolver placement (option 3 / hybrid)

The recommended hybrid passes a "candidates, not facts" hint block into
the extraction prompt. The risk this introduces is silent: a high-
confidence resolver hint about a surface form ("Tartine = Tartine
Bakery") biases the LLM toward extracting `entity_kind=organization`
even when, in this segment, the operator meant a friend's nickname for
the same word.

D-C's full-candidate-set output partly mitigates this on the
post-extraction attachment side, but does not protect the *extraction
itself* from being subtly skewed by the hint. The interview UI then sees
an already-biased extraction.

The RFC needs to either:
- defend the bias as acceptable (with rationale: "the LLM is bad at
  guessing entity kind, the hint helps more than it hurts"); or
- specify a prompt-shape guard (e.g., "candidates appear under a
  CANDIDATES-ONLY-HINTS section that the prompt explicitly tells the
  model not to treat as ground truth").

Without one of these, the hybrid choice is doing exactly what
"refusal-of-false-precision" forbids: collapsing ambiguity at extraction
time.

Suggested edit: D-B option 3 should include the prompt-shape guard, with
a sample sentence the prompt will use to frame the candidate block.

### F005 - RFC 0019 batching interaction not addressed; per-segment candidate budget may compound
Severity: minor
Source: § D-G extraction prompt impact

D-G caps the candidate block at ~1000 tokens per segment. RFC 0019 (and
the active RFC 0023 concurrent extraction work) batches multiple
segments per request. The RFC does not state whether the cap is per
*segment* or per *batch*. If 16 segments × 1000 candidate tokens land
in one batched prompt, D076's 32k budget is gone. The RFC should pin
this explicitly: per-segment cap with batch-level fail-fast if the
total exceeds budget.

Suggested edit: D-G should add "When extraction is batched, the
per-segment cap is enforced per-segment; the batched prompt aborts
construction if total candidate-block tokens exceed `CANDIDATE_BATCH_CAP`
(default 8000 tokens)."

### F006 - Grant-log placement under role-based scope is correct but does not address agent-process variation
Severity: minor
Source: § D-F grant model

D-F recommends "per agent role, persistent until revoked." This works
for striatum lanes (codex / claude / gemini are role-typed). It is
unclear whether a CLI invocation outside striatum (e.g., `engram phase3
re-extract`) carries a role, and if not, whether it inherits the
operator's grants by default. Default-deny would be safer; default-
operator-inherits matches everyday ergonomics. Pick one; state it.

Suggested edit: name the default for non-role-typed invocations.

### F007 - RFC 0028 subject_kind_hint interaction (Q2) underspecified
Severity: minor
Source: § Open questions for the design loop, Q2

RFC 0028's `subject_kind_hint` and RFC 0030's external references both
attach entity-typing information. The RFC asks whether they are
orthogonal or one deepens the other. The honest answer is "orthogonal,
but the hint should narrow the candidate-type filter": if RFC 0028 says
`subject_kind=person`, the resolver should refuse Wikidata candidates
of class `Q1656682` (organization). The RFC should state this
intersection rule rather than punt.

Suggested edit: Q2 should pick "deepening with type-narrowing" and
specify the precedence.

### F008 - Decision log compatibility check incomplete (D068 artifact-id model)
Severity: minor
Source: front-matter / context refs

The RFC names D020, D044 only briefly via context refs and does not
walk D068, D076, D080 explicitly. D068 (artifact-id model) is most
relevant: every snapshot manifest, grant exercise, and resolution log
entry is an artifact in D068's sense and needs an `art_*` id with the
documented anchor scheme. The RFC should call this out and confirm
the apply path.

Suggested edit: add a "Decision-log compatibility" subsection or
expand the front-matter context list to call out each Dxxx affected.

## Open questions

- Where does the grant-log live (scratch SQLite vs production PG)?
- Does dataset acquisition pin content hashes or just URLs?
- What prompt-shape guard prevents hint-bias at extraction time?
- Is the batching cap per-segment, per-batch, or both?

verdict: accept_with_findings
