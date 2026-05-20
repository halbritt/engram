from __future__ import annotations

from dataclasses import replace

from engram.policy import (
    CAPABILITY_EXPORT_SENSITIVE,
    CAPABILITY_READ_CROSS_CORPUS,
    CAPABILITY_READ_CROSS_TENANT,
    CAPABILITY_READ_SENSITIVE,
    POLICY_ACTIONS,
    POLICY_REASON_CODES,
    PolicyActor,
    PolicyDecision,
    PolicyRequest,
    decide_local_release,
    decide_policy,
)


def _request(**overrides: object) -> PolicyRequest:
    actor = PolicyActor(
        actor_id="worker-f-test",
        tenant_id="striatum",
        corpus_id="striatum",
        capabilities=frozenset(),
    )
    base = PolicyRequest(
        actor=actor,
        tenant_id="striatum",
        corpus_id="striatum",
        purpose="context",
        privacy_tier=1,
        sensitivity_class="routine_project",
        source_kind="striatum",
        target_surface="context_for",
        privacy_tier_ceiling=1,
    )
    return replace(base, **overrides)


def test_tier_two_is_withheld_from_tier_one_surface() -> None:
    decision = decide_policy(_request(privacy_tier=2, privacy_tier_ceiling=1))

    assert decision == PolicyDecision("withhold", "privacy_tier_exceeded")


def test_local_release_helper_uses_same_policy_contract() -> None:
    decision = decide_local_release(
        privacy_tier=2,
        privacy_tier_ceiling=1,
        target_surface="external_export",
        purpose="phase3_interview_export",
        source_kind="gold_label",
    )

    assert decision == PolicyDecision("withhold", "privacy_tier_exceeded")


def test_cite_only_sensitivity_does_not_release_body_to_context_surface() -> None:
    decision = decide_policy(
        _request(sensitivity_class="third_party_communication", target_surface="context_for")
    )

    assert decision == PolicyDecision("cite_only", "sensitivity_cite_only")


def test_cite_only_sensitivity_does_not_release_body_to_packet_surface() -> None:
    decision = decide_policy(
        _request(sensitivity_class="third_party_communication", target_surface="packet")
    )

    assert decision == PolicyDecision("cite_only", "sensitivity_cite_only")


def test_high_risk_sensitivity_is_withheld_without_sensitive_capability() -> None:
    decision = decide_policy(
        _request(sensitivity_class="health", target_surface="context_for")
    )

    assert decision == PolicyDecision("withhold", "sensitivity_withheld")


def test_sensitive_review_surface_allows_body_with_capability() -> None:
    actor = PolicyActor(
        actor_id="reviewer",
        tenant_id="striatum",
        corpus_id="striatum",
        capabilities=frozenset({CAPABILITY_READ_SENSITIVE}),
    )

    decision = decide_policy(
        _request(actor=actor, sensitivity_class="health", target_surface="local_review")
    )

    assert decision == PolicyDecision("allow", "allowed")


def test_secret_reference_exports_redacted_when_export_capability_present() -> None:
    actor = PolicyActor(
        actor_id="exporter",
        tenant_id="striatum",
        corpus_id="striatum",
        capabilities=frozenset({CAPABILITY_EXPORT_SENSITIVE}),
    )

    decision = decide_policy(
        _request(
            actor=actor,
            sensitivity_class="credential_or_secret_reference",
            target_surface="external_export",
        )
    )

    assert decision == PolicyDecision("redact", "secret_redacted")


def test_cross_tenant_defaults_fail_closed() -> None:
    decision = decide_policy(_request(tenant_id="personal", corpus_id="personal"))

    assert decision == PolicyDecision("deny", "cross_tenant_denied")


def test_cross_tenant_same_corpus_allowed_when_capability_is_present() -> None:
    actor = PolicyActor(
        actor_id="cross-tenant",
        tenant_id="striatum",
        corpus_id="shared",
        capabilities=frozenset({CAPABILITY_READ_CROSS_TENANT}),
    )

    decision = decide_policy(
        _request(actor=actor, tenant_id="personal", corpus_id="shared")
    )

    assert decision == PolicyDecision("allow", "allowed")


def test_cross_tenant_cross_corpus_requires_both_capabilities() -> None:
    actor = PolicyActor(
        actor_id="cross-tenant-only",
        tenant_id="striatum",
        corpus_id="striatum",
        capabilities=frozenset({CAPABILITY_READ_CROSS_TENANT}),
    )

    decision = decide_policy(
        _request(actor=actor, tenant_id="personal", corpus_id="personal")
    )

    assert decision == PolicyDecision("deny", "cross_corpus_denied")


def test_cross_tenant_cross_corpus_allowed_with_both_capabilities() -> None:
    actor = PolicyActor(
        actor_id="cross-boundary",
        tenant_id="striatum",
        corpus_id="striatum",
        capabilities=frozenset({CAPABILITY_READ_CROSS_TENANT, CAPABILITY_READ_CROSS_CORPUS}),
    )

    decision = decide_policy(
        _request(actor=actor, tenant_id="personal", corpus_id="personal")
    )

    assert decision == PolicyDecision("allow", "allowed")


def test_cross_corpus_defaults_fail_closed() -> None:
    decision = decide_policy(_request(corpus_id="secondary"))

    assert decision == PolicyDecision("deny", "cross_corpus_denied")


def test_cross_corpus_allowed_when_capability_is_present() -> None:
    actor = PolicyActor(
        actor_id="cross-corpus",
        tenant_id="striatum",
        corpus_id="striatum",
        capabilities=frozenset({CAPABILITY_READ_CROSS_CORPUS}),
    )

    decision = decide_policy(_request(actor=actor, corpus_id="secondary"))

    assert decision == PolicyDecision("allow", "allowed")


def test_no_ad_hoc_reason_strings_or_actions_leak_out() -> None:
    decisions = [
        decide_policy(_request()),
        decide_policy(_request(privacy_tier=2)),
        decide_policy(_request(sensitivity_class="health")),
        decide_policy(_request(sensitivity_class="third_party_communication")),
        decide_policy(_request(tenant_id="personal", corpus_id="personal")),
        decide_policy(_request(corpus_id="secondary")),
    ]

    for decision in decisions:
        assert decision.action in POLICY_ACTIONS
        assert decision.reason_code in POLICY_REASON_CODES
        assert set(decision.to_json()) == {"action", "reason_code"}
