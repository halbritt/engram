"""TestClient route coverage for the RFC 0027 / Spec 0027 web UI.

Uses FastAPI's ``TestClient`` plus the real-DB ``conn`` fixture from
``tests/conftest.py``. Tests skip cleanly when ``ENGRAM_TEST_DATABASE_URL`` is
unset.

The ``mark_session_completed`` helper used by the production routes is the
sync version from ``engram.interview.storage``; the tests do not monkeypatch
storage so the trigger-rejection banner test depends on real triggers firing.
"""

from __future__ import annotations

import importlib
import os
import sys
import uuid
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from psycopg.types.json import Jsonb

from engram.consolidator import CONSOLIDATOR_MODEL_VERSION, CONSOLIDATOR_PROMPT_VERSION
from engram.consolidator.transitions import BeliefPayload, insert_belief
from engram.extractor import EXTRACTION_PROMPT_VERSION, EXTRACTION_REQUEST_PROFILE_VERSION
from engram.interview import web as web_module
from engram.interview.storage import (
    insert_label,
    insert_session,
)

# ---------------------------------------------------------------------------
# DB seed helpers (mirrors ``tests/test_interview_storage.py`` patterns to keep
# the web tests self-contained — those helpers in turn import from
# ``test_phase2_segments`` and ``test_phase3_claims_beliefs``).
# ---------------------------------------------------------------------------


# Add tests/ to sys.path so the helper modules import cleanly when pytest is
# invoked from the repo root.
_TESTS_DIR = Path(__file__).resolve().parent
if str(_TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(_TESTS_DIR))

from test_phase2_segments import (  # noqa: E402  (sys.path tweak above)
    insert_conversation,
    insert_generation,
    insert_segment_row,
)
from test_phase3_claims_beliefs import insert_extracted_claim  # noqa: E402

CLAIM_VERSION_TRIPLE = {
    "extraction_prompt_version": EXTRACTION_PROMPT_VERSION,
    "extraction_model_version": "model-a",
    "request_profile_version": EXTRACTION_REQUEST_PROFILE_VERSION,
}

BELIEF_VERSION_TRIPLE = {
    "consolidation_prompt_version": CONSOLIDATOR_PROMPT_VERSION,
    "consolidation_model_version": CONSOLIDATOR_MODEL_VERSION,
    "request_profile_version": "interview.v1.d079.initial",
}


def _seed_claim(
    conn: Any,
    *,
    message_tier: int = 1,
    subject_text: str = "user",
    predicate: str = "drives",
    object_text: str = "Subaru",
) -> tuple[str, list[str]]:
    """Return ``(claim_id, message_ids)``."""
    stability_class = _stability_class_for_predicate(conn, predicate)
    conv_id, msg_ids = insert_conversation(
        conn, [("user", f"{subject_text} {predicate} {object_text}", message_tier)]
    )
    gen_id = insert_generation(conn, conv_id)
    seg_id = insert_segment_row(conn, gen_id, conv_id, msg_ids, active=True)
    _, claim_id = insert_extracted_claim(
        conn,
        segment_id=seg_id,
        generation_id=gen_id,
        conversation_id=conv_id,
        evidence_ids=msg_ids,
        predicate=predicate,
        object_text=object_text,
        subject_text=subject_text,
        stability_class=stability_class,
    )
    return claim_id, msg_ids


def _stability_class_for_predicate(conn: Any, predicate: str) -> str:
    """Return the canonical stability class for a seeded predicate."""
    row = conn.execute(
        "SELECT stability_class FROM predicate_vocabulary WHERE predicate = %s",
        (predicate,),
    ).fetchone()
    if row is None:
        raise AssertionError(f"test predicate {predicate!r} is not in predicate_vocabulary")
    return row[0]


def _seed_belief(conn: Any, *, privacy_tier: int = 1) -> str:
    conv_id, msg_ids = insert_conversation(conn, [("user", "I prefer vim", 1)])
    gen_id = insert_generation(conn, conv_id)
    seg_id = insert_segment_row(conn, gen_id, conv_id, msg_ids, active=True)
    _, claim_id = insert_extracted_claim(
        conn,
        segment_id=seg_id,
        generation_id=gen_id,
        conversation_id=conv_id,
        evidence_ids=msg_ids,
        predicate="prefers",
        object_text="vim",
    )
    payload = BeliefPayload(
        subject_text="user",
        predicate="prefers",
        object_text="vim",
        object_json=None,
        valid_from=datetime.now(UTC),
        valid_to=None,
        observed_at=datetime.now(UTC),
        extracted_at=datetime.now(UTC),
        status="candidate",
        confidence=0.7,
        evidence_ids=[msg_ids[0]],
        claim_ids=[claim_id],
        prompt_version=BELIEF_VERSION_TRIPLE["consolidation_prompt_version"],
        model_version=BELIEF_VERSION_TRIPLE["consolidation_model_version"],
        privacy_tier=privacy_tier,
        raw_payload={"source": "rfc0027-web-test"},
        score_breakdown={
            "mean": 0.7,
            "max": 0.7,
            "min": 0.7,
            "count": 1,
            "stddev": 0,
        },
    )
    return insert_belief(conn, payload)


def _create_session_with_one_claim(
    conn: Any,
    *,
    n: int = 3,
    message_tier: int = 1,
    subject_text: str = "user",
    predicate: str = "drives",
    object_text: str = "Subaru",
) -> tuple[str, str, list[str]]:
    """Create a fresh session row + one materialized claim target at idx=0.

    Returns ``(session_id, claim_id, message_ids)``.
    """
    claim_id, msg_ids = _seed_claim(
        conn,
        message_tier=message_tier,
        subject_text=subject_text,
        predicate=predicate,
        object_text=object_text,
    )
    session_id = insert_session(
        conn,
        seed=42,
        sampler_id="stratified",
        sampler_version="stratified.v1.d079.initial",
        strata_weights={},
    )
    # Materialize one claim row at idx=0; pad to ``n`` with extra claims.
    rows = [(claim_id, msg_ids)]
    for _ in range(n - 1):
        extra_claim, extra_msg_ids = _seed_claim(conn)
        rows.append((extra_claim, extra_msg_ids))
    snapshot_id = str(uuid.uuid4())
    for idx, (cid, _) in enumerate(rows):
        confidence, observed_at, stability_class = conn.execute(
            "SELECT confidence, extracted_at, stability_class FROM claims WHERE id = %s",
            (cid,),
        ).fetchone()
        conn.execute(
            """
            INSERT INTO gold_label_session_targets (
                session_id, idx, target_kind, target_id,
                candidate_pool_snapshot_id,
                extraction_prompt_version, extraction_model_version,
                consolidation_prompt_version, consolidation_model_version,
                request_profile_version,
                stability_class, conf_band, recency_band, belief_status,
                confidence, observed_at
            )
            VALUES (
                %s, %s, 'claim', %s,
                %s,
                %s, %s,
                NULL, NULL,
                %s,
                %s, '0.6-0.8', '<7d', NULL,
                %s, %s
            )
            """,
            (
                session_id,
                idx,
                cid,
                snapshot_id,
                CLAIM_VERSION_TRIPLE["extraction_prompt_version"],
                CLAIM_VERSION_TRIPLE["extraction_model_version"],
                CLAIM_VERSION_TRIPLE["request_profile_version"],
                stability_class,
                confidence,
                observed_at,
            ),
        )
    return session_id, claim_id, msg_ids


def _create_session_with_one_belief(conn: Any, *, belief_tier: int = 1) -> tuple[str, str]:
    """Create a fresh session row + one materialized belief target at idx=0."""
    belief_id = _seed_belief(conn, privacy_tier=belief_tier)
    session_id = insert_session(
        conn,
        seed=43,
        sampler_id="stratified",
        sampler_version="stratified.v1.d079.initial",
        strata_weights={},
    )
    confidence, observed_at, status = conn.execute(
        "SELECT confidence, observed_at, status FROM beliefs WHERE id = %s",
        (belief_id,),
    ).fetchone()
    conn.execute(
        """
        INSERT INTO gold_label_session_targets (
            session_id, idx, target_kind, target_id,
            candidate_pool_snapshot_id,
            extraction_prompt_version, extraction_model_version,
            consolidation_prompt_version, consolidation_model_version,
            request_profile_version,
            stability_class, conf_band, recency_band, belief_status,
            confidence, observed_at
        )
        VALUES (
            %s, 0, 'belief', %s,
            %s,
            NULL, NULL,
            %s, %s,
            %s,
            'preference', '0.6-0.8', '<7d', %s,
            %s, %s
        )
        """,
        (
            session_id,
            belief_id,
            str(uuid.uuid4()),
            BELIEF_VERSION_TRIPLE["consolidation_prompt_version"],
            BELIEF_VERSION_TRIPLE["consolidation_model_version"],
            BELIEF_VERSION_TRIPLE["request_profile_version"],
            status,
            confidence,
            observed_at,
        ),
    )
    return session_id, belief_id


# ---------------------------------------------------------------------------
# TestClient fixture
# ---------------------------------------------------------------------------


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch, conn: Any) -> Iterator[TestClient]:
    """FastAPI TestClient wired to the real-DB ``conn`` fixture.

    Patches ``engram.interview.web._get_conn`` so every route shares a
    connection with the test body, letting the test inspect committed rows
    without spinning up a separate connection.
    """

    def _override_get_conn() -> Iterator[Any]:
        yield conn

    web_module.app.dependency_overrides[web_module._get_conn] = _override_get_conn
    try:
        yield TestClient(web_module.app)
    finally:
        web_module.app.dependency_overrides.pop(web_module._get_conn, None)


def _format_origin_host(host: str) -> str:
    """Return a URL/Host-header-safe loopback host literal."""
    if ":" in host and not host.startswith("["):
        return f"[{host}]"
    return host


def _origin_headers(host: str = "127.0.0.1", port: int = 8765) -> dict[str, str]:
    origin_host = _format_origin_host(host)
    return {
        "host": f"{origin_host}:{port}",
        "origin": f"http://{origin_host}:{port}",
        "sec-fetch-site": "same-origin",
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_index_renders_no_open_sessions(client: TestClient) -> None:
    resp = client.get("/")
    assert resp.status_code == 200
    body = resp.text
    assert "Engram interview — open sessions" in body
    assert "No open sessions" in body
    assert "Start session" in body
    assert 'data-future="true"' in body
    assert "Entities (future)" in body
    assert '<span class="brand-name">Engram local</span>' in body
    assert 'class="surface-tab is-active"' in body
    assert (
        'href="http://127.0.0.1:8770/segments?remaining=1&amp;reviewable=1">Bench review</a>'
    ) in body
    assert '<script src="/shared-static/keyboard.js" defer></script>' in body
    assert "local-only · loopback bind: 127.0.0.1:8765 · no network egress." in body
    assert "Engram runs entirely on your machine. No cloud service. No telemetry. No CDN." in body
    assert (
        "Promotion, acceptance, and entity canonicalization arrive in Phase 4. "
        "The interview surface never flips a belief status."
    ) in body
    assert "banner-status" not in body


def test_index_uses_configured_bench_url(conn: Any) -> None:
    def _override_get_conn() -> Iterator[Any]:
        yield conn

    app = web_module.create_app(bench_url="http://127.0.0.1:9999/review")
    app.dependency_overrides[web_module._get_conn] = _override_get_conn
    try:
        with TestClient(app) as local_client:
            resp = local_client.get("/")
    finally:
        app.dependency_overrides.pop(web_module._get_conn, None)

    assert resp.status_code == 200
    assert 'href="http://127.0.0.1:9999/review">Bench review</a>' in resp.text


def test_create_app_uses_configured_bind_address(conn: Any) -> None:
    def _override_get_conn() -> Iterator[Any]:
        yield conn

    app = web_module.create_app(port=9876)
    app.dependency_overrides[web_module._get_conn] = _override_get_conn
    try:
        with TestClient(app) as local_client:
            resp = local_client.get("/")
    finally:
        app.dependency_overrides.pop(web_module._get_conn, None)

    assert resp.status_code == 200
    assert "local-only · loopback bind: 127.0.0.1:9876 · no network egress." in resp.text


def test_index_renders_shared_future_slot(client: TestClient) -> None:
    resp = client.get("/")
    assert resp.status_code == 200
    body = resp.text
    assert '<section class="future-slot" data-future="true" aria-disabled="true">' in body
    assert "Future / backlog" in body
    assert "Phase 4 work is not yet built. Tracked in RFC 0021 / D044 / D069 / D079." in body


def test_index_renders_open_sessions_with_progress(client: TestClient, conn: Any) -> None:
    session_id, claim_id, _ = _create_session_with_one_claim(conn, n=3)
    # Insert one verdict so K=1, N=3.
    insert_label(
        conn,
        session_id=session_id,
        target_kind="claim",
        target_id=claim_id,
        version_triple=CLAIM_VERSION_TRIPLE,
        prompt_template_version="interview.claim.v1.d079.initial",
        prompt_template_path="prompts/interview/claim_v1.md",
        prompt_text="Q: Is this an accurate paraphrase?",
        verdict="true",
        rationale=None,
        sampler_id="stratified",
        sampler_version="stratified.v1.d079.initial",
        candidate_pool_snapshot_id=str(uuid.uuid4()),
        active_learning_signal_version=None,
        stability_class="preference",
        conf_band="0.6-0.8",
        recency_band="<7d",
        belief_status=None,
        asked_at=datetime.now(UTC),
        answered_at=datetime.now(UTC),
    )
    resp = client.get("/")
    assert resp.status_code == 200
    body = resp.text
    assert "1/3 answered" in body
    assert session_id in body


def test_get_session_resume_uses_frozen_version_triple(client: TestClient, conn: Any) -> None:
    session_id, claim_id, _ = _create_session_with_one_claim(conn, n=1)
    asked = datetime.now(UTC)
    conn.execute(
        """
        INSERT INTO gold_labels (
            session_id, target_kind, target_id,
            extraction_prompt_version, extraction_model_version,
            consolidation_prompt_version, consolidation_model_version,
            request_profile_version,
            prompt_template_version, prompt_template_path, prompt_text,
            evidence_excerpt, verdict, rationale,
            sampler_id, sampler_version, candidate_pool_snapshot_id,
            active_learning_signal_version, stability_class, conf_band,
            recency_band, belief_status, strata_extra,
            asked_at, answered_at, privacy_tier
        )
        VALUES (
            %s, 'claim', %s,
            %s, 'model-b',
            NULL, NULL,
            %s,
            'interview.claim.v1.d079.initial',
            'prompts/interview/claim_v1.md',
            'Q',
            NULL, 'true', NULL,
            'stratified', 'stratified.v1.d079.initial', %s,
            NULL, 'preference', '0.6-0.8',
            '<7d', NULL, %s,
            %s, %s, NULL
        )
        """,
        (
            session_id,
            claim_id,
            CLAIM_VERSION_TRIPLE["extraction_prompt_version"],
            CLAIM_VERSION_TRIPLE["request_profile_version"],
            str(uuid.uuid4()),
            Jsonb({}),
            asked,
            asked,
        ),
    )

    resp = client.get(f"/sessions/{session_id}", follow_redirects=False)
    assert resp.status_code == 303
    assert resp.headers["location"] == f"/sessions/{session_id}/q/1"

    index_resp = client.get("/")
    assert index_resp.status_code == 200
    assert "0/1 answered" in index_resp.text

    question_resp = client.get(f"/sessions/{session_id}/q/1")
    assert question_resp.status_code == 200
    assert "0/1 answered" in question_resp.text


def test_get_session_targetless_open_session_requires_abandon(
    client: TestClient, conn: Any
) -> None:
    session_id = insert_session(
        conn,
        seed=44,
        sampler_id="stratified",
        sampler_version="stratified.v1.d079.initial",
        strata_weights={},
    )

    index_resp = client.get("/")
    assert index_resp.status_code == 200
    assert "0/0 answered" in index_resp.text

    resume_resp = client.get(f"/sessions/{session_id}", follow_redirects=False)
    assert resume_resp.status_code == 409
    body = resume_resp.json()
    assert body.get("error") == "session_has_no_materialized_targets"
    assert body.get("action") == "abandon_required"


def test_post_sessions_redirects_to_q1(
    client: TestClient, conn: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Seed at least one claim so the sampler returns something.
    _seed_claim(conn)
    resp = client.post(
        "/sessions",
        data={"n": 1, "seed": 7},
        headers=_origin_headers(),
        follow_redirects=False,
    )
    assert resp.status_code == 303, resp.text
    location = resp.headers["location"]
    assert "/q/1" in location
    # Verify gold_label_session_targets has one row.
    sid = location.split("/sessions/")[1].split("/")[0]
    rows = conn.execute(
        "SELECT count(*) FROM gold_label_session_targets WHERE session_id = %s",
        (sid,),
    ).fetchone()
    assert rows[0] == 1


def test_post_sessions_empty_corpus_renders_diagnostic(client: TestClient, conn: Any) -> None:
    # No claims/beliefs seeded, so sampler returns [].
    resp = client.post(
        "/sessions",
        data={"n": 5, "seed": 7},
        headers=_origin_headers(),
        follow_redirects=False,
    )
    assert resp.status_code == 200, resp.text
    body = resp.text
    assert (
        "No targets matched. The candidate pool may be empty, every target may be "
        "on cooldown, or current_beliefs has not been refreshed."
    ) in body
    assert "engram phase4 refresh-current-beliefs" in body
    assert 'data-copy-command="engram phase4 refresh-current-beliefs"' in body
    assert 'class="banner banner-warn"' in body
    assert "banner-status" not in body
    assert "querySelectorAll('[data-copy-command]')" not in body
    # Session row exists but is marked completed (or absent — implementation
    # choice). The spec recommends mark_session_completed, which keeps it out
    # of the open-sessions list.
    open_count = conn.execute(
        "SELECT count(*) FROM gold_label_sessions WHERE completed_at IS NULL",
    ).fetchone()[0]
    assert open_count == 0


def test_get_question_renders(client: TestClient, conn: Any) -> None:
    session_id, _claim_id, _ = _create_session_with_one_claim(conn, n=2)
    resp = client.get(f"/sessions/{session_id}/q/1")
    assert resp.status_code == 200, resp.text
    body = resp.text
    # Header line carries [1/2].
    assert "[1/2]" in body
    assert "conf=0.90" in body
    assert "conf=0.00" not in body
    assert (
        "Verdict is an advisory eval input. It does not flip belief status "
        "(D044) or gate extraction / consolidation (D069)."
    ) in body
    assert "※ Advisory" in body
    assert "extraction=" in body
    assert "consolidation=" in body
    assert "profile=" in body
    assert "show conversation context" in body
    # Six verdict buttons present.
    for v in ("true", "false", "stale", "unsupported", "unsure", "skip"):
        assert f'data-verdict="{v}"' in body
    # Accesskeys: t, f, s, n, u, k.
    for letter in ("t", "f", "s", "n", "u", "k"):
        assert f'accesskey="{letter}"' in body
        assert f'data-key="{letter}"' in body
    # aria-label carries verdict gloss verbatim from the vocabulary table.
    rows = conn.execute("SELECT verdict, gloss FROM gold_label_verdict_vocabulary").fetchall()
    for verdict, gloss in rows:
        assert gloss in body, f"missing gloss for {verdict}"


def test_get_question_enforces_tier_1_evidence(client: TestClient, conn: Any) -> None:
    session_id, _claim_id, _msg_ids = _create_session_with_one_claim(conn, n=1, message_tier=2)
    resp = client.get(f"/sessions/{session_id}/q/1")
    assert resp.status_code == 403
    body = resp.json()
    assert body.get("error") == "privacy_tier_ceiling"
    assert body.get("tier") == 2


def test_question_renders_predicate_intent_and_warning(client: TestClient, conn: Any) -> None:
    session_id, _claim_id, _ = _create_session_with_one_claim(
        conn,
        n=1,
        subject_text="Hobnob",
        predicate="has_name",
        object_text="Hobnob",
    )
    resp = client.get(f"/sessions/{session_id}/q/1")
    assert resp.status_code == 200, resp.text
    body = resp.text
    assert "intent: legal or preferred name (persons only)" in body
    assert "[warning]" in body
    assert "looks like a place/business" in body
    assert 'class="banner-warn"' in body


def test_post_verdict_true_single_click_commit(client: TestClient, conn: Any) -> None:
    session_id, _claim_id, _ = _create_session_with_one_claim(conn, n=3)
    resp = client.post(
        f"/sessions/{session_id}/q/1/verdict",
        data={"verdict": "true", "rationale": ""},
        headers=_origin_headers(),
    )
    assert resp.status_code == 200, resp.text
    assert resp.headers.get("hx-redirect") == f"/sessions/{session_id}/q/2"
    rows = conn.execute(
        "SELECT verdict, rationale, evidence_excerpt FROM gold_labels WHERE session_id = %s",
        (session_id,),
    ).fetchall()
    assert len(rows) == 1
    assert rows[0][0] == "true"
    assert rows[0][1] is None
    assert rows[0][2] is None


def test_post_verdict_skip_single_click_commit(client: TestClient, conn: Any) -> None:
    session_id, _claim_id, _ = _create_session_with_one_claim(conn, n=2)
    resp = client.post(
        f"/sessions/{session_id}/q/1/verdict",
        data={"verdict": "skip", "rationale": ""},
        headers=_origin_headers(),
    )
    assert resp.status_code == 200, resp.text
    assert resp.headers.get("hx-redirect") == f"/sessions/{session_id}/q/2"
    row = conn.execute(
        "SELECT verdict, rationale FROM gold_labels WHERE session_id = %s",
        (session_id,),
    ).fetchone()
    assert row == ("skip", None)


def test_post_verdict_false_two_click_flow(client: TestClient, conn: Any) -> None:
    session_id, _claim_id, _ = _create_session_with_one_claim(conn, n=3)
    resp = client.post(
        f"/sessions/{session_id}/q/1/verdict",
        data={"verdict": "false", "rationale": "correct value text"},
        headers=_origin_headers(),
    )
    assert resp.status_code == 200, resp.text
    assert resp.headers.get("hx-redirect", "").endswith("/q/2")
    row = conn.execute(
        "SELECT verdict, rationale FROM gold_labels WHERE session_id = %s",
        (session_id,),
    ).fetchone()
    assert row == ("false", "correct value text")


def test_post_verdict_blank_rationale_rejected_server_side(client: TestClient, conn: Any) -> None:
    session_id, _claim_id, _ = _create_session_with_one_claim(conn, n=3)
    resp = client.post(
        f"/sessions/{session_id}/q/1/verdict",
        data={"verdict": "false", "rationale": "   "},
        headers=_origin_headers(),
    )
    assert resp.status_code == 422
    assert resp.json() == {"error": "rationale_required", "verdict": "false"}
    rows = conn.execute(
        "SELECT count(*) FROM gold_labels WHERE session_id = %s",
        (session_id,),
    ).fetchone()
    assert rows[0] == 0


def test_post_verdict_unsure_allows_blank_rationale(client: TestClient, conn: Any) -> None:
    session_id, _claim_id, _ = _create_session_with_one_claim(conn, n=2)
    resp = client.post(
        f"/sessions/{session_id}/q/1/verdict",
        data={"verdict": "unsure", "rationale": "   "},
        headers=_origin_headers(),
    )
    assert resp.status_code == 200, resp.text
    assert resp.headers.get("hx-redirect") == f"/sessions/{session_id}/q/2"
    row = conn.execute(
        "SELECT verdict, rationale FROM gold_labels WHERE session_id = %s",
        (session_id,),
    ).fetchone()
    assert row == ("unsure", None)


def test_post_verdict_trigger_rejection_renders_banner(client: TestClient, conn: Any) -> None:
    session_id = insert_session(
        conn,
        seed=1,
        sampler_id="stratified",
        sampler_version="stratified.v1.d079.initial",
        strata_weights={},
    )
    # Insert a session_target whose target_id is a UUID that does NOT exist in
    # claims; the gold_labels validate-target trigger raises P0001 on the
    # commit attempt.
    bogus_target_id = str(uuid.uuid4())
    snapshot_id = str(uuid.uuid4())
    conn.execute(
        """
        INSERT INTO gold_label_session_targets (
            session_id, idx, target_kind, target_id,
            candidate_pool_snapshot_id,
            extraction_prompt_version, extraction_model_version,
            consolidation_prompt_version, consolidation_model_version,
            request_profile_version,
            stability_class, conf_band, recency_band, belief_status
        )
        VALUES (%s, 0, 'claim', %s, %s, %s, %s, NULL, NULL, %s,
                'preference', '0.6-0.8', '<7d', NULL)
        """,
        (
            session_id,
            bogus_target_id,
            snapshot_id,
            CLAIM_VERSION_TRIPLE["extraction_prompt_version"],
            CLAIM_VERSION_TRIPLE["extraction_model_version"],
            CLAIM_VERSION_TRIPLE["request_profile_version"],
        ),
    )
    resp = client.post(
        f"/sessions/{session_id}/q/1/verdict",
        data={"verdict": "true", "rationale": ""},
        headers=_origin_headers(),
    )
    assert resp.status_code == 200, resp.text
    body = resp.text
    assert "target was not labeled" in body
    assert resp.headers.get("hx-reswap") == "outerHTML"
    # No HX-Redirect: route re-rendered the question with the banner.
    assert resp.headers.get("hx-redirect") is None
    # No gold_labels row was committed.
    rows = conn.execute(
        "SELECT count(*) FROM gold_labels WHERE session_id = %s",
        (session_id,),
    ).fetchone()
    assert rows[0] == 0


def test_post_verdict_404_unknown_session(client: TestClient) -> None:
    fake_id = str(uuid.uuid4())
    resp = client.post(
        f"/sessions/{fake_id}/q/1/verdict",
        data={"verdict": "true", "rationale": ""},
        headers=_origin_headers(),
    )
    assert resp.status_code == 404


def test_post_verdict_404_out_of_range_idx(client: TestClient, conn: Any) -> None:
    session_id, _claim_id, _ = _create_session_with_one_claim(conn, n=3)
    resp = client.post(
        f"/sessions/{session_id}/q/99/verdict",
        data={"verdict": "true", "rationale": ""},
        headers=_origin_headers(),
    )
    assert resp.status_code == 404


def test_post_verdict_422_unknown_verdict(client: TestClient, conn: Any) -> None:
    session_id, _claim_id, _ = _create_session_with_one_claim(conn, n=2)
    resp = client.post(
        f"/sessions/{session_id}/q/1/verdict",
        data={"verdict": "garbage", "rationale": ""},
        headers=_origin_headers(),
    )
    assert resp.status_code == 422
    body = resp.json()
    assert body.get("error") == "unknown verdict"


def test_question_page_uses_shared_false_rationale_prompt(client: TestClient, conn: Any) -> None:
    session_id, _claim_id, _ = _create_session_with_one_claim(conn, n=1)
    resp = client.get(f"/sessions/{session_id}/q/1")
    assert resp.status_code == 200
    assert "what\\u0027s wrong? (e.g., wrong predicate, wrong subject" in resp.text
    assert "correct value > " not in resp.text


def test_question_page_preserves_summary_line_whitespace(client: TestClient, conn: Any) -> None:
    session_id, _claim_id, _ = _create_session_with_one_claim(conn, n=1)
    resp = client.get(f"/sessions/{session_id}/q/1")
    assert resp.status_code == 200
    assert "white-space: pre-wrap" in resp.text


def test_question_hx_request_returns_main_fragment(client: TestClient, conn: Any) -> None:
    session_id, _claim_id, _ = _create_session_with_one_claim(conn, n=1)
    resp = client.get(
        f"/sessions/{session_id}/q/1",
        headers={"HX-Request": "true"},
    )
    assert resp.status_code == 200
    body = resp.text.strip()
    assert body.startswith('<main id="main">')
    assert "<html" not in body
    assert "</body>" not in body
    assert "Engram local" not in body
    assert "local-only · loopback bind" not in body
    assert "help-modal" not in body


def test_post_verdict_403_origin_mismatch(client: TestClient, conn: Any) -> None:
    session_id, _claim_id, _ = _create_session_with_one_claim(conn, n=2)
    resp = client.post(
        f"/sessions/{session_id}/q/1/verdict",
        data={"verdict": "true", "rationale": ""},
        headers={
            "host": "127.0.0.1:8765",
            "origin": "http://evil.example:8765",
            "sec-fetch-site": "same-origin",
        },
    )
    assert resp.status_code == 403
    body = resp.json()
    assert body.get("error") == "origin_mismatch"


def test_post_verdict_requires_origin_header(client: TestClient, conn: Any) -> None:
    session_id, _claim_id, _ = _create_session_with_one_claim(conn, n=2)
    resp = client.post(
        f"/sessions/{session_id}/q/1/verdict",
        data={"verdict": "true", "rationale": ""},
        headers={"host": "127.0.0.1:8765", "sec-fetch-site": "same-origin"},
    )
    assert resp.status_code == 403
    assert resp.json().get("error") == "origin_mismatch"


def test_post_verdict_requires_same_origin_sec_fetch(client: TestClient, conn: Any) -> None:
    session_id, _claim_id, _ = _create_session_with_one_claim(conn, n=2)
    headers = _origin_headers()
    headers.pop("sec-fetch-site")
    resp = client.post(
        f"/sessions/{session_id}/q/1/verdict",
        data={"verdict": "true", "rationale": ""},
        headers=headers,
    )
    assert resp.status_code == 403
    assert resp.json().get("error") == "origin_mismatch"


def test_post_verdict_rejects_allowed_host_on_wrong_port(client: TestClient, conn: Any) -> None:
    session_id, _claim_id, _ = _create_session_with_one_claim(conn, n=2)
    resp = client.post(
        f"/sessions/{session_id}/q/1/verdict",
        data={"verdict": "true", "rationale": ""},
        headers={
            "host": "127.0.0.1:8765",
            "origin": "http://127.0.0.1:9999",
            "sec-fetch-site": "same-origin",
        },
    )
    assert resp.status_code == 403
    assert resp.json().get("error") == "origin_mismatch"


def test_post_verdict_accepts_ipv6_loopback_origin_for_ipv6_bind(conn: Any) -> None:
    app = web_module.create_app(host="::1")

    def _override_get_conn() -> Iterator[Any]:
        yield conn

    app.dependency_overrides[web_module._get_conn] = _override_get_conn
    try:
        with TestClient(app) as ipv6_client:
            session_id, _claim_id, _ = _create_session_with_one_claim(conn, n=2)
            resp = ipv6_client.post(
                f"/sessions/{session_id}/q/1/verdict",
                data={"verdict": "true", "rationale": ""},
                headers=_origin_headers(host="::1"),
            )
    finally:
        app.dependency_overrides.pop(web_module._get_conn, None)

    assert resp.status_code == 200
    assert resp.headers["HX-Redirect"] == f"/sessions/{session_id}/q/2"


def test_post_verdict_rejects_ipv6_origin_when_not_ipv6_bound(
    client: TestClient, conn: Any
) -> None:
    session_id, _claim_id, _ = _create_session_with_one_claim(conn, n=2)
    resp = client.post(
        f"/sessions/{session_id}/q/1/verdict",
        data={"verdict": "true", "rationale": ""},
        headers=_origin_headers(host="::1"),
    )
    assert resp.status_code == 403
    assert resp.json().get("error") == "origin_mismatch"


def test_origin_mismatch_blocks_all_post_routes(client: TestClient, conn: Any) -> None:
    session_id, _claim_id, _ = _create_session_with_one_claim(conn, n=1)
    bad_headers = {
        "host": "127.0.0.1:8765",
        "origin": "http://evil.example:8765",
        "sec-fetch-site": "same-origin",
    }
    checks = [
        ("post", "/sessions", {"n": "1", "seed": "3"}),
        ("post", f"/sessions/{session_id}/save-and-quit", {}),
        ("post", f"/sessions/{session_id}/complete", {}),
        ("post", f"/sessions/{session_id}/abandon", {}),
    ]
    for method, path, data in checks:
        resp = getattr(client, method)(path, data=data, headers=bad_headers)
        assert resp.status_code == 403, path
        assert resp.json().get("error") == "origin_mismatch"


def test_origin_check_delegates_to_shared_helper(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[object, tuple[str, ...]]] = []

    class RequestStub:
        def __init__(self) -> None:
            self.headers: dict[str, str] = {}

    def _fake_require_origin(request: object, *, allowed_hosts: tuple[str, ...]) -> None:
        calls.append((request, allowed_hosts))

    monkeypatch.setattr(web_module, "require_origin", _fake_require_origin)
    request: Any = RequestStub()

    web_module._origin_check(request)

    assert calls == [(request, web_module.ALLOWED_ORIGIN_HOSTS)]


def test_tier_check_delegates_to_shared_helper(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[int, int, str | None]] = []

    def _fake_require_tier_ceiling(
        tier: int, *, ceiling: int, message_id: str | None = None
    ) -> None:
        calls.append((tier, ceiling, message_id))

    monkeypatch.setattr(web_module, "require_tier_ceiling", _fake_require_tier_ceiling)

    web_module._check_tier_1(2, message_id="message-1")

    assert calls == [(2, web_module.TIER_CEILING, "message-1")]


def test_allowed_origin_hosts_default_is_loopback_only() -> None:
    """Default allowlist is the loopback set, no env var set (D081)."""

    import engram.interview.web as web

    # Re-resolve under a clean env to assert the default. This test does not
    # mutate the live ALLOWED_ORIGIN_HOSTS module attribute (other tests rely
    # on whatever it was at import time); it just checks the resolver.
    saved = os.environ.pop("ENGRAM_INTERVIEW_ALLOWED_ORIGINS", None)
    try:
        hosts = web._resolve_allowed_origin_hosts()
        assert hosts == ("127.0.0.1", "localhost")
    finally:
        if saved is not None:
            os.environ["ENGRAM_INTERVIEW_ALLOWED_ORIGINS"] = saved


def test_allowed_origin_hosts_env_var_extends_default(monkeypatch) -> None:
    """ENGRAM_INTERVIEW_ALLOWED_ORIGINS appends operator-trusted hosts (D081)."""
    import engram.interview.web as web

    monkeypatch.setenv(
        "ENGRAM_INTERVIEW_ALLOWED_ORIGINS",
        "100.85.100.81, proximal.tail0ecc2e.ts.net,  ,localhost",
    )
    hosts = web._resolve_allowed_origin_hosts()
    # Defaults preserved, extras appended in order, dedup, whitespace stripped.
    assert hosts == (
        "127.0.0.1",
        "localhost",
        "100.85.100.81",
        "proximal.tail0ecc2e.ts.net",
    )


def test_allowed_origin_hosts_for_ipv6_bind_adds_ipv6_loopback() -> None:
    hosts = web_module._allowed_origin_hosts_for_bind("::1")

    assert hosts[: len(web_module.ALLOWED_ORIGIN_HOSTS)] == web_module.ALLOWED_ORIGIN_HOSTS
    assert "::1" in hosts
    assert web_module._allowed_origin_hosts_for_bind("127.0.0.1") == web_module.ALLOWED_ORIGIN_HOSTS


def test_interview_bench_url_resolver_defaults_and_overrides(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("ENGRAM_INTERVIEW_BENCH_URL", raising=False)
    assert (
        web_module._resolve_bench_review_url()
        == "http://127.0.0.1:8770/segments?remaining=1&reviewable=1"
    )

    monkeypatch.setenv("ENGRAM_INTERVIEW_BENCH_URL", "http://127.0.0.1:9900/segments")
    assert web_module._resolve_bench_review_url() == "http://127.0.0.1:9900/segments"


def test_post_verdict_completes_session_at_n(client: TestClient, conn: Any) -> None:
    session_id, _claim_id, _ = _create_session_with_one_claim(conn, n=2)
    # Answer Q1.
    resp1 = client.post(
        f"/sessions/{session_id}/q/1/verdict",
        data={"verdict": "true"},
        headers=_origin_headers(),
    )
    assert resp1.status_code == 200
    # Answer Q2. The final POST should mark complete inside the guarded
    # verdict transaction; no mutating GET is needed.
    resp2 = client.post(
        f"/sessions/{session_id}/q/2/verdict",
        data={"verdict": "true"},
        headers=_origin_headers(),
    )
    assert resp2.status_code == 200, resp2.text
    redirect = resp2.headers.get("hx-redirect")
    assert redirect == "/"
    completed_at = conn.execute(
        "SELECT completed_at FROM gold_label_sessions WHERE session_id = %s",
        (session_id,),
    ).fetchone()[0]
    assert completed_at is not None


def test_post_verdict_last_idx_first_does_not_complete_session(
    client: TestClient, conn: Any
) -> None:
    session_id, _claim_id, _ = _create_session_with_one_claim(conn, n=2)

    resp = client.post(
        f"/sessions/{session_id}/q/2/verdict",
        data={"verdict": "true"},
        headers=_origin_headers(),
    )
    assert resp.status_code == 200, resp.text
    assert resp.headers.get("hx-redirect") == f"/sessions/{session_id}/q/1"

    completed_at = conn.execute(
        "SELECT completed_at FROM gold_label_sessions WHERE session_id = %s",
        (session_id,),
    ).fetchone()[0]
    assert completed_at is None

    resume_resp = client.get(f"/sessions/{session_id}", follow_redirects=False)
    assert resume_resp.status_code == 303
    assert resume_resp.headers["location"] == f"/sessions/{session_id}/q/1"


def test_completed_session_rejects_resume_question_and_verdict(
    client: TestClient, conn: Any
) -> None:
    session_id, _claim_id, _ = _create_session_with_one_claim(conn, n=1)
    complete_resp = client.post(
        f"/sessions/{session_id}/complete",
        headers=_origin_headers(),
        follow_redirects=False,
    )
    assert complete_resp.status_code == 303

    resume_resp = client.get(f"/sessions/{session_id}", follow_redirects=False)
    assert resume_resp.status_code == 409
    assert resume_resp.json().get("error") == "session_closed"

    question_resp = client.get(f"/sessions/{session_id}/q/1")
    assert question_resp.status_code == 409
    assert question_resp.json().get("error") == "session_closed"

    verdict_resp = client.post(
        f"/sessions/{session_id}/q/1/verdict",
        data={"verdict": "true"},
        headers=_origin_headers(),
    )
    assert verdict_resp.status_code == 409
    assert verdict_resp.json().get("error") == "session_closed"
    n_labels = conn.execute(
        "SELECT count(*) FROM gold_labels WHERE session_id = %s",
        (session_id,),
    ).fetchone()[0]
    assert n_labels == 0


def test_abandoned_session_rejects_question_verdict_complete_and_reabandon(
    client: TestClient, conn: Any
) -> None:
    session_id, _claim_id, _ = _create_session_with_one_claim(conn, n=1)
    abandon_resp = client.post(
        f"/sessions/{session_id}/abandon",
        headers=_origin_headers(),
        follow_redirects=False,
    )
    assert abandon_resp.status_code == 303

    question_resp = client.get(f"/sessions/{session_id}/q/1")
    assert question_resp.status_code == 409
    assert question_resp.json().get("error") == "session_closed"

    verdict_resp = client.post(
        f"/sessions/{session_id}/q/1/verdict",
        data={"verdict": "true"},
        headers=_origin_headers(),
    )
    assert verdict_resp.status_code == 409
    assert verdict_resp.json().get("error") == "session_closed"

    complete_resp = client.post(
        f"/sessions/{session_id}/complete",
        headers=_origin_headers(),
        follow_redirects=False,
    )
    assert complete_resp.status_code == 409

    reabandon_resp = client.post(
        f"/sessions/{session_id}/abandon",
        headers=_origin_headers(),
        follow_redirects=False,
    )
    assert reabandon_resp.status_code == 409


def test_get_complete_is_not_a_mutating_route(client: TestClient, conn: Any) -> None:
    session_id, _claim_id, _ = _create_session_with_one_claim(conn, n=1)
    resp = client.get(f"/sessions/{session_id}/complete", follow_redirects=False)
    assert resp.status_code == 405
    completed_at = conn.execute(
        "SELECT completed_at FROM gold_label_sessions WHERE session_id = %s",
        (session_id,),
    ).fetchone()[0]
    assert completed_at is None


def test_get_messages_tier_1_enforced(client: TestClient, conn: Any) -> None:
    # Seed a reachable tier-2 evidence message and try to render it.
    session_id, _claim_id, msg_ids = _create_session_with_one_claim(conn, n=1, message_tier=2)
    resp = client.get(f"/sessions/{session_id}/messages/{msg_ids[0]}")
    assert resp.status_code == 403
    body = resp.json()
    assert body.get("error") == "privacy_tier_ceiling"
    assert body.get("tier") == 2
    assert body.get("ceiling") == 1


def test_get_messages_context_max_tier_carry(client: TestClient, conn: Any) -> None:
    # Conversation with one tier-2 row in the window.
    conv_id, msg_ids = insert_conversation(
        conn,
        [
            ("user", "ok 1", 1),
            ("user", "ok 2", 1),
            ("user", "secret", 2),
            ("user", "ok 4", 1),
        ],
        conversation_tier=1,
    )
    gen_id = insert_generation(conn, conv_id)
    seg_id = insert_segment_row(conn, gen_id, conv_id, msg_ids, active=True)
    _, claim_id = insert_extracted_claim(
        conn,
        segment_id=seg_id,
        generation_id=gen_id,
        conversation_id=conv_id,
        evidence_ids=[msg_ids[1]],
        predicate="drives",
        object_text="Subaru",
    )
    session_id = insert_session(
        conn,
        seed=1,
        sampler_id="stratified",
        sampler_version="stratified.v1.d079.initial",
        strata_weights={},
    )
    confidence, observed_at = conn.execute(
        "SELECT confidence, extracted_at FROM claims WHERE id = %s",
        (claim_id,),
    ).fetchone()
    conn.execute(
        """
        INSERT INTO gold_label_session_targets (
            session_id, idx, target_kind, target_id,
            candidate_pool_snapshot_id,
            extraction_prompt_version, extraction_model_version,
            consolidation_prompt_version, consolidation_model_version,
            request_profile_version,
            stability_class, conf_band, recency_band, belief_status,
            confidence, observed_at
        )
        VALUES (%s, 0, 'claim', %s, %s, %s, %s, NULL, NULL, %s,
                'preference', '0.6-0.8', '<7d', NULL, %s, %s)
        """,
        (
            session_id,
            claim_id,
            str(uuid.uuid4()),
            CLAIM_VERSION_TRIPLE["extraction_prompt_version"],
            CLAIM_VERSION_TRIPLE["extraction_model_version"],
            CLAIM_VERSION_TRIPLE["request_profile_version"],
            confidence,
            observed_at,
        ),
    )
    # Anchor on msg_ids[1] (tier 1) but the +1 window pulls in msg_ids[2]
    # (tier 2). Context route MUST 403.
    anchor = msg_ids[1]
    resp = client.get(f"/sessions/{session_id}/messages/{anchor}/context?before=0&after=2")
    assert resp.status_code == 403
    body = resp.json()
    assert body.get("error") == "privacy_tier_ceiling"


def test_get_message_unreachable_from_session_returns_404(client: TestClient, conn: Any) -> None:
    session_id, _claim_id, _session_msg_ids = _create_session_with_one_claim(conn, n=1)
    _conv_id, other_msg_ids = insert_conversation(
        conn, [("user", "unrelated tier 1", 1)], conversation_tier=1
    )
    resp = client.get(f"/sessions/{session_id}/messages/{other_msg_ids[0]}")
    assert resp.status_code == 404


def test_get_message_same_conversation_non_evidence_returns_404(
    client: TestClient, conn: Any
) -> None:
    conv_id, msg_ids = insert_conversation(
        conn,
        [
            ("user", "cited evidence", 1),
            ("assistant", "same conversation but not cited", 1),
        ],
        conversation_tier=1,
    )
    gen_id = insert_generation(conn, conv_id)
    seg_id = insert_segment_row(conn, gen_id, conv_id, msg_ids, active=True)
    _, claim_id = insert_extracted_claim(
        conn,
        segment_id=seg_id,
        generation_id=gen_id,
        conversation_id=conv_id,
        evidence_ids=[msg_ids[0]],
        predicate="drives",
        object_text="Subaru",
    )
    session_id = insert_session(
        conn,
        seed=1,
        sampler_id="stratified",
        sampler_version="stratified.v1.d079.initial",
        strata_weights={},
    )
    confidence, observed_at = conn.execute(
        "SELECT confidence, extracted_at FROM claims WHERE id = %s",
        (claim_id,),
    ).fetchone()
    conn.execute(
        """
        INSERT INTO gold_label_session_targets (
            session_id, idx, target_kind, target_id,
            candidate_pool_snapshot_id,
            extraction_prompt_version, extraction_model_version,
            consolidation_prompt_version, consolidation_model_version,
            request_profile_version,
            stability_class, conf_band, recency_band, belief_status,
            confidence, observed_at
        )
        VALUES (%s, 0, 'claim', %s, %s, %s, %s, NULL, NULL, %s,
                'preference', '0.6-0.8', '<7d', NULL, %s, %s)
        """,
        (
            session_id,
            claim_id,
            str(uuid.uuid4()),
            CLAIM_VERSION_TRIPLE["extraction_prompt_version"],
            CLAIM_VERSION_TRIPLE["extraction_model_version"],
            CLAIM_VERSION_TRIPLE["request_profile_version"],
            confidence,
            observed_at,
        ),
    )

    full_resp = client.get(f"/sessions/{session_id}/messages/{msg_ids[1]}")
    assert full_resp.status_code == 404
    context_resp = client.get(f"/sessions/{session_id}/messages/{msg_ids[1]}/context")
    assert context_resp.status_code == 404


def test_get_messages_context_caps(client: TestClient, conn: Any) -> None:
    _conv_id, msg_ids = insert_conversation(conn, [("user", "x", 1)], conversation_tier=1)
    session_id = insert_session(
        conn,
        seed=1,
        sampler_id="stratified",
        sampler_version="stratified.v1.d079.initial",
        strata_weights={},
    )
    resp = client.get(f"/sessions/{session_id}/messages/{msg_ids[0]}/context?before=15&after=15")
    assert resp.status_code == 422


def test_get_evidence_all_tier_1_enforced(client: TestClient, conn: Any) -> None:
    # Seed a session whose target's evidence is tier 2.
    session_id, _claim_id, _ = _create_session_with_one_claim(conn, n=1, message_tier=2)
    resp = client.get(f"/sessions/{session_id}/q/1/evidence/all")
    assert resp.status_code == 403
    body = resp.json()
    assert body.get("error") == "privacy_tier_ceiling"


def test_get_evidence_all_enforces_parent_target_tier(client: TestClient, conn: Any) -> None:
    # Parent belief is Tier 2 while its cited message remains Tier 1.
    session_id, _belief_id = _create_session_with_one_belief(conn, belief_tier=2)
    resp = client.get(f"/sessions/{session_id}/q/1/evidence/all")
    assert resp.status_code == 403
    body = resp.json()
    assert body.get("error") == "privacy_tier_ceiling"
    assert body.get("tier") == 2


def test_get_evidence_all_checks_rows_beyond_preview_limit(client: TestClient, conn: Any) -> None:
    conv_id, msg_ids = insert_conversation(
        conn,
        [
            ("user", "ok 1", 1),
            ("user", "ok 2", 1),
            ("user", "ok 3", 1),
            ("user", "secret 4", 2),
        ],
        conversation_tier=1,
    )
    gen_id = insert_generation(conn, conv_id)
    seg_id = insert_segment_row(conn, gen_id, conv_id, msg_ids, active=True)
    _, claim_id = insert_extracted_claim(
        conn,
        segment_id=seg_id,
        generation_id=gen_id,
        conversation_id=conv_id,
        evidence_ids=msg_ids,
        predicate="drives",
        object_text="Subaru",
    )
    session_id = insert_session(
        conn,
        seed=1,
        sampler_id="stratified",
        sampler_version="stratified.v1.d079.initial",
        strata_weights={},
    )
    confidence, observed_at = conn.execute(
        "SELECT confidence, extracted_at FROM claims WHERE id = %s",
        (claim_id,),
    ).fetchone()
    conn.execute(
        """
        INSERT INTO gold_label_session_targets (
            session_id, idx, target_kind, target_id,
            candidate_pool_snapshot_id,
            extraction_prompt_version, extraction_model_version,
            consolidation_prompt_version, consolidation_model_version,
            request_profile_version,
            stability_class, conf_band, recency_band, belief_status,
            confidence, observed_at
        )
        VALUES (%s, 0, 'claim', %s, %s, %s, %s, NULL, NULL, %s,
                'preference', '0.6-0.8', '<7d', NULL, %s, %s)
        """,
        (
            session_id,
            claim_id,
            str(uuid.uuid4()),
            CLAIM_VERSION_TRIPLE["extraction_prompt_version"],
            CLAIM_VERSION_TRIPLE["extraction_model_version"],
            CLAIM_VERSION_TRIPLE["request_profile_version"],
            confidence,
            observed_at,
        ),
    )
    resp = client.get(f"/sessions/{session_id}/q/1/evidence/all")
    assert resp.status_code == 403
    body = resp.json()
    assert body.get("error") == "privacy_tier_ceiling"


def test_post_save_and_quit_discards_in_progress(client: TestClient, conn: Any) -> None:
    session_id, _claim_id, _ = _create_session_with_one_claim(conn, n=3)
    resp = client.post(
        f"/sessions/{session_id}/save-and-quit",
        headers=_origin_headers(),
        follow_redirects=False,
    )
    assert resp.status_code == 303
    # Banner survives in the redirect URL (URL-encoded).
    from urllib.parse import unquote

    location = unquote(resp.headers["location"])
    assert "Resume with: engram phase3 interview resume" in location
    banner_resp = client.get(resp.headers["location"])
    assert banner_resp.status_code == 200
    assert 'class="banner banner-warn"' in banner_resp.text
    assert "banner-status" not in banner_resp.text
    # No gold_labels row was committed.
    n_labels = conn.execute(
        "SELECT count(*) FROM gold_labels WHERE session_id = %s",
        (session_id,),
    ).fetchone()[0]
    assert n_labels == 0


def test_post_abandon_marks_completed(client: TestClient, conn: Any) -> None:
    session_id, _claim_id, _ = _create_session_with_one_claim(conn, n=3)
    resp = client.post(
        f"/sessions/{session_id}/abandon",
        headers=_origin_headers(),
        follow_redirects=False,
    )
    assert resp.status_code == 303
    row = conn.execute(
        "SELECT completed_at, operator_note FROM gold_label_sessions WHERE session_id = %s",
        (session_id,),
    ).fetchone()
    assert row[0] is not None
    assert row[1] == "abandoned via web"


def test_consolidator_transitions_unimportable_from_web() -> None:
    """No symbol in ``engram.interview.web`` resolves into
    ``engram.consolidator.transitions`` (D044 / D069 invariant)."""
    # Reload to be sure no other test polluted sys.modules with an import
    # path that survives between tests.
    web = importlib.reload(web_module)
    # Iterate public + private module symbols and assert none of them lives
    # in consolidator.transitions.
    for name in dir(web):
        sym = getattr(web, name)
        mod = getattr(sym, "__module__", "")
        if not isinstance(mod, str):
            continue
        assert "consolidator.transitions" not in mod, (
            f"forbidden import bled into engram.interview.web: {name} -> {mod}"
        )


def test_htmx_loaded_from_static_not_cdn(client: TestClient, conn: Any) -> None:
    """The base layout must reference ``/static/htmx.min.js``, not a CDN."""
    static_path = Path(web_module.__file__).resolve().parent / "static" / "htmx.min.js"
    if not static_path.exists() or static_path.stat().st_size == 0:
        pytest.skip("static/htmx.min.js missing or empty; operator must drop in a copy")
    resp = client.get("/")
    assert resp.status_code == 200
    body = resp.text
    assert '<script src="/static/htmx.min.js"' in body
    assert '<script src="/shared-static/keyboard.js" defer></script>' in body
    assert "unpkg.com" not in body
    assert "cdn.jsdelivr.net" not in body
    assert "cdnjs.cloudflare.com" not in body
    assert "googleapis.com" not in body
    assert "googletagmanager.com" not in body
    assert "@import" not in body
    # Static asset is actually served.
    asset = client.get("/static/htmx.min.js")
    assert asset.status_code == 200
    assert asset.text.strip() != ""
    keyboard = client.get("/shared-static/keyboard.js")
    assert keyboard.status_code == 200
    assert "data-help-open" in keyboard.text


def test_question_local_only_no_external_assets(client: TestClient, conn: Any) -> None:
    session_id, _claim_id, _ = _create_session_with_one_claim(conn, n=1)
    resp = client.get(f"/sessions/{session_id}/q/1")
    assert resp.status_code == 200
    body = resp.text
    assert "local-only · loopback bind: 127.0.0.1:8765 · no network egress." in body
    for forbidden in (
        "unpkg.com",
        "cdn.jsdelivr.net",
        "cdnjs.cloudflare.com",
        "googleapis.com",
        "googletagmanager.com",
        "@import",
    ):
        assert forbidden not in body


def test_interview_page_has_no_promotion_affordance_buttons(client: TestClient, conn: Any) -> None:
    session_id, _claim_id, _ = _create_session_with_one_claim(conn, n=1)
    for path in ("/", f"/sessions/{session_id}/q/1"):
        resp = client.get(path)
        assert resp.status_code == 200
        body = resp.text.lower()
        for button_word in (
            ">accept<",
            ">promote<",
            ">reject<",
            ">pin<",
            'data-action="accept"',
            'data-action="promote"',
            'data-action="reject"',
            'data-action="pin"',
        ):
            assert button_word not in body


def test_aria_live_region_present(client: TestClient, conn: Any) -> None:
    session_id, _claim_id, _ = _create_session_with_one_claim(conn, n=2)
    resp = client.get(f"/sessions/{session_id}/q/1")
    assert resp.status_code == 200
    assert 'aria-live="polite"' in resp.text
