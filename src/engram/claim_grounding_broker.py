"""Local RFC 0053 claim-grounding broker boundary."""

from __future__ import annotations

from collections.abc import Mapping, MutableSequence
from dataclasses import dataclass, field
from typing import Protocol

import psycopg

from engram.claim_grounding import (
    CLAIM_GROUNDING_BROKER_VERSION,
    NETWORK_FETCH_MODE,
    ClaimGroundingRequest,
    ClaimGroundingResponse,
    ClaimGroundingSchemaError,
    ground_claim_entity_locally,
    network_broker_dispatch_payload,
    validate_grounding_request,
    validate_grounding_response,
)
from engram.claim_grounding_runtime import (
    ClaimGroundingRuntimeError,
    record_claim_grounding_grant,
    record_claim_grounding_grant_use,
    record_claim_grounding_network_dispatch_attempt,
    record_claim_grounding_request,
    record_claim_grounding_response,
    verify_claim_grounding_grant_for_dispatch,
)


class ClaimGroundingNetworkAdapter(Protocol):
    """Explicit adapter for granted claim-grounding network dispatches."""

    def __call__(self, dispatch_payload: Mapping[str, object]) -> Mapping[str, object]: ...


@dataclass(frozen=True)
class DeferredClaimGroundingDispatch:
    """Recorded network-granted miss that was not sent to a live adapter."""

    request_id: str
    dispatch_payload: Mapping[str, object]


@dataclass
class ClaimGroundingBroker:
    """Resolve claim-grounding requests through local lookup and explicit adapters."""

    conn: psycopg.Connection
    network_adapter: ClaimGroundingNetworkAdapter | None = None
    local_limit: int = 5
    created_at: str | None = None
    persist_sidecars: bool = False
    deferred_dispatches: MutableSequence[DeferredClaimGroundingDispatch] = field(
        default_factory=list
    )

    def handle(self, payload: Mapping[str, object]) -> ClaimGroundingResponse:
        """Validate and resolve one claim-grounding request payload."""
        request = validate_grounding_request(payload)
        local_response = ground_claim_entity_locally(
            self.conn,
            request,
            limit=self.local_limit,
            created_at=self.created_at,
        )
        if local_response.candidates or NETWORK_FETCH_MODE not in request.allowed_modes:
            self._record_request_sidecars(request)
            self._record_response_sidecar(request, local_response)
            return local_response

        dispatch_payload = network_broker_dispatch_payload(request)
        if self.network_adapter is None:
            self._record_request_sidecars(request)
            self._record_skipped_dispatch_sidecars(request)
            self.deferred_dispatches.append(
                DeferredClaimGroundingDispatch(
                    request_id=request.request_id,
                    dispatch_payload=dispatch_payload,
                )
            )
            self._record_response_sidecar(request, local_response)
            return local_response

        self._verify_persisted_grant_before_network(request)
        adapter_response = validate_grounding_response(self.network_adapter(dispatch_payload))
        if adapter_response.request_id != request.request_id:
            raise ClaimGroundingSchemaError(
                "network adapter response request_id does not match claim-grounding request"
            )
        self._record_succeeded_dispatch_sidecars(request)
        self._record_response_sidecar(request, adapter_response)
        return adapter_response

    def _verify_persisted_grant_before_network(self, request: ClaimGroundingRequest) -> None:
        if not self.persist_sidecars:
            raise ClaimGroundingRuntimeError(
                "live claim-grounding network dispatch requires persisted sidecars"
            )
        verify_claim_grounding_grant_for_dispatch(
            self.conn,
            request,
            target=_first_network_target(request),
        )

    def _record_request_sidecars(self, request: ClaimGroundingRequest) -> None:
        if not self.persist_sidecars:
            return
        record_claim_grounding_request(self.conn, request)
        if request.network_grant is not None:
            record_claim_grounding_grant(self.conn, request)

    def _record_skipped_dispatch_sidecars(self, request: ClaimGroundingRequest) -> None:
        if not self.persist_sidecars:
            return
        record_claim_grounding_grant_use(
            self.conn,
            request,
            use_kind="verified",
            payload={"broker_decision": "network_adapter_unavailable"},
        )
        record_claim_grounding_network_dispatch_attempt(
            self.conn,
            request,
            broker_version=CLAIM_GROUNDING_BROKER_VERSION,
            target=_first_network_target(request),
            status="skipped",
            error_code="network_adapter_unavailable",
        )

    def _record_succeeded_dispatch_sidecars(self, request: ClaimGroundingRequest) -> None:
        if not self.persist_sidecars:
            return
        record_claim_grounding_grant_use(
            self.conn,
            request,
            use_kind="verified",
            payload={"broker_decision": "network_adapter_invoked"},
        )
        record_claim_grounding_network_dispatch_attempt(
            self.conn,
            request,
            broker_version=CLAIM_GROUNDING_BROKER_VERSION,
            target=_first_network_target(request),
            status="succeeded",
        )

    def _record_response_sidecar(
        self,
        request: ClaimGroundingRequest,
        response: ClaimGroundingResponse,
    ) -> None:
        if not self.persist_sidecars:
            return
        record_claim_grounding_response(self.conn, request, response)


def handle_claim_grounding_request(
    conn: psycopg.Connection,
    payload: Mapping[str, object],
    *,
    network_adapter: ClaimGroundingNetworkAdapter | None = None,
    deferred_dispatches: MutableSequence[DeferredClaimGroundingDispatch] | None = None,
    local_limit: int = 5,
    created_at: str | None = None,
    persist_sidecars: bool = False,
) -> ClaimGroundingResponse:
    """Resolve one request without granting ambient network access."""
    broker = ClaimGroundingBroker(
        conn=conn,
        network_adapter=network_adapter,
        local_limit=local_limit,
        created_at=created_at,
        persist_sidecars=persist_sidecars,
        deferred_dispatches=deferred_dispatches if deferred_dispatches is not None else [],
    )
    return broker.handle(payload)


def _first_network_target(request: ClaimGroundingRequest) -> str:
    if request.network_grant is None:
        raise ClaimGroundingSchemaError("network dispatch requires network_grant")
    return request.network_grant.allowed_network_targets[0]
