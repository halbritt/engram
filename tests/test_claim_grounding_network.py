from __future__ import annotations

import json
import socket
from collections.abc import Callable, Mapping
from urllib.error import URLError
from urllib.request import Request

import pytest

from engram.claim_grounding import validate_grounding_response
from engram.claim_grounding_network import (
    CLAIM_GROUNDING_TAVILY_ENDPOINT,
    ClaimGroundingHttpSearchAdapter,
    ClaimGroundingNetworkFetchError,
    ClaimGroundingNetworkPolicyError,
    ClaimGroundingSearchEndpointConfig,
    ClaimGroundingTavilySearchAdapter,
    ClaimGroundingTavilySearchConfig,
    configured_claim_grounding_network_adapter,
)


class _FakeResponse:
    def __init__(self, body: bytes, *, status: int = 200) -> None:
        self.body = body
        self.status = status

    def __enter__(self) -> _FakeResponse:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: object | None,
    ) -> bool | None:
        return None

    def read(self, size: int = -1) -> bytes:
        if size < 0:
            return self.body
        return self.body[:size]

    def getcode(self) -> int:
        return self.status


def test_configured_adapter_is_disabled_when_endpoint_unset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_resolve(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("disabled adapter must not resolve or open network targets")

    monkeypatch.setattr(
        "engram.claim_grounding_network.CLAIM_GROUNDING_SEARCH_ENDPOINT",
        "",
    )
    monkeypatch.setattr(socket, "getaddrinfo", fail_resolve)

    assert configured_claim_grounding_network_adapter() is None


def test_configured_tavily_adapter_is_disabled_when_api_key_unset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_resolve(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("disabled Tavily adapter must not resolve network targets")

    monkeypatch.setattr(
        "engram.claim_grounding_network.CLAIM_GROUNDING_SEARCH_PROVIDER",
        "tavily",
    )
    monkeypatch.setattr(
        "engram.claim_grounding_network.CLAIM_GROUNDING_TAVILY_API_KEY",
        "",
    )
    monkeypatch.setattr(socket, "getaddrinfo", fail_resolve)

    assert configured_claim_grounding_network_adapter() is None


def test_configured_tavily_adapter_uses_env_key_without_opening_network(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "engram.claim_grounding_network.CLAIM_GROUNDING_SEARCH_PROVIDER",
        "tavily",
    )
    monkeypatch.setattr(
        "engram.claim_grounding_network.CLAIM_GROUNDING_TAVILY_API_KEY",
        "test-key",
    )
    monkeypatch.setattr(socket, "getaddrinfo", _tavily_getaddrinfo)

    adapter = configured_claim_grounding_network_adapter(opener=_failing_opener)

    assert isinstance(adapter, ClaimGroundingTavilySearchAdapter)
    assert repr(adapter.config).find("test-key") == -1


def test_adapter_uses_get_with_fixed_query_param_and_sanitizes_rows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen_requests: list[Request] = []

    def fake_getaddrinfo(
        host: str,
        port: int | None,
        *,
        type: int,
    ) -> list[tuple[int, int, int, str, tuple[str, int]]]:
        assert host == "example.com"
        assert port is None
        assert type == socket.SOCK_STREAM
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 0))]

    def fake_open(request: Request, *, timeout: float) -> _FakeResponse:
        seen_requests.append(request)
        assert timeout == 1.5
        return _FakeResponse(
            json.dumps(
                {
                    "results": [
                        {
                            "title": " Fixture Product \n",
                            "url": "https://example.com/product",
                            "content": " Public result text. \x00 With spacing. ",
                            "ignored": "not surfaced",
                        }
                    ]
                }
            ).encode("utf-8")
        )

    monkeypatch.setattr(socket, "getaddrinfo", fake_getaddrinfo)
    adapter = ClaimGroundingHttpSearchAdapter(
        config=ClaimGroundingSearchEndpointConfig(
            endpoint_url="http://localhost:8080/search",
            timeout_seconds=1.5,
            max_bytes=4096,
            max_results=3,
        ),
        opener=fake_open,
    )

    rows = adapter.raw_result_rows(_dispatch_payload())

    assert len(rows) == 1
    assert rows[0].title == "Fixture Product"
    assert rows[0].url == "https://example.com/product"
    assert rows[0].excerpt == "Public result text. With spacing."
    assert rows[0].row_id.startswith("network-search-")
    assert len(seen_requests) == 1
    assert seen_requests[0].get_method() == "GET"
    assert seen_requests[0].full_url == "http://localhost:8080/search?q=Fixture+Product"


def test_tavily_adapter_posts_exact_query_and_sanitizes_rows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen_requests: list[Request] = []

    def fake_open(request: Request, *, timeout: float) -> _FakeResponse:
        seen_requests.append(request)
        assert timeout == 1.5
        return _FakeResponse(
            json.dumps(
                {
                    "answer": "ignored",
                    "results": [
                        {
                            "title": " Fixture Product ",
                            "url": "https://example.com/product",
                            "content": "Public Tavily result.",
                            "raw_content": "ignored raw content",
                        }
                    ],
                }
            ).encode("utf-8")
        )

    monkeypatch.setattr(socket, "getaddrinfo", _tavily_getaddrinfo)
    adapter = ClaimGroundingTavilySearchAdapter(
        config=ClaimGroundingTavilySearchConfig(
            api_key="test-key",
            timeout_seconds=1.5,
            max_bytes=4096,
            max_results=3,
        ),
        opener=fake_open,
    )

    response = validate_grounding_response(adapter(_dispatch_payload()))

    assert response.status == "resolved"
    assert response.broker_version == "claim_grounding.network_tavily_search.v1"
    assert response.candidates[0].source_url == "https://example.com/product"
    assert len(seen_requests) == 1
    request = seen_requests[0]
    assert request.get_method() == "POST"
    assert request.full_url == CLAIM_GROUNDING_TAVILY_ENDPOINT
    assert request.get_header("Authorization") == "Bearer test-key"
    body = request.data
    assert body is not None
    assert b"test-key" not in body
    payload = json.loads(body.decode("utf-8"))
    assert payload == {
        "include_answer": False,
        "include_favicon": False,
        "include_images": False,
        "include_raw_content": False,
        "max_results": 3,
        "query": "Fixture Product",
        "search_depth": "basic",
        "topic": "general",
    }


def test_tavily_adapter_trims_overlong_excerpt_below_validator_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    overlong_content = "lorem ipsum dolor sit amet " * 80

    def fake_open(request: Request, *, timeout: float) -> _FakeResponse:
        return _FakeResponse(
            json.dumps(
                {
                    "results": [
                        {
                            "title": "Fixture Product",
                            "url": "https://example.com/product",
                            "content": overlong_content,
                        }
                    ],
                }
            ).encode("utf-8")
        )

    monkeypatch.setattr(socket, "getaddrinfo", _tavily_getaddrinfo)
    adapter = ClaimGroundingTavilySearchAdapter(
        config=ClaimGroundingTavilySearchConfig(api_key="test-key"),
        opener=fake_open,
    )

    response = validate_grounding_response(adapter(_dispatch_payload()))

    assert response.status == "resolved"
    assert len(response.candidates[0].content_excerpt) <= 500


def test_tavily_adapter_redacts_api_key_from_transport_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_open(request: Request, *, timeout: float) -> _FakeResponse:
        raise URLError("provider failure for test-key")

    monkeypatch.setattr(socket, "getaddrinfo", _tavily_getaddrinfo)
    adapter = ClaimGroundingTavilySearchAdapter(
        config=ClaimGroundingTavilySearchConfig(api_key="test-key"),
        opener=fake_open,
    )

    with pytest.raises(ClaimGroundingNetworkFetchError) as exc_info:
        adapter.raw_result_rows(_dispatch_payload())

    assert "test-key" not in str(exc_info.value)
    assert "<redacted>" in str(exc_info.value)


def test_tavily_endpoint_is_fixed_to_official_api() -> None:
    with pytest.raises(ClaimGroundingNetworkPolicyError, match="Tavily endpoint"):
        ClaimGroundingTavilySearchConfig(
            endpoint_url="https://search.example.test/search",
            api_key="test-key",
        )


def test_adapter_rejects_extra_private_context_fields_before_http(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(socket, "getaddrinfo", _tavily_getaddrinfo)

    adapter = ClaimGroundingTavilySearchAdapter(
        config=ClaimGroundingTavilySearchConfig(api_key="test-key"),
        opener=_failing_opener,
    )
    payload = _dispatch_payload()
    payload["source_refs"] = [{"target_table": "messages", "target_id": "message-001"}]

    with pytest.raises(ClaimGroundingNetworkPolicyError, match="unsupported fields"):
        adapter.raw_result_rows(payload)


def test_adapter_response_payload_validates_after_sanitization(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(socket, "getaddrinfo", _public_getaddrinfo)
    adapter = ClaimGroundingHttpSearchAdapter(
        config=ClaimGroundingSearchEndpointConfig(
            endpoint_url="http://localhost:8080/search",
            max_bytes=4096,
            max_results=1,
        ),
        opener=_json_opener(
            {
                "results": [
                    {
                        "title": "Fixture Product",
                        "url": "https://example.com/product",
                        "content": "Public result text.",
                    }
                ]
            }
        ),
    )

    response = validate_grounding_response(adapter(_dispatch_payload()))

    assert response.status == "resolved"
    assert response.mode == "network_fetch"
    assert response.network_fetch == "performed_by_grounding_broker"
    assert response.candidates[0].source_url == "https://example.com/product"


@pytest.mark.parametrize(
    "endpoint_url",
    [
        "http://127.0.0.1:8080/search",
        "http://169.254.10.10/search",
        "http://10.0.0.5/search",
    ],
)
def test_endpoint_rejects_private_loopback_and_link_local_ips(endpoint_url: str) -> None:
    with pytest.raises(ClaimGroundingNetworkPolicyError, match="disallowed address"):
        ClaimGroundingSearchEndpointConfig(endpoint_url=endpoint_url)


def test_endpoint_rejects_hostnames_that_resolve_private(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def private_getaddrinfo(
        host: str,
        port: int | None,
        *,
        type: int,
    ) -> list[tuple[int, int, int, str, tuple[str, int]]]:
        assert host == "search.example.test"
        assert port is None
        assert type == socket.SOCK_STREAM
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("10.1.2.3", 0))]

    monkeypatch.setattr(socket, "getaddrinfo", private_getaddrinfo)

    with pytest.raises(ClaimGroundingNetworkPolicyError, match="disallowed address"):
        ClaimGroundingSearchEndpointConfig(endpoint_url="https://search.example.test/search")


def test_endpoint_allows_explicit_localhost_for_local_dev(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_resolve(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("explicit localhost endpoint should not require DNS")

    monkeypatch.setattr(socket, "getaddrinfo", fail_resolve)

    config = ClaimGroundingSearchEndpointConfig(
        endpoint_url="http://localhost:8080/search",
    )

    assert config.endpoint_url == "http://localhost:8080/search"


def test_dispatch_must_allow_internet_search_target_adapter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(socket, "getaddrinfo", _public_getaddrinfo)

    def fail_open(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("policy failure must happen before HTTP")

    adapter = ClaimGroundingHttpSearchAdapter(
        config=ClaimGroundingSearchEndpointConfig(
            endpoint_url="http://localhost:8080/search",
        ),
        opener=fail_open,
    )
    payload = _dispatch_payload()
    grant = dict(payload["network_grant"])
    grant["allowed_network_targets"] = ["public_dataset_api"]
    payload["network_grant"] = grant

    with pytest.raises(ClaimGroundingNetworkPolicyError, match="target adapter"):
        adapter.raw_result_rows(payload)


def test_dispatch_search_query_must_match_surface_form(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(socket, "getaddrinfo", _public_getaddrinfo)
    adapter = ClaimGroundingHttpSearchAdapter(
        config=ClaimGroundingSearchEndpointConfig(endpoint_url="http://localhost:8080/search"),
        opener=_json_opener({"results": []}),
    )
    payload = _dispatch_payload()
    grant = dict(payload["network_grant"])
    grant["search_query"] = "Fixture Product private context"
    payload["network_grant"] = grant

    with pytest.raises(ClaimGroundingNetworkPolicyError, match="surface_form"):
        adapter.raw_result_rows(payload)


@pytest.mark.parametrize("search_query", ["fixture product", " Fixture  Product "])
def test_dispatch_rejects_normalized_search_query_surface_form_mismatch(
    search_query: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(socket, "getaddrinfo", _public_getaddrinfo)
    adapter = ClaimGroundingHttpSearchAdapter(
        config=ClaimGroundingSearchEndpointConfig(endpoint_url="http://localhost:8080/search"),
        opener=_failing_opener,
    )
    payload = _dispatch_payload()
    grant = dict(payload["network_grant"])
    grant["search_query"] = search_query
    payload["network_grant"] = grant

    with pytest.raises(ClaimGroundingNetworkPolicyError, match="surface_form"):
        adapter.raw_result_rows(payload)


def test_result_rows_drop_private_result_urls(monkeypatch: pytest.MonkeyPatch) -> None:
    def mixed_getaddrinfo(
        host: str,
        port: int | None,
        *,
        type: int,
    ) -> list[tuple[int, int, int, str, tuple[str, int]]]:
        assert port is None
        assert type == socket.SOCK_STREAM
        if host == "example.com":
            return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 0))]
        if host == "private.example.test":
            return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("192.168.1.10", 0))]
        raise AssertionError(f"unexpected host {host}")

    monkeypatch.setattr(socket, "getaddrinfo", mixed_getaddrinfo)
    adapter = ClaimGroundingHttpSearchAdapter(
        config=ClaimGroundingSearchEndpointConfig(
            endpoint_url="http://localhost:8080/search",
            max_bytes=4096,
            max_results=5,
        ),
        opener=_json_opener(
            {
                "results": [
                    {
                        "title": "Private",
                        "url": "http://private.example.test/page",
                        "content": "Must be dropped.",
                    },
                    {
                        "title": "Public",
                        "url": "https://example.com/page",
                        "content": "May remain.",
                    },
                ]
            }
        ),
    )

    rows = adapter.raw_result_rows(_dispatch_payload())

    assert [row.title for row in rows] == ["Public"]


def test_adapter_enforces_response_byte_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(socket, "getaddrinfo", _public_getaddrinfo)
    adapter = ClaimGroundingHttpSearchAdapter(
        config=ClaimGroundingSearchEndpointConfig(
            endpoint_url="http://localhost:8080/search",
            max_bytes=1024,
        ),
        opener=lambda request, *, timeout: _FakeResponse(b"{" + (b" " * 1024)),
    )

    with pytest.raises(ClaimGroundingNetworkFetchError, match="exceeded"):
        adapter.raw_result_rows(_dispatch_payload())


def _json_opener(payload: Mapping[str, object]) -> Callable[[Request], _FakeResponse]:
    body = json.dumps(payload).encode("utf-8")

    def fake_open(request: Request, *, timeout: float) -> _FakeResponse:
        assert request.get_method() == "GET"
        assert timeout > 0
        return _FakeResponse(body)

    return fake_open


def _public_getaddrinfo(
    host: str,
    port: int | None,
    *,
    type: int,
) -> list[tuple[int, int, int, str, tuple[str, int]]]:
    assert host == "example.com"
    assert port is None
    assert type == socket.SOCK_STREAM
    return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 0))]


def _tavily_getaddrinfo(
    host: str,
    port: int | None,
    *,
    type: int,
) -> list[tuple[int, int, int, str, tuple[str, int]]]:
    assert port is None
    assert type == socket.SOCK_STREAM
    if host in {"api.tavily.com", "example.com"}:
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 0))]
    raise AssertionError(f"unexpected host {host}")


def _failing_opener(request: Request, *, timeout: float) -> _FakeResponse:
    raise AssertionError("test must not open a live network target")


def _dispatch_payload() -> dict[str, object]:
    return {
        "schema_version": "claim_grounding.network_dispatch.v1",
        "request_id": "req-001",
        "tenant_id": "personal",
        "corpus_id": "personal",
        "surface_form": "Fixture Product",
        "network_grant": {
            "grant_id": "grant-001",
            "granted_by": "operator",
            "granted_at": "2026-05-18T00:00:00Z",
            "expires_at": None,
            "purpose": "entity_grounding",
            "search_query": "Fixture Product",
            "query_text_class": "entity_surface_form",
            "query_privacy_tier": 1,
            "allowed_network_targets": ["internet_search"],
        },
        "requested_at": "2026-05-18T00:00:00Z",
    }
