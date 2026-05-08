"""Pure-python tests for the RFC 0021 sampler primitives.

No live DB; the sampler is exercised against a mock connection that returns
fixture rows for ``claims`` / ``current_beliefs`` / ``gold_labels``.
"""

from __future__ import annotations

import importlib
from datetime import datetime, timedelta, timezone
from typing import Any

import pytest


from engram.interview import sampler as sampler_module
from engram.interview.sampler import (
    GoldLabelSampler,
    build_strata_key,
    cooldown_days_for,
)


def _utc(year: int, month: int, day: int) -> datetime:
    return datetime(year, month, day, tzinfo=timezone.utc)


def test_build_strata_key_confidence_bands() -> None:
    now = _utc(2026, 5, 8)
    cases = [
        (0.0, "0.0-0.2"),
        (0.19, "0.0-0.2"),
        (0.2, "0.2-0.4"),
        (0.39, "0.2-0.4"),
        (0.4, "0.4-0.6"),
        (0.59, "0.4-0.6"),
        (0.6, "0.6-0.8"),
        (0.79, "0.6-0.8"),
        (0.8, "0.8-1.0"),
        (1.0, "0.8-1.0"),
    ]
    for confidence, expected in cases:
        conf_band, _recency = build_strata_key("preference", confidence, now, now)
        assert conf_band == expected, f"confidence={confidence}"


def test_build_strata_key_recency_bands() -> None:
    now = _utc(2026, 5, 8)
    cases = [
        (timedelta(days=0), "<7d"),
        (timedelta(days=6, hours=23), "<7d"),
        (timedelta(days=7), "<30d"),
        (timedelta(days=29), "<30d"),
        (timedelta(days=30), "<90d"),
        (timedelta(days=89), "<90d"),
        (timedelta(days=90), "<365d"),
        (timedelta(days=364), "<365d"),
        (timedelta(days=365), ">=365d"),
        (timedelta(days=400), ">=365d"),
    ]
    for delta, expected in cases:
        observed = now - delta
        _conf, recency_band = build_strata_key("preference", 0.5, observed, now)
        assert recency_band == expected, f"delta={delta}"


def test_cooldown_days_for_known_classes() -> None:
    assert cooldown_days_for("goal") == sampler_module.ENGRAM_GOLD_COOLDOWN_GOAL_DAYS
    assert cooldown_days_for("task") == sampler_module.ENGRAM_GOLD_COOLDOWN_TASK_DAYS
    assert cooldown_days_for("mood") == sampler_module.ENGRAM_GOLD_COOLDOWN_MOOD_DAYS
    assert (
        cooldown_days_for("preference")
        == sampler_module.ENGRAM_GOLD_COOLDOWN_PREFERENCE_DAYS
    )
    assert (
        cooldown_days_for("relationship")
        == sampler_module.ENGRAM_GOLD_COOLDOWN_RELATIONSHIP_DAYS
    )
    assert (
        cooldown_days_for("identity")
        == sampler_module.ENGRAM_GOLD_COOLDOWN_IDENTITY_DAYS
    )
    assert (
        cooldown_days_for("project_status")
        == sampler_module.ENGRAM_GOLD_COOLDOWN_PROJECT_STATUS_DAYS
    )


def test_cooldown_env_var_overrides_apply_at_module_top(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ENGRAM_GOLD_COOLDOWN_GOAL_DAYS", "21")
    monkeypatch.setenv("ENGRAM_GOLD_COOLDOWN_MOOD_DAYS", "1")
    reloaded = importlib.reload(sampler_module)
    try:
        assert reloaded.ENGRAM_GOLD_COOLDOWN_GOAL_DAYS == 21
        assert reloaded.ENGRAM_GOLD_COOLDOWN_MOOD_DAYS == 1
        assert reloaded.cooldown_days_for("goal") == 21
        assert reloaded.cooldown_days_for("mood") == 1
    finally:
        # Reset for downstream tests in the same session.
        monkeypatch.delenv("ENGRAM_GOLD_COOLDOWN_GOAL_DAYS", raising=False)
        monkeypatch.delenv("ENGRAM_GOLD_COOLDOWN_MOOD_DAYS", raising=False)
        importlib.reload(sampler_module)


# ----- mock conn -----


class _Result:
    def __init__(self, rows: list[tuple[Any, ...]]) -> None:
        self._rows = rows

    def fetchall(self) -> list[tuple[Any, ...]]:
        return list(self._rows)


class MockConn:
    """Mock psycopg connection returning fixture rows for the sampler queries."""

    def __init__(
        self,
        *,
        claim_rows: list[tuple[Any, ...]] | None = None,
        belief_rows: list[tuple[Any, ...]] | None = None,
        last_seen_rows: list[tuple[Any, ...]] | None = None,
    ) -> None:
        self.claim_rows = claim_rows or []
        self.belief_rows = belief_rows or []
        self.last_seen_rows = last_seen_rows or []
        self.queries: list[str] = []

    def execute(self, query: str, params: tuple[Any, ...] = ()) -> _Result:
        self.queries.append(query)
        text = query.strip().lower()
        if "from claims" in text:
            return _Result(self.claim_rows)
        if "from current_beliefs" in text or "from beliefs" in text:
            return _Result(self.belief_rows)
        if "from gold_labels" in text:
            return _Result(self.last_seen_rows)
        return _Result([])


def _claim_pool_row(target_id: str, *, observed: datetime, confidence: float = 0.7) -> tuple[Any, ...]:
    return (
        target_id,
        "preference",
        confidence,
        observed,
        "extract.v1.d000",
        "extract-model.v1.d000",
        "extract-profile.v1.d000",
        1,
    )


def _belief_pool_row(target_id: str, *, observed: datetime, confidence: float = 0.6) -> tuple[Any, ...]:
    return (
        target_id,
        "project_status",
        confidence,
        observed,
        "cons.v1.d000",
        "cons-model.v1.d000",
        "accepted",
        1,
    )


def test_sampler_seed_42_is_deterministic_across_calls() -> None:
    now = _utc(2026, 5, 8)
    rows = [
        _claim_pool_row(f"00000000-0000-0000-0000-00000000000{i:x}", observed=now)
        for i in range(8)
    ]
    conn1 = MockConn(claim_rows=rows)
    conn2 = MockConn(claim_rows=rows)
    s1 = GoldLabelSampler(conn1, seed=42, now=now)  # type: ignore[arg-type]
    s2 = GoldLabelSampler(conn2, seed=42, now=now)  # type: ignore[arg-type]
    out1 = s1.sample(5)
    out2 = s2.sample(5)
    assert [t.target_id for t in out1] == [t.target_id for t in out2]
    assert len(out1) == 5


def test_sampler_different_seeds_produce_different_orders() -> None:
    now = _utc(2026, 5, 8)
    rows = [
        _claim_pool_row(f"00000000-0000-0000-0000-00000000000{i:x}", observed=now)
        for i in range(8)
    ]
    conn1 = MockConn(claim_rows=rows)
    conn2 = MockConn(claim_rows=rows)
    out1 = GoldLabelSampler(conn1, seed=1, now=now).sample(5)  # type: ignore[arg-type]
    out2 = GoldLabelSampler(conn2, seed=99, now=now).sample(5)  # type: ignore[arg-type]
    # Seeds 1 vs 99 over 8 elements with shuffle should differ on at least one slot.
    assert [t.target_id for t in out1] != [t.target_id for t in out2]


def test_sampler_skip_verdicts_do_not_gate_cooldown() -> None:
    now = _utc(2026, 5, 8)
    target_id = "11111111-1111-1111-1111-111111111111"
    pool = [_claim_pool_row(target_id, observed=now)]

    # Note: _last_blocking_label_at filters out skip rows in SQL, so the mock
    # returns NO rows when skip is the only verdict — emulating the real
    # WHERE verdict <> 'skip'.
    conn = MockConn(claim_rows=pool, last_seen_rows=[])
    out = GoldLabelSampler(conn, seed=7, now=now).sample(1)  # type: ignore[arg-type]
    assert len(out) == 1
    assert out[0].target_id == target_id


def test_sampler_recent_blocking_verdict_filters_target() -> None:
    now = _utc(2026, 5, 8)
    target_id = "22222222-2222-2222-2222-222222222222"
    blocked_at = now - timedelta(days=1)  # well within preference cooldown (30d)
    pool = [_claim_pool_row(target_id, observed=now)]
    conn = MockConn(
        claim_rows=pool,
        last_seen_rows=[("claim", target_id, blocked_at)],
    )
    out = GoldLabelSampler(conn, seed=0, now=now).sample(1)  # type: ignore[arg-type]
    assert out == []


def test_sampler_ignore_cooldown_surfaces_blocked_target() -> None:
    now = _utc(2026, 5, 8)
    target_id = "33333333-3333-3333-3333-333333333333"
    blocked_at = now - timedelta(days=1)
    pool = [_claim_pool_row(target_id, observed=now)]
    conn = MockConn(
        claim_rows=pool,
        last_seen_rows=[("claim", target_id, blocked_at)],
    )
    out = GoldLabelSampler(
        conn,  # type: ignore[arg-type]
        seed=0,
        ignore_cooldown=True,
        now=now,
    ).sample(1)
    assert len(out) == 1
    assert out[0].target_id == target_id


def test_sampler_stamps_active_learning_signal_when_provided() -> None:
    now = _utc(2026, 5, 8)
    target_id = "44444444-4444-4444-4444-444444444444"
    pool = [_claim_pool_row(target_id, observed=now)]
    conn = MockConn(claim_rows=pool)
    out = GoldLabelSampler(
        conn,  # type: ignore[arg-type]
        seed=0,
        active_learning_signal_version="rfc0018.reviewer.v1",
        now=now,
    ).sample(1)
    assert len(out) == 1
    assert out[0].active_learning_signal_version == "rfc0018.reviewer.v1"


def test_sampler_no_active_learning_signal_by_default() -> None:
    now = _utc(2026, 5, 8)
    pool = [_claim_pool_row("55555555-5555-5555-5555-555555555555", observed=now)]
    conn = MockConn(claim_rows=pool)
    out = GoldLabelSampler(conn, seed=0, now=now).sample(1)  # type: ignore[arg-type]
    assert len(out) == 1
    assert out[0].active_learning_signal_version is None


def test_sampler_each_call_emits_a_new_candidate_pool_snapshot_id() -> None:
    now = _utc(2026, 5, 8)
    pool = [
        _claim_pool_row(f"66666666-6666-6666-6666-66666666666{i:x}", observed=now)
        for i in range(2)
    ]
    conn = MockConn(claim_rows=pool)
    sampler = GoldLabelSampler(conn, seed=3, now=now)  # type: ignore[arg-type]
    out_a = sampler.sample(2)
    out_b = sampler.sample(2)
    snap_a = {t.candidate_pool_snapshot_id for t in out_a}
    snap_b = {t.candidate_pool_snapshot_id for t in out_b}
    assert len(snap_a) == 1
    assert len(snap_b) == 1
    assert snap_a != snap_b
