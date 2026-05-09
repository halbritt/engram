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
import sys
import uuid
from contextlib import contextmanager
from collections.abc import Iterator
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from psycopg import errors
from psycopg.types.json import Jsonb

from engram.consolidator import CONSOLIDATOR_MODEL_VERSION, CONSOLIDATOR_PROMPT_VERSION
from engram.consolidator.transitions import BeliefPayload, insert_belief
from engram.extractor import EXTRACTION_PROMPT_VERSION, EXTRACTION_REQUEST_PROFILE_VERSION
from engram.interview import web as web_module
from engram.interview.storage import (
    insert_label,
    insert_session,
    mark_session_completed,
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


def _seed_claim(conn: Any, *, message_tier: int = 1) -> tuple[str, list[str]]:
    """Return ``(claim_id, message_ids)``."""
    conv_id, msg_ids = insert_conversation(
        conn, [("user", "I drive a Subaru", message_tier)]
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
    return claim_id, msg_ids


def _seed_belief(conn: Any) -> str:
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
        valid_from=datetime.now(timezone.utc),
        valid_to=None,
        observed_at=datetime.now(timezone.utc),
        extracted_at=datetime.now(timezone.utc),
        status="candidate",
        confidence=0.7,
        evidence_ids=[msg_ids[0]],
        claim_ids=[claim_id],
        prompt_version=BELIEF_VERSION_TRIPLE["consolidation_prompt_version"],
        model_version=BELIEF_VERSION_TRIPLE["consolidation_model_version"],
        privacy_tier=1,
        raw_payload={"source": "rfc0027-web-test"},
        score_breakdown={
            "mean": 0.7, "max": 0.7, "min": 0.7, "count": 1, "stddev": 0,
        },
    )
    return insert_belief(conn, payload)


def _create_session_with_one_claim(
    conn: Any, *, n: int = 3, message_tier: int = 1
) -> tuple[str, str, list[str]]:
    """Create a fresh session row + one materialized claim target at idx=0.

    Returns ``(session_id, claim_id, message_ids)``.
    """
    claim_id, msg_ids = _seed_claim(conn, message_tier=message_tier)
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
            VALUES (
                %s, %s, 'claim', %s,
                %s,
                %s, %s,
                NULL, NULL,
                %s,
                'preference', '0.6-0.8', '<7d', NULL
            )
            """,
            (
                session_id, idx, cid, snapshot_id,
                CLAIM_VERSION_TRIPLE["extraction_prompt_version"],
                CLAIM_VERSION_TRIPLE["extraction_model_version"],
                CLAIM_VERSION_TRIPLE["request_profile_version"],
            ),
        )
    return session_id, claim_id, msg_ids


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


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_index_renders_no_open_sessions(client: TestClient) -> None:
    resp = client.get("/")
    assert resp.status_code == 200
    body = resp.text
    assert "Engram interview — open sessions" in body
    assert "No open sessions" in body


def test_index_renders_open_sessions_with_progress(
    client: TestClient, conn: Any
) -> None:
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
        asked_at=datetime.now(timezone.utc),
        answered_at=datetime.now(timezone.utc),
    )
    resp = client.get("/")
    assert resp.status_code == 200
    body = resp.text
    assert "1/3 answered" in body
    assert session_id in body


def test_post_sessions_redirects_to_q1(
    client: TestClient, conn: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Seed at least one claim so the sampler returns something.
    _seed_claim(conn)
    resp = client.post(
        "/sessions",
        data={"n": 1, "seed": 7},
        headers={"origin": "http://127.0.0.1:8765"},
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


def test_post_sessions_empty_corpus_renders_diagnostic(
    client: TestClient, conn: Any
) -> None:
    # No claims/beliefs seeded, so sampler returns [].
    resp = client.post(
        "/sessions",
        data={"n": 5, "seed": 7},
        headers={"origin": "http://127.0.0.1:8765"},
        follow_redirects=False,
    )
    assert resp.status_code == 200, resp.text
    body = resp.text
    assert "no targets matched" in body
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
    # Six verdict buttons present.
    for v in ("true", "false", "stale", "unsupported", "unsure", "skip"):
        assert f'data-verdict="{v}"' in body
    # Accesskeys: t, f, s, n, u, k.
    for letter in ("t", "f", "s", "n", "u", "k"):
        assert f'accesskey="{letter}"' in body
    # aria-label carries verdict gloss verbatim from the vocabulary table.
    rows = conn.execute(
        "SELECT verdict, gloss FROM gold_label_verdict_vocabulary"
    ).fetchall()
    for verdict, gloss in rows:
        assert gloss in body, f"missing gloss for {verdict}"


def test_post_verdict_true_single_click_commit(
    client: TestClient, conn: Any
) -> None:
    session_id, _claim_id, _ = _create_session_with_one_claim(conn, n=3)
    resp = client.post(
        f"/sessions/{session_id}/q/1/verdict",
        data={"verdict": "true", "rationale": ""},
        headers={"origin": "http://127.0.0.1:8765"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.headers.get("hx-redirect") == f"/sessions/{session_id}/q/2"
    rows = conn.execute(
        "SELECT verdict, rationale, evidence_excerpt FROM gold_labels "
        "WHERE session_id = %s",
        (session_id,),
    ).fetchall()
    assert len(rows) == 1
    assert rows[0][0] == "true"
    assert rows[0][1] is None
    assert rows[0][2] is None


def test_post_verdict_skip_single_click_commit(
    client: TestClient, conn: Any
) -> None:
    session_id, _claim_id, _ = _create_session_with_one_claim(conn, n=2)
    resp = client.post(
        f"/sessions/{session_id}/q/1/verdict",
        data={"verdict": "skip", "rationale": ""},
        headers={"origin": "http://127.0.0.1:8765"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.headers.get("hx-redirect") == f"/sessions/{session_id}/q/2"
    row = conn.execute(
        "SELECT verdict, rationale FROM gold_labels WHERE session_id = %s",
        (session_id,),
    ).fetchone()
    assert row == ("skip", None)


def test_post_verdict_false_two_click_flow(
    client: TestClient, conn: Any
) -> None:
    session_id, _claim_id, _ = _create_session_with_one_claim(conn, n=3)
    resp = client.post(
        f"/sessions/{session_id}/q/1/verdict",
        data={"verdict": "false", "rationale": "correct value text"},
        headers={"origin": "http://127.0.0.1:8765"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.headers.get("hx-redirect", "").endswith("/q/2")
    row = conn.execute(
        "SELECT verdict, rationale FROM gold_labels WHERE session_id = %s",
        (session_id,),
    ).fetchone()
    assert row == ("false", "correct value text")


def test_post_verdict_trigger_rejection_renders_banner(
    client: TestClient, conn: Any
) -> None:
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
            session_id, bogus_target_id, snapshot_id,
            CLAIM_VERSION_TRIPLE["extraction_prompt_version"],
            CLAIM_VERSION_TRIPLE["extraction_model_version"],
            CLAIM_VERSION_TRIPLE["request_profile_version"],
        ),
    )
    resp = client.post(
        f"/sessions/{session_id}/q/1/verdict",
        data={"verdict": "true", "rationale": ""},
        headers={"origin": "http://127.0.0.1:8765"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.text
    assert "target was not labeled" in body
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
        headers={"origin": "http://127.0.0.1:8765"},
    )
    assert resp.status_code == 404


def test_post_verdict_404_out_of_range_idx(
    client: TestClient, conn: Any
) -> None:
    session_id, _claim_id, _ = _create_session_with_one_claim(conn, n=3)
    resp = client.post(
        f"/sessions/{session_id}/q/99/verdict",
        data={"verdict": "true", "rationale": ""},
        headers={"origin": "http://127.0.0.1:8765"},
    )
    assert resp.status_code == 404


def test_post_verdict_422_unknown_verdict(
    client: TestClient, conn: Any
) -> None:
    session_id, _claim_id, _ = _create_session_with_one_claim(conn, n=2)
    resp = client.post(
        f"/sessions/{session_id}/q/1/verdict",
        data={"verdict": "garbage", "rationale": ""},
        headers={"origin": "http://127.0.0.1:8765"},
    )
    assert resp.status_code == 422
    body = resp.json()
    assert body.get("error") == "unknown verdict"


def test_post_verdict_403_origin_mismatch(
    client: TestClient, conn: Any
) -> None:
    session_id, _claim_id, _ = _create_session_with_one_claim(conn, n=2)
    resp = client.post(
        f"/sessions/{session_id}/q/1/verdict",
        data={"verdict": "true", "rationale": ""},
        headers={"origin": "http://evil.example"},
    )
    assert resp.status_code == 403
    body = resp.json()
    assert body.get("error") == "origin_mismatch"


def test_post_verdict_completes_session_at_n(
    client: TestClient, conn: Any
) -> None:
    session_id, _claim_id, _ = _create_session_with_one_claim(conn, n=2)
    # Answer Q1.
    resp1 = client.post(
        f"/sessions/{session_id}/q/1/verdict",
        data={"verdict": "true"},
        headers={"origin": "http://127.0.0.1:8765"},
    )
    assert resp1.status_code == 200
    # Answer Q2 — should HX-Redirect to /complete.
    resp2 = client.post(
        f"/sessions/{session_id}/q/2/verdict",
        data={"verdict": "true"},
        headers={"origin": "http://127.0.0.1:8765"},
    )
    assert resp2.status_code == 200, resp2.text
    redirect = resp2.headers.get("hx-redirect")
    assert redirect == f"/sessions/{session_id}/complete"
    # Hit the /complete URL to actually mark it completed (the GET path
    # mirrors the POST behavior so htmx redirects work).
    resp3 = client.get(
        f"/sessions/{session_id}/complete", follow_redirects=False
    )
    assert resp3.status_code == 303
    completed_at = conn.execute(
        "SELECT completed_at FROM gold_label_sessions WHERE session_id = %s",
        (session_id,),
    ).fetchone()[0]
    assert completed_at is not None


def test_get_messages_tier_1_enforced(client: TestClient, conn: Any) -> None:
    # Seed a tier-2 message and try to render it.
    conv_id, msg_ids = insert_conversation(
        conn, [("user", "tier-2 secret", 2)], conversation_tier=1
    )
    session_id = insert_session(
        conn,
        seed=1,
        sampler_id="stratified",
        sampler_version="stratified.v1.d079.initial",
        strata_weights={},
    )
    resp = client.get(f"/sessions/{session_id}/messages/{msg_ids[0]}")
    assert resp.status_code == 403
    body = resp.json()
    assert body.get("error") == "privacy_tier_ceiling"
    assert body.get("tier") == 2
    assert body.get("ceiling") == 1


def test_get_messages_context_max_tier_carry(
    client: TestClient, conn: Any
) -> None:
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
    session_id = insert_session(
        conn,
        seed=1,
        sampler_id="stratified",
        sampler_version="stratified.v1.d079.initial",
        strata_weights={},
    )
    # Anchor on msg_ids[1] (tier 1) but the +1 window pulls in msg_ids[2]
    # (tier 2). Context route MUST 403.
    anchor = msg_ids[1]
    resp = client.get(
        f"/sessions/{session_id}/messages/{anchor}/context?before=0&after=2"
    )
    assert resp.status_code == 403
    body = resp.json()
    assert body.get("error") == "privacy_tier_ceiling"


def test_get_messages_context_caps(
    client: TestClient, conn: Any
) -> None:
    conv_id, msg_ids = insert_conversation(
        conn, [("user", "x", 1)], conversation_tier=1
    )
    session_id = insert_session(
        conn,
        seed=1,
        sampler_id="stratified",
        sampler_version="stratified.v1.d079.initial",
        strata_weights={},
    )
    resp = client.get(
        f"/sessions/{session_id}/messages/{msg_ids[0]}/context?before=15&after=15"
    )
    assert resp.status_code == 422


def test_get_evidence_all_tier_1_enforced(
    client: TestClient, conn: Any
) -> None:
    # Seed a session whose target's evidence is tier 2.
    session_id, _claim_id, _ = _create_session_with_one_claim(
        conn, n=1, message_tier=2
    )
    resp = client.get(f"/sessions/{session_id}/q/1/evidence/all")
    assert resp.status_code == 403
    body = resp.json()
    assert body.get("error") == "privacy_tier_ceiling"


def test_post_save_and_quit_discards_in_progress(
    client: TestClient, conn: Any
) -> None:
    session_id, _claim_id, _ = _create_session_with_one_claim(conn, n=3)
    resp = client.post(
        f"/sessions/{session_id}/save-and-quit",
        headers={"origin": "http://127.0.0.1:8765"},
        follow_redirects=False,
    )
    assert resp.status_code == 303
    # Banner survives in the redirect URL (URL-encoded).
    from urllib.parse import unquote
    location = unquote(resp.headers["location"])
    assert "Resume with: engram phase3 interview resume" in location
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
        headers={"origin": "http://127.0.0.1:8765"},
        follow_redirects=False,
    )
    assert resp.status_code == 303
    row = conn.execute(
        "SELECT completed_at, operator_note FROM gold_label_sessions "
        "WHERE session_id = %s",
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
    static_path = (
        Path(web_module.__file__).resolve().parent / "static" / "htmx.min.js"
    )
    if not static_path.exists() or static_path.stat().st_size == 0:
        pytest.skip(
            "static/htmx.min.js missing or empty; operator must drop in a copy"
        )
    resp = client.get("/")
    assert resp.status_code == 200
    body = resp.text
    assert '<script src="/static/htmx.min.js"' in body
    assert "unpkg.com" not in body
    assert "cdn.jsdelivr.net" not in body
    assert "cdnjs.cloudflare.com" not in body
    # Static asset is actually served.
    asset = client.get("/static/htmx.min.js")
    assert asset.status_code == 200
    assert asset.text.strip() != ""


def test_aria_live_region_present(client: TestClient, conn: Any) -> None:
    session_id, _claim_id, _ = _create_session_with_one_claim(conn, n=2)
    resp = client.get(f"/sessions/{session_id}/q/1")
    assert resp.status_code == 200
    assert 'aria-live="polite"' in resp.text
