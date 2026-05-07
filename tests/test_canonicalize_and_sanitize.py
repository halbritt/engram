"""Pure-function tests for the embedding-stability and LLM-trust-boundary helpers.

Covers RFC 0015 gaps 2 and 3:

- ``canonicalize_embeddable_text`` — the function that decides what bytes get
  hashed and embedded. A silent change here invalidates the embedding cache,
  so this test locks current behavior.
- ``sanitize_model_string`` / ``sanitize_model_json`` /
  ``sanitize_segment_draft`` — the trust boundary for LLM output. The actual
  scope of these helpers is narrower than RFC 0015 §3 hypothesizes: they only
  replace invalid UTF-8 surrogates (so the result encodes cleanly to bytes),
  they do not strip control characters, truncate, or validate the
  ``SegmentDraft`` schema. Schema validation lives upstream in
  ``parse_segment_payload`` (segmenter.py:~420) and is not the contract of the
  ``sanitize_*`` family.

These tests do not use the ``conn`` fixture — they exercise pure functions and
must run without a database.
"""

from __future__ import annotations

import pytest

from engram.segmenter import (
    SegmentDraft,
    canonicalize_embeddable_text,
    sanitize_model_json,
    sanitize_model_string,
    sanitize_segment_draft,
)


# ---------------------------------------------------------------------------
# canonicalize_embeddable_text
# ---------------------------------------------------------------------------
#
# Behavior, locked by inspecting segmenter.py:1673:
#   1. Splits on lines.
#   2. Drops lines that match MARKER_ONLY_RE (image_asset_pointer, tool_use,
#      tool_result, attachment, audio, video, file, input_image, output_image,
#      computer_call(_output), reasoning, "[tool artifact omitted ...]", and
#      <|...|> special-token markers).
#   3. ``rstrip``s each kept line (so trailing spaces and tabs go) but does
#      NOT lstrip — leading whitespace inside a line is preserved.
#   4. Joins with "\n", then collapses runs of 3+ "\n" to exactly 2.
#   5. ``strip``s the whole result (so leading/trailing blank lines and
#      spaces are removed at the document edges).
#
# Things this function does NOT do, surfaced as findings:
#   - It does not collapse internal multi-space runs ("a   b" stays "a   b").
#   - It does not collapse tabs into spaces.
#   - It does not strip control characters (e.g. \x07).
#   - It does not normalize unicode (NFC/NFD/fullwidth digits pass through).
#   - It does not strip code fences (```...``` survives).


@pytest.mark.parametrize(
    "label,raw,expected",
    [
        ("trims_outer_whitespace", "  hello  ", "hello"),
        ("empty_string", "", ""),
        ("whitespace_only", "   ", ""),
        ("preserves_internal_multi_space", "hello   world", "hello   world"),
        ("preserves_tab_in_middle", "hello \t world", "hello \t world"),
        ("rstrips_each_line", "trailing   \nspaces", "trailing\nspaces"),
        ("rstrips_but_does_not_lstrip", "  hello  \n  world  ", "hello\n  world"),
        ("preserves_double_newline", "line1\n\nline2", "line1\n\nline2"),
        ("collapses_three_newlines", "line1\n\n\nline2", "line1\n\nline2"),
        ("collapses_four_newlines", "line1\n\n\n\nline2", "line1\n\nline2"),
        ("simple_lines_unchanged", "a\nb\nc", "a\nb\nc"),
        ("drops_image_asset_pointer_marker", "[image_asset_pointer]\nbody", "body"),
        ("drops_tool_use_marker", "[tool_use]\nbody", "body"),
        ("drops_tool_artifact_omitted", "[tool artifact omitted: chars=10]\nhello", "hello"),
        ("drops_special_token_marker", "<|endoftext|>\nbody", "body"),
        ("drops_marker_in_middle", "first\n[image]\nsecond", "first\nsecond"),
        ("preserves_precomposed_unicode", "café", "café"),
        # NFD form: 'cafe' + combining acute U+0301. Unicode normalization is
        # not performed, so the decomposed sequence passes through untouched.
        ("preserves_decomposed_unicode", "café", "café"),
        ("preserves_fullwidth_digits", "１２３", "１２３"),
        ("preserves_control_char_bell", "hello\x07world", "hello\x07world"),
        ("preserves_code_fence", "```python\ncode\n```", "```python\ncode\n```"),
        (
            "kitchen_sink",
            "   \n[image]\n  hello  \n\n\n[tool_use]\nworld   ",
            "hello\n\nworld",
        ),
    ],
)
def test_canonicalize_embeddable_text_locks_output(
    label: str, raw: str, expected: str
) -> None:
    assert canonicalize_embeddable_text(raw) == expected


# ---------------------------------------------------------------------------
# sanitize_model_string
# ---------------------------------------------------------------------------
#
# Contract (segmenter.py:458): returns ``(sanitized_value, was_changed)``.
# ``None`` passes through. A string that already encodes to UTF-8 cleanly is
# returned unchanged with ``was_changed=False``. A string containing lone
# surrogates is round-tripped through ``encode("utf-8", "replace")`` so that
# every offending code point becomes ``"?"`` and ``was_changed=True``.
#
# Things this function does NOT do (locked here so a future "stricter"
# implementation has to update tests deliberately):
#   - It does not strip ASCII control characters.
#   - It does not truncate long strings.
#   - It does not coerce non-strings; passing a non-string is undefined and
#     not part of this test surface.


def test_sanitize_model_string_passes_through_plain_string() -> None:
    assert sanitize_model_string("hello world") == ("hello world", False)


def test_sanitize_model_string_passes_through_none() -> None:
    assert sanitize_model_string(None) == (None, False)


def test_sanitize_model_string_passes_through_empty_string() -> None:
    assert sanitize_model_string("") == ("", False)


def test_sanitize_model_string_does_not_strip_control_characters() -> None:
    # \x00 and \x01 are valid UTF-8 sequences, so the encode check succeeds
    # and the string is returned unchanged. This locks current behavior; a
    # future hardening that strips controls would need to update this test.
    assert sanitize_model_string("hello\x00\x01world") == ("hello\x00\x01world", False)


def test_sanitize_model_string_replaces_lone_surrogate() -> None:
    sanitized, changed = sanitize_model_string("\udc80hello")
    assert changed is True
    assert "\udc80" not in sanitized
    # The replacement codec emits "?" per offending code point.
    assert sanitized == "?hello"


def test_sanitize_model_string_does_not_truncate_long_strings() -> None:
    long = "x" * 10_000
    assert sanitize_model_string(long) == (long, False)


# ---------------------------------------------------------------------------
# sanitize_model_json
# ---------------------------------------------------------------------------
#
# Contract (segmenter.py:483): walks dict / list / str recursively and applies
# ``sanitize_model_string`` to every string-valued leaf and to every dict key
# (after coercing the key to ``str`` via ``str(key)``). Returns
# ``(sanitized, was_changed)``. Non-container, non-string scalars pass
# through unchanged with ``was_changed=False``.
#
# This is NOT a JSON parser. It does not accept a JSON-text string and parse
# it. It does not raise on malformed input — it accepts anything Python can
# hold and only inspects strings inside containers. RFC 0015 §3's framing
# ("Valid JSON parses correctly. Malformed JSON raises ...") describes a
# parser that does not exist in segmenter.py; tests here lock the actual
# walker behavior.


def test_sanitize_model_json_string_leaf_clean() -> None:
    assert sanitize_model_json("hello") == ("hello", False)


def test_sanitize_model_json_string_leaf_with_surrogate() -> None:
    sanitized, changed = sanitize_model_json("\udc80x")
    assert changed is True
    assert sanitized == "?x"


def test_sanitize_model_json_scalar_non_string_passes_through() -> None:
    assert sanitize_model_json(42) == (42, False)
    assert sanitize_model_json(True) == (True, False)
    assert sanitize_model_json(None) == (None, False)


def test_sanitize_model_json_empty_containers() -> None:
    assert sanitize_model_json([]) == ([], False)
    assert sanitize_model_json({}) == ({}, False)


def test_sanitize_model_json_nested_clean_structure() -> None:
    payload = {"a": [1, 2, {"b": "c"}]}
    sanitized, changed = sanitize_model_json(payload)
    assert changed is False
    assert sanitized == payload


def test_sanitize_model_json_nested_surrogate_propagates_changed_flag() -> None:
    payload = {"k": ["x", "\udc80y", {"kk": "z"}]}
    sanitized, changed = sanitize_model_json(payload)
    assert changed is True
    assert sanitized == {"k": ["x", "?y", {"kk": "z"}]}


def test_sanitize_model_json_surrogate_in_dict_key_is_replaced() -> None:
    payload = {"\udc80k": "v"}
    sanitized, changed = sanitize_model_json(payload)
    assert changed is True
    assert sanitized == {"?k": "v"}


def test_sanitize_model_json_coerces_non_string_dict_key_to_string() -> None:
    sanitized, changed = sanitize_model_json({1: "v"})
    # Integer key is not "changed" by surrogate replacement (no surrogates),
    # but it IS coerced into a string key by ``str(key)``.
    assert changed is False
    assert sanitized == {"1": "v"}


# ---------------------------------------------------------------------------
# sanitize_segment_draft
# ---------------------------------------------------------------------------
#
# Contract (segmenter.py:468): takes a ``SegmentDraft`` and returns a new
# ``SegmentDraft`` whose ``summary``, ``content_text``, and ``raw`` fields
# have been passed through ``sanitize_model_string`` / ``sanitize_model_json``.
# If any field was sanitized, ``raw`` is replaced with a copy that has
# ``"invalid_utf8_surrogates_replaced": True`` set; otherwise ``raw`` is
# passed through unchanged.
#
# Things this function does NOT do, surfaced as findings:
#   - It does not validate ``message_ids`` (non-empty, str-only). Callers are
#     expected to validate the draft schema upstream — see
#     ``parse_segment_payload`` at segmenter.py:~420 which raises
#     ``SegmentationError`` on bad shapes BEFORE calling sanitize.
#   - It does not check for required fields. ``SegmentDraft`` is a frozen
#     dataclass, so missing-field cases raise ``TypeError`` at construction
#     time — not the responsibility of this function.
#   - It does not enforce a length cap on ``summary`` or ``content_text``.
#   - It does not reject extra keys in ``raw`` (and could not — ``raw`` is
#     ``dict[str, Any]`` by contract).


def _draft(
    *,
    message_ids: list[str] | None = None,
    summary: str | None = "topic",
    content_text: str = "body",
    raw: dict | None = None,
) -> SegmentDraft:
    return SegmentDraft(
        message_ids=message_ids if message_ids is not None else ["m1"],
        summary=summary,
        content_text=content_text,
        raw=raw if raw is not None else {"k": "v"},
    )


def test_sanitize_segment_draft_clean_passes_through_unchanged() -> None:
    draft = _draft()
    out = sanitize_segment_draft(draft)
    assert out == draft
    # No marker should be added when nothing was sanitized.
    assert "invalid_utf8_surrogates_replaced" not in out.raw


def test_sanitize_segment_draft_replaces_surrogate_in_summary() -> None:
    out = sanitize_segment_draft(_draft(summary="\udc80bad"))
    assert out.summary == "?bad"
    assert out.raw.get("invalid_utf8_surrogates_replaced") is True


def test_sanitize_segment_draft_replaces_surrogate_in_content_text() -> None:
    out = sanitize_segment_draft(_draft(content_text="\udc80body"))
    assert out.content_text == "?body"
    assert out.raw.get("invalid_utf8_surrogates_replaced") is True


def test_sanitize_segment_draft_replaces_surrogate_in_raw_key() -> None:
    out = sanitize_segment_draft(_draft(raw={"\udc80k": "v"}))
    assert "?k" in out.raw
    assert out.raw["?k"] == "v"
    assert out.raw.get("invalid_utf8_surrogates_replaced") is True


def test_sanitize_segment_draft_preserves_none_summary() -> None:
    # ``summary`` is ``str | None`` in SegmentDraft; sanitize_model_string
    # passes ``None`` through, so the marker should NOT be set.
    out = sanitize_segment_draft(_draft(summary=None, raw={}))
    assert out.summary is None
    assert "invalid_utf8_surrogates_replaced" not in out.raw


def test_sanitize_segment_draft_does_not_validate_message_ids() -> None:
    # An empty message_ids list is structurally invalid for downstream
    # consumers but ``sanitize_segment_draft`` does NOT police it. This
    # locks the function's narrow scope: schema validation is upstream.
    out = sanitize_segment_draft(_draft(message_ids=[]))
    assert out.message_ids == []


def test_sanitize_segment_draft_does_not_truncate_oversized_fields() -> None:
    huge_summary = "s" * 100_000
    huge_content = "c" * 100_000
    out = sanitize_segment_draft(_draft(summary=huge_summary, content_text=huge_content))
    assert out.summary == huge_summary
    assert out.content_text == huge_content


def test_sanitize_segment_draft_returns_new_instance_when_sanitizing() -> None:
    # Verify the function does not mutate the original raw dict in place when
    # the marker is added. The original frozen dataclass remains as-is.
    original_raw: dict = {"k": "v"}
    draft = _draft(summary="\udc80x", raw=original_raw)
    out = sanitize_segment_draft(draft)
    assert "invalid_utf8_surrogates_replaced" in out.raw
    # Original dict object should not have been mutated.
    assert "invalid_utf8_surrogates_replaced" not in original_raw
