# Striatum Evidence Export

Run ID: `run_66ba248f6e4f47e49c130bca866e383f`
Branch: `engram/rfc0028-predicate-intent-implementation`
Run state: `completed`
Exported at: `2026-05-09T02:49:07Z`

Live SQLite state remains ignored under `.striatum/` and is not part of this export.

## Status Output

```json
{"blocked_downstream_jobs":[],"claimable_jobs":[],"human_checkpoints":[],"jobs":{"completed":8},"latest_non_accepting_review_verdicts":[],"next_actions":["inspect_blocker","export_run_evidence"],"open_blockers":[{"blocker_id":"blk_b17b8f9d745845e7871c3c58e627016d","blocker_kind":"process_review_verdict_missing","description":"<redacted-free-text>","job_id":"job_run_66ba248f6e4f47e49c130bca866e383f_review_codex","job_state":"completed","run_id":"run_66ba248f6e4f47e49c130bca866e383f","session_id":"sess_02fa86a7d9624560bd207396652c7d94","severity":"blocked","state":"open","workflow_job_id":"review_codex"},{"blocker_id":"blk_21f692125f53493f9c378a3865e51be8","blocker_kind":"process_review_verdict_missing","description":"<redacted-free-text>","job_id":"job_run_66ba248f6e4f47e49c130bca866e383f_review_gemini","job_state":"completed","run_id":"run_66ba248f6e4f47e49c130bca866e383f","session_id":"sess_bdd1084bc12c43929b096e063832875a","severity":"blocked","state":"open","workflow_job_id":"review_gemini"},{"blocker_id":"blk_857ee9425c734fcd8eeccb4a6b09ebfa","blocker_kind":"process_review_verdict_missing","description":"<redacted-free-text>","job_id":"job_run_66ba248f6e4f47e49c130bca866e383f_review_claude","job_state":"completed","run_id":"run_66ba248f6e4f47e49c130bca866e383f","session_id":"sess_02ee0110d600447daec27169fed2a60b","severity":"blocked","state":"open","workflow_job_id":"review_claude"}],"process_health":"<redacted-free-text>","runs":[{"branch_name":"engram/rfc0028-predicate-intent-implementation","run_id":"run_66ba248f6e4f47e49c130bca866e383f","state":"completed"}]}
```

## Doctor Output

```json
{"ok":false,"problems":["open blocker on terminal run: blk_b17b8f9d745845e7871c3c58e627016d","open blocker on terminal run: blk_21f692125f53493f9c378a3865e51be8","open blocker on terminal run: blk_857ee9425c734fcd8eeccb4a6b09ebfa","skill bundle outdated for profile 'claude_code': manifest_version='1.7.0' running_version='1.8.0' templates_changed=[] \u2014 run `striatum --repo /home/halbritt/git/engram skills install --profile claude_code`","skill bundle outdated for profile 'codex': manifest_version='1.7.0' running_version='1.8.0' templates_changed=[] \u2014 run `striatum --repo /home/halbritt/git/engram skills install --profile codex`"],"schema_version":"1"}
```

## Snapshot

```json
{
  "artifacts": [
    {
      "artifact_id": "art_bb367b4d1e3d4f4d8d73bfbcb444c726",
      "artifact_kind": "finding",
      "author": {
        "actual_author_line": "author: reviewer-codex-gpt-5.5-003",
        "display_model": "Codex GPT-5.5",
        "lane_id": "codex",
        "line": "author: reviewer-codex-gpt-5.5-003",
        "ordinal": 3,
        "role_id": "reviewer",
        "workflow_job_id": "final_review"
      },
      "content_sha256": "8aecbb7630fe1dd9f4981861d4b84f1ab7c99d35851bcd1714c71ee8408f8203",
      "job_id": "job_run_66ba248f6e4f47e49c130bca866e383f_final_review",
      "logical_name": "final_review",
      "repo_path": "docs/reviews/rfc0028-predicate-intent-implementation/FINAL_REVIEW.md",
      "session_id": "sess_2b8c4e9a15f04d238fb6215bb753ca32"
    },
    {
      "artifact_id": "art_e51a48e186744e8f8611097f84aadc5c",
      "artifact_kind": "findings_ledger",
      "author": {
        "actual_author_line": "author: ledger-codex-gpt-5.5-002",
        "display_model": "Codex GPT-5.5",
        "lane_id": "codex",
        "line": "author: ledger-codex-gpt-5.5-002",
        "ordinal": 2,
        "role_id": "ledger",
        "workflow_job_id": "findings_ledger"
      },
      "content_sha256": "16393b80cbb4469ae9c4eef9a7a05e4c58185dbe100a1bca0e3acf710e856152",
      "job_id": "job_run_66ba248f6e4f47e49c130bca866e383f_findings_ledger",
      "logical_name": "ledger",
      "repo_path": "docs/reviews/rfc0028-predicate-intent-implementation/FINDINGS_LEDGER.md",
      "session_id": "sess_206d719acbed454ca0a8920a6a062ec5"
    },
    {
      "artifact_id": "art_3f654b9cd50b4b959ea430a7bb079b82",
      "artifact_kind": "handoff",
      "author": {
        "actual_author_line": "author: author-codex-gpt-5.5-001",
        "display_model": "Codex GPT-5.5",
        "lane_id": "codex",
        "line": "author: author-codex-gpt-5.5-001",
        "ordinal": 1,
        "role_id": "author",
        "workflow_job_id": "implement_predicate_intent"
      },
      "content_sha256": "d781165d1e71f62ca89f827890f1f5c887441a0b44c54b107e402d3ca9d333a4",
      "job_id": "job_run_66ba248f6e4f47e49c130bca866e383f_implement_predicate_intent",
      "logical_name": "implementation_handoff",
      "repo_path": "docs/reviews/rfc0028-predicate-intent-implementation/IMPLEMENTATION_HANDOFF.md",
      "session_id": "sess_a125f3b57bab4d7aac9b0521d699cf0f"
    },
    {
      "artifact_id": "art_705b125b043f4f4aa226e96f059a7a97",
      "artifact_kind": "finding",
      "author": {
        "actual_author_line": "author: reviewer-claude-opus-002",
        "display_model": "Claude Opus",
        "lane_id": "claude",
        "line": "author: reviewer-claude-opus-002",
        "ordinal": 2,
        "role_id": "reviewer",
        "workflow_job_id": "review_claude"
      },
      "content_sha256": "16ea1a8e9995e3a10ce42276869633897bf5afc18523368c48b99d89d40b16d2",
      "job_id": "job_run_66ba248f6e4f47e49c130bca866e383f_review_claude",
      "logical_name": "review",
      "repo_path": "docs/reviews/rfc0028-predicate-intent-implementation/REVIEW_claude.md",
      "session_id": "sess_6bbaab8b765f43018fb90e5c50065d5e"
    },
    {
      "artifact_id": "art_9697291d435049ad8fda347d51dc6a80",
      "artifact_kind": "finding",
      "author": {
        "actual_author_line": "author: reviewer-codex-gpt-5.5-002",
        "display_model": "Codex GPT-5.5",
        "lane_id": "codex",
        "line": "author: reviewer-codex-gpt-5.5-002",
        "ordinal": 2,
        "role_id": "reviewer",
        "workflow_job_id": "review_codex"
      },
      "content_sha256": "b6ba62a7e405093b3e052d1d78fd9ae711e2a8cd8c9391b336f46fc40408beea",
      "job_id": "job_run_66ba248f6e4f47e49c130bca866e383f_review_codex",
      "logical_name": "review",
      "repo_path": "docs/reviews/rfc0028-predicate-intent-implementation/REVIEW_codex.md",
      "session_id": "sess_b0a9650be38c415b991cea35064b5bd6"
    },
    {
      "artifact_id": "art_ee0fae60864f41f382d5363e658e5d2e",
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
      "content_sha256": "a4979ef066fcd3ba3c383f096628079479776e8fdce1407f3287bbb9499480d5",
      "job_id": "job_run_66ba248f6e4f47e49c130bca866e383f_review_gemini",
      "logical_name": "review",
      "repo_path": "docs/reviews/rfc0028-predicate-intent-implementation/REVIEW_gemini.md",
      "session_id": "sess_bdd1084bc12c43929b096e063832875a"
    },
    {
      "artifact_id": "art_8d602d71ac0d4db0bcd3c13d6d40ade9",
      "artifact_kind": "finding",
      "author": {
        "actual_author_line": "author: reviewer-gemini-3.1-pro-preview-002",
        "display_model": "Gemini 3.1 Pro Preview",
        "lane_id": "gemini",
        "line": "author: reviewer-gemini-3.1-pro-preview-002",
        "ordinal": 2,
        "role_id": "reviewer",
        "workflow_job_id": "review_gemini"
      },
      "content_sha256": "dc9ea5baa0fba1435171b2acb1865e2606b70fb9ef35c87cb47148f48efffe0a",
      "job_id": "job_run_66ba248f6e4f47e49c130bca866e383f_review_gemini",
      "logical_name": "review_recovered",
      "repo_path": "docs/reviews/rfc0028-predicate-intent-implementation/REVIEW_gemini.md",
      "session_id": "sess_80d5db3ff5b8444e8c705a2028d73986"
    },
    {
      "artifact_id": "art_5e9da813148443aa9deed03148299ede",
      "artifact_kind": "handoff",
      "author": {
        "actual_author_line": "author: author-codex-gpt-5.5-002",
        "display_model": "Codex GPT-5.5",
        "lane_id": "codex",
        "line": "author: author-codex-gpt-5.5-002",
        "ordinal": 2,
        "role_id": "author",
        "workflow_job_id": "apply_findings"
      },
      "content_sha256": "ebf5b3b8967158bc2bee9614bb33cc0f5a180c25778c2287e2dffe0fe1520fbe",
      "job_id": "job_run_66ba248f6e4f47e49c130bca866e383f_apply_findings",
      "logical_name": "revision_handoff",
      "repo_path": "docs/reviews/rfc0028-predicate-intent-implementation/REVISION_HANDOFF.md",
      "session_id": "sess_03fc7f4b13dc4731998b46bddc43742c"
    },
    {
      "artifact_id": "art_aab1d26c9f084417a59b3a7026578494",
      "artifact_kind": "synthesis",
      "author": {
        "actual_author_line": "author: synthesizer-codex-gpt-5.5-001",
        "display_model": "Codex GPT-5.5",
        "lane_id": "codex",
        "line": "author: synthesizer-codex-gpt-5.5-001",
        "ordinal": 1,
        "role_id": "synthesizer",
        "workflow_job_id": "revision_synthesis"
      },
      "content_sha256": "efc80b47b7edaa9391215008cd6b31ada19f7da51b9f4d37a2b6b37826912a40",
      "job_id": "job_run_66ba248f6e4f47e49c130bca866e383f_revision_synthesis",
      "logical_name": "revision_synthesis",
      "repo_path": "docs/reviews/rfc0028-predicate-intent-implementation/REVISION_SYNTHESIS.md",
      "session_id": "sess_449c43b8c25a4ee081c022f2c247b184"
    }
  ],
  "blocked_downstream_jobs": [],
  "blockers": [
    {
      "blocker_id": "blk_b17b8f9d745845e7871c3c58e627016d",
      "blocker_kind": "process_review_verdict_missing",
      "description": "<redacted-free-text>",
      "job_id": "job_run_66ba248f6e4f47e49c130bca866e383f_review_codex",
      "session_id": "sess_02fa86a7d9624560bd207396652c7d94",
      "severity": "blocked",
      "state": "open"
    },
    {
      "blocker_id": "blk_21f692125f53493f9c378a3865e51be8",
      "blocker_kind": "process_review_verdict_missing",
      "description": "<redacted-free-text>",
      "job_id": "job_run_66ba248f6e4f47e49c130bca866e383f_review_gemini",
      "session_id": "sess_bdd1084bc12c43929b096e063832875a",
      "severity": "blocked",
      "state": "open"
    },
    {
      "blocker_id": "blk_857ee9425c734fcd8eeccb4a6b09ebfa",
      "blocker_kind": "process_review_verdict_missing",
      "description": "<redacted-free-text>",
      "job_id": "job_run_66ba248f6e4f47e49c130bca866e383f_review_claude",
      "session_id": "sess_02ee0110d600447daec27169fed2a60b",
      "severity": "blocked",
      "state": "open"
    }
  ],
  "exported_at": "2026-05-09T02:49:07Z",
  "jobs": [
    {
      "attempt": 1,
      "author": {
        "display_model": "Codex GPT-5.5",
        "lane_id": "codex",
        "line": null,
        "ordinal": null,
        "role_id": "author",
        "workflow_job_id": "apply_findings"
      },
      "dependencies": [
        {
          "depends_on_job_id": "job_run_66ba248f6e4f47e49c130bca866e383f_revision_synthesis",
          "latest_verdict": null,
          "required_verdicts": null,
          "state": "completed",
          "workflow_job_id": "revision_synthesis"
        }
      ],
      "display_model": "Codex GPT-5.5",
      "fresh_session_required": true,
      "job_id": "job_run_66ba248f6e4f47e49c130bca866e383f_apply_findings",
      "job_type": "draft",
      "lane": "codex",
      "max_attempts": 1,
      "role_id": "author",
      "state": "completed",
      "workflow_job_id": "apply_findings"
    },
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
          "depends_on_job_id": "job_run_66ba248f6e4f47e49c130bca866e383f_apply_findings",
          "latest_verdict": null,
          "required_verdicts": null,
          "state": "completed",
          "workflow_job_id": "apply_findings"
        }
      ],
      "display_model": "Codex GPT-5.5",
      "fresh_session_required": true,
      "job_id": "job_run_66ba248f6e4f47e49c130bca866e383f_final_review",
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
          "depends_on_job_id": "job_run_66ba248f6e4f47e49c130bca866e383f_review_claude",
          "latest_verdict": "accept_with_findings",
          "required_verdicts": [
            "accept",
            "accept_with_findings"
          ],
          "state": "completed",
          "workflow_job_id": "review_claude"
        },
        {
          "depends_on_job_id": "job_run_66ba248f6e4f47e49c130bca866e383f_review_codex",
          "latest_verdict": "accept_with_findings",
          "required_verdicts": [
            "accept",
            "accept_with_findings"
          ],
          "state": "completed",
          "workflow_job_id": "review_codex"
        },
        {
          "depends_on_job_id": "job_run_66ba248f6e4f47e49c130bca866e383f_review_gemini",
          "latest_verdict": "accept",
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
      "job_id": "job_run_66ba248f6e4f47e49c130bca866e383f_findings_ledger",
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
        "display_model": "Codex GPT-5.5",
        "lane_id": "codex",
        "line": null,
        "ordinal": null,
        "role_id": "author",
        "workflow_job_id": "implement_predicate_intent"
      },
      "dependencies": [],
      "display_model": "Codex GPT-5.5",
      "fresh_session_required": false,
      "job_id": "job_run_66ba248f6e4f47e49c130bca866e383f_implement_predicate_intent",
      "job_type": "draft",
      "lane": "codex",
      "max_attempts": 1,
      "role_id": "author",
      "state": "completed",
      "workflow_job_id": "implement_predicate_intent"
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
      "dependencies": [
        {
          "depends_on_job_id": "job_run_66ba248f6e4f47e49c130bca866e383f_implement_predicate_intent",
          "latest_verdict": null,
          "required_verdicts": null,
          "state": "completed",
          "workflow_job_id": "implement_predicate_intent"
        }
      ],
      "display_model": "Claude Opus",
      "fresh_session_required": true,
      "job_id": "job_run_66ba248f6e4f47e49c130bca866e383f_review_claude",
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
      "dependencies": [
        {
          "depends_on_job_id": "job_run_66ba248f6e4f47e49c130bca866e383f_implement_predicate_intent",
          "latest_verdict": null,
          "required_verdicts": null,
          "state": "completed",
          "workflow_job_id": "implement_predicate_intent"
        }
      ],
      "display_model": "Codex GPT-5.5",
      "fresh_session_required": true,
      "job_id": "job_run_66ba248f6e4f47e49c130bca866e383f_review_codex",
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
      "dependencies": [
        {
          "depends_on_job_id": "job_run_66ba248f6e4f47e49c130bca866e383f_implement_predicate_intent",
          "latest_verdict": null,
          "required_verdicts": null,
          "state": "completed",
          "workflow_job_id": "implement_predicate_intent"
        }
      ],
      "display_model": "Gemini 3.1 Pro Preview",
      "fresh_session_required": true,
      "job_id": "job_run_66ba248f6e4f47e49c130bca866e383f_review_gemini",
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
        "display_model": "Codex GPT-5.5",
        "lane_id": "codex",
        "line": null,
        "ordinal": null,
        "role_id": "synthesizer",
        "workflow_job_id": "revision_synthesis"
      },
      "dependencies": [
        {
          "depends_on_job_id": "job_run_66ba248f6e4f47e49c130bca866e383f_findings_ledger",
          "latest_verdict": null,
          "required_verdicts": null,
          "state": "completed",
          "workflow_job_id": "findings_ledger"
        }
      ],
      "display_model": "Codex GPT-5.5",
      "fresh_session_required": true,
      "job_id": "job_run_66ba248f6e4f47e49c130bca866e383f_revision_synthesis",
      "job_type": "synthesis",
      "lane": "codex",
      "max_attempts": 1,
      "role_id": "synthesizer",
      "state": "completed",
      "workflow_job_id": "revision_synthesis"
    }
  ],
  "run": {
    "branch_name": "engram/rfc0028-predicate-intent-implementation",
    "run_id": "run_66ba248f6e4f47e49c130bca866e383f",
    "state": "completed"
  },
  "schema_version": "striatum.evidence.v1",
  "sessions": [
    {
      "close_reason": "implementation job completed and handoff published",
      "closed_at": "2026-05-09T02:27:03Z",
      "lane_id": "codex",
      "non_fresh_reason": null,
      "ordinal": 1,
      "registered_at": "2026-05-09T02:10:57Z",
      "role_id": "author",
      "session_id": "sess_a125f3b57bab4d7aac9b0521d699cf0f",
      "slug": "author-codex-1",
      "state": "closed"
    },
    {
      "close_reason": "requeued blocked adapter review for manual artifact submission",
      "closed_at": "2026-05-09T02:44:30Z",
      "lane_id": "claude",
      "non_fresh_reason": null,
      "ordinal": 1,
      "registered_at": "2026-05-09T02:27:09Z",
      "role_id": "reviewer",
      "session_id": "sess_02ee0110d600447daec27169fed2a60b",
      "slug": "reviewer-claude-1",
      "state": "closed"
    },
    {
      "close_reason": "adapter job was requeued after manual review artifact recovery",
      "closed_at": "2026-05-09T02:40:12Z",
      "lane_id": "codex",
      "non_fresh_reason": null,
      "ordinal": 1,
      "registered_at": "2026-05-09T02:27:09Z",
      "role_id": "reviewer",
      "session_id": "sess_02fa86a7d9624560bd207396652c7d94",
      "slug": "reviewer-codex-1",
      "state": "closed"
    },
    {
      "close_reason": "adapter job was requeued after manual review artifact recovery",
      "closed_at": "2026-05-09T02:35:39Z",
      "lane_id": "gemini",
      "non_fresh_reason": null,
      "ordinal": 1,
      "registered_at": "2026-05-09T02:27:09Z",
      "role_id": "reviewer",
      "session_id": "sess_bdd1084bc12c43929b096e063832875a",
      "slug": "reviewer-gemini-1",
      "state": "closed"
    },
    {
      "close_reason": "review lane complete",
      "closed_at": "2026-05-09T02:48:08Z",
      "lane_id": "gemini",
      "non_fresh_reason": null,
      "ordinal": 2,
      "registered_at": "2026-05-09T02:35:45Z",
      "role_id": "reviewer",
      "session_id": "sess_80d5db3ff5b8444e8c705a2028d73986",
      "slug": "reviewer-gemini-2",
      "state": "closed"
    },
    {
      "close_reason": "review lane complete",
      "closed_at": "2026-05-09T02:48:08Z",
      "lane_id": "codex",
      "non_fresh_reason": null,
      "ordinal": 2,
      "registered_at": "2026-05-09T02:40:16Z",
      "role_id": "reviewer",
      "session_id": "sess_b0a9650be38c415b991cea35064b5bd6",
      "slug": "reviewer-codex-2",
      "state": "closed"
    },
    {
      "close_reason": "review lane complete",
      "closed_at": "2026-05-09T02:48:08Z",
      "lane_id": "claude",
      "non_fresh_reason": null,
      "ordinal": 2,
      "registered_at": "2026-05-09T02:44:33Z",
      "role_id": "reviewer",
      "session_id": "sess_6bbaab8b765f43018fb90e5c50065d5e",
      "slug": "reviewer-claude-2",
      "state": "closed"
    },
    {
      "close_reason": "unused duplicate ledger session",
      "closed_at": "2026-05-09T02:48:08Z",
      "lane_id": "codex",
      "non_fresh_reason": null,
      "ordinal": 1,
      "registered_at": "2026-05-09T02:44:54Z",
      "role_id": "ledger",
      "session_id": "sess_c11d13f6ab854164a4b1cf62ec05f6da",
      "slug": "ledger-codex-1",
      "state": "closed"
    },
    {
      "close_reason": "ledger job complete",
      "closed_at": "2026-05-09T02:48:08Z",
      "lane_id": "codex",
      "non_fresh_reason": null,
      "ordinal": 2,
      "registered_at": "2026-05-09T02:44:55Z",
      "role_id": "ledger",
      "session_id": "sess_206d719acbed454ca0a8920a6a062ec5",
      "slug": "ledger-codex-2",
      "state": "closed"
    },
    {
      "close_reason": "synthesis job complete",
      "closed_at": "2026-05-09T02:48:08Z",
      "lane_id": "codex",
      "non_fresh_reason": null,
      "ordinal": 1,
      "registered_at": "2026-05-09T02:45:56Z",
      "role_id": "synthesizer",
      "session_id": "sess_449c43b8c25a4ee081c022f2c247b184",
      "slug": "synthesizer-codex-1",
      "state": "closed"
    },
    {
      "close_reason": "apply findings job complete",
      "closed_at": "2026-05-09T02:48:09Z",
      "lane_id": "codex",
      "non_fresh_reason": null,
      "ordinal": 2,
      "registered_at": "2026-05-09T02:46:39Z",
      "role_id": "author",
      "session_id": "sess_03fc7f4b13dc4731998b46bddc43742c",
      "slug": "author-codex-2",
      "state": "closed"
    },
    {
      "close_reason": "run_completed",
      "closed_at": "2026-05-09T02:48:47Z",
      "lane_id": "codex",
      "non_fresh_reason": null,
      "ordinal": 3,
      "registered_at": "2026-05-09T02:48:12Z",
      "role_id": "reviewer",
      "session_id": "sess_2b8c4e9a15f04d238fb6215bb753ca32",
      "slug": "reviewer-codex-3",
      "state": "closed"
    }
  ],
  "verdicts": [
    {
      "findings_artifact_id": "art_8d602d71ac0d4db0bcd3c13d6d40ade9",
      "job_id": "job_run_66ba248f6e4f47e49c130bca866e383f_review_gemini",
      "rationale": "<redacted-free-text>",
      "session_id": "sess_80d5db3ff5b8444e8c705a2028d73986",
      "verdict": "accept",
      "verdict_id": "verdict_e49a9501b8c64ea896a510454fb056b9"
    },
    {
      "findings_artifact_id": "art_9697291d435049ad8fda347d51dc6a80",
      "job_id": "job_run_66ba248f6e4f47e49c130bca866e383f_review_codex",
      "rationale": "<redacted-free-text>",
      "session_id": "sess_b0a9650be38c415b991cea35064b5bd6",
      "verdict": "accept_with_findings",
      "verdict_id": "verdict_a00196bb21de43c383d56d2f8689535d"
    },
    {
      "findings_artifact_id": "art_705b125b043f4f4aa226e96f059a7a97",
      "job_id": "job_run_66ba248f6e4f47e49c130bca866e383f_review_claude",
      "rationale": "<redacted-free-text>",
      "session_id": "sess_6bbaab8b765f43018fb90e5c50065d5e",
      "verdict": "accept_with_findings",
      "verdict_id": "verdict_940b4ad4d391468a983625ee12c4f954"
    },
    {
      "findings_artifact_id": "art_bb367b4d1e3d4f4d8d73bfbcb444c726",
      "job_id": "job_run_66ba248f6e4f47e49c130bca866e383f_final_review",
      "rationale": "<redacted-free-text>",
      "session_id": "sess_2b8c4e9a15f04d238fb6215bb753ca32",
      "verdict": "accept",
      "verdict_id": "verdict_6fed542b75a94f3e9e1ad33de6889ae8"
    }
  ],
  "workflow": {
    "workflow_id": "rfc-0028-predicate-intent-implementation",
    "workflow_version": "2026-05-09+initial"
  }
}
```
