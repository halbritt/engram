# Striatum Evidence Export

Run ID: `run_7d822bbf1cac4692bee644939984d6bf`
Branch: `engram/rfc0021-gold-set-implementation`
Run state: `completed`
Exported at: `2026-05-08T18:53:41Z`

Live SQLite state remains ignored under `.striatum/` and is not part of this export.

## Status Output

```json
{"blocked_downstream_jobs":[],"claimable_jobs":[],"human_checkpoints":[],"jobs":{"completed":3},"latest_non_accepting_review_verdicts":[],"next_actions":[],"open_blockers":[],"process_health":"<redacted-free-text>","runs":[{"branch_name":"engram/rfc0021-gold-set-implementation","run_id":"run_7d822bbf1cac4692bee644939984d6bf","state":"completed"}]}
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
      "artifact_id": "art_ed62bdc09674466e9ed49153abd580f3",
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
      "content_sha256": "ca41094d4e454a8fd978fa2b5ea5b483de323bc2bdd6b453791a00a860ec7fd4",
      "job_id": "job_run_7d822bbf1cac4692bee644939984d6bf_final_review",
      "logical_name": "final_review",
      "repo_path": "docs/reviews/rfc0021-gold-set-implementation/FINAL_REVIEW.md",
      "session_id": "sess_11f2404435484a36bcb94d496a68af19"
    },
    {
      "artifact_id": "art_fb8802a8cd41411880ce0b21d103b033",
      "artifact_kind": "handoff",
      "author": {
        "actual_author_line": "author: author-codex-gpt-5.5-001",
        "display_model": "Codex GPT-5.5",
        "lane_id": "codex",
        "line": "author: author-codex-gpt-5.5-001",
        "ordinal": 1,
        "role_id": "author",
        "workflow_job_id": "implement_gold_set"
      },
      "content_sha256": "ebdf36e8712b06145fb64f974f415fbe3d4f8f596737fe907d1c5ee1843b999c",
      "job_id": "job_run_7d822bbf1cac4692bee644939984d6bf_implement_gold_set",
      "logical_name": "implementation_handoff",
      "repo_path": "docs/reviews/rfc0021-gold-set-implementation/IMPLEMENTATION_HANDOFF.md",
      "session_id": "sess_780e29e90a90488fbeec9d5abecfbdcd"
    },
    {
      "artifact_id": "art_f5debcee90f142cc8f3da4643fee62d6",
      "artifact_kind": "finding",
      "author": {
        "actual_author_line": "author: reviewer-codex-gpt-5.5-001",
        "display_model": "Codex GPT-5.5",
        "lane_id": "codex",
        "line": "author: reviewer-codex-gpt-5.5-001",
        "ordinal": 1,
        "role_id": "reviewer",
        "workflow_job_id": "verify_gold_set"
      },
      "content_sha256": "e3c82ae1945fc0d3eece4ed2d225c51c0dbed518354f7f0a7bc588dcfb6e71a6",
      "job_id": "job_run_7d822bbf1cac4692bee644939984d6bf_verify_gold_set",
      "logical_name": "verification_report",
      "repo_path": "docs/reviews/rfc0021-gold-set-implementation/VERIFICATION_REPORT.md",
      "session_id": "sess_ed9360f58c3c433b81ef44bedb1c0ad1"
    }
  ],
  "blocked_downstream_jobs": [],
  "blockers": [],
  "exported_at": "2026-05-08T18:53:41Z",
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
          "depends_on_job_id": "job_run_7d822bbf1cac4692bee644939984d6bf_verify_gold_set",
          "latest_verdict": "accept_with_findings",
          "required_verdicts": [
            "accept",
            "accept_with_findings"
          ],
          "state": "completed",
          "workflow_job_id": "verify_gold_set"
        }
      ],
      "display_model": "Codex GPT-5.5",
      "fresh_session_required": true,
      "job_id": "job_run_7d822bbf1cac4692bee644939984d6bf_final_review",
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
        "workflow_job_id": "implement_gold_set"
      },
      "dependencies": [],
      "display_model": "Codex GPT-5.5",
      "fresh_session_required": false,
      "job_id": "job_run_7d822bbf1cac4692bee644939984d6bf_implement_gold_set",
      "job_type": "draft",
      "lane": "codex",
      "max_attempts": 1,
      "role_id": "author",
      "state": "completed",
      "workflow_job_id": "implement_gold_set"
    },
    {
      "attempt": 1,
      "author": {
        "display_model": "Codex GPT-5.5",
        "lane_id": "codex",
        "line": null,
        "ordinal": null,
        "role_id": "reviewer",
        "workflow_job_id": "verify_gold_set"
      },
      "dependencies": [
        {
          "depends_on_job_id": "job_run_7d822bbf1cac4692bee644939984d6bf_implement_gold_set",
          "latest_verdict": null,
          "required_verdicts": null,
          "state": "completed",
          "workflow_job_id": "implement_gold_set"
        }
      ],
      "display_model": "Codex GPT-5.5",
      "fresh_session_required": true,
      "job_id": "job_run_7d822bbf1cac4692bee644939984d6bf_verify_gold_set",
      "job_type": "review",
      "lane": "codex",
      "max_attempts": 1,
      "role_id": "reviewer",
      "state": "completed",
      "workflow_job_id": "verify_gold_set"
    }
  ],
  "run": {
    "branch_name": "engram/rfc0021-gold-set-implementation",
    "run_id": "run_7d822bbf1cac4692bee644939984d6bf",
    "state": "completed"
  },
  "schema_version": "striatum.evidence.v1",
  "sessions": [
    {
      "close_reason": "run_completed",
      "closed_at": "2026-05-08T18:53:35Z",
      "lane_id": "codex",
      "non_fresh_reason": null,
      "ordinal": 1,
      "registered_at": "2026-05-08T18:22:21Z",
      "role_id": "author",
      "session_id": "sess_780e29e90a90488fbeec9d5abecfbdcd",
      "slug": "author-codex-1",
      "state": "closed"
    },
    {
      "close_reason": "run_completed",
      "closed_at": "2026-05-08T18:53:35Z",
      "lane_id": "codex",
      "non_fresh_reason": "single-process autonomous drive; verifier and author run in the same orchestrator session",
      "ordinal": 1,
      "registered_at": "2026-05-08T18:44:35Z",
      "role_id": "reviewer",
      "session_id": "sess_ed9360f58c3c433b81ef44bedb1c0ad1",
      "slug": "reviewer-codex-1",
      "state": "closed"
    },
    {
      "close_reason": "run_completed",
      "closed_at": "2026-05-08T18:53:35Z",
      "lane_id": "codex",
      "non_fresh_reason": "single-process autonomous drive; final reviewer in same orchestrator session",
      "ordinal": 2,
      "registered_at": "2026-05-08T18:49:16Z",
      "role_id": "reviewer",
      "session_id": "sess_11f2404435484a36bcb94d496a68af19",
      "slug": "reviewer-codex-2",
      "state": "closed"
    }
  ],
  "verdicts": [
    {
      "findings_artifact_id": "art_f5debcee90f142cc8f3da4643fee62d6",
      "job_id": "job_run_7d822bbf1cac4692bee644939984d6bf_verify_gold_set",
      "rationale": null,
      "session_id": "sess_ed9360f58c3c433b81ef44bedb1c0ad1",
      "verdict": "accept_with_findings",
      "verdict_id": "verdict_16d14eca1b2341a5b164950982598279"
    },
    {
      "findings_artifact_id": "art_ed62bdc09674466e9ed49153abd580f3",
      "job_id": "job_run_7d822bbf1cac4692bee644939984d6bf_final_review",
      "rationale": null,
      "session_id": "sess_11f2404435484a36bcb94d496a68af19",
      "verdict": "accept_with_findings",
      "verdict_id": "verdict_185d8c65a77e4cbcbccd7040b9a7698b"
    }
  ],
  "workflow": {
    "workflow_id": "rfc-0021-gold-set-implementation",
    "workflow_version": "2026-05-08+accepted-rfc"
  }
}
```
