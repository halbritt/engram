"""Disabled-by-default RFC 0053 HTTP/Tavily search adapter scaffold."""

from __future__ import annotations

import hashlib
import ipaddress
import json
import os
import socket
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Protocol, cast
from urllib.error import URLError
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from urllib.request import Request, urlopen

from engram.claim_grounding import (
    CLAIM_GROUNDING_NETWORK_DISPATCH_SCHEMA_VERSION,
    CLAIM_GROUNDING_RESPONSE_SCHEMA_VERSION,
    ClaimGroundingSchemaError,
)

CLAIM_GROUNDING_NETWORK_BROKER_VERSION = "claim_grounding.network_http_search.v1"
CLAIM_GROUNDING_TAVILY_NETWORK_BROKER_VERSION = "claim_grounding.network_tavily_search.v1"
CLAIM_GROUNDING_SEARCH_PROVIDER_GENERIC_HTTP = "generic_http"
CLAIM_GROUNDING_SEARCH_PROVIDER_TAVILY = "tavily"
CLAIM_GROUNDING_SEARCH_PROVIDER = os.environ.get(
    "ENGRAM_CLAIM_GROUNDING_SEARCH_PROVIDER",
    CLAIM_GROUNDING_SEARCH_PROVIDER_GENERIC_HTTP,
).strip().casefold()
CLAIM_GROUNDING_SEARCH_ENDPOINT = os.environ.get(
    "ENGRAM_CLAIM_GROUNDING_SEARCH_ENDPOINT",
    "",
).strip()
CLAIM_GROUNDING_TAVILY_ENDPOINT = "https://api.tavily.com/search"
CLAIM_GROUNDING_TAVILY_API_KEY = os.environ.get(
    "ENGRAM_CLAIM_GROUNDING_TAVILY_API_KEY",
    "",
).strip()
CLAIM_GROUNDING_TAVILY_SEARCH_DEPTH = os.environ.get(
    "ENGRAM_CLAIM_GROUNDING_TAVILY_SEARCH_DEPTH",
    "basic",
).strip().casefold()
CLAIM_GROUNDING_TAVILY_TOPIC = "general"
CLAIM_GROUNDING_SEARCH_TIMEOUT_SECONDS = float(
    os.environ.get("ENGRAM_CLAIM_GROUNDING_SEARCH_TIMEOUT_SECONDS", "3.0")
)
CLAIM_GROUNDING_SEARCH_MAX_BYTES = int(
    os.environ.get("ENGRAM_CLAIM_GROUNDING_SEARCH_MAX_BYTES", "65536")
)
CLAIM_GROUNDING_SEARCH_MAX_RESULTS = int(
    os.environ.get("ENGRAM_CLAIM_GROUNDING_SEARCH_MAX_RESULTS", "5")
)
CLAIM_GROUNDING_SEARCH_QUERY_PARAM = "q"
CLAIM_GROUNDING_SEARCH_TARGET_ADAPTER = "internet_search"
_TAVILY_SEARCH_DEPTHS = frozenset({"advanced", "basic", "fast", "ultra-fast"})
_NETWORK_DISPATCH_KEYS = frozenset(
    {
        "schema_version",
        "request_id",
        "tenant_id",
        "corpus_id",
        "surface_form",
        "network_grant",
        "requested_at",
    }
)
_MAX_TITLE_CHARS = 180
_MAX_EXCERPT_CHARS = 500


class ClaimGroundingNetworkError(RuntimeError):
    """Base error for claim-grounding network adapter failures."""


class ClaimGroundingNetworkDisabled(ClaimGroundingNetworkError):
    """Raised when a network adapter is requested without a configured endpoint."""


class ClaimGroundingNetworkPolicyError(ClaimGroundingNetworkError):
    """Raised when an endpoint, dispatch, or result violates adapter policy."""


class ClaimGroundingNetworkFetchError(ClaimGroundingNetworkError):
    """Raised when the configured endpoint cannot be fetched or parsed."""


class HttpResponse(Protocol):
    """Minimal response protocol used by urllib and tests."""

    def __enter__(self) -> HttpResponse: ...

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: object | None,
    ) -> bool | None: ...

    def read(self, size: int = -1) -> bytes: ...

    def getcode(self) -> int: ...


class UrlOpen(Protocol):
    """Callable shape for injected HTTP openers."""

    def __call__(self, request: Request, *, timeout: float) -> HttpResponse: ...


def _urlopen(request: Request, *, timeout: float) -> HttpResponse:
    return cast(HttpResponse, urlopen(request, timeout=timeout))


class ClaimGroundingConfiguredSearchAdapter(Protocol):
    """Common shape for configured broker-owned search adapters."""

    def raw_result_rows(
        self,
        dispatch_payload: Mapping[str, object],
    ) -> tuple[ClaimGroundingNetworkResultRow, ...]: ...

    def __call__(self, dispatch_payload: Mapping[str, object]) -> Mapping[str, object]: ...


@dataclass(frozen=True)
class ClaimGroundingSearchEndpointConfig:
    """Static network adapter configuration from local operator settings."""

    endpoint_url: str
    timeout_seconds: float = CLAIM_GROUNDING_SEARCH_TIMEOUT_SECONDS
    max_bytes: int = CLAIM_GROUNDING_SEARCH_MAX_BYTES
    max_results: int = CLAIM_GROUNDING_SEARCH_MAX_RESULTS
    target_adapter: str = CLAIM_GROUNDING_SEARCH_TARGET_ADAPTER

    def __post_init__(self) -> None:
        _validate_limits(
            timeout_seconds=self.timeout_seconds,
            max_bytes=self.max_bytes,
            max_results=self.max_results,
        )
        endpoint = _validated_endpoint_url(
            self.endpoint_url,
            reserved_query_keys=frozenset({CLAIM_GROUNDING_SEARCH_QUERY_PARAM}),
        )
        _assert_endpoint_host_allowed(endpoint)
        if self.target_adapter != CLAIM_GROUNDING_SEARCH_TARGET_ADAPTER:
            raise ClaimGroundingNetworkPolicyError(
                f'unsupported target adapter "{self.target_adapter}"'
            )


@dataclass(frozen=True)
class ClaimGroundingTavilySearchConfig:
    """Tavily adapter configuration from local operator settings."""

    endpoint_url: str = CLAIM_GROUNDING_TAVILY_ENDPOINT
    api_key: str = field(default=CLAIM_GROUNDING_TAVILY_API_KEY, repr=False)
    search_depth: str = CLAIM_GROUNDING_TAVILY_SEARCH_DEPTH
    timeout_seconds: float = CLAIM_GROUNDING_SEARCH_TIMEOUT_SECONDS
    max_bytes: int = CLAIM_GROUNDING_SEARCH_MAX_BYTES
    max_results: int = CLAIM_GROUNDING_SEARCH_MAX_RESULTS
    target_adapter: str = CLAIM_GROUNDING_SEARCH_TARGET_ADAPTER

    def __post_init__(self) -> None:
        _validate_limits(
            timeout_seconds=self.timeout_seconds,
            max_bytes=self.max_bytes,
            max_results=self.max_results,
        )
        if not self.api_key.strip():
            raise ClaimGroundingNetworkDisabled(
                "ENGRAM_CLAIM_GROUNDING_TAVILY_API_KEY is unset"
            )
        endpoint = _validated_endpoint_url(self.endpoint_url)
        if endpoint != CLAIM_GROUNDING_TAVILY_ENDPOINT:
            raise ClaimGroundingNetworkPolicyError(
                f"Tavily endpoint must be {CLAIM_GROUNDING_TAVILY_ENDPOINT}"
            )
        _assert_endpoint_host_allowed(endpoint)
        if self.search_depth not in _TAVILY_SEARCH_DEPTHS:
            raise ClaimGroundingNetworkPolicyError(
                f'unsupported Tavily search_depth "{self.search_depth}"'
            )
        if self.target_adapter != CLAIM_GROUNDING_SEARCH_TARGET_ADAPTER:
            raise ClaimGroundingNetworkPolicyError(
                f'unsupported target adapter "{self.target_adapter}"'
            )


@dataclass(frozen=True)
class ClaimGroundingNetworkResultRow:
    """Sanitized public search result row safe for local persistence."""

    row_id: str
    title: str
    url: str
    source_label: str
    excerpt: str
    content_hash: str
    rank: int

    def to_json(self) -> dict[str, object]:
        """Return the raw-result row payload."""
        return {
            "row_id": self.row_id,
            "title": self.title,
            "url": self.url,
            "source_label": self.source_label,
            "excerpt": self.excerpt,
            "content_hash": self.content_hash,
            "rank": self.rank,
        }

    def to_candidate_payload(self, *, search_query: str) -> dict[str, object]:
        """Return a candidate-shaped payload for later local evidence insertion."""
        return {
            "candidate_id": self.row_id,
            "entity_kind": "unknown",
            "canonical_label": self.title or search_query,
            "external_ids": [],
            "grounding_evidence_ids": [self.row_id],
            "source_url": self.url,
            "source_label": self.source_label,
            "content_hash": self.content_hash,
            "content_excerpt": self.excerpt or self.title,
            "confidence": 0.5,
            "stability": "public_search_result",
            "ambiguity_reasons": [],
        }


@dataclass(frozen=True)
class ClaimGroundingHttpSearchAdapter:
    """Constrained GET-only adapter for a configured local HTTP search endpoint."""

    config: ClaimGroundingSearchEndpointConfig
    opener: UrlOpen = _urlopen

    def raw_result_rows(
        self,
        dispatch_payload: Mapping[str, object],
    ) -> tuple[ClaimGroundingNetworkResultRow, ...]:
        """Fetch and sanitize raw public result rows for one network dispatch."""
        search_query = _search_query_from_dispatch(dispatch_payload, self.config.target_adapter)
        request = Request(
            _search_url(self.config.endpoint_url, search_query),
            method="GET",
            headers={"Accept": "application/json", "User-Agent": "engram-claim-grounding/1"},
        )
        body = self._read_response(request)
        return _parse_result_rows(body, max_results=self.config.max_results)

    def __call__(self, dispatch_payload: Mapping[str, object]) -> Mapping[str, object]:
        """Return a response-shaped payload for broker adapter injection."""
        rows = self.raw_result_rows(dispatch_payload)
        search_query = _search_query_from_dispatch(dispatch_payload, self.config.target_adapter)
        return _response_payload_from_rows(
            dispatch_payload,
            rows,
            search_query=search_query,
            broker_version=CLAIM_GROUNDING_NETWORK_BROKER_VERSION,
        )

    def _read_response(self, request: Request) -> bytes:
        return _read_http_response(
            self.opener,
            request,
            timeout_seconds=self.config.timeout_seconds,
            max_bytes=self.config.max_bytes,
        )


@dataclass(frozen=True)
class ClaimGroundingTavilySearchAdapter:
    """Constrained Tavily adapter for broker-owned internet search."""

    config: ClaimGroundingTavilySearchConfig
    opener: UrlOpen = _urlopen

    def raw_result_rows(
        self,
        dispatch_payload: Mapping[str, object],
    ) -> tuple[ClaimGroundingNetworkResultRow, ...]:
        """Fetch and sanitize Tavily result rows for one minimized dispatch."""
        search_query = _search_query_from_dispatch(dispatch_payload, self.config.target_adapter)
        request = Request(
            self.config.endpoint_url,
            data=_tavily_search_body(
                search_query=search_query,
                max_results=self.config.max_results,
                search_depth=self.config.search_depth,
            ),
            method="POST",
            headers={
                "Accept": "application/json",
                "Authorization": f"Bearer {self.config.api_key}",
                "Content-Type": "application/json",
                "User-Agent": "engram-claim-grounding/1",
            },
        )
        body = self._read_response(request)
        return _parse_result_rows(body, max_results=self.config.max_results)

    def __call__(self, dispatch_payload: Mapping[str, object]) -> Mapping[str, object]:
        """Return a response-shaped payload for broker adapter injection."""
        rows = self.raw_result_rows(dispatch_payload)
        search_query = _search_query_from_dispatch(dispatch_payload, self.config.target_adapter)
        return _response_payload_from_rows(
            dispatch_payload,
            rows,
            search_query=search_query,
            broker_version=CLAIM_GROUNDING_TAVILY_NETWORK_BROKER_VERSION,
        )

    def _read_response(self, request: Request) -> bytes:
        return _read_http_response(
            self.opener,
            request,
            timeout_seconds=self.config.timeout_seconds,
            max_bytes=self.config.max_bytes,
            secret_values=(self.config.api_key,),
        )


def configured_claim_grounding_network_adapter(
    *,
    opener: UrlOpen = _urlopen,
) -> ClaimGroundingConfiguredSearchAdapter | None:
    """Return the configured adapter, or None when network search is disabled."""
    if CLAIM_GROUNDING_SEARCH_PROVIDER == CLAIM_GROUNDING_SEARCH_PROVIDER_GENERIC_HTTP:
        if not CLAIM_GROUNDING_SEARCH_ENDPOINT:
            return None
        return ClaimGroundingHttpSearchAdapter(
            config=ClaimGroundingSearchEndpointConfig(
                endpoint_url=CLAIM_GROUNDING_SEARCH_ENDPOINT,
            ),
            opener=opener,
        )
    if CLAIM_GROUNDING_SEARCH_PROVIDER == CLAIM_GROUNDING_SEARCH_PROVIDER_TAVILY:
        if not CLAIM_GROUNDING_TAVILY_API_KEY:
            return None
        return ClaimGroundingTavilySearchAdapter(
            config=ClaimGroundingTavilySearchConfig(
                api_key=CLAIM_GROUNDING_TAVILY_API_KEY,
            ),
            opener=opener,
        )
    if not CLAIM_GROUNDING_SEARCH_PROVIDER:
        return None
    raise ClaimGroundingNetworkPolicyError(
        f'unsupported search provider "{CLAIM_GROUNDING_SEARCH_PROVIDER}"'
    )


def require_configured_claim_grounding_network_adapter(
    *,
    opener: UrlOpen = _urlopen,
) -> ClaimGroundingConfiguredSearchAdapter:
    """Return the configured adapter or fail without performing network I/O."""
    adapter = configured_claim_grounding_network_adapter(opener=opener)
    if adapter is None:
        raise ClaimGroundingNetworkDisabled(
            "claim-grounding network adapter is disabled or incomplete"
        )
    return adapter


def _validated_endpoint_url(
    endpoint_url: str,
    *,
    reserved_query_keys: frozenset[str] = frozenset(),
) -> str:
    parts = urlsplit(endpoint_url)
    if parts.scheme not in {"http", "https"}:
        raise ClaimGroundingNetworkPolicyError("search endpoint must use http or https")
    if not parts.netloc or parts.hostname is None:
        raise ClaimGroundingNetworkPolicyError("search endpoint must include a host")
    if parts.username is not None or parts.password is not None:
        raise ClaimGroundingNetworkPolicyError("search endpoint must not include credentials")
    if parts.fragment:
        raise ClaimGroundingNetworkPolicyError("search endpoint must not include a fragment")
    query_keys = {key for key, _value in parse_qsl(parts.query, keep_blank_values=True)}
    for query_key in reserved_query_keys:
        if query_key in query_keys:
            raise ClaimGroundingNetworkPolicyError(
                f'search endpoint must not predefine "{query_key}"'
            )
    return endpoint_url


def _search_url(endpoint_url: str, search_query: str) -> str:
    parts = urlsplit(endpoint_url)
    query_pairs = parse_qsl(parts.query, keep_blank_values=True)
    query_pairs.append((CLAIM_GROUNDING_SEARCH_QUERY_PARAM, search_query))
    return urlunsplit(
        (parts.scheme, parts.netloc, parts.path, urlencode(query_pairs), "")
    )


def _validate_limits(*, timeout_seconds: float, max_bytes: int, max_results: int) -> None:
    if timeout_seconds <= 0 or timeout_seconds > 15:
        raise ClaimGroundingNetworkPolicyError("timeout must be between 0 and 15 seconds")
    if max_bytes < 1024 or max_bytes > 1_048_576:
        raise ClaimGroundingNetworkPolicyError("max_bytes must be between 1024 and 1048576")
    if max_results < 1 or max_results > 20:
        raise ClaimGroundingNetworkPolicyError("max_results must be between 1 and 20")


def _tavily_search_body(
    *,
    search_query: str,
    max_results: int,
    search_depth: str,
) -> bytes:
    payload = {
        "query": search_query,
        "search_depth": search_depth,
        "max_results": max_results,
        "topic": CLAIM_GROUNDING_TAVILY_TOPIC,
        "include_answer": False,
        "include_raw_content": False,
        "include_images": False,
        "include_favicon": False,
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _read_http_response(
    opener: UrlOpen,
    request: Request,
    *,
    timeout_seconds: float,
    max_bytes: int,
    secret_values: tuple[str, ...] = (),
) -> bytes:
    try:
        with opener(request, timeout=timeout_seconds) as response:
            status = response.getcode()
            if status < 200 or status >= 300:
                raise ClaimGroundingNetworkFetchError(
                    f"search endpoint returned HTTP {status}"
                )
            body = response.read(max_bytes + 1)
    except URLError as exc:
        raise ClaimGroundingNetworkFetchError(
            _redact_secrets(str(exc), secret_values)
        ) from exc
    if len(body) > max_bytes:
        raise ClaimGroundingNetworkFetchError(
            f"search response exceeded {max_bytes} bytes"
        )
    return body


def _redact_secrets(value: str, secret_values: tuple[str, ...]) -> str:
    redacted = value
    for secret in secret_values:
        if secret:
            redacted = redacted.replace(secret, "<redacted>")
    return redacted


def _response_payload_from_rows(
    dispatch_payload: Mapping[str, object],
    rows: tuple[ClaimGroundingNetworkResultRow, ...],
    *,
    search_query: str,
    broker_version: str,
) -> Mapping[str, object]:
    if not rows:
        status = "not_found"
    elif len(rows) == 1:
        status = "resolved"
    else:
        status = "ambiguous"
    return {
        "schema_version": CLAIM_GROUNDING_RESPONSE_SCHEMA_VERSION,
        "request_id": _string_field(dispatch_payload, "request_id", prefix="dispatch"),
        "status": status,
        "mode": "network_fetch",
        "network_fetch": "performed_by_grounding_broker",
        "candidates": [
            row.to_candidate_payload(search_query=search_query) for row in rows
        ],
        "omissions": [],
        "broker_version": broker_version,
        "dataset_snapshots": [],
        "created_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
    }


def _search_query_from_dispatch(
    dispatch_payload: Mapping[str, object],
    target_adapter: str,
) -> str:
    extra_keys = set(dispatch_payload) - _NETWORK_DISPATCH_KEYS
    if extra_keys:
        names = ", ".join(sorted(str(key) for key in extra_keys))
        raise ClaimGroundingNetworkPolicyError(
            f"network dispatch contains unsupported fields: {names}"
        )
    schema_version = _string_field(dispatch_payload, "schema_version", prefix="dispatch")
    if schema_version != CLAIM_GROUNDING_NETWORK_DISPATCH_SCHEMA_VERSION:
        raise ClaimGroundingSchemaError(f'unsupported schema_version "{schema_version}"')
    surface_form = _string_field(dispatch_payload, "surface_form", prefix="dispatch")
    grant = _mapping_field(dispatch_payload, "network_grant", prefix="dispatch")
    search_query = _string_field(grant, "search_query", prefix="network_grant")
    query_text_class = _string_field(grant, "query_text_class", prefix="network_grant")
    if query_text_class != "entity_surface_form":
        raise ClaimGroundingNetworkPolicyError(
            'network adapter only accepts "entity_surface_form" queries'
        )
    if search_query != surface_form:
        raise ClaimGroundingNetworkPolicyError("search_query must match surface_form exactly")
    targets = _string_tuple(grant, "allowed_network_targets", prefix="network_grant")
    if target_adapter not in targets:
        raise ClaimGroundingNetworkPolicyError(
            f'network grant does not allow target adapter "{target_adapter}"'
        )
    return search_query


def _parse_result_rows(
    body: bytes,
    *,
    max_results: int,
) -> tuple[ClaimGroundingNetworkResultRow, ...]:
    try:
        payload = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ClaimGroundingNetworkFetchError("search endpoint did not return JSON") from exc
    if not isinstance(payload, Mapping):
        raise ClaimGroundingNetworkFetchError("search JSON root must be an object")
    raw_results = payload.get("results", [])
    if not isinstance(raw_results, list):
        raise ClaimGroundingNetworkFetchError('search JSON "results" must be an array')
    rows: list[ClaimGroundingNetworkResultRow] = []
    for raw_result in raw_results:
        if len(rows) >= max_results:
            break
        if not isinstance(raw_result, Mapping):
            continue
        row = _result_row(raw_result, rank=len(rows) + 1)
        if row is not None:
            rows.append(row)
    return tuple(rows)


def _result_row(
    raw_result: Mapping[object, object],
    *,
    rank: int,
) -> ClaimGroundingNetworkResultRow | None:
    title = _clean_text(_optional_text(raw_result.get("title")), max_chars=_MAX_TITLE_CHARS)
    url = _optional_text(raw_result.get("url"))
    excerpt = _clean_text(
        _optional_text(raw_result.get("content")) or _optional_text(raw_result.get("snippet")),
        max_chars=_MAX_EXCERPT_CHARS,
    )
    if url is None:
        return None
    if not _public_result_url_allowed(url):
        return None
    source_label = _source_label(url=url, title=title)
    row_hash_payload = {
        "title": title,
        "url": url,
        "source_label": source_label,
        "excerpt": excerpt,
    }
    content_hash = hashlib.sha256(
        json.dumps(row_hash_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return ClaimGroundingNetworkResultRow(
        row_id=f"network-search-{content_hash[:32]}",
        title=title or source_label,
        url=url,
        source_label=source_label,
        excerpt=excerpt or title or source_label,
        content_hash=content_hash,
        rank=rank,
    )


def _public_result_url_allowed(url: str) -> bool:
    try:
        parts = urlsplit(url)
        _assert_host_allowed(parts.hostname, allow_localhost=False)
    except ClaimGroundingNetworkPolicyError:
        return False
    return parts.scheme in {"http", "https"}


def _assert_endpoint_host_allowed(endpoint_url: str) -> None:
    parts = urlsplit(endpoint_url)
    _assert_host_allowed(parts.hostname, allow_localhost=parts.hostname == "localhost")


def _assert_host_allowed(hostname: str | None, *, allow_localhost: bool) -> None:
    if hostname is None:
        raise ClaimGroundingNetworkPolicyError("URL must include a hostname")
    normalized = hostname.strip("[]").casefold()
    if normalized == "localhost" and allow_localhost:
        return
    if normalized == "localhost":
        raise ClaimGroundingNetworkPolicyError("localhost is not allowed for result URLs")
    try:
        ip = ipaddress.ip_address(normalized)
    except ValueError:
        _assert_resolved_hostname_allowed(normalized)
        return
    _assert_ip_allowed(ip)


def _assert_resolved_hostname_allowed(hostname: str) -> None:
    try:
        infos = socket.getaddrinfo(hostname, None, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise ClaimGroundingNetworkPolicyError(f'could not resolve hostname "{hostname}"') from exc
    if not infos:
        raise ClaimGroundingNetworkPolicyError(f'could not resolve hostname "{hostname}"')
    for info in infos:
        sockaddr = info[4]
        if not sockaddr:
            raise ClaimGroundingNetworkPolicyError(f'could not resolve hostname "{hostname}"')
        _assert_ip_allowed(ipaddress.ip_address(str(sockaddr[0])))


def _assert_ip_allowed(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> None:
    if (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_unspecified
        or ip.is_multicast
        or ip.is_reserved
    ):
        raise ClaimGroundingNetworkPolicyError(
            f'host resolved to disallowed address "{ip}"'
        )


def _source_label(*, url: str, title: str) -> str:
    host = urlsplit(url).hostname or "search result"
    if title:
        return f"{title} ({host})"
    return host


def _clean_text(value: str | None, *, max_chars: int) -> str:
    if value is None:
        return ""
    cleaned = " ".join(value.replace("\x00", " ").split())
    if len(cleaned) <= max_chars:
        return cleaned
    return cleaned[: max_chars - 3].rstrip() + "..."


def _optional_text(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    if not value.strip():
        return None
    return value


def _mapping_field(
    payload: Mapping[str, object],
    key: str,
    *,
    prefix: str,
) -> Mapping[str, object]:
    value = payload.get(key)
    if not isinstance(value, Mapping):
        raise ClaimGroundingSchemaError(f'{prefix}."{key}" must be an object')
    if not all(isinstance(row_key, str) for row_key in value):
        raise ClaimGroundingSchemaError(f'{prefix}."{key}" keys must be strings')
    return value


def _string_field(payload: Mapping[str, object], key: str, *, prefix: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ClaimGroundingSchemaError(f'{prefix}."{key}" must be a non-empty string')
    return value


def _string_tuple(
    payload: Mapping[str, object],
    key: str,
    *,
    prefix: str,
) -> tuple[str, ...]:
    value = payload.get(key)
    if not isinstance(value, list):
        raise ClaimGroundingSchemaError(f'{prefix}."{key}" must be an array')
    rows: list[str] = []
    for index, row in enumerate(value):
        if not isinstance(row, str) or not row.strip():
            raise ClaimGroundingSchemaError(
                f'{prefix}."{key}[{index}]" must be a non-empty string'
            )
        rows.append(row)
    return tuple(rows)
