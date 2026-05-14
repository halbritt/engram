# RFC Alignment Prompt

You are aligning one existing Striatum memory RFC after the completed roadmap
workflow. You are not implementing code and not making a promotion decision.

Read the assigned RFC, the prior final synthesis, findings ledger, repair
re-review, and any job inputs. Use the maximum useful number of native
sub-agents for read-only analysis before editing. Ask them to identify exactly
which findings affect this RFC, where current text is weak, and whether edits
would conflict with adjacent RFCs.

Make only narrow proposal-text changes inside the assigned write scope. Preserve
Engram's local-only/no-cloud/no-telemetry constraint, immutable raw evidence,
rebuildable derived projections, provenance/confidence/auditability, and
personal-memory deferral. Do not edit code, tests, migrations, generated schema
docs, `DECISION_LOG.md`, or `CHANGELOG.md`.

Produce the expected handoff artifact. It must include:

- findings addressed and findings explicitly deferred;
- files changed;
- dependency impact on RFC promotion, implementation, and routine Striatum use;
- validation run and result;
- any workflow friction or remaining ambiguity for the operator.

Run `git diff --check` for the allowed paths. If references or anchors changed,
also run `make check-refs`.

