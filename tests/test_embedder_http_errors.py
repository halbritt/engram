"""Unit tests for embedder HTTP and helper error paths (RFC 0015 gap 4).

These tests cover ``OllamaEmbeddingClient``, ``http_json()``,
``vector_literal()``, and the embedding-shape validation that stands in for
"dimension-mismatch handling" inside the embedder. They do not touch the
database; the project's standard mocking pattern is
``monkeypatch.setattr(embedder, "http_json", fake_http)``.
"""

from __future__ import annotations

import io
import json
import urllib.error
from typing import Any

import pytest

from engram import embedder


# ---------------------------------------------------------------------------
# OllamaEmbeddingClient
# ---------------------------------------------------------------------------


def test_ollama_client_request_shape_and_response_capture(monkeypatch: pytest.MonkeyPatch) -> None:
    """Happy path: client posts to /api/embed with the right body and parses
    the ``embeddings`` array from the response."""

    captured: dict[str, Any] = {}

    def fake_http(
        method: str,
        url: str,
        *,
        payload: dict[str, Any] | None = None,
        timeout: int = 30,
    ) -> dict[str, Any]:
        captured["method"] = method
        captured["url"] = url
        captured["payload"] = payload
        captured["timeout"] = timeout
        return {"embeddings": [[0.1, 0.2, 0.3]]}

    monkeypatch.setattr(embedder, "http_json", fake_http)

    client = embedder.OllamaEmbeddingClient(base_url="http://127.0.0.1:11434")
    vectors = client.embed(["hello world"], model_version="nomic-embed-text:latest")

    assert vectors == [[0.1, 0.2, 0.3]]
    assert captured["method"] == "POST"
    assert captured["url"] == "http://127.0.0.1:11434/api/embed"
    assert captured["payload"] == {
        "model": "nomic-embed-text:latest",
        "input": ["hello world"],
    }
    assert captured["timeout"] == 120


def test_ollama_client_rejects_invalid_embeddings_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    """If Ollama returns the wrong shape (count mismatch), surface
    ``EmbeddingError``. This is the embedder's stand-in for "dimension /
    shape mismatch" handling."""

    def fake_http(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        # One input, two embeddings -> shape mismatch.
        return {"embeddings": [[0.1, 0.2], [0.3, 0.4]]}

    monkeypatch.setattr(embedder, "http_json", fake_http)

    client = embedder.OllamaEmbeddingClient(base_url="http://127.0.0.1:11434")
    with pytest.raises(embedder.EmbeddingError, match="invalid embeddings payload"):
        client.embed(["only one input"], model_version="m")


def test_ollama_client_rejects_empty_embedding_vector(monkeypatch: pytest.MonkeyPatch) -> None:
    """An embedding entry that is empty (zero-dimensional) is rejected — the
    closest existing analogue to dimension-mismatch detection."""

    def fake_http(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        return {"embeddings": [[]]}

    monkeypatch.setattr(embedder, "http_json", fake_http)

    client = embedder.OllamaEmbeddingClient(base_url="http://127.0.0.1:11434")
    with pytest.raises(embedder.EmbeddingError, match="empty or invalid"):
        client.embed(["x"], model_version="m")


def test_ollama_client_rejects_non_local_base_url() -> None:
    """``ensure_local_base_url`` is called from the constructor; non-local
    hosts must be rejected before any HTTP traffic occurs."""

    with pytest.raises(embedder.EmbeddingError, match="local-only"):
        embedder.OllamaEmbeddingClient(base_url="http://example.com:11434")


# ---------------------------------------------------------------------------
# http_json
# ---------------------------------------------------------------------------


def test_http_json_wraps_urlerror_as_embedding_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """``URLError`` (the umbrella for connection refused, DNS, socket
    timeouts surfaced by urllib) is wrapped in ``EmbeddingError``."""

    def raise_urlerror(*_args: Any, **_kwargs: Any) -> None:
        raise urllib.error.URLError("timed out")

    monkeypatch.setattr(embedder.urllib.request, "urlopen", raise_urlerror)

    with pytest.raises(embedder.EmbeddingError, match="local embedder request failed"):
        embedder.http_json("GET", "http://127.0.0.1:11434/api/version")


def test_http_json_wraps_http_4xx_response(monkeypatch: pytest.MonkeyPatch) -> None:
    """HTTPError (a subclass of URLError) for a 4xx response is wrapped."""

    def raise_http_error(*_args: Any, **_kwargs: Any) -> None:
        raise urllib.error.HTTPError(
            url="http://127.0.0.1:11434/api/embed",
            code=400,
            msg="Bad Request",
            hdrs=None,  # type: ignore[arg-type]
            fp=None,
        )

    monkeypatch.setattr(embedder.urllib.request, "urlopen", raise_http_error)

    with pytest.raises(embedder.EmbeddingError, match="local embedder request failed"):
        embedder.http_json(
            "POST",
            "http://127.0.0.1:11434/api/embed",
            payload={"model": "m", "input": ["x"]},
        )


def test_http_json_wraps_http_5xx_response(monkeypatch: pytest.MonkeyPatch) -> None:
    """HTTPError for a 5xx response is wrapped."""

    def raise_http_error(*_args: Any, **_kwargs: Any) -> None:
        raise urllib.error.HTTPError(
            url="http://127.0.0.1:11434/api/embed",
            code=500,
            msg="Internal Server Error",
            hdrs=None,  # type: ignore[arg-type]
            fp=None,
        )

    monkeypatch.setattr(embedder.urllib.request, "urlopen", raise_http_error)

    with pytest.raises(embedder.EmbeddingError, match="local embedder request failed"):
        embedder.http_json(
            "POST",
            "http://127.0.0.1:11434/api/embed",
            payload={"model": "m", "input": ["x"]},
        )


class _FakeResponse:
    """Minimal context-manager response double for ``urlopen``."""

    def __init__(self, body: bytes) -> None:
        self._body = body

    def __enter__(self) -> "_FakeResponse":
        return self

    def __exit__(self, *_exc: Any) -> None:
        return None

    def read(self) -> bytes:
        return self._body


def test_http_json_raises_on_malformed_json(monkeypatch: pytest.MonkeyPatch) -> None:
    """A non-JSON response body surfaces as ``EmbeddingError`` with the
    decoder's complaint embedded."""

    def fake_urlopen(*_args: Any, **_kwargs: Any) -> _FakeResponse:
        return _FakeResponse(b"not-json-at-all")

    monkeypatch.setattr(embedder.urllib.request, "urlopen", fake_urlopen)

    with pytest.raises(embedder.EmbeddingError, match="non-JSON response"):
        embedder.http_json("GET", "http://127.0.0.1:11434/api/version")


def test_http_json_raises_on_non_object_json(monkeypatch: pytest.MonkeyPatch) -> None:
    """JSON that decodes to a list (or other non-dict) is rejected."""

    def fake_urlopen(*_args: Any, **_kwargs: Any) -> _FakeResponse:
        return _FakeResponse(json.dumps([1, 2, 3]).encode("utf-8"))

    monkeypatch.setattr(embedder.urllib.request, "urlopen", fake_urlopen)

    with pytest.raises(embedder.EmbeddingError, match="non-object JSON"):
        embedder.http_json("GET", "http://127.0.0.1:11434/api/version")


# ---------------------------------------------------------------------------
# vector_literal
# ---------------------------------------------------------------------------


def test_vector_literal_formats_floats_in_pgvector_text_form() -> None:
    """Lock the current pgvector text-format output so a silent change in
    formatting does not invalidate stored vectors or the embedding cache."""

    assert embedder.vector_literal([0.1, 0.2, 0.3]) == "[0.1,0.2,0.3]"
    # Integers are coerced via ``float(...)`` then ``.9g`` formatting.
    assert embedder.vector_literal([1, 2, 3]) == "[1,2,3]"


def test_vector_literal_with_empty_input_returns_bare_brackets() -> None:
    """Empty vectors round-trip as ``"[]"`` rather than raising."""

    assert embedder.vector_literal([]) == "[]"
