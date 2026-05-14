"""Shared Origin and Sec-Fetch guard for local operator web surfaces."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol
from urllib.parse import urlsplit

from fastapi import HTTPException

DEFAULT_ALLOWED_ORIGIN_HOSTS: tuple[str, ...] = ("127.0.0.1", "localhost")
DEFAULT_ALLOWED_SCHEMES: tuple[str, ...] = ("http",)
DEFAULT_ALLOWED_SEC_FETCH_SITES: tuple[str, ...] = ("same-origin",)


class RequestLike(Protocol):
    """Minimal request shape needed by the shared Origin guard."""

    @property
    def headers(self) -> Mapping[str, str]:
        """HTTP headers, case-insensitive for Starlette/FastAPI requests."""


def expected_origin_patterns(
    *, allowed_hosts: tuple[str, ...] = DEFAULT_ALLOWED_ORIGIN_HOSTS, bound_port: int | None = None
) -> tuple[str, ...]:
    """Return user-facing expected Origin patterns."""
    port = str(bound_port) if bound_port is not None else "<bound-port>"
    return tuple(f"http://{host}:{port}" for host in allowed_hosts)


def request_host_port(request: RequestLike) -> int | None:
    """Return the numeric port from the request Host header."""
    host_header = request.headers.get("host", "")
    if not host_header:
        return None
    try:
        return urlsplit(f"//{host_header}").port
    except ValueError:
        return None


def require_origin(
    request: RequestLike,
    *,
    allowed_hosts: tuple[str, ...] = DEFAULT_ALLOWED_ORIGIN_HOSTS,
    bound_port: int | None = None,
    allowed_schemes: tuple[str, ...] = DEFAULT_ALLOWED_SCHEMES,
    require_sec_fetch_site: bool = True,
    allowed_sec_fetch_sites: tuple[str, ...] = DEFAULT_ALLOWED_SEC_FETCH_SITES,
) -> None:
    """Enforce a loopback-style Origin and Sec-Fetch-Site policy."""
    expected = expected_origin_patterns(allowed_hosts=allowed_hosts, bound_port=bound_port)
    origin = request.headers.get("origin")
    if origin is None:
        _raise_origin_mismatch(expected)

    try:
        parsed_origin = urlsplit(origin)
    except ValueError as exc:
        raise _origin_mismatch(expected) from exc

    normalized_hosts = tuple(host.lower().rstrip(".") for host in allowed_hosts)
    origin_host = (parsed_origin.hostname or "").lower().rstrip(".")
    target_port = bound_port if bound_port is not None else request_host_port(request)

    if (
        parsed_origin.scheme not in allowed_schemes
        or origin_host not in normalized_hosts
        or target_port is None
        or parsed_origin.port != target_port
        or parsed_origin.path not in ("", "/")
    ):
        _raise_origin_mismatch(expected)

    sec_fetch_site = request.headers.get("sec-fetch-site")
    if require_sec_fetch_site and sec_fetch_site not in allowed_sec_fetch_sites:
        raise HTTPException(
            status_code=403,
            detail={
                "error": "origin_mismatch",
                "expected": [f"sec-fetch-site={site}" for site in allowed_sec_fetch_sites],
            },
        )


def _origin_mismatch(expected: tuple[str, ...]) -> HTTPException:
    return HTTPException(
        status_code=403,
        detail={"error": "origin_mismatch", "expected": list(expected)},
    )


def _raise_origin_mismatch(expected: tuple[str, ...]) -> None:
    raise _origin_mismatch(expected)
