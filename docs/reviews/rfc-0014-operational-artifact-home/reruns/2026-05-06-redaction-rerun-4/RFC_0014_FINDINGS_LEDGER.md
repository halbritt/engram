# RFC 0014 Findings Ledger

author: ledger-codex-gpt-5.5-001

## Findings

### RFC0014-F001

- **Title:** Loop-scope precedence is ambiguous for flat legacy markers
- **Priority:** Major clarification, not blocking
- **Source reviewer(s):** reviewer-claude-opus-001
- **Affected artifact or section:** `docs/process/operational-artifact-home-spec.md`, Compatibility Semantics; Flat legacy marker rules; Precedence rules
- **Issue:** The spec does not define how exact-path supersession of front-matterless flat legacy blockers interacts with loop-scoped marker grouping, including where the resolving ready marker must live and whether its `(issue_id, family)` matters.
- **Relationship:** Independent; partly conflicts with reviewer-gemini-3.1-pro-preview-001 assessment that legacy compatibility leaves no critical decisions.

### RFC0014-F002

- **Title:** RFC sketch and spec use inconsistent report filenames
- **Priority:** Minor
- **Source reviewer(s):** reviewer-claude-opus-001
- **Affected artifact or section:** `docs/rfcs/0014-operational-artifact-home.md`, Proposal Sketch; `docs/process/operational-artifact-home-spec.md`, Canonical Layout
- **Issue:** The RFC sketch shows report filenames with state suffixes while the spec forbids state suffixes and defines different canonical report names.
- **Relationship:** Independent.

### RFC0014-F003

- **Title:** Repair verification report and marker stems differ
- **Priority:** Minor
- **Source reviewer(s):** reviewer-claude-opus-001
- **Affected artifact or section:** `docs/process/operational-artifact-home-spec.md`, Canonical Layout
- **Issue:** `reports/05_REPAIR_VERIFICATION.md` and `markers/05_REPAIR_VERIFIED.ready.md` use different verb forms, unlike other report and marker pairs.
- **Relationship:** Independent.

### RFC0014-F004

- **Title:** Migration lacks initial audit of existing flat legacy blockers
- **Priority:** Minor
- **Source reviewer(s):** reviewer-claude-opus-001
- **Affected artifact or section:** `docs/process/operational-artifact-home-spec.md`, Migration Work; Compatibility Semantics
- **Issue:** The migration plan does not require an upfront inventory of existing flat legacy `.blocked.md` and `.human_checkpoint.md` markers before legacy-root scanning makes them active gate inputs.
- **Relationship:** Independent.

### RFC0014-F005

- **Title:** Marker handling of non-`none` `corpus_content_included` values is underspecified
- **Priority:** Minor
- **Source reviewer(s):** reviewer-claude-opus-001
- **Affected artifact or section:** `docs/process/operational-artifact-home-spec.md`, Marker Schema and Artifact Rules; RFC 0013 Section 3
- **Issue:** The spec requires markers to set `corpus_content_included: none` but does not explicitly state validator behavior for schema-bearing markers that use values such as `owner_approved`.
- **Relationship:** Independent; adjacent to reviewer-gemini-3.1-pro-preview-001's acceptance of the privacy tightening.

### RFC0014-F006

- **Title:** `supersedes` semantics for non-`ready` markers are unspecified
- **Priority:** Minor
- **Source reviewer(s):** reviewer-claude-opus-001
- **Affected artifact or section:** `docs/process/operational-artifact-home-spec.md`, Marker Schema; Precedence rules
- **Issue:** The spec does not say whether `blocked` or `human_checkpoint` markers may use `supersedes` to thread provenance, or whether supersession is reserved for ready-to-blocked resolution.
- **Relationship:** Independent.

### RFC0014-F007

- **Title:** Spec acceptance criteria narrow malformed front-matter failure
- **Priority:** Minor
- **Source reviewer(s):** reviewer-claude-opus-001
- **Affected artifact or section:** `docs/rfcs/0014-operational-artifact-home.md`, Acceptance Criteria; `docs/process/operational-artifact-home-spec.md`, Acceptance Criteria
- **Issue:** The RFC says malformed or invalid marker front matter fails closed, while the spec acceptance criteria mention only malformed or invalid `created_at` front matter.
- **Relationship:** Independent; related to RFC0014-F010.

### RFC0014-F008

- **Title:** Human-checkpoint owner-decision evidence is not fully machine-checkable
- **Priority:** Medium
- **Source reviewer(s):** reviewer-codex-gpt-5.5-001
- **Affected artifact or section:** `docs/process/operational-artifact-home-spec.md`, Compatibility Semantics precedence rule 6; Implementation Fixtures; Acceptance Criteria
- **Issue:** The spec requires linked owner-decision evidence before a `human_checkpoint` resolves, but does not define whether tooling validates that evidence through existence checks, front matter, prose scanning, a separate evidence path, or manual verification.
- **Relationship:** Independent; partly conflicts with reviewer-gemini-3.1-pro-preview-001 assessment that the implementation contract leaves no critical decisions.

### RFC0014-F009

- **Title:** D060 path hygiene enforcement level is inconsistent
- **Priority:** Medium-low
- **Source reviewer(s):** reviewer-codex-gpt-5.5-001
- **Affected artifact or section:** `docs/process/operational-artifact-home-spec.md`, Artifact Rules; Implementation Fixtures; Acceptance Criteria
- **Issue:** Artifact Rules use advisory language for repository-relative path hygiene, while fixtures and acceptance criteria describe hardcoded home-directory paths as validation failures.
- **Relationship:** Independent.

### RFC0014-F010

- **Title:** `created_at` ordering should require timezone-aware timestamps
- **Priority:** Low
- **Source reviewer(s):** reviewer-codex-gpt-5.5-001
- **Affected artifact or section:** `docs/process/operational-artifact-home-spec.md`, Marker Schema; Compatibility Semantics precedence rules 3 and 4
- **Issue:** The spec requires valid ISO-8601 timestamps for precedence ordering but does not explicitly reject naive timestamps, leaving cross-agent ordering ambiguous.
- **Relationship:** Independent; related to RFC0014-F007.

## No-Finding Reviews

- **reviewer-gemini-3.1-pro-preview-001:** Reported no blocking findings and verdict `accept`; raised no discrete findings to ledger.
