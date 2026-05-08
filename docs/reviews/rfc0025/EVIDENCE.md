# Striatum Evidence Export

Run ID: `run_7ed4d7764ff84867a29692f575a50b50`
Branch: `engram/rfc0025-command-names-review`
Run state: `completed`
Exported at: `2026-05-08T15:19:23Z`

Live SQLite state remains ignored under `.striatum/` and is not part of this export.

## Status Output

```json
{"blocked_downstream_jobs":[],"claimable_jobs":[],"human_checkpoints":[],"jobs":{"completed":6},"latest_non_accepting_review_verdicts":[],"next_actions":[],"open_blockers":[],"runs":[{"branch_name":"engram/rfc0025-command-names-review","run_id":"run_7ed4d7764ff84867a29692f575a50b50","state":"completed"}]}
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
      "artifact_id": "art_ff60a04285e742f8971fe08e66ed46c5",
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
      "content_sha256": "a17c7e7e688e138e6177910d2cd8affd706a8dcfd1a8291e5012d568db9f7080",
      "job_id": "job_run_7ed4d7764ff84867a29692f575a50b50_final_review",
      "logical_name": "review",
      "repo_path": "docs/reviews/rfc0025/RFC_0025_COMMAND_NAMES_FINAL_REVIEW.md",
      "session_id": "sess_2834eaf1375e4dc19e825682b9c82b15"
    },
    {
      "artifact_id": "art_7c94f707cf2a41fd913bd1b0f43af214",
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
      "content_sha256": "94054c5b8da5b38d798cf078f24b9c7243940e856fe8f669cdccfde5c0964dee",
      "job_id": "job_run_7ed4d7764ff84867a29692f575a50b50_findings_ledger",
      "logical_name": "ledger",
      "repo_path": "docs/reviews/rfc0025/RFC_0025_COMMAND_NAMES_FINDINGS_LEDGER.md",
      "session_id": "sess_b46e5a1685424bf4a35cdca071ad4222"
    },
    {
      "artifact_id": "art_4d778df56d124038a1c0881ace49b981",
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
      "content_sha256": "2abac1c222cf5ac4461d6948dc8ee29d29a02e65064a2bd4d2580d0b57db0d46",
      "job_id": "job_run_7ed4d7764ff84867a29692f575a50b50_review_claude",
      "logical_name": "review",
      "repo_path": "docs/reviews/rfc0025/RFC_0025_COMMAND_NAMES_REVIEW_claude.md",
      "session_id": "sess_93a082eea9f748e39029ad09f1f66fb3"
    },
    {
      "artifact_id": "art_b880c50602f341a3b39424f323c179e9",
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
      "content_sha256": "4bd6f3694f84020bc1bf36403b4cb61d94650922f0d5fff61a6ea97639baaadf",
      "job_id": "job_run_7ed4d7764ff84867a29692f575a50b50_review_codex",
      "logical_name": "review",
      "repo_path": "docs/reviews/rfc0025/RFC_0025_COMMAND_NAMES_REVIEW_codex.md",
      "session_id": "sess_4c66db6c39054be1a5ac937b5d5dcef0"
    },
    {
      "artifact_id": "art_4955d42259ac4f058a191e78cc65e58d",
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
      "content_sha256": "6378f1f3a0e3240b169529e51e23922fe95d9037b7f351249fd6e862af4a4531",
      "job_id": "job_run_7ed4d7764ff84867a29692f575a50b50_review_gemini",
      "logical_name": "review",
      "repo_path": "docs/reviews/rfc0025/RFC_0025_COMMAND_NAMES_REVIEW_gemini.md",
      "session_id": "sess_5dbdb557e03d462f8180d7eaa814e6a9"
    },
    {
      "artifact_id": "art_d6cae5e7d8e14578be299d95f9929137",
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
      "content_sha256": "c1b47779261c91ea79ff39393d5ad04a18d9f0094ca9e075c56e0094d89f127f",
      "job_id": "job_run_7ed4d7764ff84867a29692f575a50b50_synthesis",
      "logical_name": "synthesis",
      "repo_path": "docs/reviews/rfc0025/RFC_0025_COMMAND_NAMES_SYNTHESIS.md",
      "session_id": "sess_4b98d7bfb6d54d879345960d1a64c0ae"
    }
  ],
  "blocked_downstream_jobs": [],
  "blockers": [],
  "exported_at": "2026-05-08T15:19:23Z",
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
          "depends_on_job_id": "job_run_7ed4d7764ff84867a29692f575a50b50_synthesis",
          "latest_verdict": null,
          "required_verdicts": null,
          "state": "completed",
          "workflow_job_id": "synthesis"
        }
      ],
      "display_model": "Codex GPT-5.5",
      "fresh_session_required": true,
      "job_id": "job_run_7ed4d7764ff84867a29692f575a50b50_final_review",
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
          "depends_on_job_id": "job_run_7ed4d7764ff84867a29692f575a50b50_review_claude",
          "latest_verdict": "accept_with_findings",
          "required_verdicts": [
            "accept",
            "accept_with_findings"
          ],
          "state": "completed",
          "workflow_job_id": "review_claude"
        },
        {
          "depends_on_job_id": "job_run_7ed4d7764ff84867a29692f575a50b50_review_codex",
          "latest_verdict": "accept_with_findings",
          "required_verdicts": [
            "accept",
            "accept_with_findings"
          ],
          "state": "completed",
          "workflow_job_id": "review_codex"
        },
        {
          "depends_on_job_id": "job_run_7ed4d7764ff84867a29692f575a50b50_review_gemini",
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
      "job_id": "job_run_7ed4d7764ff84867a29692f575a50b50_findings_ledger",
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
      "job_id": "job_run_7ed4d7764ff84867a29692f575a50b50_review_claude",
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
      "job_id": "job_run_7ed4d7764ff84867a29692f575a50b50_review_codex",
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
      "job_id": "job_run_7ed4d7764ff84867a29692f575a50b50_review_gemini",
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
          "depends_on_job_id": "job_run_7ed4d7764ff84867a29692f575a50b50_findings_ledger",
          "latest_verdict": null,
          "required_verdicts": null,
          "state": "completed",
          "workflow_job_id": "findings_ledger"
        }
      ],
      "display_model": "Claude Opus",
      "fresh_session_required": true,
      "job_id": "job_run_7ed4d7764ff84867a29692f575a50b50_synthesis",
      "job_type": "synthesis",
      "lane": "claude",
      "max_attempts": 1,
      "role_id": "synthesizer",
      "state": "completed",
      "workflow_job_id": "synthesis"
    }
  ],
  "run": {
    "branch_name": "engram/rfc0025-command-names-review",
    "run_id": "run_7ed4d7764ff84867a29692f575a50b50",
    "state": "completed"
  },
  "schema_version": "striatum.evidence.v1",
  "sessions": [
    {
      "close_reason": "run_completed",
      "closed_at": "2026-05-08T15:19:04Z",
      "lane_id": "codex",
      "non_fresh_reason": null,
      "ordinal": 1,
      "registered_at": "2026-05-08T15:08:26Z",
      "role_id": "synthesizer",
      "session_id": "sess_0d818d78f8aa4459a256709d2dac2ed0",
      "slug": "synthesizer-codex-1",
      "state": "closed"
    },
    {
      "close_reason": "run_completed",
      "closed_at": "2026-05-08T15:19:04Z",
      "lane_id": "codex",
      "non_fresh_reason": null,
      "ordinal": 2,
      "registered_at": "2026-05-08T15:08:26Z",
      "role_id": "reviewer",
      "session_id": "sess_2834eaf1375e4dc19e825682b9c82b15",
      "slug": "reviewer-codex-2",
      "state": "closed"
    },
    {
      "close_reason": "run_completed",
      "closed_at": "2026-05-08T15:19:04Z",
      "lane_id": "codex",
      "non_fresh_reason": null,
      "ordinal": 1,
      "registered_at": "2026-05-08T15:08:26Z",
      "role_id": "reviewer",
      "session_id": "sess_4c66db6c39054be1a5ac937b5d5dcef0",
      "slug": "reviewer-codex-1",
      "state": "closed"
    },
    {
      "close_reason": "run_completed",
      "closed_at": "2026-05-08T15:19:04Z",
      "lane_id": "gemini",
      "non_fresh_reason": null,
      "ordinal": 1,
      "registered_at": "2026-05-08T15:08:26Z",
      "role_id": "reviewer",
      "session_id": "sess_5dbdb557e03d462f8180d7eaa814e6a9",
      "slug": "reviewer-gemini-1",
      "state": "closed"
    },
    {
      "close_reason": "run_completed",
      "closed_at": "2026-05-08T15:19:04Z",
      "lane_id": "claude",
      "non_fresh_reason": null,
      "ordinal": 1,
      "registered_at": "2026-05-08T15:08:26Z",
      "role_id": "reviewer",
      "session_id": "sess_93a082eea9f748e39029ad09f1f66fb3",
      "slug": "reviewer-claude-1",
      "state": "closed"
    },
    {
      "close_reason": "run_completed",
      "closed_at": "2026-05-08T15:19:04Z",
      "lane_id": "codex",
      "non_fresh_reason": null,
      "ordinal": 1,
      "registered_at": "2026-05-08T15:08:26Z",
      "role_id": "ledger",
      "session_id": "sess_b46e5a1685424bf4a35cdca071ad4222",
      "slug": "ledger-codex-1",
      "state": "closed"
    },
    {
      "close_reason": "run_completed",
      "closed_at": "2026-05-08T15:19:04Z",
      "lane_id": "claude",
      "non_fresh_reason": null,
      "ordinal": 1,
      "registered_at": "2026-05-08T15:17:36Z",
      "role_id": "synthesizer",
      "session_id": "sess_4b98d7bfb6d54d879345960d1a64c0ae",
      "slug": "synthesizer-claude-1",
      "state": "closed"
    }
  ],
  "verdicts": [
    {
      "findings_artifact_id": "art_4d778df56d124038a1c0881ace49b981",
      "job_id": "job_run_7ed4d7764ff84867a29692f575a50b50_review_claude",
      "rationale": "<redacted-free-text>",
      "session_id": "sess_93a082eea9f748e39029ad09f1f66fb3",
      "verdict": "accept_with_findings",
      "verdict_id": "verdict_63e61823c6094e9cae7649065e378f3a"
    },
    {
      "findings_artifact_id": "art_4955d42259ac4f058a191e78cc65e58d",
      "job_id": "job_run_7ed4d7764ff84867a29692f575a50b50_review_gemini",
      "rationale": "<redacted-free-text>",
      "session_id": "sess_5dbdb557e03d462f8180d7eaa814e6a9",
      "verdict": "accept_with_findings",
      "verdict_id": "verdict_199122595f4b4998b0d7f89bf84894df"
    },
    {
      "findings_artifact_id": "art_b880c50602f341a3b39424f323c179e9",
      "job_id": "job_run_7ed4d7764ff84867a29692f575a50b50_review_codex",
      "rationale": "<redacted-free-text>",
      "session_id": "sess_4c66db6c39054be1a5ac937b5d5dcef0",
      "verdict": "accept_with_findings",
      "verdict_id": "verdict_8c60019ce58a434ca4224b7bf4ee72b3"
    },
    {
      "findings_artifact_id": "art_ff60a04285e742f8971fe08e66ed46c5",
      "job_id": "job_run_7ed4d7764ff84867a29692f575a50b50_final_review",
      "rationale": "<redacted-free-text>",
      "session_id": "sess_2834eaf1375e4dc19e825682b9c82b15",
      "verdict": "accept",
      "verdict_id": "verdict_23a0a5d3f958480e80407fea1d4f639e"
    }
  ],
  "workflow": {
    "workflow_id": "rfc-0025-command-names-review",
    "workflow_version": "2026-05-08+initial"
  }
}
```
