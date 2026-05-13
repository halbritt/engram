# Adversarial Privacy and Network-Boundary Review of RFC 0030

Review `docs/rfcs/0030-public-dataset-entity-grounding.md` as if you were
a privacy auditor whose only job is finding any path by which corpus
content, agent metadata, or operator activity could leak across the
local-first boundary.

Assume the proposal will be implemented as written. Stress-test the five
non-negotiable constraints, especially the first two:

- **No live web at extraction time.**
- **Personal evidence does not leave the machine.**

## Attack surfaces to probe

1. **Dataset acquisition.** "Pre-downloaded datasets" implies an
   acquisition step. From what hosts? Over what protocol? Are
   integrity hashes pinned? Could a user-agent string or URL path
   carry corpus-derived information by accident?
2. **Indexing path.** When a snapshot is indexed locally, does the
   indexer call out to anything (font CDNs, package mirrors, language
   model registries, ICU data)? Where is that boundary stated?
3. **Resolver lookups.** D-B option 1 puts a candidate block into the
   prompt. The local LLM is local (D020), but a malicious dataset
   could include payloads that exfiltrate through *future* model
   tool-use, log scraping, or operator copy-paste. Does the RFC
   defend against poisoned dataset content?
4. **Grant model audit trail.** Who can read the grant log? Is it
   in scratch SQLite (`.engram/`), the production DB, or both? Could
   a granted role write its grant exercises somewhere they shouldn't?
5. **Snapshot integrity.** What stops a snapshot under
   `wikidata@2026-04-15` from being silently swapped between
   extraction runs? Are snapshot ids content-addressed?
6. **Cross-machine surface.** "No cross-machine sync" is named as
   out of scope, but dotfile sync, cloud-backed home directories,
   and `git`-tracked configuration could all replicate grants or
   snapshots inadvertently. Does the RFC defend against accidental
   sync paths?
7. **Future drift.** Is "grounding" defined tightly enough that a
   future RFC couldn't quietly redefine it to include remote
   service calls "because that's how everyone does it"?
8. **Logging and traces.** Could resolver output appear in
   benchmark logs, debug traces, or operator-facing diagnostics with
   enough detail to reconstruct corpus content?

## Output

Write to your packet's expected artifact path. Use this structure:

```md
# RFC 0030 Public-Dataset Entity Grounding Adversarial Privacy Review
author: <packet author line>

Status: review
Date: 2026-05-09
RFC refs: RFC-0030
Decision refs: D020, D044, D068, D076, D080
Phase refs: PHASE-0003, PHASE-0004

## Findings

### P001 - <title>
Severity: <blocking | major | minor | nit>
Source: <path:line or section>
Attack model: <one paragraph: who, what, how>
Rationale: <paragraph>
Suggested fix: <paragraph>

## Threat model summary

verdict: <accept | accept_with_findings | needs_revision | reject>
```

Be concrete. Demand specific guards. Reject hand-waves.
Do not modify the RFC. Do not include private corpus excerpts.
