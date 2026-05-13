"""FastAPI app for the RFC 0029 bench triage workbench."""

from __future__ import annotations

import json
import os
from importlib import resources
from pathlib import Path
from urllib.parse import urlencode, urlparse

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from engram.bench_review import detail, storage
from engram.bench_review.classify import STRONG_DECISION_DISABLED_STATES, state_instruction

ALLOWED_HOSTS: frozenset[str] = frozenset({"127.0.0.1", "localhost", "::1", "testserver"})
ALLOWED_FETCH_SITES: frozenset[str] = frozenset({"same-origin", "same-site", "none"})


def _resolve_allowed_dns_suffixes() -> tuple[str, ...]:
    """Return operator-opted-in DNS suffixes allowed by Origin checks."""
    configured = os.environ.get("ENGRAM_BENCH_REVIEW_ALLOWED_DNS_SUFFIXES", "")
    suffixes: list[str] = []
    seen: set[str] = set()
    for raw in configured.split(","):
        suffix = raw.strip().lower().rstrip(".")
        if not suffix:
            continue
        if not suffix.startswith("."):
            suffix = f".{suffix}"
        if suffix not in seen:
            seen.add(suffix)
            suffixes.append(suffix)
    return tuple(suffixes)


ALLOWED_DNS_SUFFIXES: tuple[str, ...] = _resolve_allowed_dns_suffixes()


def create_app(*, review_db_path: Path, host: str = "127.0.0.1", port: int = 8770) -> FastAPI:
    """Create a bench review FastAPI app over one scratch review DB."""
    if host not in ALLOWED_HOSTS:
        raise ValueError(f"bench review host must be loopback, got {host!r}")
    app = FastAPI(title="Engram bench review")
    templates = Jinja2Templates(directory=str(_resource_dir("templates")))
    app.mount("/static", StaticFiles(directory=str(_resource_dir("static"))), name="static")

    def origin_check(request: Request) -> None:
        _origin_check(request, host=host, port=port)

    @app.get("/", response_class=HTMLResponse)
    def index(request: Request) -> HTMLResponse:
        summary = storage.summary(review_db_path)
        return templates.TemplateResponse(
            request,
            "index.html",
            {"summary": summary, "session": storage.get_session(review_db_path)},
        )

    @app.get("/segments", response_class=HTMLResponse)
    def segments(
        request: Request,
        state: str | None = None,
        tag: str | None = None,
        decision: str | None = None,
        remaining: int = 0,
        reviewable: int = 0,
        limit: int = 200,
    ) -> HTMLResponse:
        context = _queue_context(
            state=state,
            tag=tag,
            decision=decision,
            remaining=bool(remaining),
            reviewable=bool(reviewable),
        )
        rows = storage.list_segments(
            review_db_path,
            state=state,
            tag=tag,
            decision=decision,
            remaining=bool(remaining),
            reviewable=bool(reviewable),
            limit=limit,
        )
        items = [{"row": row, "tags": json.loads(row["tags_json"])} for row in rows]
        return templates.TemplateResponse(
            request,
            "segments.html",
            {
                "items": items,
                "filters": context,
                "query_suffix": _query_suffix(context),
            },
        )

    @app.get("/segments/{segment_id}", response_class=HTMLResponse)
    def segment(
        request: Request,
        segment_id: str,
        state: str | None = None,
        tag: str | None = None,
        decision: str | None = None,
        remaining: int = 1,
        reviewable: int = 0,
    ) -> HTMLResponse:
        row = storage.get_segment(review_db_path, segment_id)
        if row is None:
            raise HTTPException(status_code=404, detail="unknown segment")
        context = _queue_context(
            state=state or row["data_state"],
            tag=tag,
            decision=decision,
            remaining=bool(remaining),
            reviewable=bool(reviewable),
        )
        strong_disabled = row["data_state"] in STRONG_DECISION_DISABLED_STATES
        return templates.TemplateResponse(
            request,
            "segment.html",
            {
                "row": row,
                "tags": json.loads(row["tags_json"]),
                "instruction": state_instruction(row["data_state"]),
                "strong_disabled": strong_disabled,
                "segment_decisions": sorted(storage.SEGMENT_DECISIONS),
                "detail": detail.fetch_segment_detail(review_db_path, segment_id),
                "next_context": context,
                "next_query_suffix": _query_suffix(context),
            },
        )

    @app.get("/segments/{segment_id}/excerpt", response_class=HTMLResponse)
    def segment_excerpt(request: Request, segment_id: str) -> HTMLResponse:
        row = storage.get_segment(review_db_path, segment_id)
        if row is None:
            raise HTTPException(status_code=404, detail="unknown segment")
        return templates.TemplateResponse(
            request,
            "excerpt.html",
            {
                "row": row,
                "instruction": state_instruction(row["data_state"]),
                "detail": detail.fetch_segment_detail(review_db_path, segment_id),
            },
        )

    @app.post("/segments/{segment_id}/decision")
    def segment_decision(
        request: Request,
        segment_id: str,
        decision: str = Form(...),
        rationale: str | None = Form(default=None),
        next_state: str | None = Form(default=None),
        next_tag: str | None = Form(default=None),
        next_decision: str | None = Form(default=None),
        next_remaining: int = Form(default=1),
        next_reviewable: int = Form(default=0),
    ) -> RedirectResponse:
        origin_check(request)
        row = storage.get_segment(review_db_path, segment_id)
        if row is None:
            raise HTTPException(status_code=404, detail="unknown segment")
        if row["data_state"] in STRONG_DECISION_DISABLED_STATES and decision in {
            "accept_candidate_change",
            "flag_candidate_regression",
        }:
            raise HTTPException(status_code=400, detail="strong decision disabled for state")
        try:
            storage.record_segment_decision(
                review_db_path, segment_id=segment_id, decision=decision, rationale=rationale
            )
        except storage.BenchReviewStorageError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return RedirectResponse(
            url=_next_segment_url(
                review_db_path,
                state=_clean_filter(next_state),
                tag=_clean_filter(next_tag),
                decision=_clean_filter(next_decision),
                remaining=bool(next_remaining),
                reviewable=bool(next_reviewable),
            ),
            status_code=303,
        )

    @app.get("/summary", response_class=HTMLResponse)
    def summary_page(request: Request) -> HTMLResponse:
        return templates.TemplateResponse(
            request,
            "summary.html",
            {
                "summary": storage.summary(review_db_path),
                "run_decisions": sorted(storage.RUN_DECISIONS),
                "run_labels": storage.RUN_DECISION_LABELS,
            },
        )

    @app.post("/run-decision")
    def run_decision(
        request: Request,
        decision: str = Form(...),
        rationale: str | None = Form(default=None),
    ) -> RedirectResponse:
        origin_check(request)
        try:
            storage.record_run_decision(review_db_path, decision=decision, rationale=rationale)
        except storage.BenchReviewStorageError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return RedirectResponse(url="/summary", status_code=303)

    return app


def _origin_check(request: Request, *, host: str, port: int) -> None:
    request_host = request.url.hostname
    if request_host is None or not _is_allowed_request_host(request_host):
        raise HTTPException(status_code=403, detail={"error": "non_loopback_host"})
    fetch_site = request.headers.get("sec-fetch-site")
    if fetch_site and fetch_site not in ALLOWED_FETCH_SITES:
        raise HTTPException(status_code=403, detail={"error": "cross_site_fetch"})
    origin = request.headers.get("origin") or request.headers.get("referer")
    if origin:
        parsed = urlparse(origin)
        if parsed.hostname != request_host and not _is_allowed_request_host(parsed.hostname):
            raise HTTPException(status_code=403, detail={"error": "origin_not_allowed"})
        if parsed.port is not None and parsed.port not in {port, 80}:
            raise HTTPException(status_code=403, detail={"error": "origin_port_mismatch"})


def _is_allowed_request_host(hostname: str | None) -> bool:
    if hostname is None:
        return False
    normalized = hostname.lower().rstrip(".")
    return normalized in ALLOWED_HOSTS or any(
        normalized.endswith(suffix) for suffix in ALLOWED_DNS_SUFFIXES
    )


def _next_segment_url(
    review_db_path: Path,
    *,
    state: str | None,
    tag: str | None,
    decision: str | None,
    remaining: bool,
    reviewable: bool,
) -> str:
    context = _queue_context(
        state=state,
        tag=tag,
        decision=decision,
        remaining=remaining,
        reviewable=reviewable,
    )
    rows = storage.list_segments(
        review_db_path,
        state=context["state"],
        tag=context["tag"],
        decision=context["decision"],
        remaining=bool(context["remaining"]),
        reviewable=bool(context["reviewable"]),
        limit=1,
    )
    if rows:
        return f"/segments/{rows[0]['segment_id']}{_query_suffix(context)}"
    fallback = _queue_context(state=None, tag=None, decision=None, remaining=True, reviewable=True)
    return f"/segments{_query_suffix(fallback)}"


def _queue_context(
    *,
    state: str | None,
    tag: str | None,
    decision: str | None = None,
    remaining: bool = False,
    reviewable: bool = False,
) -> dict[str, object]:
    return {
        "state": _clean_filter(state),
        "tag": _clean_filter(tag),
        "decision": _clean_filter(decision),
        "remaining": remaining,
        "reviewable": reviewable,
    }


def _query_suffix(context: dict[str, object]) -> str:
    params: dict[str, str] = {}
    for key in ("state", "tag", "decision"):
        value = context.get(key)
        if isinstance(value, str) and value:
            params[key] = value
    if context.get("remaining"):
        params["remaining"] = "1"
    if context.get("reviewable"):
        params["reviewable"] = "1"
    return f"?{urlencode(params)}" if params else ""


def _clean_filter(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def _resource_dir(name: str) -> Path:
    return Path(str(resources.files("engram.bench_review") / name))
