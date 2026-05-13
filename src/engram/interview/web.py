"""FastAPI app for the RFC 0027 interview Web UI.

This module exposes the loopback-only Web UI that wraps the same
``engram.interview.{agent, sampler, storage, render}`` surface the CLI uses.
Route handlers are sync ``def`` because the underlying ``psycopg.Connection``
calls are synchronous; FastAPI dispatches sync handlers on its threadpool, so
``async def`` would block the event loop on every DB call (Spec 0027 §
Process model).

D044 / D069 invariant: this module MUST NOT import
``engram.consolidator.transitions`` (or anything from
``engram.consolidator``) — promote-belief / accept / reject affordances are
explicitly out of scope for the gold-set interview surface, and the import
guard is mechanically enforced by
``tests/test_interview_web.py::test_consolidator_transitions_unimportable_from_web``.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from importlib import resources
from pathlib import Path
from typing import Any, Iterable

import psycopg
from fastapi import Depends, FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from engram.db import connect
from engram.interview import (
    SAMPLER_ID,
    SAMPLER_VERSION,
    GoldLabelSampler,
    SampledTarget,
)
from engram.interview.agent import InterviewAgent
from engram.interview.errors import GoldLabelStorageError, GoldLabelVerdictError
from engram.interview.render import (
    EVIDENCE_EXCERPT_LIMIT,
    EVIDENCE_ROWS_SHOWN,
    RATIONALE_PROMPT_BY_VERDICT,
    VERDICT_VALID,
    fetch_target_display,
    format_evidence_dates,
    format_header,
    format_summary_line,
    pick_question,
)
from engram.interview.storage import (
    get_active_learning_signal_version,
    insert_session,
    mark_session_completed,
)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_DEFAULT_ALLOWED_ORIGIN_HOSTS: tuple[str, ...] = ("127.0.0.1", "localhost")


def _resolve_allowed_origin_hosts() -> tuple[str, ...]:
    """Build the Origin allowlist at module load time.

    Defaults to the loopback set ``("127.0.0.1", "localhost")``. Operators
    on a trusted network (e.g., a Tailscale tailnet) extend it via
    ``ENGRAM_INTERVIEW_ALLOWED_ORIGINS`` — a comma-separated list of host
    names appended to the default set. The env-var pattern follows the
    Engram Python coding standard (RFC 0012): tunables behind ``ENGRAM_*``
    env vars read at module top.

    Defaults remain loopback-only; opt-in is explicit. The env var extends
    only the host portion; the scheme check below is still locked to
    ``http`` (no https upgrade in v1, matching the original Spec 0027
    posture and the user-space TCP-bridge pattern documented in the
    howto's "Tailnet access" section).
    """
    extra = os.environ.get("ENGRAM_INTERVIEW_ALLOWED_ORIGINS", "")
    extra_hosts = tuple(h.strip() for h in extra.split(",") if h.strip())
    seen: set[str] = set()
    out: list[str] = []
    for h in (*_DEFAULT_ALLOWED_ORIGIN_HOSTS, *extra_hosts):
        if h not in seen:
            seen.add(h)
            out.append(h)
    return tuple(out)


ALLOWED_ORIGIN_HOSTS: tuple[str, ...] = _resolve_allowed_origin_hosts()
"""Origin allowlist (Spec 0027 § Origin allowlist behavior, extended per D081).

Defaults to the loopback set ``("127.0.0.1", "localhost")``; extended at
module load by the comma-separated ``ENGRAM_INTERVIEW_ALLOWED_ORIGINS``
env var. We accept any port on these hosts since the operator picks the
bind port at ``engram phase3 interview serve --port``. Origin checks
compare scheme=http plus host membership; no upgrade to https in v1.
"""

CONTEXT_BEFORE_AFTER_CAP: int = 20
"""Hard cap on ``before + after`` for ``/messages/{id}/context`` (F023)."""

TIER_CEILING: int = 1
"""Privacy-tier ceiling enforced on the message-rendering routes
(``/messages/{id}``, ``/messages/{id}/context``, ``/q/{idx}/evidence/all``).

The reserved env var ``ENGRAM_GOLD_INTERVIEW_RENDER_TIER_MAX`` is documented
in the spec but unimplemented in v1.
"""

# Verdict glosses keyed by verdict, populated lazily from
# ``gold_label_verdict_vocabulary`` per request. We also fall back to a
# hard-coded mapping mirroring migration 010 in case the table is empty in a
# fresh schema.
_FALLBACK_VERDICT_GLOSSES: dict[str, str] = {
    "true": "claim/belief is correct about the world",
    "false": "claim/belief is wrong about the world",
    "stale": "was true at evidence time, no longer true",
    "unsupported": "evidence does not establish claim, regardless of world truth",
    "unsure": "user cannot rule",
    "skip": "user advances without ruling (cooldown-free)",
}
_VERDICT_KEY_LETTERS: dict[str, str] = {
    "true": "t",
    "false": "f",
    "stale": "s",
    "unsupported": "n",
    "unsure": "u",
    "skip": "k",
}
_RATIONALE_REQUIRED_VERDICTS: frozenset[str] = frozenset(
    {"false", "stale", "unsupported", "unsure"}
)


# ---------------------------------------------------------------------------
# DB connection helper
# ---------------------------------------------------------------------------


def _resource_dir(name: str) -> Path:
    """Return the on-disk path of a packaged resource directory.

    Uses ``importlib.resources`` so the wheel install case works (templates
    and static assets are shipped via the ``[tool.setuptools.package-data]``
    block in pyproject.toml).
    """
    pkg = resources.files("engram.interview") / name
    # ``files()`` returns a Traversable; we need an actual path on disk for
    # Jinja2 / StaticFiles. ``as_file`` would copy on egg-zip installs but
    # Engram ships unpacked source / wheel installs only (no zip imports),
    # so str-coercion is safe.
    return Path(str(pkg))


def _get_conn() -> Iterable[psycopg.Connection]:
    """FastAPI dependency: open one psycopg connection per request.

    Closes on exit. No pool in v1 (the workload is single-operator localhost).
    """
    with connect() as conn:
        yield conn


def _get_origin_check(request: Request) -> None:
    """FastAPI dependency form of the Origin / Sec-Fetch-Site check.

    Returns ``None`` on success; raises ``HTTPException(403)`` on mismatch.
    """
    _origin_check(request)


# ---------------------------------------------------------------------------
# Origin / tier guard helpers
# ---------------------------------------------------------------------------


def _origin_check(request: Request) -> None:
    """Enforce the Origin / Sec-Fetch-Site allowlist on POST routes.

    Raises ``HTTPException(403)`` with structured body
    ``{"error": "origin_mismatch", "expected": [...]}`` on mismatch. The
    check accepts requests with no ``Origin`` header so curl / TestClient
    flows are not gratuitously broken — an attacker page would always carry
    an Origin (cross-origin requests cannot strip it). When the header is
    present, the host portion must match the loopback allowlist.

    ``Sec-Fetch-Site`` is enforced when present: must be ``same-origin``.
    """
    origin = request.headers.get("origin")
    if origin:
        host_ok = False
        for host in ALLOWED_ORIGIN_HOSTS:
            if origin.startswith(f"http://{host}:") or origin == f"http://{host}":
                host_ok = True
                break
        if not host_ok:
            raise HTTPException(
                status_code=403,
                detail={
                    "error": "origin_mismatch",
                    "expected": [f"http://{h}:<port>" for h in ALLOWED_ORIGIN_HOSTS],
                },
            )
    sec_fetch_site = request.headers.get("sec-fetch-site")
    if sec_fetch_site is not None and sec_fetch_site != "same-origin":
        raise HTTPException(
            status_code=403,
            detail={
                "error": "origin_mismatch",
                "expected": ["sec-fetch-site=same-origin"],
            },
        )


def _check_tier_1(privacy_tier: int, message_id: str | None = None) -> None:
    """Raise 403 with the privacy-tier-ceiling envelope if tier > 1."""
    if privacy_tier > TIER_CEILING:
        detail: dict[str, Any] = {
            "error": "privacy_tier_ceiling",
            "tier": int(privacy_tier),
            "ceiling": TIER_CEILING,
        }
        if message_id is not None:
            detail["message_id"] = message_id
        raise HTTPException(status_code=403, detail=detail)


# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------


def _load_verdict_glosses(conn: psycopg.Connection) -> dict[str, str]:
    """Load ``gold_label_verdict_vocabulary`` rows; fall back to hard-coded map."""
    try:
        rows = conn.execute(
            "SELECT verdict, gloss FROM gold_label_verdict_vocabulary"
        ).fetchall()
    except psycopg.Error:
        return dict(_FALLBACK_VERDICT_GLOSSES)
    glosses = dict(_FALLBACK_VERDICT_GLOSSES)
    for v, g in rows:
        glosses[v] = g
    return glosses


def _load_open_sessions(conn: psycopg.Connection) -> list[dict[str, Any]]:
    """Open sessions with ``(K, N)`` progress + age string."""
    rows = conn.execute(
        """
        SELECT
            s.session_id::text,
            s.started_at,
            (
                SELECT count(*) FROM gold_label_session_targets t
                WHERE t.session_id = s.session_id
            ) AS n_targets,
            (
                SELECT count(*) FROM gold_labels gl
                WHERE gl.session_id = s.session_id
            ) AS n_answered
        FROM gold_label_sessions s
        WHERE s.completed_at IS NULL
        ORDER BY s.started_at DESC
        """,
    ).fetchall()
    now = datetime.now(timezone.utc)
    out: list[dict[str, Any]] = []
    for sid, started_at, n_targets, n_answered in rows:
        delta = now - (started_at if started_at.tzinfo else started_at.replace(tzinfo=timezone.utc))
        hours = int(delta.total_seconds() // 3600)
        if hours < 1:
            age = "just now"
        elif hours < 24:
            age = f"{hours}h ago"
        else:
            age = f"{hours // 24}d ago"
        out.append(
            {
                "session_id": sid,
                "started_at": started_at,
                "n_targets": int(n_targets),
                "n_answered": int(n_answered),
                "age": age,
            }
        )
    return out


def _load_session_target(
    conn: psycopg.Connection, session_id: str, table_idx: int
) -> dict[str, Any] | None:
    """Load one ``gold_label_session_targets`` row keyed by (session_id, idx)."""
    row = conn.execute(
        """
        SELECT
            session_id::text,
            idx,
            target_kind,
            target_id::text,
            candidate_pool_snapshot_id::text,
            extraction_prompt_version,
            extraction_model_version,
            consolidation_prompt_version,
            consolidation_model_version,
            request_profile_version,
            stability_class,
            conf_band,
            recency_band,
            belief_status,
            active_learning_signal_version,
            confidence,
            observed_at
        FROM gold_label_session_targets
        WHERE session_id = %s AND idx = %s
        """,
        (session_id, table_idx),
    ).fetchone()
    if row is None:
        return None
    return {
        "session_id": row[0],
        "idx": int(row[1]),
        "target_kind": row[2],
        "target_id": row[3],
        "candidate_pool_snapshot_id": row[4],
        "extraction_prompt_version": row[5],
        "extraction_model_version": row[6],
        "consolidation_prompt_version": row[7],
        "consolidation_model_version": row[8],
        "request_profile_version": row[9],
        "stability_class": row[10],
        "conf_band": row[11],
        "recency_band": row[12],
        "belief_status": row[13],
        "active_learning_signal_version": row[14],
        "confidence": float(row[15]) if row[15] is not None else None,
        "observed_at": row[16],
    }


def _session_n_targets(conn: psycopg.Connection, session_id: str) -> int | None:
    row = conn.execute(
        """
        SELECT count(*) FROM gold_label_session_targets WHERE session_id = %s
        """,
        (session_id,),
    ).fetchone()
    if row is None:
        return None
    return int(row[0])


def _session_exists(conn: psycopg.Connection, session_id: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM gold_label_sessions WHERE session_id = %s",
        (session_id,),
    ).fetchone()
    return row is not None


def _session_target_to_sampled(target_row: dict[str, Any]) -> SampledTarget:
    """Reconstruct a SampledTarget from a ``gold_label_session_targets`` row.

    Spec 0027 § Routes (POST verdict): the version triple stamped at session
    creation is the one that travels back into ``insert_label`` so a
    re-extraction between renders does not drift.
    """
    return SampledTarget(
        target_kind=target_row["target_kind"],
        target_id=target_row["target_id"],
        stability_class=target_row["stability_class"],
        confidence=target_row["confidence"] if target_row["confidence"] is not None else 0.0,
        observed_at=target_row["observed_at"] or datetime.now(timezone.utc),
        conf_band=target_row["conf_band"],
        recency_band=target_row["recency_band"],
        belief_status=target_row["belief_status"],
        candidate_pool_snapshot_id=target_row["candidate_pool_snapshot_id"],
        active_learning_signal_version=target_row["active_learning_signal_version"],
        extraction_prompt_version=target_row["extraction_prompt_version"],
        extraction_model_version=target_row["extraction_model_version"],
        consolidation_prompt_version=target_row["consolidation_prompt_version"],
        consolidation_model_version=target_row["consolidation_model_version"],
        request_profile_version=target_row["request_profile_version"],
    )


def _strata_rows(
    conn: psycopg.Connection, session_id: str
) -> list[tuple[str, int]]:
    rows = conn.execute(
        """
        SELECT stability_class, count(*)
        FROM gold_labels
        WHERE session_id = %s
        GROUP BY 1
        ORDER BY 1
        """,
        (session_id,),
    ).fetchall()
    return [(r[0], int(r[1])) for r in rows]


def _n_answered(conn: psycopg.Connection, session_id: str) -> int:
    row = conn.execute(
        "SELECT count(*) FROM gold_labels WHERE session_id = %s",
        (session_id,),
    ).fetchone()
    return int(row[0]) if row is not None else 0


def _insert_session_targets(
    conn: psycopg.Connection,
    session_id: str,
    sampled: list[SampledTarget],
) -> None:
    """Materialize the sampled order into ``gold_label_session_targets``.

    Idempotent within one transaction: caller is expected to have committed
    the session row and is now extending it with target rows. Errors propagate.
    """
    for idx, target in enumerate(sampled):
        triple = target.version_triple()
        conn.execute(
            """
            INSERT INTO gold_label_session_targets (
                session_id, idx, target_kind, target_id,
                candidate_pool_snapshot_id,
                extraction_prompt_version, extraction_model_version,
                consolidation_prompt_version, consolidation_model_version,
                request_profile_version,
                stability_class, conf_band, recency_band, belief_status,
                active_learning_signal_version, confidence, observed_at
            )
            VALUES (
                %s, %s, %s, %s,
                %s,
                %s, %s,
                %s, %s,
                %s,
                %s, %s, %s, %s,
                %s, %s, %s
            )
            """,
            (
                session_id,
                idx,
                target.target_kind,
                target.target_id,
                target.candidate_pool_snapshot_id,
                triple.get("extraction_prompt_version"),
                triple.get("extraction_model_version"),
                triple.get("consolidation_prompt_version"),
                triple.get("consolidation_model_version"),
                triple.get("request_profile_version"),
                target.stability_class,
                target.conf_band,
                target.recency_band,
                target.belief_status,
                target.active_learning_signal_version,
                target.confidence,
                target.observed_at,
            ),
        )


def _abandon_session(
    conn: psycopg.Connection, session_id: str, *, operator_note: str
) -> None:
    """Mark the session completed and stamp ``operator_note``.

    Storage helper ``mark_session_completed`` does not accept an
    ``operator_note`` kwarg in v1; we issue the UPDATE directly so the spec's
    `operator_note='abandoned via web'` semantics hold without modifying
    storage.py (out of write scope for Pass B1).
    """
    conn.execute(
        """
        UPDATE gold_label_sessions
        SET completed_at = COALESCE(completed_at, now()),
            operator_note = %s
        WHERE session_id = %s
        """,
        (operator_note, session_id),
    )


# ---------------------------------------------------------------------------
# Question rendering helpers
# ---------------------------------------------------------------------------


def _render_question_template(
    request: Request,
    templates: Jinja2Templates,
    *,
    conn: psycopg.Connection,
    session_id: str,
    url_idx: int,
    target_row: dict[str, Any],
    n_targets: int,
    error_banner: str | None = None,
    full_evidence: bool = False,
) -> Response:
    """Render ``question.html`` with the standard context.

    ``full_evidence=True`` is used by the ``/q/{idx}/evidence/all`` route to
    render every cited message rather than the first ``EVIDENCE_ROWS_SHOWN``.
    """
    sampled = _session_target_to_sampled(target_row)
    display = fetch_target_display(
        conn,
        sampled,
        evidence_limit=None if full_evidence else EVIDENCE_ROWS_SHOWN,
    )

    # Tier 1 ceiling on the "show all" path: any cited message at tier > 1
    # forces a 403, mirroring /messages/{id}'s behaviour.
    if full_evidence:
        for excerpt in display.get("excerpts") or []:
            tier = _message_tier(conn, excerpt["id"])
            if tier is not None:
                _check_tier_1(tier, message_id=excerpt["id"])

    glosses = _load_verdict_glosses(conn)
    header_line = format_header(sampled, url_idx, n_targets)
    summary_line = format_summary_line(display)
    summary_lines = summary_line.splitlines() or [""]
    evidence_dates_line = format_evidence_dates(display)
    question_line = pick_question(sampled, display)

    # If we are not rendering all evidence, cap the excerpts to the first
    # EVIDENCE_ROWS_SHOWN. ``fetch_evidence_excerpts`` already imposes that
    # limit on the SQL side, but we keep the shape explicit for the template.
    if not full_evidence:
        ev = display.get("excerpts") or []
        display = {**display, "excerpts": ev[:EVIDENCE_ROWS_SHOWN]}

    n_answered = _n_answered(conn, session_id)
    strata = _strata_rows(conn, session_id)

    context = {
        "session_id": session_id,
        "idx": url_idx,
        "total": n_targets,
        "n_answered": n_answered,
        "header_line": header_line,
        "summary_line": summary_line,
        "summary_lines": summary_lines,
        "evidence_dates_line": evidence_dates_line,
        "question_line": question_line,
        "display": display,
        "version_triple": {
            "extraction_prompt_version": target_row["extraction_prompt_version"],
            "extraction_model_version": target_row["extraction_model_version"],
            "consolidation_prompt_version": target_row["consolidation_prompt_version"],
            "consolidation_model_version": target_row["consolidation_model_version"],
            "request_profile_version": target_row["request_profile_version"],
        },
        "verdict_glosses": glosses,
        "verdict_help_rows": [
            (v, glosses.get(v, ""), _VERDICT_KEY_LETTERS[v])
            for v in ("true", "false", "stale", "unsupported", "unsure", "skip")
        ],
        "rationale_prompts": RATIONALE_PROMPT_BY_VERDICT,
        "strata_rows": strata,
        "error_banner": error_banner,
    }
    return templates.TemplateResponse(request, "question.html", context)


def _message_tier(conn: psycopg.Connection, message_id: str) -> int | None:
    row = conn.execute(
        "SELECT privacy_tier FROM messages WHERE id = %s",
        (message_id,),
    ).fetchone()
    if row is None:
        return None
    return int(row[0])


def _session_can_reach_conversation(
    conn: psycopg.Connection,
    *,
    session_id: str,
    conversation_id: str,
) -> bool:
    row = conn.execute(
        """
        SELECT
            EXISTS (
                SELECT 1
                FROM gold_label_session_targets t
                JOIN claims c
                  ON t.target_kind = 'claim'
                 AND c.id = t.target_id
                JOIN messages m
                  ON m.id = ANY(c.evidence_message_ids)
                WHERE t.session_id = %s
                  AND m.conversation_id = %s
            )
            OR EXISTS (
                SELECT 1
                FROM gold_label_session_targets t
                JOIN beliefs b
                  ON t.target_kind = 'belief'
                 AND b.id = t.target_id
                JOIN messages m
                  ON m.id = ANY(b.evidence_ids)
                WHERE t.session_id = %s
                  AND m.conversation_id = %s
            )
        """,
        (session_id, conversation_id, session_id, conversation_id),
    ).fetchone()
    return bool(row and row[0])


def _check_message_reachable(
    conn: psycopg.Connection,
    *,
    session_id: str,
    conversation_id: str,
) -> None:
    if not _session_can_reach_conversation(
        conn,
        session_id=session_id,
        conversation_id=conversation_id,
    ):
        raise HTTPException(status_code=404, detail="message not reachable from session")


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------


def create_app() -> FastAPI:
    """Build the FastAPI app with all routes registered."""
    app = FastAPI(
        title="Engram interview",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )

    static_dir = _resource_dir("static")
    templates_dir = _resource_dir("templates")
    templates = Jinja2Templates(directory=str(templates_dir))

    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    # ----- GET / -----
    @app.get("/", response_class=HTMLResponse)
    def index(
        request: Request,
        conn: psycopg.Connection = Depends(_get_conn),
    ) -> Response:
        sessions = _load_open_sessions(conn)
        return templates.TemplateResponse(
            request,
            "index.html",
            {
                "open_sessions": sessions,
                "empty_corpus_banner": None,
                "save_and_quit_banner": request.query_params.get("banner"),
            },
        )

    # ----- POST /sessions -----
    @app.post("/sessions")
    def post_sessions(
        request: Request,
        n: int = Form(...),
        seed: int | None = Form(default=None),
        conn: psycopg.Connection = Depends(_get_conn),
        _origin: None = Depends(_get_origin_check),
    ) -> Response:
        if n < 1:
            raise HTTPException(status_code=422, detail={"error": "n must be >= 1"})
        actual_seed = seed if seed is not None else int.from_bytes(os.urandom(4), "big")
        session_id = insert_session(
            conn,
            seed=actual_seed,
            sampler_id=SAMPLER_ID,
            sampler_version=SAMPLER_VERSION,
            strata_weights={},
        )
        active_learning_signal = get_active_learning_signal_version(conn)
        sampler = GoldLabelSampler(
            conn,
            seed=actual_seed,
            include_superseded=False,
            ignore_cooldown=False,
            active_learning_signal_version=active_learning_signal,
        )
        sampled = sampler.sample(n)
        if not sampled:
            # F029: no targets — close the session and re-render with the
            # diagnostic banner. Spec recommends mark_session_completed so the
            # row is never DELETEd.
            mark_session_completed(conn, session_id)
            conn.commit()
            sessions = _load_open_sessions(conn)
            return templates.TemplateResponse(
                request,
                "index.html",
                {
                    "open_sessions": sessions,
                    "empty_corpus_banner": (
                        "no targets matched (empty corpus, all on cooldown, "
                        "or current_beliefs not refreshed)"
                    ),
                    "save_and_quit_banner": None,
                },
                status_code=200,
            )
        _insert_session_targets(conn, session_id, sampled)
        conn.commit()
        return RedirectResponse(
            url=f"/sessions/{session_id}/q/1", status_code=303
        )

    # ----- GET /sessions/{id} (resume) -----
    @app.get("/sessions/{session_id}")
    def get_session(
        session_id: str,
        conn: psycopg.Connection = Depends(_get_conn),
    ) -> Response:
        if not _session_exists(conn, session_id):
            raise HTTPException(status_code=404, detail="session not found")
        row = conn.execute(
            """
            SELECT MIN(t.idx)
            FROM gold_label_session_targets t
            LEFT JOIN gold_labels gl
              ON gl.session_id = t.session_id
             AND gl.target_id::text = t.target_id::text
            WHERE t.session_id = %s
              AND gl.id IS NULL
            """,
            (session_id,),
        ).fetchone()
        next_table_idx = row[0] if row is not None else None
        if next_table_idx is None:
            return RedirectResponse(url="/", status_code=303)
        return RedirectResponse(
            url=f"/sessions/{session_id}/q/{int(next_table_idx) + 1}",
            status_code=303,
        )

    # ----- GET /sessions/{id}/q/{idx} -----
    @app.get("/sessions/{session_id}/q/{idx}", response_class=HTMLResponse)
    def get_question(
        request: Request,
        session_id: str,
        idx: int,
        conn: psycopg.Connection = Depends(_get_conn),
    ) -> Response:
        if idx < 1:
            raise HTTPException(status_code=404, detail="idx out of range")
        n_targets = _session_n_targets(conn, session_id)
        if n_targets is None or n_targets == 0:
            raise HTTPException(status_code=404, detail="session has no targets")
        if idx > n_targets:
            raise HTTPException(status_code=404, detail="idx out of range")
        target_row = _load_session_target(conn, session_id, idx - 1)
        if target_row is None:
            raise HTTPException(status_code=404, detail="target row missing")
        return _render_question_template(
            request,
            templates,
            conn=conn,
            session_id=session_id,
            url_idx=idx,
            target_row=target_row,
            n_targets=n_targets,
        )

    # ----- POST /sessions/{id}/q/{idx}/verdict -----
    @app.post("/sessions/{session_id}/q/{idx}/verdict")
    def post_verdict(
        request: Request,
        session_id: str,
        idx: int,
        verdict: str = Form(...),
        rationale: str | None = Form(default=None),
        conn: psycopg.Connection = Depends(_get_conn),
        _origin: None = Depends(_get_origin_check),
    ) -> Response:
        if verdict not in VERDICT_VALID:
            raise HTTPException(
                status_code=422, detail={"error": "unknown verdict"}
            )
        n_targets = _session_n_targets(conn, session_id)
        if n_targets is None or n_targets == 0:
            raise HTTPException(status_code=404, detail="session not found")
        if idx < 1 or idx > n_targets:
            raise HTTPException(status_code=404, detail="idx out of range")
        target_row = _load_session_target(conn, session_id, idx - 1)
        if target_row is None:
            raise HTTPException(status_code=404, detail="target row missing")
        sampled = _session_target_to_sampled(target_row)
        # Single-click verdicts (true / skip) commit with rationale=None even
        # if a stray empty string came in. Two-click verdicts pass the
        # rationale verbatim (empty string is allowed for ``unsure``).
        rationale_value: str | None
        if verdict in {"true", "skip"}:
            rationale_value = None
        else:
            rationale_value = (rationale or "").strip()
            if verdict in _RATIONALE_REQUIRED_VERDICTS and not rationale_value:
                raise HTTPException(
                    status_code=422,
                    detail={"error": "rationale_required", "verdict": verdict},
                )

        agent = InterviewAgent(
            conn, sampler_id=SAMPLER_ID, sampler_version=SAMPLER_VERSION
        )
        try:
            agent.record_verdict(
                session_id, sampled, verdict, rationale=rationale_value
            )
            conn.commit()
        except (GoldLabelStorageError, GoldLabelVerdictError) as exc:
            try:
                conn.rollback()
            except psycopg.Error:
                pass
            return _render_question_template(
                request,
                templates,
                conn=conn,
                session_id=session_id,
                url_idx=idx,
                target_row=target_row,
                n_targets=n_targets,
                error_banner=str(exc),
            )

        if idx >= n_targets:
            redirect_url = f"/sessions/{session_id}/complete"
        else:
            redirect_url = f"/sessions/{session_id}/q/{idx + 1}"
        # Empty body + HX-Redirect tells htmx to follow. We also set Location
        # so direct (non-htmx) form posts work.
        resp = Response(status_code=200)
        resp.headers["HX-Redirect"] = redirect_url
        return resp

    # ----- GET /sessions/{id}/messages/{message_id} -----
    @app.get(
        "/sessions/{session_id}/messages/{message_id}",
        response_class=HTMLResponse,
    )
    def get_message(
        request: Request,
        session_id: str,
        message_id: str,
        conn: psycopg.Connection = Depends(_get_conn),
    ) -> Response:
        row = conn.execute(
            """
            SELECT
                m.id::text,
                m.role,
                m.created_at,
                m.content_text,
                m.source_kind::text,
                m.privacy_tier,
                m.conversation_id::text,
                c.title
            FROM messages m
            LEFT JOIN conversations c ON c.id = m.conversation_id
            WHERE m.id = %s
            """,
            (message_id,),
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="message not found")
        (
            msg_id,
            role,
            created_at,
            content,
            source_kind,
            privacy_tier,
            conv_id,
            conv_title,
        ) = row
        _check_message_reachable(conn, session_id=session_id, conversation_id=conv_id)
        _check_tier_1(int(privacy_tier), message_id=msg_id)
        excerpt = {
            "id": msg_id,
            "role": role,
            "created_at": created_at,
            "content": content or "",
            "source_kind": source_kind,
            "conv_title": conv_title,
        }
        return templates.TemplateResponse(
            request,
            "_evidence_excerpt.html",
            {
                "excerpt": excerpt,
                "full": True,
                "session_id": session_id,
            },
        )

    # ----- GET /sessions/{id}/messages/{message_id}/context -----
    @app.get(
        "/sessions/{session_id}/messages/{message_id}/context",
        response_class=HTMLResponse,
    )
    def get_message_context(
        request: Request,
        session_id: str,
        message_id: str,
        before: int = 2,
        after: int = 2,
        conn: psycopg.Connection = Depends(_get_conn),
    ) -> Response:
        if before < 0 or after < 0:
            raise HTTPException(status_code=422, detail={"error": "negative window"})
        if before + after > CONTEXT_BEFORE_AFTER_CAP:
            raise HTTPException(
                status_code=422,
                detail={
                    "error": "context_window_too_large",
                    "cap": CONTEXT_BEFORE_AFTER_CAP,
                },
            )
        anchor = conn.execute(
            """
            SELECT conversation_id, sequence_index, privacy_tier
            FROM messages WHERE id = %s
            """,
            (message_id,),
        ).fetchone()
        if anchor is None:
            raise HTTPException(status_code=404, detail="message not found")
        conv_id, anchor_seq, anchor_tier = anchor
        _check_message_reachable(conn, session_id=session_id, conversation_id=str(conv_id))
        if int(anchor_tier) > TIER_CEILING:
            _check_tier_1(int(anchor_tier), message_id=message_id)

        rows = conn.execute(
            """
            SELECT id::text, role, created_at, content_text, source_kind::text,
                   privacy_tier, sequence_index
            FROM messages
            WHERE conversation_id = %s
              AND sequence_index BETWEEN %s AND %s
            ORDER BY sequence_index
            """,
            (conv_id, int(anchor_seq) - before, int(anchor_seq) + after),
        ).fetchall()
        max_tier = 0
        items: list[dict[str, Any]] = []
        for r in rows:
            tier = int(r[5])
            if tier > max_tier:
                max_tier = tier
            content = r[3] or ""
            if len(content) > EVIDENCE_EXCERPT_LIMIT:
                content = content[:EVIDENCE_EXCERPT_LIMIT].rstrip() + "…"
            items.append(
                {
                    "id": r[0],
                    "role": r[1],
                    "created_at": r[2],
                    "content": content,
                    "source_kind": r[4],
                    "conv_title": None,
                }
            )
        if max_tier > TIER_CEILING:
            _check_tier_1(max_tier, message_id=message_id)
        # Render each row with the existing partial; concatenate.
        parts: list[str] = []
        for excerpt in items:
            tpl = templates.get_template("_evidence_excerpt.html")
            parts.append(
                tpl.render(
                    request=request,
                    excerpt=excerpt,
                    full=True,
                    session_id=session_id,
                )
            )
        return HTMLResponse("\n".join(parts))

    # ----- GET /sessions/{id}/q/{idx}/evidence/all -----
    @app.get(
        "/sessions/{session_id}/q/{idx}/evidence/all",
        response_class=HTMLResponse,
    )
    def get_evidence_all(
        request: Request,
        session_id: str,
        idx: int,
        conn: psycopg.Connection = Depends(_get_conn),
    ) -> Response:
        n_targets = _session_n_targets(conn, session_id)
        if n_targets is None or n_targets == 0:
            raise HTTPException(status_code=404, detail="session not found")
        if idx < 1 or idx > n_targets:
            raise HTTPException(status_code=404, detail="idx out of range")
        target_row = _load_session_target(conn, session_id, idx - 1)
        if target_row is None:
            raise HTTPException(status_code=404, detail="target row missing")
        sampled = _session_target_to_sampled(target_row)
        display = fetch_target_display(conn, sampled, evidence_limit=None)
        # Enforce Tier-1 carry across all rows we are about to render.
        for excerpt in display.get("excerpts") or []:
            tier = _message_tier(conn, excerpt["id"])
            if tier is not None:
                _check_tier_1(tier, message_id=excerpt["id"])
        parts: list[str] = []
        tpl = templates.get_template("_evidence_excerpt.html")
        for excerpt in display.get("excerpts") or []:
            parts.append(
                tpl.render(
                    request=request,
                    excerpt=excerpt,
                    full=False,
                    session_id=session_id,
                )
            )
        return HTMLResponse("\n".join(parts))

    # ----- POST /sessions/{id}/save-and-quit -----
    @app.post("/sessions/{session_id}/save-and-quit")
    def post_save_and_quit(
        session_id: str,
        conn: psycopg.Connection = Depends(_get_conn),
        _origin: None = Depends(_get_origin_check),
    ) -> Response:
        if not _session_exists(conn, session_id):
            raise HTTPException(status_code=404, detail="session not found")
        # No verdict commit. Discard any in-progress rationale text.
        banner = (
            f"Saved and quit. Resume with: engram phase3 interview resume "
            f"--session-id {session_id}"
        )
        url = f"/?banner={banner}"
        return RedirectResponse(url=url, status_code=303)

    # ----- POST /sessions/{id}/complete -----
    @app.post("/sessions/{session_id}/complete")
    def post_complete(
        session_id: str,
        conn: psycopg.Connection = Depends(_get_conn),
        _origin: None = Depends(_get_origin_check),
    ) -> Response:
        if not _session_exists(conn, session_id):
            raise HTTPException(status_code=404, detail="session not found")
        mark_session_completed(conn, session_id)
        conn.commit()
        return RedirectResponse(url="/", status_code=303)

    # GET /sessions/{id}/complete is also wired so an HX-Redirect from the
    # verdict POST can land on this URL via a normal browser navigation; it
    # simply renders index after marking the session completed.
    @app.get("/sessions/{session_id}/complete")
    def get_complete(
        request: Request,
        session_id: str,
        conn: psycopg.Connection = Depends(_get_conn),
    ) -> Response:
        if _session_exists(conn, session_id):
            mark_session_completed(conn, session_id)
            conn.commit()
        return RedirectResponse(url="/", status_code=303)

    # ----- POST /sessions/{id}/abandon -----
    @app.post("/sessions/{session_id}/abandon")
    def post_abandon(
        session_id: str,
        conn: psycopg.Connection = Depends(_get_conn),
        _origin: None = Depends(_get_origin_check),
    ) -> Response:
        if not _session_exists(conn, session_id):
            raise HTTPException(status_code=404, detail="session not found")
        _abandon_session(conn, session_id, operator_note="abandoned via web")
        conn.commit()
        return RedirectResponse(url="/", status_code=303)

    @app.exception_handler(HTTPException)
    def _http_exc_handler(_request: Request, exc: HTTPException) -> Response:
        body: Any = exc.detail
        if isinstance(body, dict):
            return JSONResponse(status_code=exc.status_code, content=body)
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": str(body) if body is not None else "http_error"},
        )

    return app


app = create_app()


__all__ = [
    "ALLOWED_ORIGIN_HOSTS",
    "CONTEXT_BEFORE_AFTER_CAP",
    "TIER_CEILING",
    "app",
    "create_app",
]
