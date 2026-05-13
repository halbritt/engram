# RFC 0027 Final Review — Task

Read `RFC_0027_INTERVIEW_WEB_UI_SYNTHESIS.md` plus
`RFC_0027_INTERVIEW_WEB_UI_FINDINGS_LEDGER.md` and RFC 0027.

Audit the synthesis: is it grounded in the ledger, does it preserve
D020 / D044 / D069 invariants, and does it produce a buildable spec
contract?

## Audit checklist

1. **Synthesis-to-ledger consistency.** Every accepted / deferred /
   rejected ledger finding has a reason aligned with its severity.
2. **Recommendation grounding.** `accept-rfc` / `revise-rfc` /
   `split-rfc` / `reject-rfc` matches what the findings support.
3. **D020 invariants.** Localhost-only binding, vendored htmx,
   no auth, no outbound network — preserved?
4. **D044 / D069 invariants.** Gold labels remain advisory; no web
   path auto-flips beliefs.
5. **Spec deltas (if accept-rfc).** Routes, templates, render API,
   migration plan, deps, tests, env var, shortcut letters,
   BUILD_PHASES insert, DECISION_LOG entry — all concrete and
   internally consistent?
6. **Implementation readiness.** Engineer with the spec in hand can
   build it without re-deriving decisions.
7. **Provenance carry.** RFC, decision, and phase references used
   correctly.

## Output

Write to `docs/reviews/rfc0027-rerun-2026-05-13/RFC_0027_INTERVIEW_WEB_UI_FINAL_REVIEW.md`:

```md
# RFC 0027 Interview Web UI Final Review

Status: final-review
Date: <YYYY-MM-DD>
RFC refs: RFC-0027
Decision refs: ...
Phase refs: ...

## Audit findings

### A001 — <title>
Severity: <blocking | major | minor | nit>
Source: <synthesis section or ledger ID>
Rationale: <one paragraph>

verdict: <accept | accept_with_findings | needs_revision | reject>
```

`needs_revision` sends the synthesis back once. `reject` means the
review cycle itself is untrustworthy.

Do not modify any other file.
