"""Interview agent (RFC 0021 § Interview agent).

The agent is the rendering surface: it loads a versioned prompt template per
``target_kind``, renders one question for the operator, and records a single
verdict via :mod:`engram.interview.storage`. It does **not** generate freeform
claims and does **not** call live LLMs (D044, D052).
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import psycopg

from engram.interview.errors import GoldLabelVerdictError
from engram.interview.sampler import SampledTarget
from engram.interview.storage import insert_label


INTERVIEW_TEMPLATE_VERSION_CLAIM_V1 = "interview.claim.v1.d079.initial"
INTERVIEW_TEMPLATE_VERSION_BELIEF_V1 = "interview.belief.v1.d079.initial"
INTERVIEW_TEMPLATE_PATH_CLAIM_V1 = "prompts/interview/claim_v1.md"
INTERVIEW_TEMPLATE_PATH_BELIEF_V1 = "prompts/interview/belief_v1.md"

VALID_VERDICTS: frozenset[str] = frozenset(
    {"true", "false", "stale", "unsupported", "unsure", "skip"}
)
RATIONALE_CHAR_LIMIT = 2000


_REPO_ROOT = Path(__file__).resolve().parents[3]


def _resolve_template_path(relative: str) -> Path:
    """Resolve a relative ``prompts/...`` path against the repo root."""
    return _REPO_ROOT / relative


class InterviewAgent:
    """Render questions and record verdicts for one operator session."""

    def __init__(
        self,
        conn: psycopg.Connection,
        *,
        sampler_id: str,
        sampler_version: str,
    ) -> None:
        self.conn = conn
        self.sampler_id = sampler_id
        self.sampler_version = sampler_version

    @staticmethod
    def template_for(target: SampledTarget) -> tuple[str, str]:
        """Return ``(template_version, template_path)`` for a sampled target."""
        if target.target_kind == "claim":
            return INTERVIEW_TEMPLATE_VERSION_CLAIM_V1, INTERVIEW_TEMPLATE_PATH_CLAIM_V1
        if target.target_kind == "belief":
            return INTERVIEW_TEMPLATE_VERSION_BELIEF_V1, INTERVIEW_TEMPLATE_PATH_BELIEF_V1
        raise GoldLabelVerdictError(f"unknown target_kind: {target.target_kind}")

    def render_question(self, target: SampledTarget) -> str:
        """Read the on-disk template for ``target`` and return the rendered text."""
        _, relative_path = self.template_for(target)
        path = _resolve_template_path(relative_path)
        try:
            text = path.read_text(encoding="utf-8")
        except FileNotFoundError as exc:
            raise GoldLabelVerdictError(
                f"interview template missing: {relative_path}"
            ) from exc
        # v1 keeps placeholder substitution lazy: the template itself documents
        # the expected slots. Operator-facing rendering is the CLI's job.
        return text

    def record_verdict(
        self,
        session_id: str,
        target: SampledTarget,
        verdict: str,
        rationale: str | None = None,
        *,
        evidence_excerpt: str | None = None,
        asked_at: datetime | None = None,
        answered_at: datetime | None = None,
    ) -> str:
        """Insert one ``gold_labels`` row for ``target`` and return its UUID."""
        if verdict not in VALID_VERDICTS:
            raise GoldLabelVerdictError(
                f"verdict {verdict!r} not in {sorted(VALID_VERDICTS)}"
            )
        if rationale is not None and len(rationale) > RATIONALE_CHAR_LIMIT:
            raise GoldLabelVerdictError(
                f"rationale exceeds {RATIONALE_CHAR_LIMIT} chars (got {len(rationale)})"
            )
        prompt_text = self.render_question(target)
        template_version, template_path = self.template_for(target)
        now = datetime.now(timezone.utc)
        return insert_label(
            self.conn,
            session_id=session_id,
            target_kind=target.target_kind,
            target_id=target.target_id,
            version_triple=target.version_triple(),
            prompt_template_version=template_version,
            prompt_template_path=template_path,
            prompt_text=prompt_text,
            verdict=verdict,
            rationale=rationale,
            sampler_id=self.sampler_id,
            sampler_version=self.sampler_version,
            candidate_pool_snapshot_id=target.candidate_pool_snapshot_id,
            active_learning_signal_version=target.active_learning_signal_version,
            stability_class=target.stability_class,
            conf_band=target.conf_band,
            recency_band=target.recency_band,
            belief_status=target.belief_status,
            asked_at=asked_at or now,
            answered_at=answered_at or now,
            evidence_excerpt=evidence_excerpt,
        )
