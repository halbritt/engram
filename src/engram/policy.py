"""Central deterministic policy decisions for local memory release surfaces."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

CAPABILITY_READ_CROSS_TENANT = "memory.read_cross_tenant"
CAPABILITY_READ_CROSS_CORPUS = "memory.read_cross_corpus"
CAPABILITY_READ_SENSITIVE = "memory.read_sensitive"
CAPABILITY_EXPORT_SENSITIVE = "memory.export_sensitive"
LOCAL_POLICY_TENANT_ID = "local"
LOCAL_POLICY_CORPUS_ID = "local"

PolicyAction = Literal["allow", "redact", "withhold", "cite_only", "deny"]
ReasonCode = Literal[
    "allowed",
    "privacy_tier_exceeded",
    "cross_tenant_denied",
    "cross_corpus_denied",
    "sensitivity_cite_only",
    "sensitivity_withheld",
    "secret_redacted",
]

POLICY_ACTIONS: frozenset[str] = frozenset(
    {"allow", "redact", "withhold", "cite_only", "deny"}
)
POLICY_REASON_CODES: frozenset[str] = frozenset(
    {
        "allowed",
        "privacy_tier_exceeded",
        "cross_tenant_denied",
        "cross_corpus_denied",
        "sensitivity_cite_only",
        "sensitivity_withheld",
        "secret_redacted",
    }
)

SENSITIVITY_CITE_ONLY_CLASSES: frozenset[str] = frozenset(
    {
        "personal_private",
        "third_party_communication",
        "calendar_contact",
        "behavioral_activity",
        "raw_media",
    }
)
SENSITIVITY_WITHHOLD_CLASSES: frozenset[str] = frozenset(
    {
        "exact_location",
        "health",
        "biometric",
        "finance",
    }
)
SENSITIVITY_SECRET_CLASSES: frozenset[str] = frozenset(
    {"credential_or_secret_reference"}
)

CITE_ONLY_SURFACES: frozenset[str] = frozenset(
    {"assistant_context", "context_for", "packet", "mcp_packet"}
)
RAW_RELEASE_SURFACES: frozenset[str] = frozenset(
    {"review", "local_review", "audit", "operator_audit"}
)
EXPORT_SURFACES: frozenset[str] = frozenset({"export", "external_export"})


@dataclass(frozen=True)
class PolicyActor:
    """Local caller scope and capabilities used for release decisions."""

    actor_id: str
    tenant_id: str
    corpus_id: str
    capabilities: frozenset[str] = frozenset()


@dataclass(frozen=True)
class PolicyRequest:
    """One candidate release decision for a memory item."""

    actor: PolicyActor
    tenant_id: str
    corpus_id: str
    purpose: str
    privacy_tier: int
    sensitivity_class: str
    source_kind: str
    target_surface: str
    privacy_tier_ceiling: int


@dataclass(frozen=True)
class PolicyDecision:
    """Closed action and reason emitted by the policy module."""

    action: PolicyAction
    reason_code: ReasonCode

    def to_json(self) -> dict[str, str]:
        """Return the stable external decision shape."""
        return {"action": self.action, "reason_code": self.reason_code}


def decide_local_release(
    *,
    privacy_tier: int,
    privacy_tier_ceiling: int,
    target_surface: str,
    purpose: str,
    sensitivity_class: str = "routine_project",
    source_kind: str = "local",
    actor_id: str = "local-operator",
    capabilities: frozenset[str] = frozenset(),
    tenant_id: str = LOCAL_POLICY_TENANT_ID,
    corpus_id: str = LOCAL_POLICY_CORPUS_ID,
) -> PolicyDecision:
    """Build a same-tenant local policy request for legacy release surfaces."""
    actor = PolicyActor(
        actor_id=actor_id,
        tenant_id=tenant_id,
        corpus_id=corpus_id,
        capabilities=capabilities,
    )
    request = PolicyRequest(
        actor=actor,
        tenant_id=tenant_id,
        corpus_id=corpus_id,
        purpose=purpose,
        privacy_tier=privacy_tier,
        sensitivity_class=sensitivity_class,
        source_kind=source_kind,
        target_surface=target_surface,
        privacy_tier_ceiling=privacy_tier_ceiling,
    )
    return decide_policy(request)


def decide_policy(request: PolicyRequest) -> PolicyDecision:
    """Return the deterministic policy decision for one candidate item."""
    boundary_decision = _decide_boundary(request)
    if boundary_decision is not None:
        return boundary_decision

    if int(request.privacy_tier) > int(request.privacy_tier_ceiling):
        return PolicyDecision("withhold", "privacy_tier_exceeded")

    sensitivity_decision = _decide_sensitivity(request)
    if sensitivity_decision is not None:
        return sensitivity_decision

    return PolicyDecision("allow", "allowed")


def _decide_boundary(request: PolicyRequest) -> PolicyDecision | None:
    actor = request.actor
    if request.tenant_id != actor.tenant_id:
        if CAPABILITY_READ_CROSS_TENANT not in actor.capabilities:
            return PolicyDecision("deny", "cross_tenant_denied")
        if (
            request.corpus_id != actor.corpus_id
            and CAPABILITY_READ_CROSS_CORPUS not in actor.capabilities
        ):
            return PolicyDecision("deny", "cross_corpus_denied")
        return None
    if (
        request.corpus_id != actor.corpus_id
        and CAPABILITY_READ_CROSS_CORPUS not in actor.capabilities
    ):
        return PolicyDecision("deny", "cross_corpus_denied")
    return None


def _decide_sensitivity(request: PolicyRequest) -> PolicyDecision | None:
    if request.sensitivity_class in SENSITIVITY_SECRET_CLASSES:
        if CAPABILITY_EXPORT_SENSITIVE in request.actor.capabilities:
            return PolicyDecision("redact", "secret_redacted")
        return PolicyDecision("withhold", "sensitivity_withheld")

    if request.sensitivity_class in SENSITIVITY_WITHHOLD_CLASSES:
        if _can_release_sensitive_body(request):
            return None
        return PolicyDecision("withhold", "sensitivity_withheld")

    if request.sensitivity_class in SENSITIVITY_CITE_ONLY_CLASSES:
        if request.target_surface in CITE_ONLY_SURFACES:
            return PolicyDecision("cite_only", "sensitivity_cite_only")
        if _can_release_sensitive_body(request):
            return None
        return PolicyDecision("withhold", "sensitivity_withheld")

    return None


def _can_release_sensitive_body(request: PolicyRequest) -> bool:
    if request.target_surface in RAW_RELEASE_SURFACES:
        return CAPABILITY_READ_SENSITIVE in request.actor.capabilities
    if request.target_surface in EXPORT_SURFACES:
        return CAPABILITY_EXPORT_SENSITIVE in request.actor.capabilities
    return False
