# RFC 0050: Source Ingestion Expansion

| Field | Value |
|-------|-------|
| RFC | RFC-0050 |
| Title | Source Ingestion Expansion |
| Status | proposal |
| Date | 2026-05-15 |
| Authors | gemini lane |
| Source Design | `docs/design/source-ingestion-expansion-proposal-2026-05-15.md` |

## Context

Engram's mission is to build a complete, time-indexed biography of a human life. Currently, the system is primarily a "conversation memory," focused on AI chat exports (ChatGPT, Claude, Gemini). While Phase 1.5 successfully implemented these sources, the `source_kind` enum remains a closed vocabulary, and each new importer requires bespoke schema additions and logic.

To move from "chat memory" to "life biography," Engram must expand into the vast corpus of local data: git history, build artifacts, project notes, documents, and eventually multimodal observation data (location, photos, calendar). 

The source design document proposes a universal **Source Contract** and a taxonomy of **Evidence Lanes** to ensure that expansion is structured, rebuildable, and respects Engram's core local-first and privacy constraints.

## The Source Contract

Every source adapter must satisfy a standardized contract before it can be integrated. This prevents the "folklore" of per-source implementation and ensures that provenance, privacy, and rebuildability are handled uniformly.

### Mandatory Contract Fields

| Field | Purpose |
|-------|---------|
| `source_family` | High-level category (e.g., `git`, `chat`, `document`). |
| `sub_kinds` | Granular record types (e.g., `commit`, `diff_stat`, `message`). |
| `raw_artifact_boundary` | Definition of the immutable unit of evidence (e.g., "local repository object database"). |
| `identity_keys` | Keys used for deduplication and stable reference (e.g., `commit_sha`). |
| `temporal_mapping` | Mapping of source timestamps to `observed_at` and `recorded_at`. |
| `privacy_default` | Default tier (1-5) assigned to new evidence. |
| `acquisition_mode` | How data reaches the machine (e.g., `local_filesystem`, `explicit_export`). |
| `network_policy` | Must be `no_outbound_calls` for all corpus-reading processes. |
| `projection_families` | The target tables or observation types derived from this source. |
| `extraction_eligibility` | Whether LLM-based claim extraction is enabled by default. |

### Importer Verification
Every importer must pass an automated validation suite asserting:
1. **Idempotency:** Re-importing the same artifact produces zero duplicate records.
2. **Conflict Detection:** Mismatched content for the same `external_id` raises an `IngestConflict`.
3. **Immutability:** Raw rows are protected by triggers; re-projection does not edit raw rows.
4. **No Egress:** The process passes the Level 1 no-egress gate (static/runtime inspection).

## Evidence Lanes

Sources are grouped into four lanes, each with distinct semantics and extraction postures.

### 1. Conversation Evidence
Threaded, participant-based communication.
- **Sources:** Slack/Discord exports, Email (mbox/Maildir), meeting transcripts.
- **Projection:** Conversations, messages, participant edges.
- **Extraction:** AI-conversation extraction is default-on; human-to-human communication requires an explicit approval gate due to third-party privacy.

### 2. Document and Note Evidence
User-authored files where structure and revision history matter.
- **Sources:** Obsidian vaults, Markdown directories, project READMEs/RFCs.
- **Projection:** Documents, chunks, headings, frontmatter, path-based links.
- **Extraction:** Segmentation and retrieval are early priorities; sensitive journals default to Tier 2+.

### 3. Project and Execution Evidence
Structured traces of work intent and outcome.
- **Sources:** Git history, build logs, test reports (JUnit/pytest), Striatum artifacts.
- **Projection:** Project events, code references, artifact hashes, failure signatures.
- **Extraction:** Meta-data and summaries first; full logs and patches remain local-only and are cited, not pasted into context by default.

### 4. Observation and Life Evidence
Dense, non-textual context of the physical and digital world.
- **Sources:** Location timelines, photo libraries, calendar, health/finance exports.
- **Projection:** Observations (RFC 0033), place visits (RFC 0035), events (RFC 0034).
- **Extraction:** Stricter default privacy (Tier 3+); requires specialized observation-layer parsers before claim extraction.

## Projection Families and Observation Layer

Following the pattern established in RFC 0033, non-textual sources do not emit claims directly. Instead, they produce **Observations**: atomic, source-backed assertions that can be interpreted into semantic events.

- **Immutable Raw Evidence:** Stored in `sources`, `conversations`, `messages`, `notes`, or `captures`.
- **Observations:** Normalized signals (e.g., `location_sample`, `media_exif_coordinate`).
- **Interpretation:** Clusters of observations (e.g., a "Dinner with Alice" event candidate).
- **Beliefs:** Only consolidated, bitemporal facts promoted from interpretations reach the belief layer.

## Privacy Defaults and Egress

Engram's "no-cloud" constraint is enforced through the following rules:

1. **Privacy Tier Inheritance:** A derived projection (observation, chunk, claim, or belief) inherits the *maximum* privacy tier of its cited raw evidence.
2. **No-Egress Policy:** Any process reading the corpus (importer, segmenter, embedder, extractor) is prohibited from making network calls.
3. **Data Egress Refusal:** No derived products (summaries, packets) may leave the machine. Sharing is an explicit, user-initiated export of a specific slice.
4. **Third-Party Data:** Human chat and email sources are treated as high-risk. Extraction is blocked until a third-party data policy is accepted.

## Rollout Strategy

Expansion proceeds from high-signal, low-risk project data to high-sensitivity life data.

### Stage 1: Project Evidence (Git & Build)
- Implement `source_kind='git'` (metadata and diff stats).
- Implement `source_kind='build_artifact'` (test suite summaries, failure signatures).
- Purpose: Ground the AI assistant in the actual state of the project it is helping with.

### Stage 2: Project Notes (Markdown)
- Ingest local Markdown trees and Obsidian project docs.
- Purpose: Align code and build evidence with human-authored intent.

### Stage 3: Communication Backfills (Exports)
- Ingest Slack, Discord, and Email exports.
- Purpose: Provide historical context for collaboration and decisions.

### Stage 4: Multimodal Life Records (RFC 0033-0036)
- Implement location, photo, and calendar lanes.
- Purpose: Complete the biography and enable day-level summaries.

## Evaluation Gates

Borrowed from the RFC 0049 style, every new source family must pass the following gates before promotion:

- **EG-101: Idempotency Gate.** Repeated imports of the same repository or directory produce zero duplicate events.
- **EG-102: No-Network Gate.** Sandbox proof that the importer makes zero outbound calls during processing.
- **EG-103: Rebuild Gate.** Proof that deleting all projections for a source and re-running the worker produces a bit-for-bit identical projection set.
- **EG-104: Citation Gate.** Every derived record must carry a valid `evidence_ids` or `reference_id` link back to raw evidence.

## Scope Kept Out

To prevent unconstrained expansion, the following are explicitly deferred:
- **Media Bodies:** Photo/video files are referenced by path and hash; Engram does not become a media storage system.
- **Cloud APIs:** No direct integration with Gmail, Slack, or GitHub APIs. All data must be local exports.
- **Derived Product Leak:** Summaries are for local use; no "sync back to the cloud" is permitted.
- **Personal-Memory Paste-Through:** Striatum or other application-memory tenants cannot read personal memory without explicit, per-session operator grants.

## Open Questions for Human Decision

1. **Patch Retention:** Should Git importers store full patch bodies in `raw_payload`, or only metadata and diff stats?
2. **Third-Party Privacy:** What is the specific threshold for when a human-to-human conversation is "safe" for automated LLM extraction?
3. **Source Registry:** At what point should the `source_kind` enum be replaced by a dynamic registry table to avoid migration churn?

## Cross-References

| Area | Related RFCs |
|------|--------------|
| Multimodal / Observation | RFC 0033, RFC 0034, RFC 0035, RFC 0036 |
| Striatum Corpus Boundary | RFC 0044, RFC 0045 |
| Evaluation / Gates | RFC 0049 |
| Privacy / Reclassification | D028, D032 |

---
*Author Byline: gemini lane*
