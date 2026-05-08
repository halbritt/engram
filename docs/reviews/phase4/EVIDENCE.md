# Striatum Evidence Export

Run ID: `run_5d6486686414472ea6b82f6f5a9d172d`
Branch: `engram/phase4-spec-review`
Run state: `completed`
Exported at: `2026-05-08T08:50:49Z`

Live SQLite state remains ignored under `.striatum/` and is not part of this export.

## Status Output

```json
{"blocked_downstream_jobs":[],"claimable_jobs":[],"human_checkpoints":[],"jobs":{"completed":6},"latest_non_accepting_review_verdicts":[],"next_actions":[],"open_blockers":[],"runs":[{"branch_name":"engram/phase4-spec-review","run_id":"run_5d6486686414472ea6b82f6f5a9d172d","state":"completed"}]}
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
      "artifact_id": "art_a6c8180e90b74cd097433375f159ae2e",
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
      "content_sha256": "97d9adcc1d00172f24a63cef7a0ed327e906bac146ac199cf75dcd8c6dc0afa8",
      "job_id": "job_run_5d6486686414472ea6b82f6f5a9d172d_final_review",
      "logical_name": "review",
      "repo_path": "docs/reviews/phase4/PHASE_4_SPEC_FINAL_REVIEW.md",
      "session_id": "sess_0d2539973b43443bb889273d9c2ca897"
    },
    {
      "artifact_id": "art_e9442fb1ee234026b983ca9ef8433b3d",
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
      "content_sha256": "a3835aa1686fe8d2cc8c9ab5867eff86abab3ee2d4a31330024de7c231d561af",
      "job_id": "job_run_5d6486686414472ea6b82f6f5a9d172d_findings_ledger",
      "logical_name": "ledger",
      "repo_path": "docs/reviews/phase4/PHASE_4_SPEC_FINDINGS_LEDGER.md",
      "session_id": "sess_f2eafc8f756a45929b646bc9e88222a8"
    },
    {
      "artifact_id": "art_5bb3f15e6d5d4be38ed1adb6fc177307",
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
      "content_sha256": "b9ec7bcbc0227dbcdb16276c5e3d26a5fce5b1462739f900455f528a639cabe2",
      "job_id": "job_run_5d6486686414472ea6b82f6f5a9d172d_review_claude",
      "logical_name": "review",
      "repo_path": "docs/reviews/phase4/PHASE_4_SPEC_REVIEW_claude.md",
      "session_id": "sess_699c7cf9cd264412bd876f5a56236da0"
    },
    {
      "artifact_id": "art_5b17bad375a44d4ca0cba46959e94e5f",
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
      "content_sha256": "a6aa6997b031ed4ee89aa8c76c5bbbdcf2fb11e2c0ebf4d7176ca4647cffa2c8",
      "job_id": "job_run_5d6486686414472ea6b82f6f5a9d172d_review_codex",
      "logical_name": "review",
      "repo_path": "docs/reviews/phase4/PHASE_4_SPEC_REVIEW_codex.md",
      "session_id": "sess_39825812af2b4163a2b4ea55e87ee372"
    },
    {
      "artifact_id": "art_626844fc7e264f158848dadeaa4fbc57",
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
      "content_sha256": "f18ccf7af599499ee82583488b54b033937a3c48a2f16293c87984824b5a089d",
      "job_id": "job_run_5d6486686414472ea6b82f6f5a9d172d_review_gemini",
      "logical_name": "review",
      "repo_path": "docs/reviews/phase4/PHASE_4_SPEC_REVIEW_gemini.md",
      "session_id": "sess_157da9fb96fa46f0876a3a3fc9804691"
    },
    {
      "artifact_id": "art_5994d4053c504850aacee8c2f9052b84",
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
      "content_sha256": "8488ac0f6d960558368133454c502c110ef01a8d6e3bb37842162af9a0c2239a",
      "job_id": "job_run_5d6486686414472ea6b82f6f5a9d172d_synthesis",
      "logical_name": "synthesis",
      "repo_path": "docs/reviews/phase4/PHASE_4_SPEC_SYNTHESIS.md",
      "session_id": "sess_59232121406649e890a51fa322928658"
    }
  ],
  "blocked_downstream_jobs": [],
  "blockers": [],
  "exported_at": "2026-05-08T08:50:49Z",
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
          "depends_on_job_id": "job_run_5d6486686414472ea6b82f6f5a9d172d_synthesis",
          "latest_verdict": null,
          "required_verdicts": null,
          "state": "completed",
          "workflow_job_id": "synthesis"
        }
      ],
      "display_model": "Codex GPT-5.5",
      "fresh_session_required": true,
      "job_id": "job_run_5d6486686414472ea6b82f6f5a9d172d_final_review",
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
          "depends_on_job_id": "job_run_5d6486686414472ea6b82f6f5a9d172d_review_claude",
          "latest_verdict": "accept_with_findings",
          "required_verdicts": [
            "accept",
            "accept_with_findings"
          ],
          "state": "completed",
          "workflow_job_id": "review_claude"
        },
        {
          "depends_on_job_id": "job_run_5d6486686414472ea6b82f6f5a9d172d_review_codex",
          "latest_verdict": "accept_with_findings",
          "required_verdicts": [
            "accept",
            "accept_with_findings"
          ],
          "state": "completed",
          "workflow_job_id": "review_codex"
        },
        {
          "depends_on_job_id": "job_run_5d6486686414472ea6b82f6f5a9d172d_review_gemini",
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
      "job_id": "job_run_5d6486686414472ea6b82f6f5a9d172d_findings_ledger",
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
      "job_id": "job_run_5d6486686414472ea6b82f6f5a9d172d_review_claude",
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
      "job_id": "job_run_5d6486686414472ea6b82f6f5a9d172d_review_codex",
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
      "job_id": "job_run_5d6486686414472ea6b82f6f5a9d172d_review_gemini",
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
          "depends_on_job_id": "job_run_5d6486686414472ea6b82f6f5a9d172d_findings_ledger",
          "latest_verdict": null,
          "required_verdicts": null,
          "state": "completed",
          "workflow_job_id": "findings_ledger"
        }
      ],
      "display_model": "Claude Opus",
      "fresh_session_required": true,
      "job_id": "job_run_5d6486686414472ea6b82f6f5a9d172d_synthesis",
      "job_type": "synthesis",
      "lane": "claude",
      "max_attempts": 1,
      "role_id": "synthesizer",
      "state": "completed",
      "workflow_job_id": "synthesis"
    }
  ],
  "run": {
    "branch_name": "engram/phase4-spec-review",
    "run_id": "run_5d6486686414472ea6b82f6f5a9d172d",
    "state": "completed"
  },
  "schema_version": "striatum.evidence.v1",
  "sessions": [
    {
      "close_reason": "run_completed",
      "closed_at": "2026-05-08T08:50:38Z",
      "lane_id": "gemini",
      "non_fresh_reason": null,
      "ordinal": 1,
      "registered_at": "2026-05-08T08:44:23Z",
      "role_id": "reviewer",
      "session_id": "sess_157da9fb96fa46f0876a3a3fc9804691",
      "slug": "reviewer-gemini-1",
      "state": "closed"
    },
    {
      "close_reason": "run_completed",
      "closed_at": "2026-05-08T08:50:38Z",
      "lane_id": "codex",
      "non_fresh_reason": null,
      "ordinal": 1,
      "registered_at": "2026-05-08T08:44:23Z",
      "role_id": "reviewer",
      "session_id": "sess_39825812af2b4163a2b4ea55e87ee372",
      "slug": "reviewer-codex-1",
      "state": "closed"
    },
    {
      "close_reason": "run_completed",
      "closed_at": "2026-05-08T08:50:38Z",
      "lane_id": "claude",
      "non_fresh_reason": null,
      "ordinal": 1,
      "registered_at": "2026-05-08T08:44:23Z",
      "role_id": "reviewer",
      "session_id": "sess_699c7cf9cd264412bd876f5a56236da0",
      "slug": "reviewer-claude-1",
      "state": "closed"
    },
    {
      "close_reason": "run_completed",
      "closed_at": "2026-05-08T08:50:38Z",
      "lane_id": "codex",
      "non_fresh_reason": null,
      "ordinal": 1,
      "registered_at": "2026-05-08T08:47:40Z",
      "role_id": "ledger",
      "session_id": "sess_f2eafc8f756a45929b646bc9e88222a8",
      "slug": "ledger-codex-1",
      "state": "closed"
    },
    {
      "close_reason": "run_completed",
      "closed_at": "2026-05-08T08:50:38Z",
      "lane_id": "claude",
      "non_fresh_reason": null,
      "ordinal": 1,
      "registered_at": "2026-05-08T08:48:44Z",
      "role_id": "synthesizer",
      "session_id": "sess_59232121406649e890a51fa322928658",
      "slug": "synthesizer-claude-1",
      "state": "closed"
    },
    {
      "close_reason": "run_completed",
      "closed_at": "2026-05-08T08:50:38Z",
      "lane_id": "codex",
      "non_fresh_reason": null,
      "ordinal": 2,
      "registered_at": "2026-05-08T08:50:08Z",
      "role_id": "reviewer",
      "session_id": "sess_0d2539973b43443bb889273d9c2ca897",
      "slug": "reviewer-codex-2",
      "state": "closed"
    }
  ],
  "verdicts": [
    {
      "findings_artifact_id": "art_5bb3f15e6d5d4be38ed1adb6fc177307",
      "job_id": "job_run_5d6486686414472ea6b82f6f5a9d172d_review_claude",
      "rationale": "<redacted-free-text>",
      "session_id": "sess_699c7cf9cd264412bd876f5a56236da0",
      "verdict": "accept_with_findings",
      "verdict_id": "verdict_586d4fcb7e594d8fb0305756c4784279"
    },
    {
      "findings_artifact_id": "art_5b17bad375a44d4ca0cba46959e94e5f",
      "job_id": "job_run_5d6486686414472ea6b82f6f5a9d172d_review_codex",
      "rationale": "<redacted-free-text>",
      "session_id": "sess_39825812af2b4163a2b4ea55e87ee372",
      "verdict": "accept_with_findings",
      "verdict_id": "verdict_785ba1ee5db048adb977de25f489e864"
    },
    {
      "findings_artifact_id": "art_626844fc7e264f158848dadeaa4fbc57",
      "job_id": "job_run_5d6486686414472ea6b82f6f5a9d172d_review_gemini",
      "rationale": "<redacted-free-text>",
      "session_id": "sess_157da9fb96fa46f0876a3a3fc9804691",
      "verdict": "accept_with_findings",
      "verdict_id": "verdict_be9b35e9092e4c4d96f9e5ea888ca310"
    },
    {
      "findings_artifact_id": "art_a6c8180e90b74cd097433375f159ae2e",
      "job_id": "job_run_5d6486686414472ea6b82f6f5a9d172d_final_review",
      "rationale": "<redacted-free-text>",
      "session_id": "sess_0d2539973b43443bb889273d9c2ca897",
      "verdict": "accept_with_findings",
      "verdict_id": "verdict_0ef722f470ad4251a10213f4213c8ba1"
    }
  ],
  "workflow": {
    "workflow_id": "phase-4-build-spec-review",
    "workflow_version": "2026-05-07+initial"
  }
}
```
