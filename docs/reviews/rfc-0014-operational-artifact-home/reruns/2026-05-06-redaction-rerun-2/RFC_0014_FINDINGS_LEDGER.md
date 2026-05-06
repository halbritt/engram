# RFC 0014 Findings Ledger

author: ledger-codex-gpt-5.5-001

## Findings

### RFC0014-F001: Cross-root marker precedence algorithm is underspecified

- **Priority:** high
- **Source reviewer or reviewers:** reviewer-claude-opus-001; reviewer-codex-gpt-5.5-001
- **Affected artifact or section:** RFC 0014 migration plan; marker discovery and `supersedes` semantics; `scripts/phase3_tmux_agents.sh`
- **Issue statement:** RFC 0014 requires new `docs/operations/` markers and legacy RFC 0013 marker roots to be treated as one logical marker set, but does not define a deterministic mixed-root discovery, precedence, and cross-root `supersedes` algorithm. This leaves room for implementations to sort or prioritize by root, miss legacy markers, or fail to preserve RFC 0013 blocked/human-checkpoint behavior.
- **Relationship:** duplicate

### RFC0014-F002: RFC body delegates resolved layout decisions to the spec while retaining open questions

- **Priority:** medium
- **Source reviewer or reviewers:** reviewer-claude-opus-001; reviewer-codex-gpt-5.5-001
- **Affected artifact or section:** RFC 0014 introduction; "Proposal Sketch"; "Open Questions"; acceptance criteria
- **Issue statement:** RFC 0014 says the spec handoff resolves layout and migration choices, but the RFC body still labels key content as a proposal sketch and leaves open questions visible. A reader reviewing the RFC alone cannot tell which choices are normative without consulting the external spec.
- **Relationship:** duplicate

### RFC0014-F003: Redaction contract is partially duplicated and may drift from RFC 0013

- **Priority:** medium
- **Source reviewer or reviewers:** reviewer-claude-opus-001; reviewer-gemini-3.1-pro-preview-001
- **Affected artifact or section:** RFC 0014 "Artifact Rules"; RFC 0013 Section 3 redaction contract
- **Issue statement:** RFC 0014 reproduces some RFC 0013 allow/forbid rules but omits or truncates parts of the prior contract, including the explicit `corpus_content_included: owner_approved` marker requirement and some allowed artifact examples. This creates policy drift risk unless RFC 0013 Section 3 is incorporated unchanged or referenced as authoritative.
- **Relationship:** duplicate

### RFC0014-F004: Script migration testing expectations are too implicit

- **Priority:** medium
- **Source reviewer or reviewers:** reviewer-claude-opus-001; reviewer-codex-gpt-5.5-001
- **Affected artifact or section:** RFC 0014 migration plan; acceptance criteria; `scripts/phase3_tmux_agents.sh`
- **Issue statement:** The migration plan names the script that must change but does not require concrete tests or fixtures for legacy-only, operations-only, mixed-root, cross-root `supersedes`, unresolved blocked, or newer `human_checkpoint` cases. Automation could pass a smoke test while regressing RFC 0013 marker behavior.
- **Relationship:** duplicate

### RFC0014-F005: Migration plan leaves transition rules unclear

- **Priority:** medium
- **Source reviewer or reviewers:** reviewer-claude-opus-001
- **Affected artifact or section:** RFC 0014 migration plan; RFC 0013 Section 10 automation contract
- **Issue statement:** The RFC does not clearly state whether existing `docs/reviews/<area>/postbuild/markers/<run>/` directories are frozen, whether new legacy markers may still be written during transition, or how RFC 0013's singular post-build marker-tree automation contract is amended.
- **Relationship:** independent

### RFC0014-F006: `docs/operations/` needs an explicit local-diagnostics boundary

- **Priority:** low
- **Source reviewer or reviewers:** reviewer-codex-gpt-5.5-001
- **Affected artifact or section:** RFC 0014 artifact rules; proposed `docs/operations/README.md`
- **Issue statement:** A new tracked operational root may attract richer run notes over time. The RFC does not explicitly require a README or equivalent boundary statement directing private repair evidence to ignored `logs/operational/` and restating that markers may never contain private corpus content.
- **Relationship:** independent

### RFC0014-F007: Proposal-sketch framing weakens the canonical layout statement

- **Priority:** low
- **Source reviewer or reviewers:** reviewer-claude-opus-001
- **Affected artifact or section:** RFC 0014 "Proposal Sketch"
- **Issue statement:** The RFC describes its layout block as the original proposal sketch rather than the final implementation contract. This leaves the RFC without a single canonical layout statement after the spec handoff.
- **Relationship:** duplicate of RFC0014-F002

### RFC0014-F008: Agent-runner validation success signal should remain narrow

- **Priority:** low
- **Source reviewer or reviewers:** reviewer-codex-gpt-5.5-001
- **Affected artifact or section:** RFC 0014 validation framing; non-goals
- **Issue statement:** RFC 0014 is suitable as a bounded `agent_runner` validation target, but the validation signal should be limited to redacted artifact generation, stable byline/format handling, source-only constraints, and policy review rather than live marker orchestration.
- **Relationship:** independent

### RFC0014-F009: Operational state and review feedback are cleanly separated

- **Priority:** non-blocking
- **Source reviewer or reviewers:** reviewer-claude-opus-001; reviewer-gemini-3.1-pro-preview-001
- **Affected artifact or section:** RFC 0014 problem statement; proposal; non-goals
- **Issue statement:** The proposed split between `docs/operations/` for operational run state and `docs/reviews/` for model review feedback addresses the overloaded review-directory problem and preserves a clear boundary between run artifacts and review synthesis.
- **Relationship:** duplicate

### RFC0014-F010: Legacy compatibility intent is present

- **Priority:** non-blocking
- **Source reviewer or reviewers:** reviewer-gemini-3.1-pro-preview-001
- **Affected artifact or section:** RFC 0014 migration plan
- **Issue statement:** The migration plan explicitly intends for `scripts/phase3_tmux_agents.sh` to read both new and legacy marker roots as a single logical set, reducing the risk that existing markers are orphaned.
- **Relationship:** conflicting with RFC0014-F001 on sufficiency, but not on intent

### RFC0014-F011: Privacy posture is broadly preserved

- **Priority:** low
- **Source reviewer or reviewers:** reviewer-claude-opus-001; reviewer-gemini-3.1-pro-preview-001
- **Affected artifact or section:** RFC 0014 artifact rules; privacy and redaction constraints; non-goals
- **Issue statement:** Reviewers found that RFC 0014 does not introduce a new raw-corpus-content authorization and preserves the local-first/no-egress posture in spirit, while noting related redaction-contract gaps captured separately.
- **Relationship:** duplicate

### RFC0014-F012: RFC 0014 is a bounded validation target for `agent_runner`

- **Priority:** non-blocking
- **Source reviewer or reviewers:** reviewer-claude-opus-001; reviewer-gemini-3.1-pro-preview-001; reviewer-codex-gpt-5.5-001
- **Affected artifact or section:** RFC 0014 scope; validation framing; dependencies on RFC 0013
- **Issue statement:** Reviewers agree RFC 0014 is a small, process-focused target suitable for `agent_runner` dogfooding because it has clear dependencies, redacted artifacts, and concrete script/runbook implications, subject to the narrower validation framing captured in RFC0014-F008.
- **Relationship:** duplicate
