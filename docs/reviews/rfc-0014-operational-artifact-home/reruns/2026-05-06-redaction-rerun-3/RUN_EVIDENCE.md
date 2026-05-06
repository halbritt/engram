# Agent Runner Evidence Export

Run ID: `run_198eb48427bb407c87dc72e03bc21948`
Branch: `agent-runner/rfc-0014-validation`
Run state: `running`
Exported at: `2026-05-06T20:24:26Z`

Live SQLite state remains ignored under `.agent_runner/` and is not part of this export.

## Status Output

```json
{"blocked_downstream_jobs":[{"blocked_by":[{"depends_on_job_id":"job_run_198eb48427bb407c87dc72e03bc21948_synthesis","latest_verdict":null,"required_verdicts":null,"state":"blocked","workflow_job_id":"synthesis"}],"job_id":"job_run_198eb48427bb407c87dc72e03bc21948_final_review","lane":"codex","role_id":"reviewer","state":"blocked","workflow_job_id":"final_review"},{"blocked_by":[{"depends_on_job_id":"job_run_198eb48427bb407c87dc72e03bc21948_review_codex","latest_verdict":"needs_revision","required_verdicts":["accept","accept_with_findings"],"state":"waiting_human","workflow_job_id":"review_codex"}],"job_id":"job_run_198eb48427bb407c87dc72e03bc21948_findings_ledger","lane":"codex","role_id":"ledger","state":"blocked","workflow_job_id":"findings_ledger"},{"blocked_by":[{"depends_on_job_id":"job_run_198eb48427bb407c87dc72e03bc21948_findings_ledger","latest_verdict":null,"required_verdicts":null,"state":"blocked","workflow_job_id":"findings_ledger"}],"job_id":"job_run_198eb48427bb407c87dc72e03bc21948_synthesis","lane":"claude","role_id":"synthesizer","state":"blocked","workflow_job_id":"synthesis"}],"claimable_jobs":[],"human_checkpoints":[{"blocker_id":"blk_7bf5cc384502409384c3ad1f29540343","blocker_kind":"revision_routing","description":"<redacted-free-text>","job_id":"job_run_198eb48427bb407c87dc72e03bc21948_review_codex","job_state":"waiting_human","run_id":"run_198eb48427bb407c87dc72e03bc21948","session_id":"sess_ff1e27e694ef4032a770e1dfd0196d43","severity":"human_checkpoint","state":"open","workflow_job_id":"review_codex"}],"jobs":{"blocked":3,"completed":2,"waiting_human":1},"latest_non_accepting_review_verdicts":[{"findings_artifact_id":"art_734d3baa12ec40b88aec04e8ffe3f942","job_id":"job_run_198eb48427bb407c87dc72e03bc21948_review_codex","job_state":"waiting_human","rationale":"<redacted-free-text>","run_id":"run_198eb48427bb407c87dc72e03bc21948","session_id":"sess_ff1e27e694ef4032a770e1dfd0196d43","verdict":"needs_revision","verdict_id":"verdict_1dc888e8e02b4ac6a64fb8e7aae50f91","workflow_job_id":"review_codex"}],"next_actions":["inspect_blocker","export_run_evidence","resolve_human_checkpoint","revise_workflow_cycle"],"open_blockers":[{"blocker_id":"blk_7bf5cc384502409384c3ad1f29540343","blocker_kind":"revision_routing","description":"<redacted-free-text>","job_id":"job_run_198eb48427bb407c87dc72e03bc21948_review_codex","job_state":"waiting_human","run_id":"run_198eb48427bb407c87dc72e03bc21948","session_id":"sess_ff1e27e694ef4032a770e1dfd0196d43","severity":"human_checkpoint","state":"open","workflow_job_id":"review_codex"}],"runs":[{"branch_name":"agent-runner/rfc-0014-validation","run_id":"run_198eb48427bb407c87dc72e03bc21948","state":"running"}]}
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
      "artifact_id": "art_390efebac4f948ff95acbc8bdb08fee9",
      "artifact_kind": "finding",
      "author": {
        "display_model": "Claude Opus",
        "lane_id": "claude",
        "line": "author: reviewer-claude-opus-001",
        "ordinal": 1,
        "role_id": "reviewer",
        "workflow_job_id": "review_claude"
      },
      "content_sha256": "f0ef48d3b11d4b6d12bb606ce0caf8017776d46c47b455a68559d36664c2ac77",
      "job_id": "job_run_198eb48427bb407c87dc72e03bc21948_review_claude",
      "logical_name": "review",
      "repo_path": "docs/reviews/rfc-0014-operational-artifact-home/reruns/2026-05-06-redaction-rerun-3/RFC_0014_REVIEW_claude.md",
      "session_id": "sess_b6a1bfaaa2d54d4f8129ded107081f0e"
    },
    {
      "artifact_id": "art_734d3baa12ec40b88aec04e8ffe3f942",
      "artifact_kind": "finding",
      "author": {
        "display_model": "Codex GPT-5.5",
        "lane_id": "codex",
        "line": "author: reviewer-codex-gpt-5.5-001",
        "ordinal": 1,
        "role_id": "reviewer",
        "workflow_job_id": "review_codex"
      },
      "content_sha256": "e6efc54f38d94fcc1892124bac1d146205c01edf7fbdbfe9f9e4a3e52ac688da",
      "job_id": "job_run_198eb48427bb407c87dc72e03bc21948_review_codex",
      "logical_name": "review",
      "repo_path": "docs/reviews/rfc-0014-operational-artifact-home/reruns/2026-05-06-redaction-rerun-3/RFC_0014_REVIEW_codex.md",
      "session_id": "sess_ff1e27e694ef4032a770e1dfd0196d43"
    },
    {
      "artifact_id": "art_1f759ecdf1124b4d8fd4be49bac0fd5f",
      "artifact_kind": "finding",
      "author": {
        "display_model": "Gemini 3.1 Pro Preview",
        "lane_id": "gemini",
        "line": "author: reviewer-gemini-3.1-pro-preview-001",
        "ordinal": 1,
        "role_id": "reviewer",
        "workflow_job_id": "review_gemini"
      },
      "content_sha256": "d37c1cb91b021d38a157035624ee5c08e59271dbc2bd8ab185eb5801b2456359",
      "job_id": "job_run_198eb48427bb407c87dc72e03bc21948_review_gemini",
      "logical_name": "review",
      "repo_path": "docs/reviews/rfc-0014-operational-artifact-home/reruns/2026-05-06-redaction-rerun-3/RFC_0014_REVIEW_gemini.md",
      "session_id": "sess_534ce77468e244b484a4ce7379fe21ab"
    }
  ],
  "blocked_downstream_jobs": [
    {
      "blocked_by": [
        {
          "depends_on_job_id": "job_run_198eb48427bb407c87dc72e03bc21948_synthesis",
          "latest_verdict": null,
          "required_verdicts": null,
          "state": "blocked",
          "workflow_job_id": "synthesis"
        }
      ],
      "job_id": "job_run_198eb48427bb407c87dc72e03bc21948_final_review",
      "lane": "codex",
      "role_id": "reviewer",
      "state": "blocked",
      "workflow_job_id": "final_review"
    },
    {
      "blocked_by": [
        {
          "depends_on_job_id": "job_run_198eb48427bb407c87dc72e03bc21948_review_codex",
          "latest_verdict": "needs_revision",
          "required_verdicts": [
            "accept",
            "accept_with_findings"
          ],
          "state": "waiting_human",
          "workflow_job_id": "review_codex"
        }
      ],
      "job_id": "job_run_198eb48427bb407c87dc72e03bc21948_findings_ledger",
      "lane": "codex",
      "role_id": "ledger",
      "state": "blocked",
      "workflow_job_id": "findings_ledger"
    },
    {
      "blocked_by": [
        {
          "depends_on_job_id": "job_run_198eb48427bb407c87dc72e03bc21948_findings_ledger",
          "latest_verdict": null,
          "required_verdicts": null,
          "state": "blocked",
          "workflow_job_id": "findings_ledger"
        }
      ],
      "job_id": "job_run_198eb48427bb407c87dc72e03bc21948_synthesis",
      "lane": "claude",
      "role_id": "synthesizer",
      "state": "blocked",
      "workflow_job_id": "synthesis"
    }
  ],
  "blockers": [
    {
      "blocker_id": "blk_7bf5cc384502409384c3ad1f29540343",
      "blocker_kind": "revision_routing",
      "description": "<redacted-free-text>",
      "job_id": "job_run_198eb48427bb407c87dc72e03bc21948_review_codex",
      "session_id": "sess_ff1e27e694ef4032a770e1dfd0196d43",
      "severity": "human_checkpoint",
      "state": "open"
    }
  ],
  "exported_at": "2026-05-06T20:24:26Z",
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
          "depends_on_job_id": "job_run_198eb48427bb407c87dc72e03bc21948_synthesis",
          "latest_verdict": null,
          "required_verdicts": null,
          "state": "blocked",
          "workflow_job_id": "synthesis"
        }
      ],
      "display_model": "Codex GPT-5.5",
      "fresh_session_required": true,
      "job_id": "job_run_198eb48427bb407c87dc72e03bc21948_final_review",
      "job_type": "review",
      "lane": "codex",
      "max_attempts": 1,
      "role_id": "reviewer",
      "state": "blocked",
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
          "depends_on_job_id": "job_run_198eb48427bb407c87dc72e03bc21948_review_claude",
          "latest_verdict": "accept_with_findings",
          "required_verdicts": [
            "accept",
            "accept_with_findings"
          ],
          "state": "completed",
          "workflow_job_id": "review_claude"
        },
        {
          "depends_on_job_id": "job_run_198eb48427bb407c87dc72e03bc21948_review_codex",
          "latest_verdict": "needs_revision",
          "required_verdicts": [
            "accept",
            "accept_with_findings"
          ],
          "state": "waiting_human",
          "workflow_job_id": "review_codex"
        },
        {
          "depends_on_job_id": "job_run_198eb48427bb407c87dc72e03bc21948_review_gemini",
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
      "job_id": "job_run_198eb48427bb407c87dc72e03bc21948_findings_ledger",
      "job_type": "ledger",
      "lane": "codex",
      "max_attempts": 1,
      "role_id": "ledger",
      "state": "blocked",
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
      "job_id": "job_run_198eb48427bb407c87dc72e03bc21948_review_claude",
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
      "job_id": "job_run_198eb48427bb407c87dc72e03bc21948_review_codex",
      "job_type": "review",
      "lane": "codex",
      "max_attempts": 1,
      "role_id": "reviewer",
      "state": "waiting_human",
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
      "job_id": "job_run_198eb48427bb407c87dc72e03bc21948_review_gemini",
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
          "depends_on_job_id": "job_run_198eb48427bb407c87dc72e03bc21948_findings_ledger",
          "latest_verdict": null,
          "required_verdicts": null,
          "state": "blocked",
          "workflow_job_id": "findings_ledger"
        }
      ],
      "display_model": "Claude Opus",
      "fresh_session_required": true,
      "job_id": "job_run_198eb48427bb407c87dc72e03bc21948_synthesis",
      "job_type": "synthesis",
      "lane": "claude",
      "max_attempts": 1,
      "role_id": "synthesizer",
      "state": "blocked",
      "workflow_job_id": "synthesis"
    }
  ],
  "run": {
    "branch_name": "agent-runner/rfc-0014-validation",
    "run_id": "run_198eb48427bb407c87dc72e03bc21948",
    "state": "running"
  },
  "schema_version": "agent-runner.evidence.v1",
  "verdicts": [
    {
      "findings_artifact_id": "art_390efebac4f948ff95acbc8bdb08fee9",
      "job_id": "job_run_198eb48427bb407c87dc72e03bc21948_review_claude",
      "rationale": "<redacted-free-text>",
      "session_id": "sess_b6a1bfaaa2d54d4f8129ded107081f0e",
      "verdict": "accept_with_findings",
      "verdict_id": "verdict_7e8c4ee19e734ee9838fb24c99f03482"
    },
    {
      "findings_artifact_id": "art_1f759ecdf1124b4d8fd4be49bac0fd5f",
      "job_id": "job_run_198eb48427bb407c87dc72e03bc21948_review_gemini",
      "rationale": "<redacted-free-text>",
      "session_id": "sess_534ce77468e244b484a4ce7379fe21ab",
      "verdict": "accept",
      "verdict_id": "verdict_564dd8f5da39471b889e36dcc71d1368"
    },
    {
      "findings_artifact_id": "art_734d3baa12ec40b88aec04e8ffe3f942",
      "job_id": "job_run_198eb48427bb407c87dc72e03bc21948_review_codex",
      "rationale": "<redacted-free-text>",
      "session_id": "sess_ff1e27e694ef4032a770e1dfd0196d43",
      "verdict": "needs_revision",
      "verdict_id": "verdict_1dc888e8e02b4ac6a64fb8e7aae50f91"
    }
  ],
  "workflow": {
    "workflow_id": "rfc-0014-operational-artifact-home",
    "workflow_version": "2026-05-06+spec-handoff+2026-05-06-redaction-rerun-3"
  }
}
```
