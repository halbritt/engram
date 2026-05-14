"""FastAPI app for the RFC 0029 bench triage workbench."""

from __future__ import annotations

import json
import os
import sqlite3
from hashlib import sha256
from importlib import resources
from pathlib import Path
from urllib.parse import urlencode

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from jinja2 import ChoiceLoader, FileSystemLoader

from engram.bench_review import detail, storage
from engram.bench_review.classify import STRONG_DECISION_DISABLED_STATES, state_instruction
from engram.web import assets as shared_assets
from engram.web.origin import require_origin
from engram.web.tier import require_tier_ceiling

ALLOWED_HOSTS: frozenset[str] = frozenset({"127.0.0.1", "localhost", "::1", "testserver"})
DEFAULT_LOOPBACK_ORIGIN_HOSTS: tuple[str, ...] = ("127.0.0.1", "localhost", "testserver")
BENCH_DISCLAIMER: str = (
    "Bench review decisions do not mutate production data or bypass Phase 4 gates."
)
BUILD_SHA: str | None = os.environ.get("ENGRAM_BUILD_SHA")
INTERVIEW_URL: str = os.environ.get("ENGRAM_BENCH_REVIEW_INTERVIEW_URL", "http://127.0.0.1:8765/")
BENCH_DECISION_HELP_ROWS: tuple[tuple[str, str, str], ...] = (
    (
        "Accept candidate change",
        "a",
        "Scratch-local approval of the candidate delta for this benchmark row.",
    ),
    (
        "Flag candidate regression",
        "r",
        "Scratch-local marker that the candidate output is worse or risky.",
    ),
    ("Needs follow-up", "u", "Keep the row in follow-up queues for manual investigation."),
    ("Exclude from review", "x", "Exclude noise while keeping risky exclusions visible."),
)
BENCH_SHORTCUT_ROWS: tuple[tuple[str, str], ...] = (
    ("?", "Open help"),
    ("Esc", "Close help"),
    ("/", "Focus the queue filter"),
    ("a", "Accept candidate change"),
    ("r", "Flag candidate regression"),
    ("u", "Needs follow-up"),
    ("x", "Exclude from review"),
)
BENCH_DISCLOSURE_LINES: tuple[str, ...] = (
    (
        "Decisions written here are scratch-local. They do not feed production "
        "extraction, consolidation, audits, or serving. Promotion is an owner / "
        "coordinator action through the normal gate artifact (D074)."
    ),
    "Loopback bind only; non-loopback access requires future RFC/token-auth work.",
)


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
    app = FastAPI(
        title="Engram bench review",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    templates = _templates()
    templates.env.globals.update(
        bench_disclaimer=BENCH_DISCLAIMER,
        bench_url="/segments?remaining=1&reviewable=1",
        bind_address=f"{host}:{port}",
        bind_host=host,
        bind_port=port,
        build_sha=BUILD_SHA,
        data_state_display=_data_state_display,
        decision_help_rows=BENCH_DECISION_HELP_ROWS,
        decision_icon=_decision_icon,
        decision_label=_decision_label,
        disclosure_lines=BENCH_DISCLOSURE_LINES,
        help_title="Bench review help",
        interview_url=INTERVIEW_URL,
        keyboard_static_url="/shared-static/keyboard.js",
        rationale_max_chars=storage.RATIONALE_MAX_CHARS,
        shortcut_rows=BENCH_SHORTCUT_ROWS,
        surface="bench",
        surface_label="Bench review",
        tag_label=_tag_label,
        verdict_help_rows=(),
    )
    app.mount("/static", StaticFiles(directory=str(_resource_dir("static"))), name="static")
    app.mount(
        "/shared-static",
        StaticFiles(directory=str(shared_assets.static_dir())),
        name="shared-static",
    )

    def origin_check(request: Request) -> None:
        _origin_check(request, host=host, port=port)

    @app.get("/", response_class=HTMLResponse)
    def index(request: Request) -> HTMLResponse:
        summary = storage.summary(review_db_path)
        session = storage.get_session(review_db_path)
        rows = storage.list_segments(review_db_path, limit=None)
        readiness = _compute_readiness(summary, rows)
        return templates.TemplateResponse(
            request,
            "index.html",
            {
                "metadata_only": session["segments_path"] is None,
                "queue_tabs": _queue_tabs(_queue_context(state=None, tag=None)),
                "readiness": readiness,
                "resume_target": _resume_target(summary, rows, readiness),
                "run_metadata": _run_metadata(session, rows),
                "session": session,
                "summary": summary,
            },
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
                "active_queue_label": _active_queue_label(context),
                "items": items,
                "filters": context,
                "queue_tabs": _queue_tabs(context),
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
        session = storage.get_session(review_db_path)
        context = _queue_context(
            state=state or row["data_state"],
            tag=tag,
            decision=decision,
            remaining=bool(remaining),
            reviewable=bool(reviewable),
        )
        strong_disabled = row["data_state"] in STRONG_DECISION_DISABLED_STATES
        tags = json.loads(row["tags_json"])
        return templates.TemplateResponse(
            request,
            "segment.html",
            {
                "row": row,
                "disabled_tooltip": _strong_disabled_tooltip(row["data_state"]),
                "exclude_tooltip": _exclude_tooltip(row["data_state"], tags),
                "tags": tags,
                "instruction": state_instruction(row["data_state"]),
                "strong_disabled": strong_disabled,
                "detail": detail.fetch_segment_detail(review_db_path, segment_id),
                "metadata_only": session["segments_path"] is None,
                "next_context": context,
                "next_query_suffix": _query_suffix(context),
            },
        )

    @app.get("/segments/{segment_id}/excerpt", response_class=HTMLResponse)
    def segment_excerpt(request: Request, segment_id: str) -> HTMLResponse:
        row = storage.get_segment(review_db_path, segment_id)
        if row is None:
            raise HTTPException(status_code=404, detail="unknown segment")
        segment_detail = detail.fetch_segment_detail(review_db_path, segment_id)
        _require_excerpt_tier(segment_detail.privacy_tier)
        return templates.TemplateResponse(
            request,
            "excerpt.html",
            {
                "row": row,
                "instruction": state_instruction(row["data_state"]),
                "detail": segment_detail,
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
    ) -> Response:
        origin_check(request)
        row = storage.get_segment(review_db_path, segment_id)
        if row is None:
            raise HTTPException(status_code=404, detail="unknown segment")
        session = storage.get_session(review_db_path)
        if session["segments_path"] is None:
            return JSONResponse(
                {"error": "metadata-only session"},
                status_code=400,
            )
        if row["data_state"] in STRONG_DECISION_DISABLED_STATES and decision in {
            "accept_candidate_change",
            "flag_candidate_regression",
        }:
            return JSONResponse(
                {"error": "strong decision disabled for state"},
                status_code=400,
            )
        if rationale is not None and len(rationale) > storage.RATIONALE_MAX_CHARS:
            return JSONResponse(
                {"error": f"rationale exceeds {storage.RATIONALE_MAX_CHARS} characters"},
                status_code=400,
            )
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
        summary = storage.summary(review_db_path)
        rows = storage.list_segments(review_db_path, limit=None)
        return templates.TemplateResponse(
            request,
            "summary.html",
            {
                "readiness": _compute_readiness(summary, rows),
                "run_decisions": sorted(storage.RUN_DECISIONS),
                "run_labels": storage.RUN_DECISION_LABELS,
                "run_metadata": _run_metadata(storage.get_session(review_db_path), rows),
                "summary": summary,
            },
        )

    @app.post("/run-decision")
    def run_decision(
        request: Request,
        decision: str = Form(...),
        rationale: str | None = Form(default=None),
    ) -> Response:
        origin_check(request)
        readiness = _compute_readiness(
            storage.summary(review_db_path),
            storage.list_segments(review_db_path, limit=None),
        )
        if (
            decision == "safe_to_promote"
            and readiness["state"] != "ready_for_owner_gate_recommendation"
        ):
            return JSONResponse(
                {"error": "promotion recommendation is not ready"},
                status_code=409,
            )
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
    require_origin(
        request,
        allowed_hosts=_allowed_origin_hosts(request_host),
        bound_port=port,
    )


def _require_excerpt_tier(privacy_tier: int | None) -> None:
    if privacy_tier is None:
        return
    try:
        require_tier_ceiling(privacy_tier)
    except HTTPException as exc:
        if not (
            exc.status_code == 403
            and isinstance(exc.detail, dict)
            and exc.detail.get("error") == "privacy_tier_ceiling"
        ):
            raise
        raise HTTPException(
            status_code=403,
            detail={
                "error": "privacy_tier_ceiling",
                "privacy_tier": privacy_tier,
            },
        ) from exc


def _compute_readiness(summary: dict[str, object], rows: list[sqlite3.Row]) -> dict[str, str]:
    """Return the display readiness state for the current scratch review."""
    run_decision = summary.get("run_decision")
    if run_decision == "safe_to_promote":
        return _readiness_display("promotion_recommendation_recorded")
    if run_decision in {"blocked_by_regressions", "needs_more_review"}:
        return _readiness_display("rejection_recommendation_recorded")
    if not rows:
        return _readiness_display("review_incomplete")
    if any(row["decision"] == "flag_candidate_regression" for row in rows):
        return _readiness_display("blocked")
    if any(row["decision"] == "needs_followup" for row in rows):
        return _readiness_display("blocked")
    if any(
        row["decision"] == "exclude_from_review" and _is_blocking_exclusion(row) for row in rows
    ):
        return _readiness_display("blocked")
    if any(
        row["decision"] is None and row["data_state"] in STRONG_DECISION_DISABLED_STATES
        for row in rows
    ):
        return _readiness_display("blocked")
    if any(row["decision"] is None and _row_requires_review(row) for row in rows):
        return _readiness_display("review_incomplete")
    return _readiness_display("ready_for_owner_gate_recommendation")


def _readiness_display(state: str) -> dict[str, str]:
    displays = {
        "blocked": {
            "state": "blocked",
            "label": "Blocked",
            "copy": "One or more hard blockers prevent recommendation.",
            "class": "readiness-blocked",
        },
        "review_incomplete": {
            "state": "review_incomplete",
            "label": "Review incomplete",
            "copy": "Reviewable items remain undecided.",
            "class": "readiness-incomplete",
        },
        "ready_for_owner_gate_recommendation": {
            "state": "ready_for_owner_gate_recommendation",
            "label": "Ready (recommendation, not gate)",
            "copy": "Scratch-local recommendation; not a gate.",
            "class": "readiness-ready",
        },
        "promotion_recommendation_recorded": {
            "state": "promotion_recommendation_recorded",
            "label": "Proposed",
            "copy": "Scratch-local recommendation; not a gate.",
            "class": "readiness-proposed",
        },
        "rejection_recommendation_recorded": {
            "state": "rejection_recommendation_recorded",
            "label": "Proposed rejection",
            "copy": "Scratch-local recommendation; not a gate.",
            "class": "readiness-proposed",
        },
    }
    return displays[state]


def _row_requires_review(row: sqlite3.Row) -> bool:
    tags = _row_tags(row)
    if row["data_state"] != "complete":
        return True
    return tags != {"unchanged"}


def _is_blocking_exclusion(row: sqlite3.Row) -> bool:
    tags = _row_tags(row)
    return row["data_state"] != "complete" or tags != {"unchanged"}


def _row_tags(row: sqlite3.Row) -> set[str]:
    return {str(tag) for tag in json.loads(row["tags_json"])}


def _resume_target(
    summary: dict[str, object], rows: list[sqlite3.Row], readiness: dict[str, str]
) -> dict[str, object]:
    total = int(summary.get("total") or 0)
    decided = int(summary.get("decided") or 0)
    if total == 0:
        return {"href": "/segments", "label": "No segments loaded", "disabled": True}
    if any(row["decision"] == "flag_candidate_regression" for row in rows):
        return {
            "href": "/segments?decision=flag_candidate_regression",
            "label": "Review regressions",
        }
    if any(row["decision"] == "needs_followup" for row in rows):
        return {"href": "/segments?decision=needs_followup", "label": "Review follow-up"}
    if any(
        row["decision"] == "exclude_from_review" and _is_blocking_exclusion(row) for row in rows
    ):
        return {
            "href": "/segments?decision=exclude_from_review",
            "label": "Review excluded blockers",
        }
    if readiness["state"] == "ready_for_owner_gate_recommendation":
        return {"href": "/summary", "label": "Record recommendation"}
    if any(row["decision"] is None and _row_requires_review(row) for row in rows):
        return {
            "href": "/segments?remaining=1&reviewable=1",
            "label": "Start review" if decided == 0 else "Resume review",
        }
    return {"href": "/summary", "label": "Open summary"}


def _run_metadata(session: sqlite3.Row, rows: list[sqlite3.Row]) -> dict[str, object]:
    return {
        "candidate_triple": _version_triple(
            session["candidate_prompt_version"],
            session["candidate_model_version"],
            session["candidate_request_profile_version"],
        ),
        "prior_comparison_mode": "database",
        "prior_triple": _version_triple(
            session["prior_prompt_version"],
            session["prior_model_version"],
            session["prior_request_profile_version"],
        ),
        "public_candidate_artifact_id": session["run_id"],
        "queue_fingerprint": _queue_fingerprint(session, rows),
        "reviewer_label": "operator",
    }


def _version_triple(prompt: str | None, model: str | None, profile: str | None) -> str:
    return "/".join(value or "unknown" for value in (prompt, model, profile))


def _queue_fingerprint(session: sqlite3.Row, rows: list[sqlite3.Row]) -> str:
    payload = {
        "candidate": [
            session["candidate_prompt_version"],
            session["candidate_model_version"],
            session["candidate_request_profile_version"],
        ],
        "prior": [
            session["prior_prompt_version"],
            session["prior_model_version"],
            session["prior_request_profile_version"],
        ],
        "segments": [
            {
                "candidate": row["candidate_claim_count"],
                "decision": row["decision"],
                "prior": row["prior_claim_count"],
                "segment_id": row["segment_id"],
                "state": row["data_state"],
                "tags": json.loads(row["tags_json"]),
            }
            for row in rows
        ],
    }
    digest = sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()
    return digest[:16]


def _queue_tabs(active_context: dict[str, object]) -> list[dict[str, object]]:
    tab_contexts: tuple[tuple[str, dict[str, object]], ...] = (
        ("Needs review", _queue_context(state=None, tag=None, remaining=True, reviewable=True)),
        ("Zeroed", _queue_context(state="candidate_zero", tag=None, remaining=True)),
        (
            "Newly nonzero",
            _queue_context(state=None, tag="newly_nonzero", remaining=True, reviewable=True),
        ),
        (
            "Count changed",
            _queue_context(state=None, tag="count_changed", remaining=True, reviewable=True),
        ),
        (
            "Predicate mix changed",
            _queue_context(
                state=None,
                tag="predicate_mix_changed",
                remaining=True,
                reviewable=True,
            ),
        ),
        (
            "High drops",
            _queue_context(state=None, tag="high_drop_count", remaining=True, reviewable=True),
        ),
        (
            "Provenance",
            _queue_context(state=None, tag="provenance_anomaly", remaining=True, reviewable=True),
        ),
        ("Schema / parse", _queue_context(state="candidate_malformed", tag=None, remaining=True)),
        ("Follow-up", _queue_context(state=None, tag=None, decision="needs_followup")),
        (
            "Regressions",
            _queue_context(state=None, tag=None, decision="flag_candidate_regression"),
        ),
        (
            "Excluded blockers",
            _queue_context(state=None, tag=None, decision="exclude_from_review"),
        ),
        (
            "Accepted",
            _queue_context(state=None, tag=None, decision="accept_candidate_change"),
        ),
        ("Unchanged", _queue_context(state=None, tag="unchanged")),
        ("All", _queue_context(state=None, tag=None)),
    )
    active_suffix = _query_suffix(active_context)
    return [
        {
            "active": _query_suffix(context) == active_suffix,
            "href": f"/segments{_query_suffix(context)}",
            "label": label,
        }
        for label, context in tab_contexts
    ]


def _active_queue_label(context: dict[str, object]) -> str:
    suffix = _query_suffix(context)
    for tab in _queue_tabs(context):
        if tab["active"]:
            return str(tab["label"])
    return f"Filtered queue {suffix}" if suffix else "All"


def _data_state_display(data_state: str) -> dict[str, str]:
    displays = {
        "candidate_malformed": {
            "label": "Failed",
            "token": "failed",
            "copy": "Candidate record failed schema or parse validation.",
        },
        "candidate_missing": {
            "label": "Unavailable",
            "token": "unavailable",
            "copy": "Candidate / prior record missing for this segment.",
        },
        "prior_missing": {
            "label": "Unavailable",
            "token": "unavailable",
            "copy": "Candidate / prior record missing for this segment.",
        },
        "candidate_redacted": {
            "label": "Redacted",
            "token": "redacted",
            "copy": "Structured fields preserved; text intentionally absent.",
        },
        "candidate_zero": {
            "label": "Candidate zero",
            "token": "candidate-zero",
            "copy": "Candidate emitted zero claims for this segment.",
        },
        "complete": {
            "label": "Complete",
            "token": "complete",
            "copy": "Prior and candidate structured comparison data are available.",
        },
    }
    return displays.get(
        data_state,
        {"label": data_state.replace("_", " "), "token": "unknown", "copy": data_state},
    )


def _decision_label(decision: str | None) -> str:
    labels = {
        "accept_candidate_change": "Accept candidate change",
        "flag_candidate_regression": "Flag candidate regression",
        "needs_followup": "Needs follow-up",
        "exclude_from_review": "Exclude from review",
    }
    if decision is None:
        return "Undecided"
    return labels.get(decision, decision.replace("_", " "))


def _decision_icon(decision: str) -> str:
    icons = {
        "accept_candidate_change": "⊕",
        "flag_candidate_regression": "⊖",
        "needs_followup": "...",
        "exclude_from_review": "↷",
    }
    return icons.get(decision, "•")


def _tag_label(tag: str) -> str:
    return tag.replace("_", " ")


def _strong_disabled_tooltip(data_state: str) -> str:
    return (
        f"Strong decisions disabled while {data_state}. "
        "Resolve the artifact (regenerate / disambiguate) to enable."
    )


def _exclude_tooltip(data_state: str, tags: list[str]) -> str | None:
    if data_state != "complete" or set(tags) != {"unchanged"}:
        return (
            "Excluding a risky row leaves it visible in blocker queues; "
            "consider Flag candidate regression instead."
        )
    return None


def _is_allowed_request_host(hostname: str | None) -> bool:
    if hostname is None:
        return False
    normalized = hostname.lower().rstrip(".")
    return normalized in ALLOWED_HOSTS or any(
        normalized.endswith(suffix) for suffix in ALLOWED_DNS_SUFFIXES
    )


def _allowed_origin_hosts(request_host: str) -> tuple[str, ...]:
    normalized = request_host.lower().rstrip(".")
    if normalized in ALLOWED_HOSTS:
        hosts = [*DEFAULT_LOOPBACK_ORIGIN_HOSTS]
        if normalized == "::1":
            hosts.append("::1")
        return tuple(dict.fromkeys(hosts))
    return (normalized,)


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


def _templates() -> Jinja2Templates:
    bench_template_dir = _resource_dir("templates")
    templates = Jinja2Templates(directory=str(bench_template_dir))
    templates.env.loader = ChoiceLoader(
        (
            FileSystemLoader(str(bench_template_dir)),
            FileSystemLoader(str(shared_assets.template_dir())),
        )
    )
    return templates
