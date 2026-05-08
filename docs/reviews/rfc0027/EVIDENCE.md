# Striatum Evidence Export

Run ID: `run_ac31166f50b941efbe7abae2fee47b80`
Branch: `engram/rfc0027-interview-web-ui-review`
Run state: `completed`
Exported at: `2026-05-08T22:33:19Z`

Live SQLite state remains ignored under `.striatum/` and is not part of this export.

## Status Output

```json
{"blocked_downstream_jobs":[],"claimable_jobs":[],"human_checkpoints":[],"jobs":{"completed":6},"latest_non_accepting_review_verdicts":[],"next_actions":[],"open_blockers":[],"process_health":"<redacted-free-text>","runs":[{"branch_name":"engram/rfc0027-interview-web-ui-review","run_id":"run_ac31166f50b941efbe7abae2fee47b80","state":"completed"}]}
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
      "artifact_id": "art_6ba38b079eab4c339bcd8bda5cd92771",
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
      "content_sha256": "12704bd5478644fa645f99966477b49cd6f1cf35076562e408ea680611d6c1dd",
      "job_id": "job_run_ac31166f50b941efbe7abae2fee47b80_final_review",
      "logical_name": "review",
      "repo_path": "docs/reviews/rfc0027/RFC_0027_INTERVIEW_WEB_UI_FINAL_REVIEW.md",
      "session_id": "sess_34e48acba6a849f4a37571953ea64477"
    },
    {
      "artifact_id": "art_590d3a99a0eb466c858c030c27e04493",
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
      "content_sha256": "b429f609f795f1c99d87e91b2aa4df727d45e82007f6d95f74a92311f161c827",
      "job_id": "job_run_ac31166f50b941efbe7abae2fee47b80_findings_ledger",
      "logical_name": "ledger",
      "repo_path": "docs/reviews/rfc0027/RFC_0027_INTERVIEW_WEB_UI_FINDINGS_LEDGER.md",
      "session_id": "sess_616ab3ef1e054c0ead6e420aa9b779ff"
    },
    {
      "artifact_id": "art_9c9ccc1fc4024088a9190a468d26986c",
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
      "content_sha256": "60e01ef82716c235dd6d79fe6f5255d93e11c4f2f31246de5e0be628944e02ed",
      "job_id": "job_run_ac31166f50b941efbe7abae2fee47b80_review_claude",
      "logical_name": "review",
      "repo_path": "docs/reviews/rfc0027/RFC_0027_INTERVIEW_WEB_UI_REVIEW_claude.md",
      "session_id": "sess_1cdde3742b0f4e39b4e895da6ede59ef"
    },
    {
      "artifact_id": "art_191e1ec9512d414cb2243d855c9f878b",
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
      "content_sha256": "c0e10f804a47f34e0b6b1088a26411f8a216331dd8eeae66a200c98cb8d4cc98",
      "job_id": "job_run_ac31166f50b941efbe7abae2fee47b80_review_codex",
      "logical_name": "review",
      "repo_path": "docs/reviews/rfc0027/RFC_0027_INTERVIEW_WEB_UI_REVIEW_codex.md",
      "session_id": "sess_bb121f50b72e40bea3e69c54772117a8"
    },
    {
      "artifact_id": "art_dd795e4e06a44b52855a75353f0a233c",
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
      "content_sha256": "836200ee212ee179fe15e5d970123733cd543413dd7e4a96494041514f187d64",
      "job_id": "job_run_ac31166f50b941efbe7abae2fee47b80_review_gemini",
      "logical_name": "review",
      "repo_path": "docs/reviews/rfc0027/RFC_0027_INTERVIEW_WEB_UI_REVIEW_gemini.md",
      "session_id": "sess_1f1d3a31594a46fcba1536a68fc08b5b"
    },
    {
      "artifact_id": "art_22da775e2f7841cfaf3aced2cc15412a",
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
      "content_sha256": "17975fb29fd7645cb5399267cbcfc5da8f9c367b946b7a61e7455bb6f6d27ed2",
      "job_id": "job_run_ac31166f50b941efbe7abae2fee47b80_synthesis",
      "logical_name": "synthesis",
      "repo_path": "docs/reviews/rfc0027/RFC_0027_INTERVIEW_WEB_UI_SYNTHESIS.md",
      "session_id": "sess_f9ce7ac2dde848bfa7dff9a44d9ad451"
    }
  ],
  "blocked_downstream_jobs": [],
  "blockers": [],
  "exported_at": "2026-05-08T22:33:19Z",
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
          "depends_on_job_id": "job_run_ac31166f50b941efbe7abae2fee47b80_synthesis",
          "latest_verdict": null,
          "required_verdicts": null,
          "state": "completed",
          "workflow_job_id": "synthesis"
        }
      ],
      "display_model": "Codex GPT-5.5",
      "fresh_session_required": true,
      "job_id": "job_run_ac31166f50b941efbe7abae2fee47b80_final_review",
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
          "depends_on_job_id": "job_run_ac31166f50b941efbe7abae2fee47b80_review_claude",
          "latest_verdict": "accept_with_findings",
          "required_verdicts": [
            "accept",
            "accept_with_findings"
          ],
          "state": "completed",
          "workflow_job_id": "review_claude"
        },
        {
          "depends_on_job_id": "job_run_ac31166f50b941efbe7abae2fee47b80_review_codex",
          "latest_verdict": "accept_with_findings",
          "required_verdicts": [
            "accept",
            "accept_with_findings"
          ],
          "state": "completed",
          "workflow_job_id": "review_codex"
        },
        {
          "depends_on_job_id": "job_run_ac31166f50b941efbe7abae2fee47b80_review_gemini",
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
      "job_id": "job_run_ac31166f50b941efbe7abae2fee47b80_findings_ledger",
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
      "job_id": "job_run_ac31166f50b941efbe7abae2fee47b80_review_claude",
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
      "job_id": "job_run_ac31166f50b941efbe7abae2fee47b80_review_codex",
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
      "job_id": "job_run_ac31166f50b941efbe7abae2fee47b80_review_gemini",
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
          "depends_on_job_id": "job_run_ac31166f50b941efbe7abae2fee47b80_findings_ledger",
          "latest_verdict": null,
          "required_verdicts": null,
          "state": "completed",
          "workflow_job_id": "findings_ledger"
        }
      ],
      "display_model": "Claude Opus",
      "fresh_session_required": true,
      "job_id": "job_run_ac31166f50b941efbe7abae2fee47b80_synthesis",
      "job_type": "synthesis",
      "lane": "claude",
      "max_attempts": 1,
      "role_id": "synthesizer",
      "state": "completed",
      "workflow_job_id": "synthesis"
    }
  ],
  "run": {
    "branch_name": "engram/rfc0027-interview-web-ui-review",
    "run_id": "run_ac31166f50b941efbe7abae2fee47b80",
    "state": "completed"
  },
  "schema_version": "striatum.evidence.v1",
  "sessions": [
    {
      "close_reason": "run_completed",
      "closed_at": "2026-05-08T22:33:19Z",
      "lane_id": "claude",
      "non_fresh_reason": null,
      "ordinal": 1,
      "registered_at": "2026-05-08T22:12:00Z",
      "role_id": "reviewer",
      "session_id": "sess_1cdde3742b0f4e39b4e895da6ede59ef",
      "slug": "reviewer-claude-1",
      "state": "closed"
    },
    {
      "close_reason": "run_completed",
      "closed_at": "2026-05-08T22:33:19Z",
      "lane_id": "gemini",
      "non_fresh_reason": null,
      "ordinal": 1,
      "registered_at": "2026-05-08T22:12:00Z",
      "role_id": "reviewer",
      "session_id": "sess_1f1d3a31594a46fcba1536a68fc08b5b",
      "slug": "reviewer-gemini-1",
      "state": "closed"
    },
    {
      "close_reason": "run_completed",
      "closed_at": "2026-05-08T22:33:19Z",
      "lane_id": "codex",
      "non_fresh_reason": null,
      "ordinal": 1,
      "registered_at": "2026-05-08T22:12:00Z",
      "role_id": "ledger",
      "session_id": "sess_616ab3ef1e054c0ead6e420aa9b779ff",
      "slug": "ledger-codex-1",
      "state": "closed"
    },
    {
      "close_reason": "run_completed",
      "closed_at": "2026-05-08T22:33:19Z",
      "lane_id": "codex",
      "non_fresh_reason": null,
      "ordinal": 1,
      "registered_at": "2026-05-08T22:12:00Z",
      "role_id": "reviewer",
      "session_id": "sess_bb121f50b72e40bea3e69c54772117a8",
      "slug": "reviewer-codex-1",
      "state": "closed"
    },
    {
      "close_reason": "run_completed",
      "closed_at": "2026-05-08T22:33:19Z",
      "lane_id": "codex",
      "non_fresh_reason": null,
      "ordinal": 2,
      "registered_at": "2026-05-08T22:12:01Z",
      "role_id": "reviewer",
      "session_id": "sess_34e48acba6a849f4a37571953ea64477",
      "slug": "reviewer-codex-2",
      "state": "closed"
    },
    {
      "close_reason": "run_completed",
      "closed_at": "2026-05-08T22:33:19Z",
      "lane_id": "claude",
      "non_fresh_reason": null,
      "ordinal": 1,
      "registered_at": "2026-05-08T22:12:01Z",
      "role_id": "synthesizer",
      "session_id": "sess_f9ce7ac2dde848bfa7dff9a44d9ad451",
      "slug": "synthesizer-claude-1",
      "state": "closed"
    }
  ],
  "verdicts": [
    {
      "findings_artifact_id": "art_9c9ccc1fc4024088a9190a468d26986c",
      "job_id": "job_run_ac31166f50b941efbe7abae2fee47b80_review_claude",
      "rationale": null,
      "session_id": "sess_1cdde3742b0f4e39b4e895da6ede59ef",
      "verdict": "accept_with_findings",
      "verdict_id": "verdict_b3c0c7434c5a470bbe9fb37819d921b7"
    },
    {
      "findings_artifact_id": "art_191e1ec9512d414cb2243d855c9f878b",
      "job_id": "job_run_ac31166f50b941efbe7abae2fee47b80_review_codex",
      "rationale": null,
      "session_id": "sess_bb121f50b72e40bea3e69c54772117a8",
      "verdict": "accept_with_findings",
      "verdict_id": "verdict_15abe49b2d9f4fe0a7354282ef20cc49"
    },
    {
      "findings_artifact_id": "art_dd795e4e06a44b52855a75353f0a233c",
      "job_id": "job_run_ac31166f50b941efbe7abae2fee47b80_review_gemini",
      "rationale": null,
      "session_id": "sess_1f1d3a31594a46fcba1536a68fc08b5b",
      "verdict": "accept_with_findings",
      "verdict_id": "verdict_271c010db63641bbb0ad3f2673c50aee"
    },
    {
      "findings_artifact_id": "art_6ba38b079eab4c339bcd8bda5cd92771",
      "job_id": "job_run_ac31166f50b941efbe7abae2fee47b80_final_review",
      "rationale": null,
      "session_id": "sess_34e48acba6a849f4a37571953ea64477",
      "verdict": "accept_with_findings",
      "verdict_id": "verdict_2dcf2d6db1ac461aa2464aaeaeb5692a"
    }
  ],
  "workflow": {
    "workflow_id": "rfc-0027-interview-web-ui-review",
    "workflow_version": "2026-05-08+initial"
  }
}
```
