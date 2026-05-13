"""RFC 0021 gold-set interview curation public API."""

from __future__ import annotations

from engram.interview.agent import (
    INTERVIEW_TEMPLATE_PATH_BELIEF_V1,
    INTERVIEW_TEMPLATE_PATH_CLAIM_V1,
    INTERVIEW_TEMPLATE_VERSION_BELIEF_V1,
    INTERVIEW_TEMPLATE_VERSION_CLAIM_V1,
    RATIONALE_CHAR_LIMIT,
    VALID_VERDICTS,
    InterviewAgent,
)
from engram.interview.errors import (
    GoldLabelSamplerError,
    GoldLabelStorageError,
    GoldLabelVerdictError,
    InterviewError,
)
from engram.interview.sampler import (
    ENGRAM_GOLD_ACTIVE_LEARNING_THRESHOLD,
    ENGRAM_GOLD_COOLDOWN_GOAL_DAYS,
    ENGRAM_GOLD_COOLDOWN_IDENTITY_DAYS,
    ENGRAM_GOLD_COOLDOWN_MOOD_DAYS,
    ENGRAM_GOLD_COOLDOWN_PREFERENCE_DAYS,
    ENGRAM_GOLD_COOLDOWN_PROJECT_STATUS_DAYS,
    ENGRAM_GOLD_COOLDOWN_RELATIONSHIP_DAYS,
    ENGRAM_GOLD_COOLDOWN_TASK_DAYS,
    SAMPLER_ID,
    SAMPLER_VERSION,
    GoldLabelSampler,
    SampledTarget,
    build_strata_key,
    cooldown_days_for,
)
from engram.interview.storage import (
    Session,
    SessionTarget,
    get_active_learning_signal_version,
    insert_label,
    insert_active_learning_event,
    insert_session,
    insert_session_targets,
    list_session_targets,
    list_sessions,
    load_session_target,
    mark_session_completed,
    session_target_to_sampled,
    unanswered_session_targets,
)


class GoldLabelStorage:
    """Thin wrapper bundling the storage helpers behind a class facade.

    Operators and tests can either call the module-level helpers directly
    (``insert_session``, ``insert_label``, ...) or instantiate this class to
    keep a connection handle around. v1 keeps both surfaces equivalent.
    """

    def __init__(self, conn) -> None:  # type: ignore[no-untyped-def]
        self.conn = conn

    def insert_session(self, **kwargs) -> str:  # type: ignore[no-untyped-def]
        return insert_session(self.conn, **kwargs)

    def insert_label(self, **kwargs) -> str:  # type: ignore[no-untyped-def]
        return insert_label(self.conn, **kwargs)

    def mark_session_completed(self, session_id: str) -> None:
        mark_session_completed(self.conn, session_id)

    def list_sessions(self, *, state: str | None = None) -> list[Session]:
        return list_sessions(self.conn, state=state)


__all__ = [
    "ENGRAM_GOLD_ACTIVE_LEARNING_THRESHOLD",
    "ENGRAM_GOLD_COOLDOWN_GOAL_DAYS",
    "ENGRAM_GOLD_COOLDOWN_IDENTITY_DAYS",
    "ENGRAM_GOLD_COOLDOWN_MOOD_DAYS",
    "ENGRAM_GOLD_COOLDOWN_PREFERENCE_DAYS",
    "ENGRAM_GOLD_COOLDOWN_PROJECT_STATUS_DAYS",
    "ENGRAM_GOLD_COOLDOWN_RELATIONSHIP_DAYS",
    "ENGRAM_GOLD_COOLDOWN_TASK_DAYS",
    "GoldLabelSampler",
    "GoldLabelSamplerError",
    "GoldLabelStorage",
    "GoldLabelStorageError",
    "GoldLabelVerdictError",
    "INTERVIEW_TEMPLATE_PATH_BELIEF_V1",
    "INTERVIEW_TEMPLATE_PATH_CLAIM_V1",
    "INTERVIEW_TEMPLATE_VERSION_BELIEF_V1",
    "INTERVIEW_TEMPLATE_VERSION_CLAIM_V1",
    "InterviewAgent",
    "InterviewError",
    "RATIONALE_CHAR_LIMIT",
    "SAMPLER_ID",
    "SAMPLER_VERSION",
    "SampledTarget",
    "Session",
    "SessionTarget",
    "VALID_VERDICTS",
    "build_strata_key",
    "cooldown_days_for",
    "get_active_learning_signal_version",
    "insert_active_learning_event",
    "insert_label",
    "insert_session",
    "insert_session_targets",
    "list_session_targets",
    "list_sessions",
    "load_session_target",
    "mark_session_completed",
    "session_target_to_sampled",
    "unanswered_session_targets",
]
