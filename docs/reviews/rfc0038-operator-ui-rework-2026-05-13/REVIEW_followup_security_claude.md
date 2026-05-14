# RFC 0038 Follow-up Local-First / Security Review

author: operator [self-declared: rfc0038-followup-security-review]

Status: review
Date: 2026-05-13
Lane: review_followup_security_claude
Workflow: `rfc-0038-operator-ui-rework-followup-2026-05-13`
RFC refs: RFC-0038
Spec refs: ENGRAM_UI_REWORK_HANDOFF.md, Spec 0027, RFC 0027, RFC 0028, RFC 0029
Decision refs: D044, D069, D074, D080, D081
Posture: security (local-first, no-CDN, CSRF/Origin, Tier 1 ceiling,
truthful-status copy, no weakening of DB validation or provenance)
Verdict: **needs_revision**

## Scope and method

This is the security-posture re-review for the RFC 0038 UI repair pass. Per
the work-packet review policy (`document_only`, `cross_round` context), I
read only the listed target documents and prior-round review artifacts. I
did not browse implementation files, the Striatum ledger, or other
repository contents.

Documents read for this pass:

- `AGENTS.md`
- `ENGRAM_UI_REWORK_HANDOFF.md` (design contract)
- `docs/rfcs/0038-operator-ui-rework.md`
- `docs/reviews/rfc0038-operator-ui-rework-2026-05-13/REVIEW_correctness_codex.md`
- `docs/reviews/rfc0038-operator-ui-rework-2026-05-13/REVIEW_ergonomics_claude.md`
- `docs/reviews/rfc0038-operator-ui-rework-2026-05-13/REPAIR_EVIDENCE.md`
- `docs/process/multi-agent-review-loop.md`
- `docs/process/project-judgment.md`
- `CHANGELOG.md`

The review checks five security-relevant constraints from the handoff and
the RFC:

1. local-only: loopback bind, no cloud, no telemetry, no hosted auth;
2. no-CDN: every asset served from the in-process static mount, no
   `https://` references to external hosts;
3. CSRF / Origin: every mutating route enforces the Origin allowlist
   plus `Sec-Fetch-Site: same-origin`, with the shared single
   enforcement point at `engram.web.origin.require_origin`;
4. Tier 1 ceiling: full-message, context, `evidence/all`, and bench
   excerpt routes 403 when target or carried tier > 1;
5. truthful-status: audit-footer text is operationally accurate, the
   bench "does not mutate production data" banner is present where
   decisions are committed, the Phase 4 disclosure is unsoftened, and
   no derived row claims canonical status.

The work-packet objective also names a sixth axis: route / test-fixture
changes during the repair must not weaken database validation or
provenance constraints. That is checked against the failing-test note
in REPAIR_EVIDENCE.md.

## Verdict summary

`needs_revision`.

- The no-CDN / local-only / loopback posture is **preserved** per the
  repair evidence and the surviving design contract. The repair
  introduces no new external asset references.
- The Tier 1 ceiling posture is **preserved**. The repair evidence does
  not document any change to tier handling, and no review finding
  weakens it. The DB trigger that rejected the new failing route test
  fixture is database validation working as designed; it is not a
  weakening signal.
- The CSRF / Origin posture is **not yet repaired to the RFC's
  single-enforcement-point target**. The correctness review's C004
  (bench POST origin guard fail-open for missing browser-origin
  metadata) is not mentioned in the repair evidence, and the
  ergonomics review's F001 documents that the shared
  `engram.web.origin.require_origin` helper exists but is not wired
  into either surface. The bench POST path is therefore likely still
  running the original local helper with the C004 fail-open shape.
- The truthful-status posture has two **open** local weaknesses that
  the repair did not address: F006 (the literal "does not mutate"
  banner is absent from `/segments/{id}`, the page where the operator
  actually commits decisions) and F019 (the interview audit footer
  template hard-codes `127.0.0.1:8765` as a default when the
  `bind_address` context variable is missing, which can produce a
  *literally untrue* bind line on a non-default port).

The handoff is explicit that the audit footer and the "does not
mutate" banner are not marketing copy — they are operator
trust-circuit-breakers (§6.3). A footer that can lie and a banner
absent from the commit-decision page are both load-bearing security
defects in this design.

## Findings

Severity is local-first / security severity, not generic correctness
severity. "Major" means a contract from the handoff §6.3 or §5.4 is
not met. "Minor" means the constraint holds today but the design
trends drift-prone.

### S001 — Major — bench POST origin guard fail-open is not visibly repaired

Sources:
- `REVIEW_correctness_codex.md` § "C004 — Major — bench POST origin
  guard still fails open for missing browser-origin metadata."
- `REPAIR_EVIDENCE.md` § "Finding Status From Focused Evidence"
  (silent on C004; only C001, C002, C005 statuses are documented).
- `ENGRAM_UI_REWORK_HANDOFF.md` § 5.4 ("`engram.web.origin.require_origin`
  — single enforcement point. Bench's current `_origin_check` collapses
  into this.").
- `REVIEW_ergonomics_claude.md` § F001 ("`origin.py` … are also
  unreferenced from the rendered DOM as far as the templates show.").

C004 was filed against the bench POST origin guard in the prior round.
The recorded behavior was: a POST that omits `Origin`, `Referer`, and
`Sec-Fetch-Site` reaches the route handler — the helper only validates
each header if present. The minimal change the correctness lane asked
for was either:

- adopt `engram.web.origin.require_origin(request, *, host, port)`
  from the shared substrate, or
- update the local helper to require an exact loopback Origin **plus**
  `Sec-Fetch-Site: same-origin` before any mutation.

REPAIR_EVIDENCE.md explicitly enumerates which findings it considered
repaired (C001, C002, C005) and notes "no-CDN/static checks pass,"
"focused Ruff / whitespace checks pass," and adds the new DB-trigger
route blocker. It is silent on C004. The ergonomics review,
performed against the same tree, confirms that the shared origin
helper is "packaged but not integrated" — the substrate exists, but
both surfaces still mount their own `base.html` chrome and (by
extension) their own pre-existing helpers.

From documents alone, the conservative reading is: C004 is still
open. A security review that accepts means "we looked and found
nothing actionable"; here we looked and found a major finding with
no positive evidence of repair.

Recommendation:

- Switch bench POST routes to `engram.web.origin.require_origin` (the
  single enforcement point the handoff names) **or** tighten the local
  helper to require both an exact loopback `Origin` value and
  `Sec-Fetch-Site: same-origin` before any mutation.
- Add focused tests for missing-Origin and missing-Sec-Fetch-Site
  POSTs (not just bad-Origin), as C004 asked.
- Reflect the fix explicitly in the next repair-evidence document so
  future security re-reviews do not have to infer it.

### S002 — Major — shared origin / tier helpers are unused; the single-enforcement-point goal is not met

Sources:
- `ENGRAM_UI_REWORK_HANDOFF.md` § 5.4 (`engram.web.origin.require_origin`,
  `engram.web.tier.require_tier_ceiling` — single enforcement points).
- `ENGRAM_UI_REWORK_HANDOFF.md` § 8 (RFC slice 1: "Shared web substrate"
  must be wired into interview and bench).
- `REVIEW_ergonomics_claude.md` § F001 ("Shared chrome substrate
  exists but neither surface uses it … The substrate Python helpers —
  `chrome.py`, `status.py`, `origin.py`, `tier.py`, `assets.py` — are
  also unreferenced from the rendered DOM as far as the templates
  show.").
- `REVIEW_correctness_codex.md` § C003 (Major: "shared web substrate
  is packaged but not integrated into the surfaces").
- `REPAIR_EVIDENCE.md` (does not document wiring the shared substrate
  into either surface; reports only that shared templates parse and
  shared tests pass).

The handoff is explicit that the security helpers `require_origin`
and `require_tier_ceiling` exist as the **single** enforcement points
for CSRF/Origin and Tier 1 carry, with the bench's own `_origin_check`
collapsing into them. Both the correctness and ergonomics reviews
flagged that the substrate is built but unwired. The repair evidence
does not claim the wiring was done.

Security consequence: the two surfaces continue to enforce CSRF /
Origin and Tier 1 through two separate code paths. Any divergence
between those paths is a latent gap (C004 is the concrete example of
why this matters). Even if C004 were fixed in-place on the bench
local helper, the architectural defense-in-depth from a single
enforcement point would still be missing, and any future tightening
(e.g., the strict `same-origin` policy the handoff calls out in §11
Open Question 9) would have to be applied in two places without
test infrastructure to catch drift.

Recommendation:

- Wire bench (and interview) POST routes through
  `engram.web.origin.require_origin` exactly once. Make the local
  helpers thin wrappers (or delete them).
- Do the same for `_check_tier_1` → `require_tier_ceiling`, even on
  the routes where the current behavior is already correct.
- Once wired, add the negative-case tests the handoff §9.2 / §9.4 /
  §9.7 enumerate (missing-Origin POST, missing-Sec-Fetch-Site POST,
  tier-2 evidence row in `evidence/all`, tier-2 carry in context).

### S003 — Major — bench segment detail page lacks the "does not mutate" banner

Source:
- `REVIEW_ergonomics_claude.md` § F006.
- `ENGRAM_UI_REWORK_HANDOFF.md` § 6.2 ("Run-decision surface must
  render the literal banner … move it from `summary.html` body into
  a persistent header position on `/` and `/summary`.").
- `ENGRAM_UI_REWORK_HANDOFF.md` § 3.2 (bench segment-detail first
  viewport list).

The literal handoff banner — `Bench review decisions do not mutate
production data or bypass Phase 4 gates.` — is rendered on `/` and
`/summary` but is missing on `/segments/{id}`. That is the page
where the operator submits decisions; it is the most security-
relevant truthful-status surface in the bench workflow. An operator
who deep-links a segment (queue notification, saved URL) commits a
decision without the banner in the same viewport.

Severity classification: this is filed in the ergonomics review at
"major" for ergonomic reasons. For security review I keep it at
"major" because the handoff §6.3 places this banner in the
"circuit-breaker for the operator's trust model" set, not the
"polish copy" set, and the strongest operator-trust touchpoint is
the page that currently has the weakest assertion.

Recommendation:

- Include the literal banner (via the shared `_status_banner.html` /
  `_state_instruction_banner.html`, or a dedicated partial) at the
  top of `segment.html`. Do not soften the copy.

### S004 — Major — interview audit footer can render an inaccurate bind address

Sources:
- `REVIEW_ergonomics_claude.md` § F019.
- `ENGRAM_UI_REWORK_HANDOFF.md` § 3.1, § 6.3 (audit footer is a
  literal operational truth — `local-only · loopback bind:
  127.0.0.1:<port> · no network egress`).
- `ENGRAM_UI_REWORK_HANDOFF.md` § 5.1 (`audit_footer` shared partial
  inputs `bind_address`, `build_sha`, `egress_status`).

The interview `base.html` audit footer falls back to a hard-coded
`127.0.0.1:8765` literal when `bind_address` is not in the template
context. If the interview process binds a non-default port (operator
ran `--port`, or the process picked up a non-default
`ENGRAM_INTERVIEW_BIND_PORT`) and the context plumbing misses the
variable, the audit footer **displays a wrong port**. The bench
template does not have this fallback (no surface), but it also does
not use the shared `chrome.audit_footer_copy(...)` helper.

The ergonomics review classes this as trivial (it is a low-frequency
defect path). For a security posture review, this is the literal
"the audit footer must not lie" contract from the handoff §6.3. A
footer that can lie is a load-bearing defect for the operator's
trust model, even if the path is narrow.

Recommendation:

- Render the audit footer via the shared `chrome.audit_footer_copy`
  helper that already handles bind-address resolution from the
  application configuration (or from `request.url`, fail-loud if
  neither is set).
- Or, at minimum, treat a missing `bind_address` as a 500 (no
  fallback string), not a silent default. The footer is not allowed
  to display unverified content.

### S005 — Minor — failing route test exposes a fixture issue, not a weakened trigger

Sources:
- `REPAIR_EVIDENCE.md` (failing test:
  `tests/test_interview_web.py::test_question_renders_predicate_intent_and_warning`,
  error: `claim stability_class does not match predicate vocabulary`,
  `fn_claims_insert_prepare_validate()` line 101).
- `ENGRAM_UI_REWORK_HANDOFF.md` § 6.1 (predicate-intent line is the
  artifact the failing test asserts).
- `AGENTS.md` § "Architecture Principles" (raw evidence is
  immutable; preserve provenance / stability-class invariants).
- `CHANGELOG.md` (RFC 0028 predicate-intent: migration 012 adds
  nullable `predicate_vocabulary.subject_kind_hint`; extractor at
  `extractor.v9.d082.predicate-intent`).

The failing test seeds a `has_name` claim through the real DB path.
The DB trigger rejects the insert because the claim's
`stability_class` does not match the predicate vocabulary mapping
for `has_name`. That trigger is database validation working as
designed — RFC 0028's predicate-intent surfacing relies on this
mapping; weakening it would let claims through with stability
classes the vocabulary says do not apply.

This finding is filed not as a present weakness but as a forward
constraint on the repair team:

- The fix path is to seed the test fixture with a valid
  (predicate, stability_class) pairing or to populate
  `predicate_vocabulary` for `has_name` so the seeded
  `stability_class` is accepted. The fix is **not** to change the
  trigger thresholds, drop the trigger, or insert claims via a raw
  SQL bypass.
- The work-packet objective explicitly calls out: "route/test
  fixture changes do not weaken database validation or provenance
  constraints." This finding ratifies that constraint and names the
  forbidden path.

No present weakness, but the next attempt at this fix is the
highest-risk one for D044 / D069 / D078 invariants. Logging the
constraint here so the followup work cannot silently relax the
trigger.

### S006 — Minor — Origin / Sec-Fetch-Site policy unification is still an open design question

Sources:
- `ENGRAM_UI_REWORK_HANDOFF.md` § 11 (Open question 9: "the unified
  `require_origin` helper must pick one and apply it to both
  surfaces. The handoff defaults to the stricter behavior
  (`same-origin` only).").
- `CHANGELOG.md` (D081: `ENGRAM_INTERVIEW_ALLOWED_ORIGINS` extends
  the loopback allowlist; non-loopback bind plus token auth is
  documented as the F005 follow-on).

The handoff names this as the policy to land: interview's strict
`same-origin` becomes the unified contract for both surfaces. The
bench's current tolerance for `same-origin` / `same-site` / `none`
is a divergence that operators on user-space TCP forwarders (e.g.,
the Tailscale-tailnet pattern recorded in D081) may have learned
to depend on without realizing it.

This is not a present weakness — the bench already enforces
loopback Origin when the header is set, and the tailnet pattern is
operator-configured — but it is the policy lever S001 and S002 will
land against. If the unification ends up choosing the looser policy
silently, that's a security regression relative to the handoff
default.

Recommendation:

- When S001 / S002 are repaired, land them with the strict policy
  (`same-origin` only) as the handoff specifies, even if it requires
  documenting an opt-out env var for the tailnet TCP-forwarder
  pattern (D081). Do not silently inherit the bench's looser
  behavior into the shared helper.

## Verified preserved

The following constraints were checked against the documents and
are preserved by the repair pass.

- **No-CDN / no external asset markers.** REPAIR_EVIDENCE.md records
  a focused resource scan over 26 shared / interview / bench
  template / static resources with no external asset markers found.
  No review or changelog entry introduces a CDN URL or external
  font import.
- **Loopback-only bind, single-worker.** Per CHANGELOG.md and the
  handoff's Stack line, `uvicorn --workers 1` + loopback-only. No
  document in this round indicates a change to the bind shape; D080
  (loopback-only bind) and D081 (Origin allowlist extension) are
  unchanged.
- **Tier 1 ceiling on Tier 1-gated routes.** No finding or
  changelog entry weakens the Tier 1 enforcement on
  `/messages/{message_id}`, `/messages/{message_id}/context`, or
  `/sessions/{id}/q/{idx}/evidence/all`. The DB trigger that
  rejected the new failing test is a separate predicate-vocabulary
  validation, not a tier guard. The bench excerpt route's tier
  enforcement is unchanged from the position documented in the
  handoff §11 Open Question 8 (route-level 403 still TBD; not
  altered by this repair pass).
- **Database validation / provenance preserved.** The failing route
  test is rejected by `fn_claims_insert_prepare_validate()`. That
  trigger is doing its job. No document records any weakening of
  append-only triggers, stability-class validation, or
  predicate-vocabulary enforcement.
- **Phase 4 / promotion non-authorization copy.** No review or
  changelog entry softens the "Phase 4 is gated / scratch-local /
  not a promotion authority" copy (RFC 0038 § Non-Goals; handoff
  § 1, § 3.4, § 6.3). The `Entities (future)` tab disabled state
  remains, even if the literal is duplicated across templates
  (F017, drift risk only).
- **Raw evidence not overwritten in place.** The repair touches
  templates, web routes, route tests, and the shared substrate
  package. Nothing in the repair evidence or in the reviews
  indicates raw-evidence-row writes or migration changes that
  would mutate canonical evidence.
- **No new cloud / telemetry / hosted-auth introductions.** No
  changelog entry or finding adds any non-local dependency,
  outbound network call, or hosted-auth surface.

## Outstanding constraints for the next repair pass

These are the load-bearing items the next repair lane must close
before the security posture can be accepted:

1. **Wire bench POST routes through the shared origin helper, with
   strict missing-header denial** (S001 + S002). Add positive tests
   for missing-Origin and missing-Sec-Fetch-Site POSTs.
2. **Wire interview and bench audit footer through the shared
   `audit_footer_copy` helper, with no template-level fallback
   literal** (S004). Render-time misconfiguration must fail loud,
   not silently lie.
3. **Render the "does not mutate" banner on `/segments/{id}`**
   (S003). Use the shared partial so future copy changes land in
   one place.
4. **Repair the failing route test by fixing the fixture, not the
   trigger** (S005). The predicate-vocabulary / stability-class
   match must keep producing the rejection on bad inputs.
5. **When the helpers unify, default to the strict `same-origin`
   policy** (S006). The unified helper is the place to land any
   tailnet opt-out, not the bench's existing looser local helper.

## Pre-existing notes carried forward

The work-packet `context_policy` allows retaining prior context.
No prior-round security review exists for RFC 0038 in this
directory; the two prior reviews are correctness (codex) and
ergonomics (claude). Findings carried from those into this
security pass are limited to:

- **C004** → S001 (treated as still-open from documents).
- **C003 / F001** → S002 (substrate built, not wired).
- **F006** → S003 (banner missing on segment detail).
- **F019** → S004 (audit footer fallback literal).
- **F017** → noted under "Verified preserved" only as a drift risk.

All other prior-round findings (ergonomics F002–F005, F007–F018;
correctness C001 / C002 / C005) are out of scope for this security
posture.

## Verdict

`needs_revision`.

Local-only / no-CDN / Tier 1 ceiling / database-validation
posture is preserved. CSRF / Origin posture and audit-footer
truthful-status posture are not yet at the handoff target: S001
(bench POST fail-open) is unrepaired per documents, S002 (shared
helpers not wired) blocks the single-enforcement-point contract,
S003 missing banner on the commit-decision page weakens the
"does not mutate" trust assertion, and S004 lets the audit
footer render an inaccurate bind line. The next repair pass
should close S001–S004 explicitly and call them out in the
repair-evidence document so future re-reviews do not have to
infer their status.
