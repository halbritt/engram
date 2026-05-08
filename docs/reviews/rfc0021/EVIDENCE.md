# Striatum Evidence Export

Run ID: `run_c5453f21c248430c9398c197e46f0867`
Branch: `engram/rfc0021-gold-set-review`
Run state: `completed`
Exported at: `2026-05-08T18:09:20Z`

Live SQLite state remains ignored under `.striatum/` and is not part of this export.

## Status Output

```json
{"blocked_downstream_jobs":[],"claimable_jobs":[],"human_checkpoints":[],"jobs":{"completed":6},"latest_non_accepting_review_verdicts":[],"next_actions":[],"open_blockers":[],"process_health":"<redacted-free-text>","runs":[{"branch_name":"engram/rfc0021-gold-set-review","run_id":"run_c5453f21c248430c9398c197e46f0867","state":"completed"}]}
```

## Doctor Output

```json
{"ok":true,"problems":[],"schema_version":"1"}
```

## Snapshot

```json
{
  "artifacts": [
    {
      "artifact_id": "art_2f73b30776c44dad98aadbefa43b0e4f",
      "artifact_kind": "decision",
      "content_sha256": "f3c0dfed396fcbf9cde2ca140b818ed514f9145cc8f44249ee8b4f8ddca6fc0e",
      "job_id": null,
      "logical_name": "dec_84da55fd849b49548ea4eff3807b65cf",
      "repo_path": "docs/reviews/rfc0021/COORDINATOR_CONTINUE_DECISION.md",
      "session_id": null
    },
    {
      "artifact_id": "art_794b209957ec4187ba12e05eedb219b3",
      "artifact_kind": "finding",
      "author": {
        "actual_author_line": "author: reviewer-codex-gpt-5.5-002",
        "display_model": "Codex GPT-5.5",
        "lane_id": "codex",
        "line": "author: reviewer-codex-gpt-5.5-002",
        "ordinal": 2,
        "role_id": "reviewer",
        "workflow_job_id": "final_review"
      },
      "content_sha256": "d9f527231c077be58580ec52ff6d4e0b5e45819ae6db5ef9b729f777be2c8f81",
      "job_id": "job_run_c5453f21c248430c9398c197e46f0867_final_review",
      "logical_name": "review",
      "repo_path": "docs/reviews/rfc0021/RFC_0021_GOLD_SET_FINAL_REVIEW.md",
      "session_id": "sess_0971faeeed284e58ab0a5860ed5cc229"
    },
    {
      "artifact_id": "art_d8d3ef722bc24cd7afb96e04de1c560f",
      "artifact_kind": "findings_ledger",
      "author": {
        "actual_author_line": "author: ledger-codex-gpt-5.5-001",
        "display_model": "Codex GPT-5.5",
        "lane_id": "codex",
        "line": "author: ledger-codex-gpt-5.5-001",
        "ordinal": 1,
        "role_id": "ledger",
        "workflow_job_id": "findings_ledger"
      },
      "content_sha256": "ff6cbe23db2b6f93a1e7f5165babbc9cafc1a178a6caeb7400fd7c192c5f46aa",
      "job_id": "job_run_c5453f21c248430c9398c197e46f0867_findings_ledger",
      "logical_name": "ledger",
      "repo_path": "docs/reviews/rfc0021/RFC_0021_GOLD_SET_FINDINGS_LEDGER.md",
      "session_id": "sess_146bc0ade5c346138142623e398ae5d1"
    },
    {
      "artifact_id": "art_a8cecb02f4ec4c359596fe05b58d3663",
      "artifact_kind": "finding",
      "author": {
        "actual_author_line": "author: reviewer-claude-opus-001",
        "display_model": "Claude Opus",
        "lane_id": "claude",
        "line": "author: reviewer-claude-opus-001",
        "ordinal": 1,
        "role_id": "reviewer",
        "workflow_job_id": "review_claude"
      },
      "content_sha256": "91dcae72fcdd43a85b29fac8e3f0c5fb1ac24fd2917a04d2efedf2caf6fd3ee5",
      "job_id": "job_run_c5453f21c248430c9398c197e46f0867_review_claude",
      "logical_name": "review",
      "repo_path": "docs/reviews/rfc0021/RFC_0021_GOLD_SET_REVIEW_claude.md",
      "session_id": "sess_2e2b1eeda46f41afb981bcde2f104466"
    },
    {
      "artifact_id": "art_7c247207c0854436a3bae8a13c9e4b3b",
      "artifact_kind": "finding",
      "author": {
        "actual_author_line": "author: reviewer-codex-gpt-5.5-001",
        "display_model": "Codex GPT-5.5",
        "lane_id": "codex",
        "line": "author: reviewer-codex-gpt-5.5-001",
        "ordinal": 1,
        "role_id": "reviewer",
        "workflow_job_id": "review_codex"
      },
      "content_sha256": "54b6e2e35cfbe1c734a568a79004c704373b06b131604180d5a795107fe3bfff",
      "job_id": "job_run_c5453f21c248430c9398c197e46f0867_review_codex",
      "logical_name": "review",
      "repo_path": "docs/reviews/rfc0021/RFC_0021_GOLD_SET_REVIEW_codex.md",
      "session_id": "sess_f8be211c93af45178ae7340608df72a9"
    },
    {
      "artifact_id": "art_971505ba266c4940b3e8211d12a3c6a0",
      "artifact_kind": "finding",
      "author": {
        "actual_author_line": "author: reviewer-gemini-3.1-pro-preview-001",
        "display_model": "Gemini 3.1 Pro Preview",
        "lane_id": "gemini",
        "line": "author: reviewer-gemini-3.1-pro-preview-001",
        "ordinal": 1,
        "role_id": "reviewer",
        "workflow_job_id": "review_gemini"
      },
      "content_sha256": "31ae48f8ff724eb4ebd38d9fc7e4a5014cdab686399417cca00e71ee39913a92",
      "job_id": "job_run_c5453f21c248430c9398c197e46f0867_review_gemini",
      "logical_name": "review",
      "repo_path": "docs/reviews/rfc0021/RFC_0021_GOLD_SET_REVIEW_gemini.md",
      "session_id": "sess_c897b6bb31c44f38bca4a9879164c053"
    },
    {
      "artifact_id": "art_c533bddc92ef45d89c2e44b6a4a9936a",
      "artifact_kind": "synthesis",
      "author": {
        "actual_author_line": "author: synthesizer-claude-opus-001",
        "display_model": "Claude Opus",
        "lane_id": "claude",
        "line": "author: synthesizer-claude-opus-001",
        "ordinal": 1,
        "role_id": "synthesizer",
        "workflow_job_id": "synthesis"
      },
      "content_sha256": "1e282f2a20a81675985851a120f21eaf5fa4bdd023cef825183e023a8c41cfad",
      "job_id": "job_run_c5453f21c248430c9398c197e46f0867_synthesis",
      "logical_name": "synthesis",
      "repo_path": "docs/reviews/rfc0021/RFC_0021_GOLD_SET_SYNTHESIS.md",
      "session_id": "sess_84d29cbc82be42dd8b65d91bf03d6ad6"
    }
  ],
  "blocked_downstream_jobs": [],
  "blockers": [
    {
      "blocker_id": "blk_7380f354e4ba4b1893608d7dd564aefe",
      "blocker_kind": "revision_routing",
      "description": "<redacted-free-text>",
      "job_id": "job_run_c5453f21c248430c9398c197e46f0867_review_claude",
      "session_id": "sess_2e2b1eeda46f41afb981bcde2f104466",
      "severity": "human_checkpoint",
      "state": "resolved"
    },
    {
      "blocker_id": "blk_3eb2166e390e45e78af3e2ab955000c0",
      "blocker_kind": "revision_routing",
      "description": "<redacted-free-text>",
      "job_id": "job_run_c5453f21c248430c9398c197e46f0867_review_codex",
      "session_id": "sess_f8be211c93af45178ae7340608df72a9",
      "severity": "human_checkpoint",
      "state": "resolved"
    },
    {
      "blocker_id": "blk_e473e384561746fd9a5391985c839f3e",
      "blocker_kind": "revision_routing",
      "description": "<redacted-free-text>",
      "job_id": "job_run_c5453f21c248430c9398c197e46f0867_review_gemini",
      "session_id": "sess_c897b6bb31c44f38bca4a9879164c053",
      "severity": "human_checkpoint",
      "state": "resolved"
    }
  ],
  "exported_at": "2026-05-08T18:09:20Z",
  "jobs": [
    {
      "attempt": 1,
      "author": {
        "display_model": "Codex GPT-5.5",
        "lane_id": "codex",
        "line": null,
        "ordinal": null,
        "role_id": "reviewer",
        "workflow_job_id": "final_review"
      },
      "dependencies": [
        {
          "depends_on_job_id": "job_run_c5453f21c248430c9398c197e46f0867_synthesis",
          "latest_verdict": null,
          "required_verdicts": null,
          "state": "completed",
          "workflow_job_id": "synthesis"
        }
      ],
      "display_model": "Codex GPT-5.5",
      "fresh_session_required": true,
      "job_id": "job_run_c5453f21c248430c9398c197e46f0867_final_review",
      "job_type": "review",
      "lane": "codex",
      "max_attempts": 1,
      "role_id": "reviewer",
      "state": "completed",
      "workflow_job_id": "final_review"
    },
    {
      "attempt": 1,
      "author": {
        "display_model": "Codex GPT-5.5",
        "lane_id": "codex",
        "line": null,
        "ordinal": null,
        "role_id": "ledger",
        "workflow_job_id": "findings_ledger"
      },
      "dependencies": [
        {
          "depends_on_job_id": "job_run_c5453f21c248430c9398c197e46f0867_review_claude",
          "latest_verdict": "accept_with_findings",
          "required_verdicts": [
            "accept",
            "accept_with_findings"
          ],
          "state": "completed",
          "workflow_job_id": "review_claude"
        },
        {
          "depends_on_job_id": "job_run_c5453f21c248430c9398c197e46f0867_review_codex",
          "latest_verdict": "accept_with_findings",
          "required_verdicts": [
            "accept",
            "accept_with_findings"
          ],
          "state": "completed",
          "workflow_job_id": "review_codex"
        },
        {
          "depends_on_job_id": "job_run_c5453f21c248430c9398c197e46f0867_review_gemini",
          "latest_verdict": "accept_with_findings",
          "required_verdicts": [
            "accept",
            "accept_with_findings"
          ],
          "state": "completed",
          "workflow_job_id": "review_gemini"
        }
      ],
      "display_model": "Codex GPT-5.5",
      "fresh_session_required": true,
      "job_id": "job_run_c5453f21c248430c9398c197e46f0867_findings_ledger",
      "job_type": "ledger",
      "lane": "codex",
      "max_attempts": 1,
      "role_id": "ledger",
      "state": "completed",
      "workflow_job_id": "findings_ledger"
    },
    {
      "attempt": 1,
      "author": {
        "display_model": "Claude Opus",
        "lane_id": "claude",
        "line": null,
        "ordinal": null,
        "role_id": "reviewer",
        "workflow_job_id": "review_claude"
      },
      "dependencies": [],
      "display_model": "Claude Opus",
      "fresh_session_required": true,
      "job_id": "job_run_c5453f21c248430c9398c197e46f0867_review_claude",
      "job_type": "review",
      "lane": "claude",
      "max_attempts": 1,
      "role_id": "reviewer",
      "state": "completed",
      "workflow_job_id": "review_claude"
    },
    {
      "attempt": 1,
      "author": {
        "display_model": "Codex GPT-5.5",
        "lane_id": "codex",
        "line": null,
        "ordinal": null,
        "role_id": "reviewer",
        "workflow_job_id": "review_codex"
      },
      "dependencies": [],
      "display_model": "Codex GPT-5.5",
      "fresh_session_required": true,
      "job_id": "job_run_c5453f21c248430c9398c197e46f0867_review_codex",
      "job_type": "review",
      "lane": "codex",
      "max_attempts": 1,
      "role_id": "reviewer",
      "state": "completed",
      "workflow_job_id": "review_codex"
    },
    {
      "attempt": 1,
      "author": {
        "display_model": "Gemini 3.1 Pro Preview",
        "lane_id": "gemini",
        "line": null,
        "ordinal": null,
        "role_id": "reviewer",
        "workflow_job_id": "review_gemini"
      },
      "dependencies": [],
      "display_model": "Gemini 3.1 Pro Preview",
      "fresh_session_required": true,
      "job_id": "job_run_c5453f21c248430c9398c197e46f0867_review_gemini",
      "job_type": "review",
      "lane": "gemini",
      "max_attempts": 1,
      "role_id": "reviewer",
      "state": "completed",
      "workflow_job_id": "review_gemini"
    },
    {
      "attempt": 1,
      "author": {
        "display_model": "Claude Opus",
        "lane_id": "claude",
        "line": null,
        "ordinal": null,
        "role_id": "synthesizer",
        "workflow_job_id": "synthesis"
      },
      "dependencies": [
        {
          "depends_on_job_id": "job_run_c5453f21c248430c9398c197e46f0867_findings_ledger",
          "latest_verdict": null,
          "required_verdicts": null,
          "state": "completed",
          "workflow_job_id": "findings_ledger"
        }
      ],
      "display_model": "Claude Opus",
      "fresh_session_required": true,
      "job_id": "job_run_c5453f21c248430c9398c197e46f0867_synthesis",
      "job_type": "synthesis",
      "lane": "claude",
      "max_attempts": 1,
      "role_id": "synthesizer",
      "state": "completed",
      "workflow_job_id": "synthesis"
    }
  ],
  "run": {
    "branch_name": "engram/rfc0021-gold-set-review",
    "run_id": "run_c5453f21c248430c9398c197e46f0867",
    "state": "completed"
  },
  "schema_version": "striatum.evidence.v1",
  "sessions": [
    {
      "close_reason": "run_completed",
      "closed_at": "2026-05-08T18:09:12Z",
      "lane_id": "claude",
      "non_fresh_reason": null,
      "ordinal": 1,
      "registered_at": "2026-05-08T17:52:23Z",
      "role_id": "reviewer",
      "session_id": "sess_2e2b1eeda46f41afb981bcde2f104466",
      "slug": "reviewer-claude-1",
      "state": "closed"
    },
    {
      "close_reason": "run_completed",
      "closed_at": "2026-05-08T18:09:12Z",
      "lane_id": "codex",
      "non_fresh_reason": null,
      "ordinal": 2,
      "registered_at": "2026-05-08T17:52:24Z",
      "role_id": "reviewer",
      "session_id": "sess_0971faeeed284e58ab0a5860ed5cc229",
      "slug": "reviewer-codex-2",
      "state": "closed"
    },
    {
      "close_reason": "run_completed",
      "closed_at": "2026-05-08T18:09:12Z",
      "lane_id": "codex",
      "non_fresh_reason": null,
      "ordinal": 1,
      "registered_at": "2026-05-08T17:52:24Z",
      "role_id": "ledger",
      "session_id": "sess_146bc0ade5c346138142623e398ae5d1",
      "slug": "ledger-codex-1",
      "state": "closed"
    },
    {
      "close_reason": "run_completed",
      "closed_at": "2026-05-08T18:09:12Z",
      "lane_id": "claude",
      "non_fresh_reason": null,
      "ordinal": 1,
      "registered_at": "2026-05-08T17:52:24Z",
      "role_id": "synthesizer",
      "session_id": "sess_84d29cbc82be42dd8b65d91bf03d6ad6",
      "slug": "synthesizer-claude-1",
      "state": "closed"
    },
    {
      "close_reason": "run_completed",
      "closed_at": "2026-05-08T18:09:12Z",
      "lane_id": "gemini",
      "non_fresh_reason": null,
      "ordinal": 1,
      "registered_at": "2026-05-08T17:52:24Z",
      "role_id": "reviewer",
      "session_id": "sess_c897b6bb31c44f38bca4a9879164c053",
      "slug": "reviewer-gemini-1",
      "state": "closed"
    },
    {
      "close_reason": "run_completed",
      "closed_at": "2026-05-08T18:09:12Z",
      "lane_id": "codex",
      "non_fresh_reason": null,
      "ordinal": 1,
      "registered_at": "2026-05-08T17:52:24Z",
      "role_id": "reviewer",
      "session_id": "sess_f8be211c93af45178ae7340608df72a9",
      "slug": "reviewer-codex-1",
      "state": "closed"
    },
    {
      "close_reason": "run_completed",
      "closed_at": "2026-05-08T18:09:12Z",
      "lane_id": "gemini",
      "non_fresh_reason": null,
      "ordinal": 2,
      "registered_at": "2026-05-08T17:58:55Z",
      "role_id": "reviewer",
      "session_id": "sess_8af7779f687846fdbc5e877c78c2abd1",
      "slug": "reviewer-gemini-2",
      "state": "closed"
    },
    {
      "close_reason": "run_completed",
      "closed_at": "2026-05-08T18:09:12Z",
      "lane_id": "codex",
      "non_fresh_reason": null,
      "ordinal": 3,
      "registered_at": "2026-05-08T17:58:55Z",
      "role_id": "reviewer",
      "session_id": "sess_dcf2aaafdcc54bea91196ae783853979",
      "slug": "reviewer-codex-3",
      "state": "closed"
    },
    {
      "close_reason": "run_completed",
      "closed_at": "2026-05-08T18:09:12Z",
      "lane_id": "claude",
      "non_fresh_reason": null,
      "ordinal": 2,
      "registered_at": "2026-05-08T17:58:55Z",
      "role_id": "reviewer",
      "session_id": "sess_e5f06aaea7c34ec39466b1eb10914158",
      "slug": "reviewer-claude-2",
      "state": "closed"
    }
  ],
  "verdicts": [
    {
      "findings_artifact_id": "art_a8cecb02f4ec4c359596fe05b58d3663",
      "job_id": "job_run_c5453f21c248430c9398c197e46f0867_review_claude",
      "rationale": null,
      "session_id": "sess_2e2b1eeda46f41afb981bcde2f104466",
      "verdict": "needs_revision",
      "verdict_id": "verdict_5508144e91df462db6a8baa985d5daa8"
    },
    {
      "findings_artifact_id": "art_7c247207c0854436a3bae8a13c9e4b3b",
      "job_id": "job_run_c5453f21c248430c9398c197e46f0867_review_codex",
      "rationale": null,
      "session_id": "sess_f8be211c93af45178ae7340608df72a9",
      "verdict": "needs_revision",
      "verdict_id": "verdict_d37735e7418748cc986946d60cca479d"
    },
    {
      "findings_artifact_id": "art_971505ba266c4940b3e8211d12a3c6a0",
      "job_id": "job_run_c5453f21c248430c9398c197e46f0867_review_gemini",
      "rationale": null,
      "session_id": "sess_c897b6bb31c44f38bca4a9879164c053",
      "verdict": "needs_revision",
      "verdict_id": "verdict_4d96e512d422446e85878bf12450a742"
    },
    {
      "findings_artifact_id": "art_a8cecb02f4ec4c359596fe05b58d3663",
      "job_id": "job_run_c5453f21c248430c9398c197e46f0867_review_claude",
      "rationale": "<redacted-free-text>",
      "session_id": "sess_e5f06aaea7c34ec39466b1eb10914158",
      "verdict": "accept_with_findings",
      "verdict_id": "verdict_90a064b9b60b4c25a95210f4ebe33075"
    },
    {
      "findings_artifact_id": "art_7c247207c0854436a3bae8a13c9e4b3b",
      "job_id": "job_run_c5453f21c248430c9398c197e46f0867_review_codex",
      "rationale": "<redacted-free-text>",
      "session_id": "sess_dcf2aaafdcc54bea91196ae783853979",
      "verdict": "accept_with_findings",
      "verdict_id": "verdict_24aff1082b034690bc9433cf5aebb976"
    },
    {
      "findings_artifact_id": "art_971505ba266c4940b3e8211d12a3c6a0",
      "job_id": "job_run_c5453f21c248430c9398c197e46f0867_review_gemini",
      "rationale": "<redacted-free-text>",
      "session_id": "sess_8af7779f687846fdbc5e877c78c2abd1",
      "verdict": "accept_with_findings",
      "verdict_id": "verdict_5b7b90a833c2439596051c97131ff9b1"
    },
    {
      "findings_artifact_id": "art_794b209957ec4187ba12e05eedb219b3",
      "job_id": "job_run_c5453f21c248430c9398c197e46f0867_final_review",
      "rationale": null,
      "session_id": "sess_0971faeeed284e58ab0a5860ed5cc229",
      "verdict": "accept_with_findings",
      "verdict_id": "verdict_1084dadfc98a47cf95def3950704f8d3"
    }
  ],
  "workflow": {
    "workflow_id": "rfc-0021-gold-set-review",
    "workflow_version": "2026-05-08+initial"
  }
}
```
