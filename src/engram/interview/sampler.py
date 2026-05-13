"""Stratified gold-label sampler with seeded RNG (RFC 0021 § Sampler).

Implements the v1 contract:

* Source view: ``current_beliefs`` (D077) by default; ``include_superseded``
  opts back into ``beliefs`` for adversarial sweeps.
* Strata: ``stability_class`` x ``conf_band`` x ``recency_band``, plus
  ``belief_status`` for beliefs.
* Cooldowns: per-stability-class via ``ENGRAM_GOLD_COOLDOWN_<CLASS>_DAYS``
  env vars, applied against the latest non-skip ``gold_labels.answered_at``.
* Active-learning bias is opt-in: enabled only when
  ``active_learning_signal_version`` is provided. v1 stamps the version onto
  every emitted row but does not bias selection (sample order remains
  stratified random).
* Each ``sample()`` call generates a single ``candidate_pool_snapshot_id``
  (UUID) so replays are anchored.

The pure helper :func:`build_strata_key` returns the (conf_band, recency_band)
tuple for a (confidence, observed_at, now) triple — testable without DB.
"""

from __future__ import annotations

import os
import random
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any  # noqa: F401  # used for psycopg row typing

import psycopg

from engram.interview.errors import GoldLabelSamplerError


ENGRAM_GOLD_COOLDOWN_GOAL_DAYS = int(os.environ.get("ENGRAM_GOLD_COOLDOWN_GOAL_DAYS", 14))
ENGRAM_GOLD_COOLDOWN_TASK_DAYS = int(os.environ.get("ENGRAM_GOLD_COOLDOWN_TASK_DAYS", 7))
ENGRAM_GOLD_COOLDOWN_MOOD_DAYS = int(os.environ.get("ENGRAM_GOLD_COOLDOWN_MOOD_DAYS", 3))
ENGRAM_GOLD_COOLDOWN_PREFERENCE_DAYS = int(
    os.environ.get("ENGRAM_GOLD_COOLDOWN_PREFERENCE_DAYS", 30)
)
ENGRAM_GOLD_COOLDOWN_RELATIONSHIP_DAYS = int(
    os.environ.get("ENGRAM_GOLD_COOLDOWN_RELATIONSHIP_DAYS", 60)
)
ENGRAM_GOLD_COOLDOWN_IDENTITY_DAYS = int(
    os.environ.get("ENGRAM_GOLD_COOLDOWN_IDENTITY_DAYS", 90)
)
ENGRAM_GOLD_COOLDOWN_PROJECT_STATUS_DAYS = int(
    os.environ.get("ENGRAM_GOLD_COOLDOWN_PROJECT_STATUS_DAYS", 30)
)

ENGRAM_GOLD_ACTIVE_LEARNING_THRESHOLD = int(
    os.environ.get("ENGRAM_GOLD_ACTIVE_LEARNING_THRESHOLD", 500)
)
ENGRAM_GOLD_REASK_CAP = int(os.environ.get("ENGRAM_GOLD_REASK_CAP", 3))

SAMPLER_ID = "stratified"
SAMPLER_VERSION = "stratified.v1.d079.initial"

# Verdicts that gate cooldown calculation. ``skip`` is cooldown-free per RFC.
COOLDOWN_VERDICTS: frozenset[str] = frozenset(
    {"true", "false", "stale", "unsupported", "unsure"}
)


def cooldown_days_for(stability_class: str) -> int:
    """Return the configured ``(target, any verdict)`` cooldown for a class."""
    table = {
        "goal": ENGRAM_GOLD_COOLDOWN_GOAL_DAYS,
        "task": ENGRAM_GOLD_COOLDOWN_TASK_DAYS,
        "mood": ENGRAM_GOLD_COOLDOWN_MOOD_DAYS,
        "preference": ENGRAM_GOLD_COOLDOWN_PREFERENCE_DAYS,
        "relationship": ENGRAM_GOLD_COOLDOWN_RELATIONSHIP_DAYS,
        "identity": ENGRAM_GOLD_COOLDOWN_IDENTITY_DAYS,
        "project_status": ENGRAM_GOLD_COOLDOWN_PROJECT_STATUS_DAYS,
    }
    return table.get(stability_class, 14)


def build_strata_key(
    stability_class: str,
    confidence: float,
    observed_at: datetime,
    now: datetime,
) -> tuple[str, str]:
    """Return ``(conf_band, recency_band)`` for one target, per RFC buckets.

    Confidence boundaries: ``[0.0, 0.2)``, ``[0.2, 0.4)``, ``[0.4, 0.6)``,
    ``[0.6, 0.8)``, ``[0.8, 1.0]``. The 1.0 endpoint is inclusive.
    Recency boundaries: ``<7d``, ``<30d``, ``<90d``, ``<365d``, ``>=365d``.
    """
    if confidence < 0.0 or confidence > 1.0:
        raise GoldLabelSamplerError(f"confidence out of range: {confidence}")
    if confidence < 0.2:
        conf_band = "0.0-0.2"
    elif confidence < 0.4:
        conf_band = "0.2-0.4"
    elif confidence < 0.6:
        conf_band = "0.4-0.6"
    elif confidence < 0.8:
        conf_band = "0.6-0.8"
    else:
        conf_band = "0.8-1.0"

    # stability_class is consumed for parity with the RFC strata cross-product;
    # v1 does not produce per-class recency variants.
    _ = stability_class

    if observed_at.tzinfo is None:
        observed_at = observed_at.replace(tzinfo=timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    delta = now - observed_at
    if delta < timedelta(days=7):
        recency_band = "<7d"
    elif delta < timedelta(days=30):
        recency_band = "<30d"
    elif delta < timedelta(days=90):
        recency_band = "<90d"
    elif delta < timedelta(days=365):
        recency_band = "<365d"
    else:
        recency_band = ">=365d"
    return conf_band, recency_band


@dataclass(frozen=True)
class SampledTarget:
    """One sampled target row, ready for the agent to render and record."""

    target_kind: str
    target_id: str
    stability_class: str
    confidence: float
    observed_at: datetime
    conf_band: str
    recency_band: str
    belief_status: str | None
    candidate_pool_snapshot_id: str
    active_learning_signal_version: str | None
    extraction_prompt_version: str | None
    extraction_model_version: str | None
    consolidation_prompt_version: str | None
    consolidation_model_version: str | None
    request_profile_version: str
    payload: dict[str, Any] = field(default_factory=dict)

    def version_triple(self) -> dict[str, str]:
        """Return the version triple for storage.insert_label."""
        triple: dict[str, str] = {"request_profile_version": self.request_profile_version}
        if self.target_kind == "claim":
            assert self.extraction_prompt_version is not None
            assert self.extraction_model_version is not None
            triple["extraction_prompt_version"] = self.extraction_prompt_version
            triple["extraction_model_version"] = self.extraction_model_version
        else:
            assert self.consolidation_prompt_version is not None
            assert self.consolidation_model_version is not None
            triple["consolidation_prompt_version"] = self.consolidation_prompt_version
            triple["consolidation_model_version"] = self.consolidation_model_version
        return triple


@dataclass(frozen=True)
class CandidatePoolRow:
    """One row in the candidate pool before cooldown filtering."""

    target_kind: str
    target_id: str
    stability_class: str
    confidence: float
    observed_at: datetime
    extraction_prompt_version: str | None
    extraction_model_version: str | None
    consolidation_prompt_version: str | None
    consolidation_model_version: str | None
    request_profile_version: str
    belief_status: str | None
    privacy_tier: int


ReaskKey = tuple[str, str, str | None, str | None, str | None, str | None, str]


class GoldLabelSampler:
    """Stratified sampler with seeded RNG.

    Reads ``current_beliefs`` by default. Falls through gracefully if the
    materialized view is missing or empty in a test environment.
    """

    def __init__(
        self,
        conn: psycopg.Connection,
        *,
        seed: int,
        strata_weights: dict[str, Any] | None = None,
        include_superseded: bool = False,
        ignore_cooldown: bool = False,
        active_learning_signal_version: str | None = None,
        ignore_reask_cap: bool = False,
        now: datetime | None = None,
    ) -> None:
        self.conn = conn
        self.seed = seed
        self.strata_weights = strata_weights or {}
        self.include_superseded = include_superseded
        self.ignore_cooldown = ignore_cooldown
        self.active_learning_signal_version = active_learning_signal_version
        self.ignore_reask_cap = ignore_reask_cap
        self._now = now or datetime.now(timezone.utc)
        self._rng = random.Random(seed)

    def _fetch_pool(self) -> list[CandidatePoolRow]:
        rows: list[CandidatePoolRow] = []
        # claims: extraction triple, no belief_status
        claim_rows = self.conn.execute(
            """
            SELECT
                id::text,
                stability_class,
                confidence,
                extracted_at,
                extraction_prompt_version,
                extraction_model_version,
                request_profile_version,
                privacy_tier
            FROM claims
            """,
        ).fetchall()
        for row in claim_rows:
            rows.append(
                CandidatePoolRow(
                    target_kind="claim",
                    target_id=row[0],
                    stability_class=row[1],
                    confidence=float(row[2]),
                    observed_at=row[3],
                    extraction_prompt_version=row[4],
                    extraction_model_version=row[5],
                    consolidation_prompt_version=None,
                    consolidation_model_version=None,
                    request_profile_version=row[6],
                    belief_status=None,
                    privacy_tier=row[7],
                )
            )

        # beliefs: consolidation triple, has belief_status. Read current_beliefs
        # by default; fall through to beliefs when --include-superseded is set.
        belief_source = "current_beliefs"
        belief_request_profile = "interview.v1.d079.initial"
        if self.include_superseded:
            belief_source = "beliefs"
        try:
            belief_rows = self.conn.execute(
                f"""
                SELECT
                    id::text,
                    stability_class,
                    confidence,
                    observed_at,
                    prompt_version,
                    model_version,
                    status,
                    privacy_tier
                FROM {belief_source}
                """,
            ).fetchall()
        except psycopg.Error:
            # current_beliefs view may not be refreshed yet in fresh schemas.
            belief_rows = []
        for row in belief_rows:
            rows.append(
                CandidatePoolRow(
                    target_kind="belief",
                    target_id=row[0],
                    stability_class=row[1],
                    confidence=float(row[2]),
                    observed_at=row[3],
                    extraction_prompt_version=None,
                    extraction_model_version=None,
                    consolidation_prompt_version=row[4],
                    consolidation_model_version=row[5],
                    request_profile_version=belief_request_profile,
                    belief_status=row[6],
                    privacy_tier=row[7],
                )
            )
        return rows

    def _last_blocking_label_at(self) -> dict[tuple[str, str], datetime]:
        """Return ``(target_kind, target_id) -> latest non-skip answered_at``."""
        rows = self.conn.execute(
            """
            SELECT
                target_kind,
                target_id::text,
                MAX(answered_at)
            FROM gold_labels
            WHERE verdict <> 'skip'
            GROUP BY target_kind, target_id
            """,
        ).fetchall()
        result: dict[tuple[str, str], datetime] = {}
        for row in rows:
            result[(row[0], row[1])] = row[2]
        return result

    def _cooldown_filter(
        self,
        pool: list[CandidatePoolRow],
        last_seen: dict[tuple[str, str], datetime],
    ) -> list[CandidatePoolRow]:
        if self.ignore_cooldown:
            return pool
        kept: list[CandidatePoolRow] = []
        for row in pool:
            blocked_until = last_seen.get((row.target_kind, row.target_id))
            if blocked_until is None:
                kept.append(row)
                continue
            cooldown = timedelta(days=cooldown_days_for(row.stability_class))
            if self._now - blocked_until >= cooldown:
                kept.append(row)
        return kept

    def _label_counts_by_target_version(self) -> dict[ReaskKey, int]:
        """Return non-skip label counts by target and exact version triple."""
        rows = self.conn.execute(
            """
            SELECT
                target_kind,
                target_id::text,
                extraction_prompt_version,
                extraction_model_version,
                consolidation_prompt_version,
                consolidation_model_version,
                request_profile_version,
                count(*)
            FROM gold_labels
            WHERE verdict <> 'skip'
            GROUP BY
                target_kind,
                target_id,
                extraction_prompt_version,
                extraction_model_version,
                consolidation_prompt_version,
                consolidation_model_version,
                request_profile_version
            """
        ).fetchall()
        counts: dict[ReaskKey, int] = {}
        for row in rows:
            key = (
                row[0],
                row[1],
                row[2],
                row[3],
                row[4],
                row[5],
                row[6],
            )
            counts[key] = int(row[7])
        return counts

    def _reask_key(self, row: CandidatePoolRow) -> ReaskKey:
        return (
            row.target_kind,
            row.target_id,
            row.extraction_prompt_version,
            row.extraction_model_version,
            row.consolidation_prompt_version,
            row.consolidation_model_version,
            row.request_profile_version,
        )

    def _reask_cap_filter(
        self,
        pool: list[CandidatePoolRow],
        counts: dict[ReaskKey, int],
    ) -> list[CandidatePoolRow]:
        if self.ignore_reask_cap or ENGRAM_GOLD_REASK_CAP <= 0:
            return pool
        return [
            row
            for row in pool
            if counts.get(self._reask_key(row), 0) < ENGRAM_GOLD_REASK_CAP
        ]

    def _strata_filter(self, pool: list[CandidatePoolRow]) -> list[CandidatePoolRow]:
        if not self.strata_weights:
            return pool
        allowed_keys = {"stability_class", "conf_band", "recency_band", "belief_status"}
        unknown = sorted(set(self.strata_weights) - allowed_keys)
        if unknown:
            raise GoldLabelSamplerError(f"unknown strata filter key(s): {', '.join(unknown)}")

        filtered: list[CandidatePoolRow] = []
        for row in pool:
            conf_band, recency_band = build_strata_key(
                row.stability_class,
                row.confidence,
                row.observed_at,
                self._now,
            )
            values = {
                "stability_class": row.stability_class,
                "conf_band": conf_band,
                "recency_band": recency_band,
                "belief_status": row.belief_status,
            }
            if all(values[key] == str(value) for key, value in self.strata_weights.items()):
                filtered.append(row)
        return filtered

    def sample(self, n: int) -> list[SampledTarget]:
        if n < 0:
            raise GoldLabelSamplerError(f"sample n must be >= 0, got {n}")
        snapshot_id = str(uuid.uuid4())
        try:
            pool = self._fetch_pool()
        except psycopg.Error as exc:
            raise GoldLabelSamplerError(f"failed to read candidate pool: {exc}") from exc

        last_seen = {} if self.ignore_cooldown else self._last_blocking_label_at()
        filtered = self._cooldown_filter(pool, last_seen)
        filtered = self._reask_cap_filter(filtered, self._label_counts_by_target_version())
        filtered = self._strata_filter(filtered)
        if not filtered:
            return []

        # Stratify by (stability_class, conf_band, recency_band, belief_status).
        # v1 implementation: deterministic shuffle then take n. Strata weights
        # are stamped onto the session row but the v1 sampler does not yet
        # rebalance pulls — RFC 0021 § Sampler v1 explicitly defers deeper
        # introspection to v1.1.
        order = list(range(len(filtered)))
        self._rng.shuffle(order)
        selected: list[SampledTarget] = []
        for idx in order[:n]:
            row = filtered[idx]
            conf_band, recency_band = build_strata_key(
                row.stability_class, row.confidence, row.observed_at, self._now
            )
            selected.append(
                SampledTarget(
                    target_kind=row.target_kind,
                    target_id=row.target_id,
                    stability_class=row.stability_class,
                    confidence=row.confidence,
                    observed_at=row.observed_at,
                    conf_band=conf_band,
                    recency_band=recency_band,
                    belief_status=row.belief_status,
                    candidate_pool_snapshot_id=snapshot_id,
                    active_learning_signal_version=self.active_learning_signal_version,
                    extraction_prompt_version=row.extraction_prompt_version,
                    extraction_model_version=row.extraction_model_version,
                    consolidation_prompt_version=row.consolidation_prompt_version,
                    consolidation_model_version=row.consolidation_model_version,
                    request_profile_version=row.request_profile_version,
                    payload={"privacy_tier": row.privacy_tier},
                )
            )
        return selected
