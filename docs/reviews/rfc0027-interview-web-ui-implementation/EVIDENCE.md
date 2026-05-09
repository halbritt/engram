# Striatum Evidence Export

Run ID: `run_71ed7436b9b24d7fb503b4483ae57dd2`
Branch: `engram/rfc0027-interview-web-ui-implementation`
Run state: `completed`
Exported at: `2026-05-09T00:32:43Z`

Live SQLite state remains ignored under `.striatum/` and is not part of this export.

## Status Output

```json
{"blocked_downstream_jobs":[],"claimable_jobs":[],"human_checkpoints":[],"jobs":{"completed":4},"latest_non_accepting_review_verdicts":[],"next_actions":[],"open_blockers":[],"process_health":"<redacted-free-text>","runs":[{"branch_name":"engram/rfc0027-interview-web-ui-implementation","run_id":"run_71ed7436b9b24d7fb503b4483ae57dd2","state":"completed"}]}
```

## Doctor Output

```json
{"ok":false,"problems":["skill bundle outdated for profile 'claude_code': manifest_version='1.1.0' running_version='1.4.1' templates_changed=[] \u2014 run `striatum --repo /home/halbritt/git/engram skills install --profile claude_code`"],"schema_version":"1"}
```

## Snapshot

```json
{
  "artifacts": [
    {
      "artifact_id": "art_fd513db1e73a4242b7422a2fdc5a19a9",
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
      "content_sha256": "37f4fb639f3636d8f156fe45a45b0c0d7b98c8d77f50f445e93b2be2b23cc56b",
      "job_id": "job_run_71ed7436b9b24d7fb503b4483ae57dd2_final_review",
      "logical_name": "final_review",
      "repo_path": "docs/reviews/rfc0027-interview-web-ui-implementation/FINAL_REVIEW.md",
      "session_id": "sess_5d5ac96efb614481bcf60a58e4d5825c"
    },
    {
      "artifact_id": "art_2497925fa5f34ba3962b4f4b7e3d99b5",
      "artifact_kind": "handoff",
      "author": {
        "actual_author_line": "author: author-codex-gpt-5.5-002",
        "display_model": "Codex GPT-5.5",
        "lane_id": "codex",
        "line": "author: author-codex-gpt-5.5-002",
        "ordinal": 2,
        "role_id": "author",
        "workflow_job_id": "implement_web_app"
      },
      "content_sha256": "b8ebbfa0e49fe317f6f2813edb0ef2b4b738b5b92e013d1e4d88bc7ca8e3e26a",
      "job_id": "job_run_71ed7436b9b24d7fb503b4483ae57dd2_implement_web_app",
      "logical_name": "web_app_handoff",
      "repo_path": "docs/reviews/rfc0027-interview-web-ui-implementation/PASS_B1_WEB_APP_HANDOFF.md",
      "session_id": "sess_8e88592a8a2e47828eee216e3350f42d"
    },
    {
      "artifact_id": "art_dad7ce00412347d090fb8417c662f710",
      "artifact_kind": "handoff",
      "author": {
        "actual_author_line": "author: author-codex-gpt-5.5-001",
        "display_model": "Codex GPT-5.5",
        "lane_id": "codex",
        "line": "author: author-codex-gpt-5.5-001",
        "ordinal": 1,
        "role_id": "author",
        "workflow_job_id": "implement_serve_cli"
      },
      "content_sha256": "2ba8e181b9994360ce929603d1315bb20002c240deb415d8b8932594cec48d67",
      "job_id": "job_run_71ed7436b9b24d7fb503b4483ae57dd2_implement_serve_cli",
      "logical_name": "serve_cli_handoff",
      "repo_path": "docs/reviews/rfc0027-interview-web-ui-implementation/PASS_B2_SERVE_CLI_HANDOFF.md",
      "session_id": "sess_9e964bb10c8647618474cfe1eb1aba74"
    },
    {
      "artifact_id": "art_9a874d09675a43c98e72175ab2d844eb",
      "artifact_kind": "finding",
      "author": {
        "actual_author_line": "author: reviewer-codex-gpt-5.5-001",
        "display_model": "Codex GPT-5.5",
        "lane_id": "codex",
        "line": "author: reviewer-codex-gpt-5.5-001",
        "ordinal": 1,
        "role_id": "reviewer",
        "workflow_job_id": "verify_web_ui"
      },
      "content_sha256": "dfd1ddbb4df51ad5174641de96f7bd3fadf3c3240ff796995d5a4abd825bbb99",
      "job_id": "job_run_71ed7436b9b24d7fb503b4483ae57dd2_verify_web_ui",
      "logical_name": "verification_report",
      "repo_path": "docs/reviews/rfc0027-interview-web-ui-implementation/VERIFICATION_REPORT.md",
      "session_id": "sess_7b433333dd5b4c239118fa6a0cc120d1"
    }
  ],
  "blocked_downstream_jobs": [],
  "blockers": [],
  "exported_at": "2026-05-09T00:32:43Z",
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
          "depends_on_job_id": "job_run_71ed7436b9b24d7fb503b4483ae57dd2_verify_web_ui",
          "latest_verdict": "accept_with_findings",
          "required_verdicts": [
            "accept",
            "accept_with_findings"
          ],
          "state": "completed",
          "workflow_job_id": "verify_web_ui"
        }
      ],
      "display_model": "Codex GPT-5.5",
      "fresh_session_required": true,
      "job_id": "job_run_71ed7436b9b24d7fb503b4483ae57dd2_final_review",
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
        "role_id": "author",
        "workflow_job_id": "implement_serve_cli"
      },
      "dependencies": [],
      "display_model": "Codex GPT-5.5",
      "fresh_session_required": true,
      "job_id": "job_run_71ed7436b9b24d7fb503b4483ae57dd2_implement_serve_cli",
      "job_type": "draft",
      "lane": "codex",
      "max_attempts": 1,
      "role_id": "author",
      "state": "completed",
      "workflow_job_id": "implement_serve_cli"
    },
    {
      "attempt": 1,
      "author": {
        "display_model": "Codex GPT-5.5",
        "lane_id": "codex",
        "line": null,
        "ordinal": null,
        "role_id": "author",
        "workflow_job_id": "implement_web_app"
      },
      "dependencies": [],
      "display_model": "Codex GPT-5.5",
      "fresh_session_required": false,
      "job_id": "job_run_71ed7436b9b24d7fb503b4483ae57dd2_implement_web_app",
      "job_type": "draft",
      "lane": "codex",
      "max_attempts": 1,
      "role_id": "author",
      "state": "completed",
      "workflow_job_id": "implement_web_app"
    },
    {
      "attempt": 1,
      "author": {
        "display_model": "Codex GPT-5.5",
        "lane_id": "codex",
        "line": null,
        "ordinal": null,
        "role_id": "reviewer",
        "workflow_job_id": "verify_web_ui"
      },
      "dependencies": [
        {
          "depends_on_job_id": "job_run_71ed7436b9b24d7fb503b4483ae57dd2_implement_serve_cli",
          "latest_verdict": null,
          "required_verdicts": null,
          "state": "completed",
          "workflow_job_id": "implement_serve_cli"
        },
        {
          "depends_on_job_id": "job_run_71ed7436b9b24d7fb503b4483ae57dd2_implement_web_app",
          "latest_verdict": null,
          "required_verdicts": null,
          "state": "completed",
          "workflow_job_id": "implement_web_app"
        }
      ],
      "display_model": "Codex GPT-5.5",
      "fresh_session_required": true,
      "job_id": "job_run_71ed7436b9b24d7fb503b4483ae57dd2_verify_web_ui",
      "job_type": "review",
      "lane": "codex",
      "max_attempts": 1,
      "role_id": "reviewer",
      "state": "completed",
      "workflow_job_id": "verify_web_ui"
    }
  ],
  "run": {
    "branch_name": "engram/rfc0027-interview-web-ui-implementation",
    "run_id": "run_71ed7436b9b24d7fb503b4483ae57dd2",
    "state": "completed"
  },
  "schema_version": "striatum.evidence.v1",
  "sessions": [
    {
      "close_reason": "run_completed",
      "closed_at": "2026-05-09T00:32:43Z",
      "lane_id": "codex",
      "non_fresh_reason": null,
      "ordinal": 2,
      "registered_at": "2026-05-09T00:07:38Z",
      "role_id": "author",
      "session_id": "sess_8e88592a8a2e47828eee216e3350f42d",
      "slug": "author-codex-2",
      "state": "closed"
    },
    {
      "close_reason": "run_completed",
      "closed_at": "2026-05-09T00:32:43Z",
      "lane_id": "codex",
      "non_fresh_reason": null,
      "ordinal": 1,
      "registered_at": "2026-05-09T00:07:38Z",
      "role_id": "author",
      "session_id": "sess_9e964bb10c8647618474cfe1eb1aba74",
      "slug": "author-codex-1",
      "state": "closed"
    },
    {
      "close_reason": "run_completed",
      "closed_at": "2026-05-09T00:32:43Z",
      "lane_id": "codex",
      "non_fresh_reason": "single-process orchestrator drives review jobs in same session",
      "ordinal": 1,
      "registered_at": "2026-05-09T00:24:42Z",
      "role_id": "reviewer",
      "session_id": "sess_7b433333dd5b4c239118fa6a0cc120d1",
      "slug": "reviewer-codex-1",
      "state": "closed"
    },
    {
      "close_reason": "run_completed",
      "closed_at": "2026-05-09T00:32:43Z",
      "lane_id": "codex",
      "non_fresh_reason": "single-process orchestrator",
      "ordinal": 2,
      "registered_at": "2026-05-09T00:28:55Z",
      "role_id": "reviewer",
      "session_id": "sess_5d5ac96efb614481bcf60a58e4d5825c",
      "slug": "reviewer-codex-2",
      "state": "closed"
    }
  ],
  "verdicts": [
    {
      "findings_artifact_id": "art_9a874d09675a43c98e72175ab2d844eb",
      "job_id": "job_run_71ed7436b9b24d7fb503b4483ae57dd2_verify_web_ui",
      "rationale": null,
      "session_id": "sess_7b433333dd5b4c239118fa6a0cc120d1",
      "verdict": "accept_with_findings",
      "verdict_id": "verdict_c55a9917bab34b75aad6567c55b63641"
    },
    {
      "findings_artifact_id": "art_fd513db1e73a4242b7422a2fdc5a19a9",
      "job_id": "job_run_71ed7436b9b24d7fb503b4483ae57dd2_final_review",
      "rationale": null,
      "session_id": "sess_5d5ac96efb614481bcf60a58e4d5825c",
      "verdict": "accept_with_findings",
      "verdict_id": "verdict_a3421315cebf4f098906b8a136c6bb7b"
    }
  ],
  "workflow": {
    "workflow_id": "rfc-0027-interview-web-ui-implementation",
    "workflow_version": "2026-05-09+post-passA-parallel-B"
  }
}
```
