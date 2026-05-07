# Agent Runner Evidence Export

Run ID: `run_cc00924e495a412a9775bc71e4eec27b`
Branch: `agent-runner/rfc-0014-validation`
Run state: `completed`
Exported at: `2026-05-06T19:12:51Z`

Live SQLite state remains ignored under `.agent_runner/` and is not part of this export.

## Status Output

```json
{"blocked_downstream_jobs":[],"claimable_jobs":[],"human_checkpoints":[],"jobs":{"completed":6},"latest_non_accepting_review_verdicts":[],"next_actions":[],"open_blockers":[],"runs":[{"branch_name":"agent-runner/rfc-0014-validation","run_id":"run_cc00924e495a412a9775bc71e4eec27b","state":"completed"}]}
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
      "artifact_id": "art_896ac62245ee4fd0b2101b7b82884e2b",
      "artifact_kind": "finding",
      "author": {
        "display_model": "Codex GPT-5.5",
        "lane_id": "codex",
        "line": "author: reviewer-codex-gpt-5.5-002",
        "ordinal": 2,
        "role_id": "reviewer",
        "workflow_job_id": "final_review"
      },
      "content_sha256": "ce5987522f88cdd168cd158379f6fbd7e68fa8185672b2586f6d691ce60fface",
      "job_id": "job_run_cc00924e495a412a9775bc71e4eec27b_final_review",
      "logical_name": "review",
      "repo_path": "docs/reviews/rfc-0014-operational-artifact-home/reruns/2026-05-06-redaction-rerun-2/RFC_0014_FINAL_REVIEW.md",
      "session_id": "sess_05dbd70d41774a3e8503e17ed76a5fd6"
    },
    {
      "artifact_id": "art_9412c6e62985454882140e8b2ff65909",
      "artifact_kind": "findings_ledger",
      "author": {
        "display_model": "Codex GPT-5.5",
        "lane_id": "codex",
        "line": "author: ledger-codex-gpt-5.5-001",
        "ordinal": 1,
        "role_id": "ledger",
        "workflow_job_id": "findings_ledger"
      },
      "content_sha256": "ba253e48e47643b6cb9bb5e1709801147b91323202d04742130b38cae381fb33",
      "job_id": "job_run_cc00924e495a412a9775bc71e4eec27b_findings_ledger",
      "logical_name": "ledger",
      "repo_path": "docs/reviews/rfc-0014-operational-artifact-home/reruns/2026-05-06-redaction-rerun-2/RFC_0014_FINDINGS_LEDGER.md",
      "session_id": "sess_e3c9c6604f3a4135a12537d558dcf6b9"
    },
    {
      "artifact_id": "art_c2009be9a29d4db89b644c21466e24e3",
      "artifact_kind": "finding",
      "author": {
        "display_model": "Claude Opus",
        "lane_id": "claude",
        "line": "author: reviewer-claude-opus-001",
        "ordinal": 1,
        "role_id": "reviewer",
        "workflow_job_id": "review_claude"
      },
      "content_sha256": "20cd9f4bb116919f6eefcacda0ad66bd97bd836243390cbf8c140865462ea90a",
      "job_id": "job_run_cc00924e495a412a9775bc71e4eec27b_review_claude",
      "logical_name": "review",
      "repo_path": "docs/reviews/rfc-0014-operational-artifact-home/reruns/2026-05-06-redaction-rerun-2/RFC_0014_REVIEW_claude.md",
      "session_id": "sess_89a033bfa5604b87a382e5d12f7fbec7"
    },
    {
      "artifact_id": "art_19091c51b0604d52be7b16928761cde6",
      "artifact_kind": "finding",
      "author": {
        "display_model": "Codex GPT-5.5",
        "lane_id": "codex",
        "line": "author: reviewer-codex-gpt-5.5-001",
        "ordinal": 1,
        "role_id": "reviewer",
        "workflow_job_id": "review_codex"
      },
      "content_sha256": "3034d1a5d1ba5f6aa8b358d8f53a258a4c44722cbb38b7067f86b7c3ef9e17fd",
      "job_id": "job_run_cc00924e495a412a9775bc71e4eec27b_review_codex",
      "logical_name": "review",
      "repo_path": "docs/reviews/rfc-0014-operational-artifact-home/reruns/2026-05-06-redaction-rerun-2/RFC_0014_REVIEW_codex.md",
      "session_id": "sess_1d1a39f0ef8d466faf26b63e272eca97"
    },
    {
      "artifact_id": "art_8622f85d76724b26b5945cbe755bd69b",
      "artifact_kind": "finding",
      "author": {
        "display_model": "Gemini 3.1 Pro Preview",
        "lane_id": "gemini",
        "line": "author: reviewer-gemini-3.1-pro-preview-001",
        "ordinal": 1,
        "role_id": "reviewer",
        "workflow_job_id": "review_gemini"
      },
      "content_sha256": "87b0ad29e51e572f683da2198e98d347542b03990500c8387176ff6341e6717d",
      "job_id": "job_run_cc00924e495a412a9775bc71e4eec27b_review_gemini",
      "logical_name": "review",
      "repo_path": "docs/reviews/rfc-0014-operational-artifact-home/reruns/2026-05-06-redaction-rerun-2/RFC_0014_REVIEW_gemini.md",
      "session_id": "sess_7f2aca5aeaac461e9c96b4bf9a74577d"
    },
    {
      "artifact_id": "art_b555e219cde64dd1ba0de5e30a9e9773",
      "artifact_kind": "synthesis",
      "author": {
        "display_model": "Claude Opus",
        "lane_id": "claude",
        "line": "author: synthesizer-claude-opus-001",
        "ordinal": 1,
        "role_id": "synthesizer",
        "workflow_job_id": "synthesis"
      },
      "content_sha256": "3f5bf973967a40e6d4fd07f871183329204299e5038e84ba07340b565516542e",
      "job_id": "job_run_cc00924e495a412a9775bc71e4eec27b_synthesis",
      "logical_name": "synthesis",
      "repo_path": "docs/reviews/rfc-0014-operational-artifact-home/reruns/2026-05-06-redaction-rerun-2/RFC_0014_SYNTHESIS.md",
      "session_id": "sess_1678f205837e4780b1b91e21daa4863b"
    }
  ],
  "blocked_downstream_jobs": [],
  "blockers": [],
  "exported_at": "2026-05-06T19:12:51Z",
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
          "depends_on_job_id": "job_run_cc00924e495a412a9775bc71e4eec27b_synthesis",
          "latest_verdict": null,
          "required_verdicts": null,
          "state": "completed",
          "workflow_job_id": "synthesis"
        }
      ],
      "display_model": "Codex GPT-5.5",
      "fresh_session_required": true,
      "job_id": "job_run_cc00924e495a412a9775bc71e4eec27b_final_review",
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
          "depends_on_job_id": "job_run_cc00924e495a412a9775bc71e4eec27b_review_claude",
          "latest_verdict": "accept_with_findings",
          "required_verdicts": [
            "accept",
            "accept_with_findings"
          ],
          "state": "completed",
          "workflow_job_id": "review_claude"
        },
        {
          "depends_on_job_id": "job_run_cc00924e495a412a9775bc71e4eec27b_review_codex",
          "latest_verdict": "accept_with_findings",
          "required_verdicts": [
            "accept",
            "accept_with_findings"
          ],
          "state": "completed",
          "workflow_job_id": "review_codex"
        },
        {
          "depends_on_job_id": "job_run_cc00924e495a412a9775bc71e4eec27b_review_gemini",
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
      "job_id": "job_run_cc00924e495a412a9775bc71e4eec27b_findings_ledger",
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
      "job_id": "job_run_cc00924e495a412a9775bc71e4eec27b_review_claude",
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
      "job_id": "job_run_cc00924e495a412a9775bc71e4eec27b_review_codex",
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
      "job_id": "job_run_cc00924e495a412a9775bc71e4eec27b_review_gemini",
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
          "depends_on_job_id": "job_run_cc00924e495a412a9775bc71e4eec27b_findings_ledger",
          "latest_verdict": null,
          "required_verdicts": null,
          "state": "completed",
          "workflow_job_id": "findings_ledger"
        }
      ],
      "display_model": "Claude Opus",
      "fresh_session_required": true,
      "job_id": "job_run_cc00924e495a412a9775bc71e4eec27b_synthesis",
      "job_type": "synthesis",
      "lane": "claude",
      "max_attempts": 1,
      "role_id": "synthesizer",
      "state": "completed",
      "workflow_job_id": "synthesis"
    }
  ],
  "run": {
    "branch_name": "agent-runner/rfc-0014-validation",
    "run_id": "run_cc00924e495a412a9775bc71e4eec27b",
    "state": "completed"
  },
  "schema_version": "agent-runner.evidence.v1",
  "verdicts": [
    {
      "findings_artifact_id": "art_c2009be9a29d4db89b644c21466e24e3",
      "job_id": "job_run_cc00924e495a412a9775bc71e4eec27b_review_claude",
      "rationale": "<redacted-free-text>",
      "session_id": "sess_89a033bfa5604b87a382e5d12f7fbec7",
      "verdict": "accept_with_findings",
      "verdict_id": "verdict_001fddb51c184c26adac89012c8c0498"
    },
    {
      "findings_artifact_id": "art_8622f85d76724b26b5945cbe755bd69b",
      "job_id": "job_run_cc00924e495a412a9775bc71e4eec27b_review_gemini",
      "rationale": "<redacted-free-text>",
      "session_id": "sess_7f2aca5aeaac461e9c96b4bf9a74577d",
      "verdict": "accept_with_findings",
      "verdict_id": "verdict_1d962ed4badc4b73a306bd3cd920ba65"
    },
    {
      "findings_artifact_id": "art_19091c51b0604d52be7b16928761cde6",
      "job_id": "job_run_cc00924e495a412a9775bc71e4eec27b_review_codex",
      "rationale": "<redacted-free-text>",
      "session_id": "sess_1d1a39f0ef8d466faf26b63e272eca97",
      "verdict": "accept_with_findings",
      "verdict_id": "verdict_825dd5b0fd5f47359a88686ec5050b14"
    },
    {
      "findings_artifact_id": "art_896ac62245ee4fd0b2101b7b82884e2b",
      "job_id": "job_run_cc00924e495a412a9775bc71e4eec27b_final_review",
      "rationale": "<redacted-free-text>",
      "session_id": "sess_05dbd70d41774a3e8503e17ed76a5fd6",
      "verdict": "accept",
      "verdict_id": "verdict_8159a3c93ca8463b9675da148d8fc705"
    }
  ],
  "workflow": {
    "workflow_id": "rfc-0014-operational-artifact-home",
    "workflow_version": "2026-05-06+2026-05-06-redaction-rerun-2"
  }
}
```
