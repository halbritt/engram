# RFC 0014 Review

author: reviewer-codex-gpt-5.5-001

## Findings

### High: cross-root marker precedence is still underspecified for implementation

RFC 0014 says `scripts/phase3_tmux_agents.sh` should read `docs/operations/`
markers and legacy RFC 0013 marker roots as one logical marker set, and should
preserve RFC 0013 cross-root `supersedes` semantics. That keeps the right
intent, but the RFC body does not define a deterministic discovery and
precedence algorithm for mixed roots.

RFC 0013 requires scripts to compute newest marker state per `issue_id` and
`family`, with `ready` resolving `blocked` only when it explicitly names the
older marker in `supersedes`; newer `blocked` or `human_checkpoint` markers
block expansion even if older ready markers exist. RFC 0014 should restate the
mixed-root behavior enough that an implementation prompt cannot accidentally
sort by path root, prefer the new root, or treat migration as a clean handoff.

Suggested fix: add a short implementation contract saying marker state is
computed across both roots before precedence is evaluated; `supersedes` may
point across roots; root location must not alter gate priority; unresolved
legacy `blocked` or `human_checkpoint` markers continue to block until
explicitly superseded.

### Medium: migration plan relies on a spec handoff without making the RFC self-contained enough to review acceptance

RFC 0014 states that `docs/process/operational-artifact-home-spec.md` resolves
the open layout questions, and the acceptance criteria require that the spec
handoff has resolved those choices explicitly. In the RFC body, however, the
concrete contract is still partly labeled "Proposal Sketch" and the open
questions remain present.

That creates implementation risk because a later worker could reasonably
implement the sketch while another treats the unseen spec as authoritative. It
also weakens runner validation: the target artifact under review is the RFC,
but the RFC delegates key acceptance facts to another document.

Suggested fix: either promote the resolved choices directly into a normative
"Decision" or "Implementation Contract" section, or make the migration plan
explicitly require applying the spec into RFC 0014 before acceptance.

### Medium: script migration testing expectations are too implicit

The migration plan names `scripts/phase3_tmux_agents.sh`, but it does not state
what behavior must be tested or demonstrated after the path change. RFC 0013
already requires status output to surface the newest blocked or human-checkpoint
marker and `next` to refuse expansion while blocked. RFC 0014 should carry those
exact checks forward for the mixed-root transition.

Suggested fix: add acceptance criteria for legacy-only, operations-only, and
mixed-root marker cases, including cross-root `supersedes`, unresolved legacy
blocked markers, and a newer `human_checkpoint` overriding older ready markers.

### Low: privacy rules are preserved, but the new `docs/operations/` root needs an explicit local-diagnostics boundary

RFC 0014 preserves RFC 0013 redaction rules and keeps untracked diagnostics
under `logs/operational/`. That is good. The remaining risk is operational
drift: a new tracked root named `docs/operations/` can attract richer run notes
over time.

Suggested fix: add a `docs/operations/README.md` requirement that repeats the
forbidden-content rule, points private repair evidence to ignored
`logs/operational/`, and states that markers may never contain private corpus
content.

### Low: RFC 0014 is a useful bounded `agent_runner` validation target, but the success signal should be narrower

The RFC is a good bounded validation target because it has a small document
surface, clear dependency on RFC 0013, and concrete script/runbook migration
implications. The validation should not be "agent_runner controls repository
markers"; RFC 0014 correctly rejects that. The useful validation is whether a
runner can produce a redacted review artifact with stable byline/format,
preserve source-only constraints, and check a proposed process migration against
prior policy.

Suggested fix: add a validation note that this target exercises artifact
generation and policy review only, not live marker orchestration.

## Blocking Status

No blocking findings. The proposal preserves the local-first constraint, keeps
review feedback under `docs/reviews/`, and does not authorize moving or deleting
legacy artifacts. The main risks are implementation ambiguity around mixed-root
marker precedence and delegated spec authority.

Verdict: accept_with_findings
