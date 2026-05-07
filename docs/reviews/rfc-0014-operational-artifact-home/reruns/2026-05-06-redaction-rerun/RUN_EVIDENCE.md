# Agent Runner Evidence Export

Run ID: `run_e1e472612df34abe8f0daef7cf9ffd32`
Branch: `agent-runner/rfc-0014-validation`
Run state: `running`
Exported at: `2026-05-06T17:42:44Z`

Live SQLite state remains ignored under `.agent_runner/` and is not part of this export.

## Status Output

```json
{"blocked_downstream_jobs":[{"blocked_by":[{"depends_on_job_id":"job_run_e1e472612df34abe8f0daef7cf9ffd32_synthesis","latest_verdict":null,"required_verdicts":null,"state":"blocked","workflow_job_id":"synthesis"}],"job_id":"job_run_e1e472612df34abe8f0daef7cf9ffd32_final_review","lane":"codex","role_id":"reviewer","state":"blocked","workflow_job_id":"final_review"},{"blocked_by":[{"depends_on_job_id":"job_run_e1e472612df34abe8f0daef7cf9ffd32_review_gemini","latest_verdict":"needs_revision","required_verdicts":["accept","accept_with_findings"],"state":"waiting_human","workflow_job_id":"review_gemini"}],"job_id":"job_run_e1e472612df34abe8f0daef7cf9ffd32_findings_ledger","lane":"codex","role_id":"ledger","state":"blocked","workflow_job_id":"findings_ledger"},{"blocked_by":[{"depends_on_job_id":"job_run_e1e472612df34abe8f0daef7cf9ffd32_findings_ledger","latest_verdict":null,"required_verdicts":null,"state":"blocked","workflow_job_id":"findings_ledger"}],"job_id":"job_run_e1e472612df34abe8f0daef7cf9ffd32_synthesis","lane":"claude","role_id":"synthesizer","state":"blocked","workflow_job_id":"synthesis"}],"claimable_jobs":[],"human_checkpoints":[{"blocker_id":"blk_d60c6aaecb6146af8a1d89fedbe3a695","blocker_kind":"revision_routing","description":"<redacted-free-text>","job_id":"job_run_e1e472612df34abe8f0daef7cf9ffd32_review_gemini","job_state":"waiting_human","run_id":"run_e1e472612df34abe8f0daef7cf9ffd32","session_id":"sess_cd3f271bbe7f4f3abf2bdd7da24aef72","severity":"human_checkpoint","state":"open","workflow_job_id":"review_gemini"}],"jobs":{"blocked":3,"completed":2,"waiting_human":1},"latest_non_accepting_review_verdicts":[{"findings_artifact_id":"art_7c9fd53775784946957462f17a5c62e3","job_id":"job_run_e1e472612df34abe8f0daef7cf9ffd32_review_gemini","job_state":"waiting_human","rationale":"<redacted-free-text>","run_id":"run_e1e472612df34abe8f0daef7cf9ffd32","session_id":"sess_cd3f271bbe7f4f3abf2bdd7da24aef72","verdict":"needs_revision","verdict_id":"verdict_b8b842e2860d4143a23bfaa1d897d032","workflow_job_id":"review_gemini"}],"next_actions":["inspect_blocker","export_run_evidence","resolve_human_checkpoint","revise_workflow_cycle"],"open_blockers":[{"blocker_id":"blk_d60c6aaecb6146af8a1d89fedbe3a695","blocker_kind":"revision_routing","description":"<redacted-free-text>","job_id":"job_run_e1e472612df34abe8f0daef7cf9ffd32_review_gemini","job_state":"waiting_human","run_id":"run_e1e472612df34abe8f0daef7cf9ffd32","session_id":"sess_cd3f271bbe7f4f3abf2bdd7da24aef72","severity":"human_checkpoint","state":"open","workflow_job_id":"review_gemini"}],"runs":[{"branch_name":"agent-runner/rfc-0014-validation","run_id":"run_e1e472612df34abe8f0daef7cf9ffd32","state":"running"}]}
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
      "artifact_id": "art_230942c0acc440f98f8efe7ffaba8dee",
      "artifact_kind": "finding",
      "author": {
        "display_model": "Claude Opus",
        "lane_id": "claude",
        "line": "Author: reviewer / claude / Claude Opus / review_claude",
        "role_id": "reviewer",
        "workflow_job_id": "review_claude"
      },
      "content_sha256": "62f6131c36df509bade5af47d2171e06118402ae66d9f37331b5832327c986d7",
      "job_id": "job_run_e1e472612df34abe8f0daef7cf9ffd32_review_claude",
      "logical_name": "review",
      "repo_path": "docs/reviews/rfc-0014-operational-artifact-home/reruns/2026-05-06-redaction-rerun/RFC_0014_REVIEW_claude.md",
      "session_id": "sess_694e1067565d40d68b3025000c40fa38"
    },
    {
      "artifact_id": "art_9733d3aeb56043119db640ee17b3b8b8",
      "artifact_kind": "finding",
      "author": {
        "display_model": "Codex GPT-5.5",
        "lane_id": "codex",
        "line": "Author: reviewer / codex / Codex GPT-5.5 / review_codex",
        "role_id": "reviewer",
        "workflow_job_id": "review_codex"
      },
      "content_sha256": "acd76493204e2e67270b07961210a4aa852b03f02f1dfdc7d197ff9982eaa380",
      "job_id": "job_run_e1e472612df34abe8f0daef7cf9ffd32_review_codex",
      "logical_name": "review",
      "repo_path": "docs/reviews/rfc-0014-operational-artifact-home/reruns/2026-05-06-redaction-rerun/RFC_0014_REVIEW_codex.md",
      "session_id": "sess_be7b2c092c7144ca82b9351bd65820bf"
    },
    {
      "artifact_id": "art_7c9fd53775784946957462f17a5c62e3",
      "artifact_kind": "finding",
      "author": {
        "display_model": "Gemini 3.1 Pro Preview",
        "lane_id": "gemini",
        "line": "Author: reviewer / gemini / Gemini 3.1 Pro Preview / review_gemini",
        "role_id": "reviewer",
        "workflow_job_id": "review_gemini"
      },
      "content_sha256": "572a12672c148283d3f9eeaa39b0e2312384b142ffa671104ed1a3ad23942fe8",
      "job_id": "job_run_e1e472612df34abe8f0daef7cf9ffd32_review_gemini",
      "logical_name": "review",
      "repo_path": "docs/reviews/rfc-0014-operational-artifact-home/reruns/2026-05-06-redaction-rerun/RFC_0014_REVIEW_gemini.md",
      "session_id": "sess_cd3f271bbe7f4f3abf2bdd7da24aef72"
    }
  ],
  "blocked_downstream_jobs": [
    {
      "blocked_by": [
        {
          "depends_on_job_id": "job_run_e1e472612df34abe8f0daef7cf9ffd32_synthesis",
          "latest_verdict": null,
          "required_verdicts": null,
          "state": "blocked",
          "workflow_job_id": "synthesis"
        }
      ],
      "job_id": "job_run_e1e472612df34abe8f0daef7cf9ffd32_final_review",
      "lane": "codex",
      "role_id": "reviewer",
      "state": "blocked",
      "workflow_job_id": "final_review"
    },
    {
      "blocked_by": [
        {
          "depends_on_job_id": "job_run_e1e472612df34abe8f0daef7cf9ffd32_review_gemini",
          "latest_verdict": "needs_revision",
          "required_verdicts": [
            "accept",
            "accept_with_findings"
          ],
          "state": "waiting_human",
          "workflow_job_id": "review_gemini"
        }
      ],
      "job_id": "job_run_e1e472612df34abe8f0daef7cf9ffd32_findings_ledger",
      "lane": "codex",
      "role_id": "ledger",
      "state": "blocked",
      "workflow_job_id": "findings_ledger"
    },
    {
      "blocked_by": [
        {
          "depends_on_job_id": "job_run_e1e472612df34abe8f0daef7cf9ffd32_findings_ledger",
          "latest_verdict": null,
          "required_verdicts": null,
          "state": "blocked",
          "workflow_job_id": "findings_ledger"
        }
      ],
      "job_id": "job_run_e1e472612df34abe8f0daef7cf9ffd32_synthesis",
      "lane": "claude",
      "role_id": "synthesizer",
      "state": "blocked",
      "workflow_job_id": "synthesis"
    }
  ],
  "blockers": [
    {
      "blocker_id": "blk_d60c6aaecb6146af8a1d89fedbe3a695",
      "blocker_kind": "revision_routing",
      "description": "<redacted-free-text>",
      "job_id": "job_run_e1e472612df34abe8f0daef7cf9ffd32_review_gemini",
      "session_id": "sess_cd3f271bbe7f4f3abf2bdd7da24aef72",
      "severity": "human_checkpoint",
      "state": "open"
    }
  ],
  "exported_at": "2026-05-06T17:42:44Z",
  "jobs": [
    {
      "attempt": 1,
      "author": {
        "display_model": "Codex GPT-5.5",
        "lane_id": "codex",
        "line": "Author: reviewer / codex / Codex GPT-5.5 / final_review",
        "role_id": "reviewer",
        "workflow_job_id": "final_review"
      },
      "dependencies": [
        {
          "depends_on_job_id": "job_run_e1e472612df34abe8f0daef7cf9ffd32_synthesis",
          "latest_verdict": null,
          "required_verdicts": null,
          "state": "blocked",
          "workflow_job_id": "synthesis"
        }
      ],
      "display_model": "Codex GPT-5.5",
      "fresh_session_required": true,
      "job_id": "job_run_e1e472612df34abe8f0daef7cf9ffd32_final_review",
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
        "line": "Author: ledger / codex / Codex GPT-5.5 / findings_ledger",
        "role_id": "ledger",
        "workflow_job_id": "findings_ledger"
      },
      "dependencies": [
        {
          "depends_on_job_id": "job_run_e1e472612df34abe8f0daef7cf9ffd32_review_claude",
          "latest_verdict": "accept_with_findings",
          "required_verdicts": [
            "accept",
            "accept_with_findings"
          ],
          "state": "completed",
          "workflow_job_id": "review_claude"
        },
        {
          "depends_on_job_id": "job_run_e1e472612df34abe8f0daef7cf9ffd32_review_codex",
          "latest_verdict": "accept_with_findings",
          "required_verdicts": [
            "accept",
            "accept_with_findings"
          ],
          "state": "completed",
          "workflow_job_id": "review_codex"
        },
        {
          "depends_on_job_id": "job_run_e1e472612df34abe8f0daef7cf9ffd32_review_gemini",
          "latest_verdict": "needs_revision",
          "required_verdicts": [
            "accept",
            "accept_with_findings"
          ],
          "state": "waiting_human",
          "workflow_job_id": "review_gemini"
        }
      ],
      "display_model": "Codex GPT-5.5",
      "fresh_session_required": true,
      "job_id": "job_run_e1e472612df34abe8f0daef7cf9ffd32_findings_ledger",
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
        "line": "Author: reviewer / claude / Claude Opus / review_claude",
        "role_id": "reviewer",
        "workflow_job_id": "review_claude"
      },
      "dependencies": [],
      "display_model": "Claude Opus",
      "fresh_session_required": true,
      "job_id": "job_run_e1e472612df34abe8f0daef7cf9ffd32_review_claude",
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
        "line": "Author: reviewer / codex / Codex GPT-5.5 / review_codex",
        "role_id": "reviewer",
        "workflow_job_id": "review_codex"
      },
      "dependencies": [],
      "display_model": "Codex GPT-5.5",
      "fresh_session_required": true,
      "job_id": "job_run_e1e472612df34abe8f0daef7cf9ffd32_review_codex",
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
        "line": "Author: reviewer / gemini / Gemini 3.1 Pro Preview / review_gemini",
        "role_id": "reviewer",
        "workflow_job_id": "review_gemini"
      },
      "dependencies": [],
      "display_model": "Gemini 3.1 Pro Preview",
      "fresh_session_required": true,
      "job_id": "job_run_e1e472612df34abe8f0daef7cf9ffd32_review_gemini",
      "job_type": "review",
      "lane": "gemini",
      "max_attempts": 1,
      "role_id": "reviewer",
      "state": "waiting_human",
      "workflow_job_id": "review_gemini"
    },
    {
      "attempt": 1,
      "author": {
        "display_model": "Claude Opus",
        "lane_id": "claude",
        "line": "Author: synthesizer / claude / Claude Opus / synthesis",
        "role_id": "synthesizer",
        "workflow_job_id": "synthesis"
      },
      "dependencies": [
        {
          "depends_on_job_id": "job_run_e1e472612df34abe8f0daef7cf9ffd32_findings_ledger",
          "latest_verdict": null,
          "required_verdicts": null,
          "state": "blocked",
          "workflow_job_id": "findings_ledger"
        }
      ],
      "display_model": "Claude Opus",
      "fresh_session_required": true,
      "job_id": "job_run_e1e472612df34abe8f0daef7cf9ffd32_synthesis",
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
    "run_id": "run_e1e472612df34abe8f0daef7cf9ffd32",
    "state": "running"
  },
  "schema_version": "agent-runner.evidence.v1",
  "verdicts": [
    {
      "findings_artifact_id": "art_230942c0acc440f98f8efe7ffaba8dee",
      "job_id": "job_run_e1e472612df34abe8f0daef7cf9ffd32_review_claude",
      "rationale": "<redacted-free-text>",
      "session_id": "sess_694e1067565d40d68b3025000c40fa38",
      "verdict": "accept_with_findings",
      "verdict_id": "verdict_f37c67291dc64b268e7d6f654b540096"
    },
    {
      "findings_artifact_id": "art_9733d3aeb56043119db640ee17b3b8b8",
      "job_id": "job_run_e1e472612df34abe8f0daef7cf9ffd32_review_codex",
      "rationale": "<redacted-free-text>",
      "session_id": "sess_be7b2c092c7144ca82b9351bd65820bf",
      "verdict": "accept_with_findings",
      "verdict_id": "verdict_5ac6a3344b444bb1bdae7a47ae01d25b"
    },
    {
      "findings_artifact_id": "art_7c9fd53775784946957462f17a5c62e3",
      "job_id": "job_run_e1e472612df34abe8f0daef7cf9ffd32_review_gemini",
      "rationale": "<redacted-free-text>",
      "session_id": "sess_cd3f271bbe7f4f3abf2bdd7da24aef72",
      "verdict": "needs_revision",
      "verdict_id": "verdict_b8b842e2860d4143a23bfaa1d897d032"
    }
  ],
  "workflow": {
    "workflow_id": "rfc-0014-operational-artifact-home",
    "workflow_version": "2026-05-06+2026-05-06-redaction-rerun"
  }
}
```
