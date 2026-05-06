# Agent Runner Evidence Export

Run ID: `run_45627c1a87fc4d11a109b5600518901b`
Branch: `agent-runner/rfc-0014-validation`
Run state: `completed`
Exported at: `2026-05-06T22:27:02Z`

Live SQLite state remains ignored under `.agent_runner/` and is not part of this export.

## Status Output

```json
{"blocked_downstream_jobs":[],"claimable_jobs":[],"human_checkpoints":[],"jobs":{"completed":8},"latest_non_accepting_review_verdicts":[],"next_actions":[],"open_blockers":[],"runs":[{"branch_name":"agent-runner/rfc-0014-validation","run_id":"run_45627c1a87fc4d11a109b5600518901b","state":"completed"}]}
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
      "artifact_id": "art_12a642d70de14d259aea5f5641e8734b",
      "artifact_kind": "finding",
      "author": {
        "display_model": "Codex GPT-5.5",
        "lane_id": "codex",
        "line": "author: reviewer-codex-gpt-5.5-002",
        "ordinal": 2,
        "role_id": "reviewer",
        "workflow_job_id": "final_review"
      },
      "content_sha256": "01e43e10eb6f95d0ded33d3b77faa399a6081ba38723dfaf0d448b082e7ef7eb",
      "job_id": "job_run_45627c1a87fc4d11a109b5600518901b_final_review",
      "logical_name": "review",
      "repo_path": "docs/reviews/rfc-0014-operational-artifact-home/reruns/2026-05-06-redaction-rerun-4/RFC_0014_FINAL_REVIEW.md",
      "session_id": "sess_5b918c75a931482f95a60680d1989094"
    },
    {
      "artifact_id": "art_40e8a5fdbf6c4c3d97e2b8a130d1023e",
      "artifact_kind": "finding",
      "author": {
        "display_model": "Codex GPT-5.5",
        "lane_id": "codex",
        "line": "author: reviewer-codex-gpt-5.5-003",
        "ordinal": 3,
        "role_id": "reviewer",
        "workflow_job_id": "final_review"
      },
      "content_sha256": "284c13ad7e48a77a39f8bc0db9f47b363e22d1a9362f7ee3d517927aba4431d7",
      "job_id": "job_run_45627c1a87fc4d11a109b5600518901b_final_review_a2",
      "logical_name": "review",
      "repo_path": "docs/reviews/rfc-0014-operational-artifact-home/reruns/2026-05-06-redaction-rerun-4/RFC_0014_FINAL_REVIEW.md",
      "session_id": "sess_842a0040a1d641589a46c9034da901cd"
    },
    {
      "artifact_id": "art_3bb3082346324cda81cdd4b1cc6b1928",
      "artifact_kind": "findings_ledger",
      "author": {
        "display_model": "Codex GPT-5.5",
        "lane_id": "codex",
        "line": "author: ledger-codex-gpt-5.5-001",
        "ordinal": 1,
        "role_id": "ledger",
        "workflow_job_id": "findings_ledger"
      },
      "content_sha256": "9cb17c0bf29d1c7bde1235de290d0ace0388021e4ea369c7f558b95def533d6e",
      "job_id": "job_run_45627c1a87fc4d11a109b5600518901b_findings_ledger",
      "logical_name": "ledger",
      "repo_path": "docs/reviews/rfc-0014-operational-artifact-home/reruns/2026-05-06-redaction-rerun-4/RFC_0014_FINDINGS_LEDGER.md",
      "session_id": "sess_2c04e3db42e74d9bbe30ac657fcfab4c"
    },
    {
      "artifact_id": "art_6c9f7997a4e741bc8b70dcc76e8c07bf",
      "artifact_kind": "finding",
      "author": {
        "display_model": "Claude Opus",
        "lane_id": "claude",
        "line": "author: reviewer-claude-opus-001",
        "ordinal": 1,
        "role_id": "reviewer",
        "workflow_job_id": "review_claude"
      },
      "content_sha256": "3bf1d3ddf0015f259f7efa75292eff176148f8505c33df5f195590d1b3e49c53",
      "job_id": "job_run_45627c1a87fc4d11a109b5600518901b_review_claude",
      "logical_name": "review",
      "repo_path": "docs/reviews/rfc-0014-operational-artifact-home/reruns/2026-05-06-redaction-rerun-4/RFC_0014_REVIEW_claude.md",
      "session_id": "sess_02a11b653b114321a2ff84b4c7897fad"
    },
    {
      "artifact_id": "art_ff528638bc0d49619e0e99ef746adfff",
      "artifact_kind": "finding",
      "author": {
        "display_model": "Codex GPT-5.5",
        "lane_id": "codex",
        "line": "author: reviewer-codex-gpt-5.5-001",
        "ordinal": 1,
        "role_id": "reviewer",
        "workflow_job_id": "review_codex"
      },
      "content_sha256": "1c95d5f9c726a97ad6388381505bd2310c1da468bfbccc78c5be2869bc012be0",
      "job_id": "job_run_45627c1a87fc4d11a109b5600518901b_review_codex",
      "logical_name": "review",
      "repo_path": "docs/reviews/rfc-0014-operational-artifact-home/reruns/2026-05-06-redaction-rerun-4/RFC_0014_REVIEW_codex.md",
      "session_id": "sess_fe14bc9997794006ac8c3ce439f99023"
    },
    {
      "artifact_id": "art_5d6b3b38ae2849a4a5910d7bbefb001a",
      "artifact_kind": "finding",
      "author": {
        "display_model": "Gemini 3.1 Pro Preview",
        "lane_id": "gemini",
        "line": "author: reviewer-gemini-3.1-pro-preview-001",
        "ordinal": 1,
        "role_id": "reviewer",
        "workflow_job_id": "review_gemini"
      },
      "content_sha256": "e567410f86ae144ecb198781b49892a97cf62c92bcdf7c7430528566d040bf48",
      "job_id": "job_run_45627c1a87fc4d11a109b5600518901b_review_gemini",
      "logical_name": "review",
      "repo_path": "docs/reviews/rfc-0014-operational-artifact-home/reruns/2026-05-06-redaction-rerun-4/RFC_0014_REVIEW_gemini.md",
      "session_id": "sess_7e88f883efc34696b754423b7ef46897"
    },
    {
      "artifact_id": "art_0235bc87045045b8b59843ce06bfd26c",
      "artifact_kind": "synthesis",
      "author": {
        "display_model": "Claude Opus",
        "lane_id": "claude",
        "line": "author: synthesizer-claude-opus-001",
        "ordinal": 1,
        "role_id": "synthesizer",
        "workflow_job_id": "synthesis"
      },
      "content_sha256": "41290523873bdf556ce9a33a5545c96396472ace2a53fcb88ec7235a82668d94",
      "job_id": "job_run_45627c1a87fc4d11a109b5600518901b_synthesis",
      "logical_name": "synthesis",
      "repo_path": "docs/reviews/rfc-0014-operational-artifact-home/reruns/2026-05-06-redaction-rerun-4/RFC_0014_SYNTHESIS.md",
      "session_id": "sess_b162e260eea345379ccefe99cfe1c36e"
    },
    {
      "artifact_id": "art_d0904d3e17ef4563b861cf19c9d4aa8b",
      "artifact_kind": "synthesis",
      "author": {
        "display_model": "Claude Opus",
        "lane_id": "claude",
        "line": "author: synthesizer-claude-opus-002",
        "ordinal": 2,
        "role_id": "synthesizer",
        "workflow_job_id": "synthesis"
      },
      "content_sha256": "5f3906d0413e2eb2efce9370adf9e82e503999dc5581dddc8095ee2939cc0b72",
      "job_id": "job_run_45627c1a87fc4d11a109b5600518901b_synthesis_a2",
      "logical_name": "synthesis",
      "repo_path": "docs/reviews/rfc-0014-operational-artifact-home/reruns/2026-05-06-redaction-rerun-4/RFC_0014_SYNTHESIS.md",
      "session_id": "sess_092b40be21374f229db6c436934a3f8c"
    }
  ],
  "blocked_downstream_jobs": [],
  "blockers": [],
  "exported_at": "2026-05-06T22:27:02Z",
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
          "depends_on_job_id": "job_run_45627c1a87fc4d11a109b5600518901b_synthesis",
          "latest_verdict": null,
          "required_verdicts": null,
          "state": "completed",
          "workflow_job_id": "synthesis"
        }
      ],
      "display_model": "Codex GPT-5.5",
      "fresh_session_required": true,
      "job_id": "job_run_45627c1a87fc4d11a109b5600518901b_final_review",
      "job_type": "review",
      "lane": "codex",
      "max_attempts": 1,
      "role_id": "reviewer",
      "state": "completed",
      "workflow_job_id": "final_review"
    },
    {
      "attempt": 2,
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
          "depends_on_job_id": "job_run_45627c1a87fc4d11a109b5600518901b_synthesis_a2",
          "latest_verdict": null,
          "required_verdicts": null,
          "state": "completed",
          "workflow_job_id": "synthesis"
        }
      ],
      "display_model": "Codex GPT-5.5",
      "fresh_session_required": true,
      "job_id": "job_run_45627c1a87fc4d11a109b5600518901b_final_review_a2",
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
          "depends_on_job_id": "job_run_45627c1a87fc4d11a109b5600518901b_review_claude",
          "latest_verdict": "accept_with_findings",
          "required_verdicts": [
            "accept",
            "accept_with_findings"
          ],
          "state": "completed",
          "workflow_job_id": "review_claude"
        },
        {
          "depends_on_job_id": "job_run_45627c1a87fc4d11a109b5600518901b_review_codex",
          "latest_verdict": "accept_with_findings",
          "required_verdicts": [
            "accept",
            "accept_with_findings"
          ],
          "state": "completed",
          "workflow_job_id": "review_codex"
        },
        {
          "depends_on_job_id": "job_run_45627c1a87fc4d11a109b5600518901b_review_gemini",
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
      "job_id": "job_run_45627c1a87fc4d11a109b5600518901b_findings_ledger",
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
      "job_id": "job_run_45627c1a87fc4d11a109b5600518901b_review_claude",
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
      "job_id": "job_run_45627c1a87fc4d11a109b5600518901b_review_codex",
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
      "job_id": "job_run_45627c1a87fc4d11a109b5600518901b_review_gemini",
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
          "depends_on_job_id": "job_run_45627c1a87fc4d11a109b5600518901b_findings_ledger",
          "latest_verdict": null,
          "required_verdicts": null,
          "state": "completed",
          "workflow_job_id": "findings_ledger"
        }
      ],
      "display_model": "Claude Opus",
      "fresh_session_required": true,
      "job_id": "job_run_45627c1a87fc4d11a109b5600518901b_synthesis",
      "job_type": "synthesis",
      "lane": "claude",
      "max_attempts": 1,
      "role_id": "synthesizer",
      "state": "completed",
      "workflow_job_id": "synthesis"
    },
    {
      "attempt": 2,
      "author": {
        "display_model": "Claude Opus",
        "lane_id": "claude",
        "line": null,
        "ordinal": null,
        "role_id": "synthesizer",
        "workflow_job_id": "synthesis"
      },
      "dependencies": [],
      "display_model": "Claude Opus",
      "fresh_session_required": true,
      "job_id": "job_run_45627c1a87fc4d11a109b5600518901b_synthesis_a2",
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
    "run_id": "run_45627c1a87fc4d11a109b5600518901b",
    "state": "completed"
  },
  "schema_version": "agent-runner.evidence.v1",
  "verdicts": [
    {
      "findings_artifact_id": "art_6c9f7997a4e741bc8b70dcc76e8c07bf",
      "job_id": "job_run_45627c1a87fc4d11a109b5600518901b_review_claude",
      "rationale": "<redacted-free-text>",
      "session_id": "sess_02a11b653b114321a2ff84b4c7897fad",
      "verdict": "accept_with_findings",
      "verdict_id": "verdict_ff288da418bc4bd689f5824558910b64"
    },
    {
      "findings_artifact_id": "art_5d6b3b38ae2849a4a5910d7bbefb001a",
      "job_id": "job_run_45627c1a87fc4d11a109b5600518901b_review_gemini",
      "rationale": "<redacted-free-text>",
      "session_id": "sess_7e88f883efc34696b754423b7ef46897",
      "verdict": "accept",
      "verdict_id": "verdict_e2ce16d7737b478aba372a30fe1dc4c3"
    },
    {
      "findings_artifact_id": "art_ff528638bc0d49619e0e99ef746adfff",
      "job_id": "job_run_45627c1a87fc4d11a109b5600518901b_review_codex",
      "rationale": "<redacted-free-text>",
      "session_id": "sess_fe14bc9997794006ac8c3ce439f99023",
      "verdict": "accept_with_findings",
      "verdict_id": "verdict_e519260f3b8f47e681c36988112a9874"
    },
    {
      "findings_artifact_id": "art_12a642d70de14d259aea5f5641e8734b",
      "job_id": "job_run_45627c1a87fc4d11a109b5600518901b_final_review",
      "rationale": "<redacted-free-text>",
      "session_id": "sess_5b918c75a931482f95a60680d1989094",
      "verdict": "needs_revision",
      "verdict_id": "verdict_f5c22717a78b46338679d8a95788fcc7"
    },
    {
      "findings_artifact_id": "art_40e8a5fdbf6c4c3d97e2b8a130d1023e",
      "job_id": "job_run_45627c1a87fc4d11a109b5600518901b_final_review_a2",
      "rationale": "<redacted-free-text>",
      "session_id": "sess_842a0040a1d641589a46c9034da901cd",
      "verdict": "accept_with_findings",
      "verdict_id": "verdict_e204b5e751484a1dbd45663ecf80db9f"
    }
  ],
  "workflow": {
    "workflow_id": "rfc-0014-operational-artifact-home",
    "workflow_version": "2026-05-06+spec-handoff+2026-05-06-redaction-rerun-4"
  }
}
```
